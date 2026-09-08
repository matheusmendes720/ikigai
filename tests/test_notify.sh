#!/usr/bin/env bash
# tests/test_notify.sh — end-to-end test for scripts/notify.sh
#
# Acceptance: specs/M8-notification-channel/SPEC.md criterion #5 —
# "tests cover: disabled mode / idempotent duplicate suppression /
# dry-run / spike alarm wire".
#
# Test design (per spec):
#   1. Disabled mode: unset LOOP_NOTIFY_TOPIC, run, assert exit 0
#      and no HTTP call attempted (counter=0 via stub curl).
#   2. Idempotent duplicate suppression: send same reason+message
#      twice within cooldown, assert only ONE HTTP POST attempted
#      (counter=1; second call suppressed).
#   3. Dry-run mode: --dry-run flag, assert exit 0, prints curl
#      command to stdout, does NOT POST (counter=0).
#   4. Spike alarm wire: seed progress.md with >$10 cost_usd today,
#      run cost-dashboard.sh, assert exit=2 + spike_alarm in report.
#      Then invoke notify.sh --reason spike_alarm, assert counter=1.
#
# Implementation: copies notify.sh into a temp dir so its REPO_ROOT
# resolution (`$(dirname "$0")/..`) lands on the temp dir. Stub
# `curl` via PATH override + counter file — no real network calls.
#
# POSIX + Git Bash compatible. Pure shell, no Python deps.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NOTIFY="$PROJECT_ROOT/scripts/notify.sh"
COST_DASHBOARD="$PROJECT_ROOT/scripts/cost-dashboard.sh"

if [[ ! -f "$NOTIFY" ]]; then
    echo "FATAL: $NOTIFY not found" >&2
    exit 1
fi

PASS=0
FAIL=0
fail() { echo "FAIL: $*"; FAIL=$((FAIL + 1)); }
ok()   { echo "PASS: $*"; PASS=$((PASS + 1)); }

# Build a tmp sandbox with: scripts/notify.sh + scripts/cost-dashboard.sh +
# .claude/loop/logs/ + a fake curl bin (stub). All four tests share one
# sandbox but reset the counter + state file between tests.
TMPDIR="$(mktemp -d -t notify-test.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT
mkdir -p "$TMPDIR/scripts" "$TMPDIR/.claude/loop/logs" "$TMPDIR/bin"
cp "$NOTIFY" "$TMPDIR/scripts/notify.sh"
if [[ -f "$COST_DASHBOARD" ]]; then
    cp "$COST_DASHBOARD" "$TMPDIR/scripts/cost-dashboard.sh"
fi

# Stub curl: increments COUNTER_FILE on each invocation, prints "200" to
# stdout (mimics a successful HTTP 200 response), exits 0. Real curl is
# NEVER invoked — no network calls during tests.
COUNTER_FILE="$TMPDIR/bin/curl.counter"
cat > "$TMPDIR/bin/curl" <<'STUB'
#!/usr/bin/env bash
COUNTER_FILE="${COUNTER_FILE:?stub curl needs COUNTER_FILE}"
echo $(( $(cat "$COUNTER_FILE" 2>/dev/null || echo 0) + 1 )) > "$COUNTER_FILE"
echo "200"
exit 0
STUB
chmod +x "$TMPDIR/bin/curl"

reset_counter() { echo 0 > "$COUNTER_FILE"; }
reset_state()   { rm -f "$TMPDIR/.claude/loop/logs/notify-state.json"; }
reset()         { reset_counter; reset_state; }

# Helper: run notify.sh with stubbed PATH and isolated REPO_ROOT.
RUN_NOTIFY() {
    COUNTER_FILE="$COUNTER_FILE" \
    PATH="$TMPDIR/bin:$PATH" \
    LOOP_NOTIFY_SERVER="https://stub.test" \
    LOOP_NOTIFY_COOLDOWN_SEC="600" \
    bash "$TMPDIR/scripts/notify.sh" "$@"
}

# ---------- Test 1: disabled mode ----------
echo "=== Test 1: disabled mode (LOOP_NOTIFY_TOPIC unset) ==="
reset
set +e
RUN_NOTIFY --reason test --message "ping" >/dev/null 2>&1
EXIT_CODE=$?
set -e
if [[ "$EXIT_CODE" == "0" ]]; then
    ok "exit 0 (disabled mode = no-op)"
else
    fail "exit $EXIT_CODE (expected 0 for disabled mode)"
fi
COUNT=$(cat "$COUNTER_FILE")
if [[ "$COUNT" == "0" ]]; then
    ok "no HTTP call attempted (counter=0)"
else
    fail "counter=$COUNT (expected 0 — disabled mode must not POST)"
fi

# ---------- Test 2: idempotent duplicate suppression ----------
echo "=== Test 2: idempotent duplicate suppression ==="
reset
export LOOP_NOTIFY_TOPIC="test-topic-abcdef123456"

