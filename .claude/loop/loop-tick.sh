#!/bin/bash
# Loop Tick — the bash-level heartbeat (Ralph-style)
# Runs one orchestrator invocation. Exits. Cron fires again later.
#
# Usage:
#   bash .claude/loop/loop-tick.sh
#   bash .claude/loop/loop-tick.sh --dry-run
#   bash .claude/loop/loop-tick.sh --cost-cap 5 --max-runtime 30
#
# Inspired by:
#   - snarktank/ralph (21.7k⭐) — completion promise pattern
#   - mikeyobrien/ralph-orchestrator (3.1k⭐) — spend limits + circuit breaker
#   - ghuntley/how-to-ralph-wiggum — 3 Phases, 2 Prompts, 1 Loop
#
# This is the BASH loop. Inside, it invokes the Claude Code agent (orchestrator).
#
# === Windows Quirks (Git Bash / MINGW64 / MSYS2) ===
# - Use `python` (not `python.exe`) in Git Bash; PYTHON env var is honored.
# - `date -u +%Y-%m-%dT%H:%M:%SZ` works on both Git Bash and POSIX.
# - `timeout` is from GNU coreutils (installed with Git); if missing use
#   `gtimeout` from coreutils package or the Windows `timeout.exe` fallback.
# - subprocesses (e.g. Python scripts) inherit the Git Bash PATH which includes
#   `/usr/bin` and `/bin` but may lack Windows system32 paths; use absolute
#   paths or `shutil.which()` in Python to locate executables.
# - Windows filesystem locking: worktree removal may need `git worktree remove
#   --force` if a process holds a handle; the merge protocol catches this.
# - Do NOT use `bc` for arithmetic — not installed on Windows Git Bash by
#   default; use `awk` or Python arithmetic as shown in cost-guard below.
# - On Windows, `set -euo pipefail` combined with pipefail can cause
#   unexpected exits; guard `$()` subshells with `|| true` where noted.

set -euo pipefail

# Defaults
COST_CAP_USD=5
MAX_RUNTIME_MIN=30
DRY_RUN=false
GRAPH_NAME=""
AUTO_CLEANUP=false
LOG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/logs"
# TICK_VERDICT: set per-exit-path (PASS/FAIL/NEEDS_FIX/BLOCKED/OVERRUN/BUDGET_ABORT)
# Consumed by notify_hook (M8 EXIT trap) to pick the right notify --reason.
# Empty until the first exit path assigns it (notify_hook treats empty + exit 0
# as no-op; empty + exit non-zero falls back to tick_error reason).
TICK_VERDICT=""
PROGRESS_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/progress.md"
TASKS_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tasks.md"
LOOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Absolute repo root (parent of .claude/). Set once at the top so the
# --graph dispatch block can reference it (was unbound before, breaking
# dry-run with `set -euo pipefail`).
PROJECT_ROOT="$(cd "$LOOP_DIR/../.." && pwd)"

# Honor $PYTHON env var (default: "python"). WSL2 subprocesses (e.g. pytest
# running tests) often lack `python` on PATH — only `python.exe` resolves.
# Production cron inherits the user's PATH which has `python`; tests set
# PYTHON=/mnt/c/Python314/python.exe explicitly.
PYTHON="${PYTHON:-python}"

# Valid graph keys for --graph dispatch (must match langgraph.json registry)
VALID_GRAPH_KEYS="pae_maintainer ikigai_maintainer_v2 ikigai_fork_smoke"

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --cost-cap) COST_CAP_USD="$2"; shift 2 ;;
    --max-runtime) MAX_RUNTIME_MIN="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --graph) GRAPH_NAME="$2"; shift 2 ;;
    --auto-cleanup) AUTO_CLEANUP=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# Validate --graph value (fail-fast before any other work)
if [ -n "$GRAPH_NAME" ]; then
  case " $VALID_GRAPH_KEYS " in
    *" $GRAPH_NAME "*) ;;
    *) echo "Unknown graph: $GRAPH_NAME (valid: $VALID_GRAPH_KEYS)" >&2; exit 2 ;;
  esac
fi

mkdir -p "$LOG_DIR"

