#!/usr/bin/env bash
# M123 — daily backtest cron driver.
#
# Runs the full backtest pipeline once per day at ~06:00 local time.
# Intended to be wired up via:
#   - Linux/macOS: crontab entry
#   - Windows: Task Scheduler (see scripts/cron/setup-task-scheduler.ps1)
#
# Output:
#   - reports/backtest-Q1.md (latest report)
#   - reports/baselines/<YYYY-MM-DD>.json (archived)
#   - reports/baselines/<YYYY-MM-DD>.llm.json (LLM-judge archived)
#   - reports/backtest-trend.md (weekly trend)
#
# The baseline_archive step is first-wins same-day, so running this twice
# in one day is safe (second run no-ops on the archive).

set -euo pipefail

# Resolve repo root from script location (works for symlinks too).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO"

# Detect Python (prefer repo venv, fall back to PATH python).
PYTHON=""
if [[ -x "$REPO/src/ikigai/.venv/Scripts/python.exe" ]]; then
    PYTHON="$REPO/src/ikigai/.venv/Scripts/python.exe"  # Windows
elif [[ -x "$REPO/src/ikigai/.venv/bin/python" ]]; then
    PYTHON="$REPO/src/ikigai/.venv/bin/python"          # POSIX
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
else
    echo "[$(date -Iseconds)] CRON FAILED: no python interpreter" >&2
    exit 1
fi

# Local logs directory.
mkdir -p "$REPO/.life/logs"
LOG="$REPO/.life/logs/cron-backtest.log"

# Run pipeline. Skip-gen because scenarios are stable.
echo "[$(date -Iseconds)] Starting daily backtest pipeline" >> "$LOG"
if bash "$REPO/scripts/backtest/run_backtest.sh" --skip-gen >> "$LOG" 2>&1; then
    echo "[$(date -Iseconds)] Pipeline OK" >> "$LOG"
    exit 0
else
    rc=$?
    echo "[$(date -Iseconds)] Pipeline FAILED (rc=$rc)" >> "$LOG"
    exit $rc
fi
