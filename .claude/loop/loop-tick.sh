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
LOG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/logs"
PROGRESS_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/progress.md"
LOOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --cost-cap) COST_CAP_USD="$2"; shift 2 ;;
    --max-runtime) MAX_RUNTIME_MIN="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

mkdir -p "$LOG_DIR"

# Timestamp for this tick
TICK_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TICK_ID=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/tick-$TICK_ID.log"

echo "[$TICK_TS] Loop tick starting (id=$TICK_ID, cost_cap=\$$COST_CAP_USD, max_runtime=${MAX_RUNTIME_MIN}min)" | tee "$LOG_FILE"

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
  exit 124
fi

echo "[$TICK_TS] Tick done (exit=$EXIT_CODE)" | tee -a "$LOG_FILE"
exit $EXIT_CODE