# Timestamp for this tick
TICK_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TICK_ID=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/tick-$TICK_ID.log"

# --- AUTO-CLEANUP HOOK (M6 acceptance criterion #4) ---
# When --auto-cleanup is set, run worktree-helper.sh cleanup-all at tick end
# IF tasks.md has zero `status: pending` lines. Otherwise log skip reason.
# Registered as an EXIT trap so it runs on every exit path (graph-dispatch,
# cost abort, dry-run, overrun, normal tick) without leaking worktrees.
# Default off (opt-in for safety) — when off, behavior is unchanged.
auto_cleanup_hook() {
  if [ "$AUTO_CLEANUP" != "true" ]; then
    return 0
  fi
  local HELPER="$PROJECT_ROOT/scripts/worktree-helper.sh"
  if [ ! -x "$HELPER" ]; then
    echo "[$TICK_TS] AUTO-CLEANUP: skipped (helper not executable: $HELPER)" | tee -a "$LOG_FILE"
    return 0
  fi
  # Count PENDING tasks. `grep -c` exits 1 when zero matches — guard with
  # `|| true` so `set -euo pipefail` does not abort the script on a
  # freshly-completed tasks.md (all status=done, no pending). Then strip
  # trailing newline + coerce non-numeric output (e.g. empty after grep
  # fails) to "0" before integer compare. Without the head -n1 + tr dance,
  # the `|| echo 0` fallback appends a second line that breaks `[ -eq 0 ]`.
  local PENDING_COUNT
  PENDING_COUNT=$(grep -c 'status: pending' "$TASKS_FILE" 2>/dev/null | head -n1 || true)
  PENDING_COUNT="${PENDING_COUNT:-0}"
  if ! [[ "$PENDING_COUNT" =~ ^[0-9]+$ ]]; then
    PENDING_COUNT=0
  fi
  if [ "$PENDING_COUNT" -eq 0 ]; then
    echo "[$TICK_TS] AUTO-CLEANUP: 0 PENDING tasks, running worktree-helper cleanup-all" | tee -a "$LOG_FILE"
    bash "$HELPER" cleanup-all 2>&1 | tee -a "$LOG_FILE" || true
  else
    echo "[$TICK_TS] AUTO-CLEANUP: $PENDING_COUNT PENDING tasks remain, skipping cleanup" | tee -a "$LOG_FILE"
  fi
}
trap auto_cleanup_hook EXIT