set +e
RUN_NOTIFY --reason tick_fail --message "FAIL: cost > budget" >/dev/null 2>&1
RUN_NOTIFY --reason tick_fail --message "FAIL: cost > budget" >/dev/null 2>&1
RUN_NOTIFY --reason tick_fail --message "FAIL: cost > budget" >/dev/null 2>&1
set -e
COUNT=$(cat "$COUNTER_FILE")
if [[ "$COUNT" == "1" ]]; then
    ok "3 duplicate sends → counter=1 (idempotency enforced)"
else
    fail "counter=$COUNT (expected 1 — only first POST should fire)"
fi

# Different message within same reason = different hash = SHOULD send
reset
RUN_NOTIFY --reason tick_fail --message "FAIL: budget exceeded" >/dev/null 2>&1
RUN_NOTIFY --reason tick_fail --message "different message body" >/dev/null 2>&1
COUNT=$(cat "$COUNTER_FILE")
if [[ "$COUNT" == "2" ]]; then
    ok "different messages bypass dedup (counter=2)"
else
    fail "counter=$COUNT (expected 2 — different msg bodies should each POST)"
fi

# ---------- Test 3: dry-run mode ----------
echo "=== Test 3: dry-run mode ==="
reset
OUT=$(RUN_NOTIFY --reason test --message "ping" --dry-run 2>/dev/null)
EXIT_CODE=$?
COUNT=$(cat "$COUNTER_FILE")
if [[ "$EXIT_CODE" == "0" ]]; then
    ok "exit 0 (dry-run is success)"
else
    fail "exit $EXIT_CODE (expected 0)"
fi
if [[ "$COUNT" == "0" ]]; then
    ok "no HTTP call attempted (counter=0)"
else
    fail "counter=$COUNT (expected 0 — dry-run must NOT POST)"
fi
if echo "$OUT" | grep -q "DRY-RUN"; then
    ok "stdout contains DRY-RUN marker"
else
    fail "stdout missing DRY-RUN marker (got: $OUT)"
fi
if echo "$OUT" | grep -q "curl"; then
    ok "stdout contains curl command"
else
    fail "stdout missing curl command (got: $OUT)"
fi

# ---------- Test 4: spike alarm wire ----------
echo "=== Test 4: spike alarm wire (cost-dashboard exit 2 → notify) ==="
# This integration test requires cost-dashboard.sh to exist in the
# sandbox. Skip gracefully if it's not available (e.g., during T-8.2
# review before T-7.x ships). When skipped, test 4 is informational
# only — groups 1-3 are the contract for T-8.2 closure.
if [[ ! -f "$TMPDIR/scripts/cost-dashboard.sh" ]]; then
    echo "SKIP: cost-dashboard.sh not available (test 4 deferred to integration milestone)"
else
    reset
    TODAY=$(date -u +%Y-%m-%d)
    PROGRESS="$TMPDIR/.claude/loop/progress.md"
    mkdir -p "$TMPDIR/.claude/loop"
    cat > "$PROGRESS" <<EOF
## ${TODAY} | spike-tick-1 | PASS
- commit: aaa
- cost_usd: 6.00

## ${TODAY} | spike-tick-2 | PASS
- commit: bbb
- cost_usd: 5.50
EOF

    set +e
    bash "$TMPDIR/scripts/cost-dashboard.sh" >/dev/null 2>&1
    DASH_EXIT=$?
    set -e
    if [[ "$DASH_EXIT" == "2" ]]; then
        ok "cost-dashboard.sh exited 2 (spike detected)"
    else
        fail "cost-dashboard.sh exit $DASH_EXIT (expected 2 for >\$10 spike)"
    fi

    # Wire #1 from SPEC §4: cost-dashboard exit 2 → notify spike_alarm
    REPORT="$TMPDIR/.claude/loop/logs/cost-report.md"
    SPIKE_MSG=$(grep -E '^- \*\*' "$REPORT" | head -10 || echo "spike detected")
    RUN_NOTIFY --reason spike_alarm --message "$SPIKE_MSG" >/dev/null 2>&1
    COUNT=$(cat "$COUNTER_FILE")
    if [[ "$COUNT" == "1" ]]; then
        ok "notify fired once after spike (counter=1)"
    else
        fail "counter=$COUNT (expected 1 — spike alarm should fire once)"
    fi

    # State file should record the dedup key
    if [[ -f "$TMPDIR/.claude/loop/logs/notify-state.json" ]] || \
       [[ -f "$TMPDIR/.claude/loop/logs/notify-state.txt" ]]; then
        ok "state file written"
    else
        # notify.sh writes "<key> <ts>" lines (append-only text, not JSON
        # despite the name); either extension or no extension is fine
        STATE_FILES=$(ls "$TMPDIR/.claude/loop/logs/notify-state"* 2>/dev/null | wc -l)
        if [[ "$STATE_FILES" -ge 1 ]]; then
            ok "state file written"
        else
            fail "state file not written (expected .claude/loop/logs/notify-state*)"
        fi
    fi
fi

# ---------- Summary ----------
echo ""
echo "=== Summary: $PASS pass, $FAIL fail ==="
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
