#!/bin/bash
# Test for notify-wrap.sh — wraps a command, posts notification, returns command's exit code.

set -euo pipefail

THIS_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$THIS_DIR/../.." && pwd)"
WRAP="$REPO_ROOT/.claude/helpers/notify-wrap.sh"
LOG="${NOTIFY_FILE:-$REPO_ROOT/.life/logs/notifications.log}"
# Ensure parent dir exists
mkdir -p "$(dirname "$LOG")"

if [ ! -x "$WRAP" ]; then
    echo "FAIL: $WRAP not executable"
    exit 1
fi

# Helper to count log lines
line_count() { [ -f "$LOG" ] && wc -l < "$LOG" || echo 0; }

# Helper to clear log between tests
clear_log() { rm -f "$LOG"; }

# Test 1: successful command posts success notification
clear_log
LINES_BEFORE=$(line_count)
export PYTHONPATH="$REPO_ROOT/src"
if "$WRAP" test-success "test title" "true" 2>/dev/null; then
    RC=0
else
    RC=$?
fi
if [ "$RC" -ne 0 ]; then
    echo "FAIL: notify-wrap should propagate exit code 0 from true, got $RC"
    exit 1
fi
sleep 0.2  # let async writes flush
LINES_AFTER=$(line_count)
if [ "$((LINES_AFTER - LINES_BEFORE))" -lt 1 ]; then
    echo "FAIL: notify-wrap true did not write to $LOG (before=$LINES_BEFORE after=$LINES_AFTER)"
    exit 1
fi
if ! grep -q "test title" "$LOG"; then
    echo "FAIL: log missing title marker"
    tail -5 "$LOG"
    exit 1
fi
echo "PASS: success path wrote notification"

# Test 2: failing command posts error notification, propagates non-zero exit code
clear_log
LINES_BEFORE=$(line_count)
set +e
"$WRAP" test-failure "test title" "false" 2>/dev/null
RC=$?
set -e
if [ "$RC" -eq 0 ]; then
    echo "FAIL: notify-wrap should propagate non-zero exit code, got $RC"
    exit 1
fi
sleep 0.2
LINES_AFTER=$(line_count)
if [ "$((LINES_AFTER - LINES_BEFORE))" -lt 1 ]; then
    echo "FAIL: notify-wrap false did not write to $LOG"
    exit 1
fi
if ! grep -q "test title" "$LOG"; then
    echo "FAIL: log missing title marker"
    tail -5 "$LOG"
    exit 1
fi
if ! grep -q "level.*error\|❌" "$LOG"; then
    echo "FAIL: log missing error icon"
    tail -5 "$LOG"
    exit 1
fi
echo "PASS: failure path wrote notification + propagated rc=$RC"

# Test 3: title and body in log
clear_log
"$WRAP" "title-test-3" "title-arg-body" "echo hello" >/dev/null 2>&1
sleep 0.2
if ! grep -q "title-arg-body" "$LOG"; then
    echo "FAIL: log missing title"
    exit 1
fi
if ! grep -q "rc=" "$LOG"; then
    echo "FAIL: log missing rc=... in body"
    tail -5 "$LOG" >&2
    exit 1
fi
if ! grep -q "elapsed=" "$LOG"; then
    echo "FAIL: log missing elapsed=... in body"
    tail -5 "$LOG" >&2
    exit 1
fi
echo "PASS: log contains title + rc + elapsed"

# Test 4: usage error when no command given
set +e
"$WRAP" only-name only-title 2>/dev/null
RC=$?
set -e
if [ "$RC" -eq 0 ]; then
    echo "FAIL: should fail with usage error when no command"
    exit 1
fi
echo "PASS: usage error when no command (rc=$RC)"

echo "ALL notify-wrap tests passed"