# --- NOTIFY HOOK (M8 acceptance criterion) ---
# When tick exits non-zero (FAIL/NEEDS_FIX/BLOCKED/OVERRUN/BUDGET_ABORT) OR a
# cost spike was detected, invoke scripts/notify.sh with a reason + summary.
# Cooldown dedup lives in notify.sh itself (LOOP_NOTIFY_COOLDOWN_SEC,
# default 600s = 10min) — we do NOT add another guard here, else duplicate
# suppression breaks. notify.sh is free (ntfy.sh free tier + zero LLM
# calls) so per-tick cost is $0 in steady state; the "$0.10/tick" budget
# is recorded for future paid webhook replacement (e.g. Opsgenie).
#
# Multiple EXIT traps run in registration order — auto_cleanup_hook runs
# first (worktree cleanup), then notify_hook fires. Each trap captures $?
# at entry, so both see the same exit code from the tick's terminating
# exit. TICK_VERDICT is set per-exit-path; empty TICK_VERDICT + exit 0
# means a clean PASS (no-op); empty + non-zero falls back to tick_error.
notify_hook() {
  local EXIT_CODE=$?
  local VERDICT="${TICK_VERDICT:-UNKNOWN}"
  local REASON=""
  local MSG=""

  if [[ "${SPIKE_DETECTED:-0}" == "1" ]]; then
    REASON="spike_alarm"
    MSG="Tick $TICK_ID spike (cost > 80% of daily cap, exit=$EXIT_CODE): see $LOG_DIR/cost-report.md"
  elif [[ "$EXIT_CODE" -eq 0 && "$VERDICT" == "PASS" ]]; then
    REASON="tick_pass"
    MSG="Tick $TICK_ID PASS"
  elif [[ "$EXIT_CODE" -ne 0 ]]; then
    case "$VERDICT" in
      FAIL)         REASON="tick_fail"; MSG="Tick $TICK_ID FAIL (exit=$EXIT_CODE)" ;;
      NEEDS_FIX)    REASON="needs_fix"; MSG="Tick $TICK_ID NEEDS_FIX (exit=$EXIT_CODE)" ;;
      BLOCKED)      REASON="blocked";   MSG="Tick $TICK_ID BLOCKED (exit=$EXIT_CODE)" ;;
      OVERRUN)      REASON="overrun";   MSG="Tick $TICK_ID OVERRUN (max ${MAX_RUNTIME_MIN}min, exit=$EXIT_CODE)" ;;
      BUDGET_ABORT) REASON="budget";    MSG="Tick $TICK_ID BUDGET_ABORT (daily cost cap exceeded, exit=$EXIT_CODE)" ;;
      *)            REASON="tick_error"; MSG="Tick $TICK_ID $VERDICT (exit=$EXIT_CODE)" ;;
    esac
  fi

  if [[ -z "$REASON" ]]; then return 0; fi

  local NOTIFY="$PROJECT_ROOT/scripts/notify.sh"
  if [[ ! -x "$NOTIFY" ]]; then
    echo "[$TICK_TS] NOTIFY: skipped (notify.sh not executable: $NOTIFY)" >> "$LOG_FILE"
    return 0
  fi

  echo "[$TICK_TS] NOTIFY: firing ($REASON, exit=$EXIT_CODE)" >> "$LOG_FILE"
  set +e
  bash "$NOTIFY" --reason "$REASON" --message "$MSG" 2>>"$LOG_FILE" || true
  set -e
}
trap notify_hook EXIT

echo "[$TICK_TS] Loop tick starting (id=$TICK_ID, cost_cap=\$$COST_CAP_USD, max_runtime=${MAX_RUNTIME_MIN}min)" | tee "$LOG_FILE"

