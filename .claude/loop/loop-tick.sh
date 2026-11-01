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

# --graph dispatch was retired together with the LangGraph harness (ADR-037):
# the graph registry (langgraph.json) and the vibe-ops/langgraph entry points
# are no longer part of the published scope. The flag is kept only so an old
# cron entry fails loudly instead of silently running something else.
VALID_GRAPH_KEYS=""

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

# --graph dispatch is retired (ADR-037) - fail fast, before any other work.
if [ -n "$GRAPH_NAME" ]; then
  echo "--graph $GRAPH_NAME is retired (ADR-037): the LangGraph registry left the canonical scope." >&2
  echo "Run an orchestrator tick instead, or the MCP transport: python -m src.transport.mcp_server" >&2
  exit 2
fi

mkdir -p "$LOG_DIR"

# Timestamp for this tick
TICK_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TICK_ID=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/tick-$TICK_ID.log"

# --- HEARTBEAT (M39) ---
# Write a heartbeat timestamp so the daemon-watchdog can detect extended
# daemon death (22h+ silent gap observed 2026-09-07→08). Watchdog alerts
# when the last heartbeat is older than WATCHDOG_THRESHOLD_SEC (default 5400s
# = 90min, 1.5x the 60min tick interval). Exits 0 always — heartbeat
# write failures must not abort the tick.
HEARTBEAT_FILE="$LOOP_DIR/.daemon-heartbeat.json"
mkdir -p "$(dirname "$HEARTBEAT_FILE")"
echo "{\"last_heartbeat\":\"$TICK_TS\",\"tick_id\":\"$TICK_ID\"}" > "$HEARTBEAT_FILE" 2>/dev/null || true

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

# --- GRAPH DISPATCH (retired, ADR-037) ---
# The deterministic --graph path ran the LangGraph graphs registered in
# langgraph.json (pae_maintainer, ikigai_maintainer_v2, ikigai_fork_smoke)
# with a SqliteSaver checkpoint at .swarm/langgraph_checkpoint.db. The
# registry, the graph factories and the langgraph-checkpoint dependency left
# the canonical scope with the serverless pivot, so the path is gone: the
# orchestrator tick is the only entry point, and the agent surface is the
# MCP transport (src/transport/mcp_server.py, ADR-011).


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

  # Canonical MCP transport (ADR-011 / ADR-037). The loop workers talk to
  # the serverless MCP server (`src/transport/mcp_server.py`) over stdio or
  # HTTP (`IKIGAI_MCP_TRANSPORT`, `FASTMCP_HOST`, `FASTMCP_PORT`). The retired
  # local bridge (`.claude/loop/mcp_bridge.py`), its stdio spawner
  # (`interfaces/cli/mcp_runtime.py`) and the tracing stack left the canonical
  # scope with the serverless pivot, so there is nothing to bind at loop
  # startup: workers reach the MCP server through the transport itself and
  # fall back to Bash + file tools (degraded mode) when it is unreachable.
  unset MCP_BIND_OUTPUT MCP_BIND_EXIT

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
