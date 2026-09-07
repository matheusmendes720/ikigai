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
DAILY_CAP=$((COST_CAP_USD * 10))
TODAY_SPEND=$(grep "^## .* \\$" "$PROGRESS_FILE" 2>/dev/null | grep "$(date -u +%Y-%m-%d)" | awk -F'$' '{s+=$NF} END {printf "%.2f", s+0}')
if (( $(echo "$TODAY_SPEND > $DAILY_CAP * 0.8" | bc -l 2>/dev/null || echo 0) )); then
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
2. Worker implements, tests, commits
3. Spawn 1 verifier sub-agent in same worktree
4. Verifier returns JSON verdict
5. Append to progress.md (NEW line, never edit past)
6. If PASS: edit roadmap.md (mark milestone DONE), edit tasks.md (mark task done)
7. If FAIL × max_attempts: write BLOCKED to progress.md, exit
8. If NEEDS_FIX: append notes, exit

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
# In life-oss, we have:
#   1. claude-flow (built-in to .claude/)
#   2. MiniMax Mavis (via mavis tool)
#   3. Direct Claude Code via the orchestrator agent file
#
# For now, use Claude Code directly. The user can wire to claude-flow later.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../.."
PROJECT_ROOT=$(pwd)

# Use timeout to enforce max runtime
timeout $((MAX_RUNTIME_MIN * 60)) claude-code \
  --agent "$PROJECT_ROOT/.claude/agents/loop/orchestrator.md" \
  --prompt "$ORCHESTRATOR_PROMPT" \
  --model claude-opus-4-8 \
  --max-cost "$COST_CAP_USD" \
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