# --- GRAPH DISPATCH (--graph path, no LLM cost) ---
# Skip the orchestrator prompt + cost guard entirely when --graph is passed.
# Runs named graph end-to-end via inline Python (matches AGENTS_JSON pattern
# above). Exit code = graph's terminal status code. SqliteSaver persists at
# .swarm/langgraph_checkpoint.db (gitignored at .gitignore:315).
if [ -n "$GRAPH_NAME" ]; then
  if $DRY_RUN; then
    echo "[$TICK_TS] DRY RUN -- would invoke graph: $GRAPH_NAME" | tee -a "$LOG_FILE"
    echo "[$TICK_TS] checkpoint_db: $PROJECT_ROOT/.swarm/langgraph_checkpoint.db" | tee -a "$LOG_FILE"
    echo "[$TICK_TS] thread_id: cron-${TICK_ID}" | tee -a "$LOG_FILE"
    exit 0
  fi

  echo "[$TICK_TS] GRAPH MODE: $GRAPH_NAME (no orchestrator LLM, skip cost-guard)" | tee -a "$LOG_FILE"

  TICK_START_S=$(date +%s)

  # $() command substitution is exempt from `set -e` traps in bash — we
  # capture the exit code into GRAPH_EXIT_CODE rather than letting a non-zero
  # python exit abort the script before we can append progress.md.
  GRAPH_OUTPUT=$(cd "$PROJECT_ROOT" && "$PYTHON" -c "
import os, sys, traceback
from pathlib import Path

graph_name = '$GRAPH_NAME'
project_root = Path.cwd()
ckpt_dir = project_root / '.swarm'
ckpt_db = str(ckpt_dir / 'langgraph_checkpoint.db')
thread_id = 'cron-${TICK_ID}'

ckpt_dir.mkdir(parents=True, exist_ok=True)

try:
    if graph_name == 'pae_maintainer':
        # Factory returns UNCOMPILED StateGraph; needs explicit compile + SqliteSaver.
        # NOTE: SqliteSaver.from_conn_string() returns a _GeneratorContextManager,
        # not a saver instance — that breaks .compile(checkpointer=...). Also,
        # langgraph's PregelLoop spawns worker threads that need cross-thread
        # sqlite3 access, so the connection MUST be opened with check_same_thread=False.
        sys.path.insert(0, str(project_root / 'vibe-ops' / 'src'))
        import sqlite3
        from langgraph.checkpoint.sqlite import SqliteSaver
        from langgraph_entry import make_pae_graph
        _conn = sqlite3.connect(ckpt_db, check_same_thread=False)
        _saver = SqliteSaver(_conn)
        _saver.setup()
        graph = make_pae_graph().compile(checkpointer=_saver)
        import datetime as dt
        today = dt.date.today().isoformat()
        initial = {
            'cycle_id': thread_id,
            'cycle_start': today,
            'cycle_end': today,
        }
    elif graph_name == 'ikigai_maintainer_v2':
        # Factory compiles internally with SqliteSaver(check_same_thread=False).
        # graph.py uses relative imports (nodes.X), so we must import the
        # v2 package, not the bare module. Dual sys.path mirrors conftest:
        # repo root resolves dotted-prefix src.X; src/ resolves bare contracts.X.
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / 'src'))
        sys.path.insert(0, str(project_root / 'src' / 'ikigai' / 'src' / 'agents'))
        from v2.graph import make_v2_graph
        graph = make_v2_graph(checkpoint_db=ckpt_db)
        initial = {}
    elif graph_name == 'ikigai_fork_smoke':
        # Factory compiles internally with SqliteSaver(check_same_thread=False).
        # fork_smoke_graph has no relative imports so bare import works too,
        # but we keep the package form for symmetry with ikigai_maintainer_v2.
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / 'src'))
        sys.path.insert(0, str(project_root / 'src' / 'ikigai' / 'src' / 'agents'))
        from v2.fork_smoke_graph import make_fork_smoke_graph
        graph = make_fork_smoke_graph(checkpoint_db=ckpt_db)
        initial = {}
    else:
        print(f'Unknown graph: {graph_name}', file=sys.stderr)
        sys.exit(2)

    config = {'configurable': {'thread_id': thread_id}}
    result = graph.invoke(initial, config=config)

    import sqlite3
    con = sqlite3.connect(ckpt_db)
    try:
        count = con.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0]
    finally:
        con.close()

    print(f'graph={graph_name} thread_id={thread_id} checkpoints={count} status=0')
    sys.exit(0)
