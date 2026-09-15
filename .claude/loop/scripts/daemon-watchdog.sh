#!/usr/bin/env bash
# daemon-watchdog.sh — M39 Daemon Health Watchdog
# Detects when the loop daemon has been silent for > WATCHDOG_THRESHOLD_SEC.
#
# The daemon-manager runs loop-tick.sh in a `while true` wrapper. When
# loop-tick crashes-and-exits faster than sleep returns (Windows edge case),
# the wrapper immediately re-enters and fires another tick — this rapid cycling
# looks like a heartbeat. When the wrapper itself dies (OOM, segfault, manual
# kill), ALL ticks stop with no alert.
#
# This watchdog detects both silent death and extended idle, then alerts via
# ntfy.sh (ntfy.sh is already wired in notify.sh M8 infrastructure).
#
# Usage:
#   bash .claude/loop/scripts/daemon-watchdog.sh [--dry-run]
#
# No Co-Authored-By trailer per project convention.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOOP_DIR="$PROJECT_ROOT/.claude/loop"
HEARTBEAT_FILE="$LOOP_DIR/.daemon-heartbeat.json"
SCHEDULES_DIR="$PROJECT_ROOT/.claude-flow/schedules"
LOG_FILE="$LOOP_DIR/logs/watchdog.log"

# Default: alert if no heartbeat for 90min (1.5x the 60min tick interval)
WATCHDOG_THRESHOLD_SEC="${WATCHDOG_THRESHOLD_SEC:-5400}"

mkdir -p "$(dirname "$HEARTBEAT_FILE")"
mkdir -p "$(dirname "$LOG_FILE")"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] watchdog: $*" >&2; }

# --- Parse heartbeat ---

if [ ! -f "$HEARTBEAT_FILE" ]; then
  log "WARN: no heartbeat file at $HEARTBEAT_FILE — daemon has never fired"
  # Don't alert on first run (daemon may not be started yet)
  exit 0
fi

HEARTBEAT_FILE_WIN=$(cygpath -m "$HEARTBEAT_FILE" 2>/dev/null || echo "$HEARTBEAT_FILE")
LAST_TS=$(python3 -c "
import json, sys
from datetime import datetime, timezone
with open('$HEARTBEAT_FILE_WIN') as f:
    d = json.load(f)
ts_str = d['last_heartbeat'].replace('Z','+00:00')
ts = datetime.fromisoformat(ts_str)
now = datetime.now(timezone.utc)
delta = (now - ts).total_seconds()
print(f'{delta:.0f}')
" 2>/dev/null || echo "99999")

log "last heartbeat: ${LAST_TS}s ago (threshold: ${WATCHDOG_THRESHOLD_SEC}s)"

# --- Check threshold ---

if [ "${LAST_TS:-99999}" -lt "$WATCHDOG_THRESHOLD_SEC" ]; then
  log "OK: daemon heartbeat fresh (${LAST_TS}s < ${WATCHDOG_THRESHOLD_SEC}s)"
  exit 0
fi

# --- Alert: daemon is silent ---
log "ALERT: daemon silent for ${LAST_TS}s (threshold ${WATCHDOG_THRESHOLD_SEC}s)"

NOTIFY_MSG="WATCHDOG ALERT: loop daemon silent for ${LAST_TS}s (>${WATCHDOG_THRESHOLD_SEC}s threshold). Daemon may be dead. Check .claude/loop/logs/ for recent tick logs."

NOTIFY="$PROJECT_ROOT/scripts/notify.sh"
if [ -x "$NOTIFY" ]; then
  # Use high priority for watchdog alerts — this is a potential daemon death
  bash "$NOTIFY" --reason watchdog_alert --message "$NOTIFY_MSG" --priority high 2>/dev/null || true
else
  log "WARN: notify.sh not executable at $NOTIFY — skipping webhook alert"
fi

# Write alert to local log so there's a persistent record even if ntfy fails
log "WATCHDOG ALERT written: $NOTIFY_MSG" >> "$LOG_FILE"

echo "WATCHDOG: silent ${LAST_TS}s, threshold ${WATCHDOG_THRESHOLD_SEC}s"
exit 0