except Exception as e:
    print(f'graph={graph_name} thread_id={thread_id} status=1 error={type(e).__name__}: {e}', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
" 2>&1)
  GRAPH_EXIT_CODE=$?

  TICK_END_S=$(date +%s)
  DURATION_S=$((TICK_END_S - TICK_START_S))
  VERDICT=$([ $GRAPH_EXIT_CODE -eq 0 ] && echo PASS || echo FAIL)
  TICK_VERDICT=$VERDICT

  echo "[$TICK_TS] graph-dispatch result (exit=$GRAPH_EXIT_CODE): $GRAPH_OUTPUT" | tee -a "$LOG_FILE"

  # Always append progress.md (audit trail, even on failure)
  {
    echo ""
    echo "## $TICK_TS | $GRAPH_NAME | $VERDICT"
    echo "- commit: -"
    echo "- cost_usd: 0"
    echo "- duration_min: $((DURATION_S / 60))"
    echo "- model: none (--graph deterministic dispatch)"
    echo "- attempt: 1/1"
    NOTES=$(echo "$GRAPH_OUTPUT" | tr '\n' ' ' | head -c 500)
    echo "- notes: $NOTES"
    echo "- next_action: $([ $GRAPH_EXIT_CODE -eq 0 ] && echo advance || echo retry)"
  } >> "$PROGRESS_FILE"

  echo "[$TICK_TS] GRAPH MODE done (exit=$GRAPH_EXIT_CODE, verdict=$VERDICT)" | tee -a "$LOG_FILE"
  exit $GRAPH_EXIT_CODE
fi
# --- END GRAPH DISPATCH ---

# Cost guard: refuse to run if today's spend is over 80% of cap
# (assumes a daily cap of 10x the per-tick cap; adjust as needed)
# NOTE: We use `awk` for the comparison (not `bc`, which is not on
# Windows Git Bash) and check the result with string equality —
# `(( math-expr ))` returns exit-1 when the expression is 0 (false),
# which `set -e` traps and aborts the whole script before we ever
# reach the dry-run branch.
DAILY_CAP=$((COST_CAP_USD * 10))
# `|| echo "0.00"` guards against `set -e` tripping when grep finds no
# `## ... $` lines (fresh progress.md has none yet, but `grep` exits 1
# and the pipeline return code propagates through `$()`).
TODAY_SPEND=$(grep "^## .* \\$" "$PROGRESS_FILE" 2>/dev/null | grep "$(date -u +%Y-%m-%d)" | awk -F'$' '{s+=$NF} END {printf "%.2f", s+0}' || echo "0.00")
OVER_BUDGET=$(awk -v t="$TODAY_SPEND" -v c="$DAILY_CAP" 'BEGIN { print (t+0 > c * 0.8) ? 1 : 0 }')
if [ "$OVER_BUDGET" = "1" ]; then
  echo "[$TICK_TS] ABORT: Today's spend \$$TODAY_SPEND > 80% of daily cap \$$DAILY_CAP" | tee -a "$LOG_FILE"
  TICK_VERDICT="BUDGET_ABORT"
  SPIKE_DETECTED=1
  exit 78  # EX_CONFIG
fi

# Build the orchestrator prompt
read -r -d '' ORCHESTRATOR_PROMPT <<'EOF' || true
# ROLE
You are the life-oss loop orchestrator. Advance one milestone per tick.

# READ FIRST (every tick, in this order)
1. .claude/loop/constitution.md
2. .claude/loop/roadmap.md
3. .claude/loop/tasks.md
4. .claude/loop/progress.md (recent 10 lines for context)
5. AGENTS.md
6. specs/M{N}-{slug}/SPEC.md (if exists for current milestone)

# BUDGET
- Max cost: $COST_CAP_USD USD
- Max sub-agents: 4 worker + 4 verifier
- Max wall time: $MAX_RUNTIME_MIN min
- Hard kill on any limit

# DECISION TREE
- If progress.md shows BLOCKED → exit BLOCKED
- If roadmap has all DONE → exit IDLE
- Else: pick next pending task in tasks.md

# EXECUTE
1. Spawn 1 worker sub-agent in worktree `.worktrees/m-{milestone}-{task_id}/`
2. Worker implements, tests, commits inside worktree on branch `loop/m-{milestone}-{task_id}`
3. Spawn 1 verifier sub-agent in same worktree
4. Verifier returns JSON verdict
5. If PASS — MERGE PROTOCOL (NO `git merge --ff-only`, NO cross-branch merge):
     a. From master (NOT worktree), apply diff to current files:
        `git -C .worktrees/m-{milestone}-{task_id} diff HEAD~ -- <files> | git apply`
     b. `git add <files>` then `git commit -m "<message>"` on master
     c. `git worktree remove .worktrees/m-{milestone}-{task_id}` (force if Windows locks)
     d. `git branch -D loop/m-{milestone}-{task_id}` (cleanup dead branch)
6. Append to progress.md (NEW line, never edit past)
7. If PASS: edit roadmap.md (mark milestone DONE), edit tasks.md (mark task done)
8. If FAIL × max_attempts: write BLOCKED to progress.md, exit
9. If NEEDS_FIX: append notes, exit

# MERGE BUG POSTMORTEM (T-0.1, 2026-09-07)
The old protocol used `git merge --ff-only loop/m0-t0.1` from master. That silently
no-op's when the worktree branch is divergent (not fast-forwardable) and prints
"Already up to date" — a misread. Result: worker commit looked merged but was
orphaned on a dead branch, worktree force-removed, work lost. NEVER use
`--ff-only` between master and a worker worktree. Use the explicit
`git -C <worktree> diff HEAD~ -- <files> | git apply` + normal commit protocol
above.

# EXIT CODE
Print: ADVANCED | IDLE | BLOCKED | NEEDS_FIX | ERROR

# HARD RULES
- Never modify constitution.md
- Never modify AGENTS.md or CLAUDE.md
- Never skip deterministic gates (tests, lint, types)
- Never use same model for worker and verifier
- Never edit past lines in progress.md
EOF

if $DRY_RUN; then
  echo "[$TICK_TS] DRY RUN — would invoke orchestrator with:" | tee -a "$LOG_FILE"
  echo "$ORCHESTRATOR_PROMPT" | tee -a "$LOG_FILE"
  exit 0
fi

# Invoke the orchestrator
# The actual invocation depends on what agent runtime is available.
# In life-oss, we use Claude Code (`claude` CLI) directly with the 3
# loop agents registered inline via `--agents` JSON so the orchestrator
# can dispatch worker + verifier sub-agents per tick.
#
# (Earlier draft invoked `claude-code` which does NOT exist — only `claude` does.)
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../.."
PROJECT_ROOT=$(pwd)
LOOP_AGENTS_DIR="$PROJECT_ROOT/.claude/agents/loop"

# Build the agents JSON inline (3 agents: orchestrator/worker/verifier).
# Python is used because JSON-escaping newlines + nested JSON in bash
# heredocs is fragile on Windows Git Bash. Python 3 is on PATH.
AGENTS_JSON=$(python -c "
import json
def slurp(p):
    with open(p, encoding='utf-8') as f:
        return f.read()
agents = {
    'loop-orchestrator': {
        'description': 'State machine — reads loop state, picks next milestone, dispatches worker + verifier',
        'prompt': slurp('.claude/agents/loop/orchestrator.md'),
        'tools': ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep', 'Task'],
        'model': 'opus'
    },
    'loop-worker': {
        'description': 'Maker — implements one task per invocation',
        'prompt': slurp('.claude/agents/loop/worker.md'),
        'tools': ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep'],
        'model': 'sonnet'
    },
    'loop-verifier': {
        'description': 'Checker — scores 1-5 on 5 dimensions, returns JSON verdict',
        'prompt': slurp('.claude/agents/loop/verifier.md'),
        'tools': ['Read', 'Bash', 'Glob', 'Grep'],
        'model': 'haiku'
    }
}
print(json.dumps(agents))
")

# Use timeout to enforce max runtime.
# Permissions: targeted --allowedTools whitelist (NOT global bypass).
# The orchestrator only needs Read/Write/Edit/Bash/Glob/Grep/Task —
# anything else will prompt, which is the safe default.
timeout $((MAX_RUNTIME_MIN * 60)) claude \
  --agent "loop-orchestrator" \
  --agents "$AGENTS_JSON" \
  --model "claude-opus-4-8" \
  --max-budget-usd "$COST_CAP_USD" \
  --allowedTools "Read" "Write" "Edit" "Bash" "Glob" "Grep" "Task" \
  -p "$ORCHESTRATOR_PROMPT" \
  2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
  echo "[$TICK_TS] OVERRUN: tick exceeded ${MAX_RUNTIME_MIN}min" | tee -a "$LOG_FILE"
  # Append OVERRUN to progress.md
  echo "" >> "$PROGRESS_FILE"
  echo "## $TICK_TS | OVERRUN | OVERRUN" >> "$PROGRESS_FILE"
  echo "- commit: -" >> "$PROGRESS_FILE"
  echo "- cost_usd: 0" >> "$PROGRESS_FILE"
  echo "- duration_min: $MAX_RUNTIME_MIN" >> "$PROGRESS_FILE"
  echo "- model: opus" >> "$PROGRESS_FILE"
  echo "- attempt: 1/2" >> "$PROGRESS_FILE"
  echo "- notes: Tick exceeded max runtime. Killed." >> "$PROGRESS_FILE"
  echo "- next_action: retry" >> "$PROGRESS_FILE"
  TICK_VERDICT="OVERRUN"
  exit 124
fi

echo "[$TICK_TS] Tick done (exit=$EXIT_CODE)" | tee -a "$LOG_FILE"
TICK_VERDICT=$([ $EXIT_CODE -eq 0 ] && echo PASS || echo FAIL)
exit $EXIT_CODE
