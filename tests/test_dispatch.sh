#!/usr/bin/env bash
# tests/test_dispatch.sh — end-to-end test for scripts/dispatch.sh
#
# Acceptance: SPEC.md criterion — "4 test groups:
#   Group 1: missing task (no <task_id> or unknown) → exit 1 + not_found
#   Group 2: already-done task → exit 0 + already_complete
#   Group 3: not-pending dry-run (status: pending + --dry-run) → exit 0
#   Group 4: regression-failed short-circuit → exit 1 + regression_failed"
#
# Implementation: copies dispatch.sh into a temp dir so its REPO_ROOT
# resolution lands on the temp sandbox. Tasks are seeded in a synthetic
# tasks.md. Regression sweep is stubbed via DISPATCH_REGRESSION_CMD env
# override so tests run fast without depending on M6/M7/M8.
#
# POSIX + Git Bash compatible. Pure shell, no Python deps.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DISPATCH="$PROJECT_ROOT/scripts/dispatch.sh"

if [[ ! -f "$DISPATCH" ]]; then
    echo "FATAL: $DISPATCH not found" >&2
    exit 1
fi

PASS=0
FAIL=0
fail() { echo "FAIL: $*"; FAIL=$((FAIL + 1)); }
ok()   { echo "PASS: $*"; PASS=$((PASS + 1)); }

# Build a tmp sandbox with: dispatch.sh + .claude/loop/tasks.md
# The script uses $(dirname "$0")/.. to find REPO_ROOT, so we place the
# script at <tmp>/scripts/ and tasks.md at <tmp>/.claude/loop/.
TMPDIR="$(mktemp -d -t dispatch-test.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT
mkdir -p "$TMPDIR/scripts" "$TMPDIR/.claude/loop"
cp "$DISPATCH" "$TMPDIR/scripts/dispatch.sh"

TASKS_MD="$TMPDIR/.claude/loop/tasks.md"
RUN_DISPATCH() {
    bash "$TMPDIR/scripts/dispatch.sh" "$@"
}

# ---------- Group 1: missing task ----------
echo "=== Group 1: missing task → exit 1 + not_found ==="

# Need a minimal tasks.md so the script can distinguish "unknown task"
# from "tasks.md missing". Create one with a different task.
cat > "$TASKS_MD" <<'EOF'
# Current Tasks — Loop Engineering

### T-OTHER-1 — Some other task
- **status:** done
EOF

# Test 1a: no task_id argument
set +e
OUT=$(RUN_DISPATCH 2>&1)
EXIT_CODE=$?
set -e
if [[ "$EXIT_CODE" == "1" ]]; then
    ok "no task_id → exit 1"
else
    fail "exit $EXIT_CODE (expected 1 for missing task_id)"
fi

# Test 1b: unknown task_id
set +e
OUT=$(RUN_DISPATCH T-DOES-NOT-EXIST 2>&1)
EXIT_CODE=$?
set -e
if [[ "$EXIT_CODE" == "1" ]]; then
    ok "unknown task_id → exit 1"
else
    fail "exit $EXIT_CODE (expected 1 for unknown task)"
fi
if echo "$OUT" | grep -q "not_found"; then
    ok "stdout contains not_found"
else
    fail "stdout missing not_found (got: $OUT)"
fi

# ---------- Group 2: already-done task (idempotent replay) ----------
echo "=== Group 2: already-done task → exit 0 + already_complete ==="

# Create tasks.md with a done task
cat > "$TASKS_MD" <<'EOF'
# Current Tasks — Loop Engineering

## Active Tasks

### T-10.999 — Test done task
- **status:** done
- **acceptance:**
  - [x] always passes
- **estimated_cost_usd:** 0.00
- **notes:** scaffold test
EOF

set +e
OUT=$(RUN_DISPATCH T-10.999 2>&1)
EXIT_CODE=$?
set -e
if [[ "$EXIT_CODE" == "0" ]]; then
    ok "done task → exit 0"
else
    fail "exit $EXIT_CODE (expected 0 for already-done task)"
fi
if echo "$OUT" | grep -q "already_complete"; then
    ok "stdout contains already_complete"
else
    fail "stdout missing already_complete (got: $OUT)"
fi
if echo "$OUT" | grep -q "status: done"; then
    ok "stdout shows status: done"
else
    fail "stdout missing status: done"
fi

# ---------- Group 3: pending task dry-run ----------
echo "=== Group 3: pending task + --dry-run → exit 0 (no commit/push) ==="

cat > "$TASKS_MD" <<'EOF'
# Current Tasks — Loop Engineering

## Active Tasks

### T-10.888 — Test pending task
- **status:** pending
- **acceptance:**
  - [ ] to be done
- **estimated_cost_usd:** 0.00
- **notes:** scaffold test
EOF

set +e
OUT=$(RUN_DISPATCH T-10.888 --dry-run 2>&1)
EXIT_CODE=$?
set -e
if [[ "$EXIT_CODE" == "0" ]]; then
    ok "pending task + --dry-run → exit 0"
else
    fail "exit $EXIT_CODE (expected 0 for dry-run)"
fi
if echo "$OUT" | grep -q "status: pending"; then
    ok "stdout shows status: pending"
else
    fail "stdout missing status: pending"
fi
if echo "$OUT" | grep -q "mode: dry-run"; then
    ok "stdout shows mode: dry-run"
else
    fail "stdout missing mode: dry-run"
fi
if echo "$OUT" | grep -q "would_dispatch: T-10.888"; then
    ok "stdout shows would_dispatch"
else
    fail "stdout missing would_dispatch"
fi
if echo "$OUT" | grep -q "dry_run_complete"; then
    ok "stdout shows dry_run_complete"
else
    fail "stdout missing dry_run_complete"
fi

# ---------- Group 4: regression-failed short-circuit ----------
echo "=== Group 4: regression_failed short-circuit → exit 1 ==="

cat > "$TASKS_MD" <<'EOF'
# Current Tasks — Loop Engineering

## Active Tasks

### T-10.777 — Test regression failure
- **status:** pending
- **acceptance:**
  - [ ] stub
- **estimated_cost_usd:** 0.00
- **notes:** scaffold test
EOF

# Create a fake regression script that always exits 1
FAKE_REGRESSION="$TMPDIR/fake-regression.sh"
cat > "$FAKE_REGRESSION" <<'STUB'
#!/bin/bash
echo "fake regression sweep failed"
exit 1
STUB
chmod +x "$FAKE_REGRESSION"

set +e
# DISPATCH_REGRESSION_CMD overrides the real sweep so tests run fast
OUT=$(DISPATCH_REGRESSION_CMD="$FAKE_REGRESSION" RUN_DISPATCH T-10.777 --execute 2>&1)
EXIT_CODE=$?
set -e
if [[ "$EXIT_CODE" == "1" ]]; then
    ok "regression sweep failure → exit 1"
else
    fail "exit $EXIT_CODE (expected 1 on regression failure)"
fi
if echo "$OUT" | grep -q "regression_failed"; then
    ok "stdout contains regression_failed"
else
    fail "stdout missing regression_failed (got: $OUT)"
fi
if echo "$OUT" | grep -q "would_dispatch"; then
    fail "stdout should NOT show would_dispatch on --execute (but did)"
else
    ok "stdout does NOT show would_dispatch on --execute (correct)"
fi

# ---------- Group 5: tick_pass reason fires on PASS via EXIT trap ----------
echo "=== Group 5: tick_pass reason fires on PASS via EXIT trap ==="

cat > "$TASKS_MD" <<'EOF'
# Current Tasks — Loop Engineering

## Active Tasks

### T-10.651 — Test PASS notify
- **status:** pending
- **acceptance:**
  - [ ] stub
- **estimated_cost_usd:** 0.00
- **notes:** notify test
EOF

MARKER_FILE="${TMPDIR}/notify-reason-marker.txt"
rm -f "$MARKER_FILE"

STUB_NOTIFY="$TMPDIR/stub-notify.sh"
cat > "$STUB_NOTIFY" <<'STUB'
#!/bin/bash
MARKER="${MARKER_FILE:-/tmp/notify-reason-marker.txt}"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reason) echo "$2" >> "$MARKER"; shift 2 ;;
        *) shift ;;
    esac
done
exit 0
STUB
chmod +x "$STUB_NOTIFY"

OUT=$(MARKER_FILE="$MARKER_FILE" \
      DISPATCH_TASKS_MD="$TASKS_MD" \
      DISPATCH_PROGRESS_MD="$TMPDIR/.claude/loop/progress.md" \
      DISPATCH_NOTIFY_CMD="$STUB_NOTIFY" \
      bash "$TMPDIR/scripts/dispatch.sh" T-10.651 --execute 2>&1)
EXIT_CODE=$?

if [[ "$EXIT_CODE" == "0" ]]; then
    ok "PASS dispatch exits 0"
else
    fail "exit $EXIT_CODE (expected 0)"
fi

if grep -q "tick_pass" "$MARKER_FILE" 2>/dev/null; then
    ok "notify fired with tick_pass reason"
else
    fail "notify did NOT fire tick_pass (marker=$(cat "$MARKER_FILE" 2>/dev/null || echo MISSING))"
fi

# ---------- Group 6: --dry-run runs regression sweep (gate test) ----------
echo "=== Group 6: --dry-run runs regression sweep (gate test) ==="

cat > "$TASKS_MD" <<'EOF'
# Current Tasks — Loop Engineering

## Active Tasks

### T-10.652 — Test dry-run regression
- **status:** pending
- **acceptance:**
  - [ ] stub
- **estimated_cost_usd:** 0.00
- **notes:** regression gate test
EOF

FAKE_REGRESSION_FAIL="$TMPDIR/fake-regression-fail.sh"
cat > "$FAKE_REGRESSION_FAIL" <<'STUB'
#!/bin/bash
echo "fake regression sweep failed"
exit 1
STUB
chmod +x "$FAKE_REGRESSION_FAIL"

set +e
OUT=$(DISPATCH_TASKS_MD="$TASKS_MD" \
      DISPATCH_PROGRESS_MD="$TMPDIR/.claude/loop/progress.md" \
      DISPATCH_REGRESSION_CMD="$FAKE_REGRESSION_FAIL" \
      bash "$TMPDIR/scripts/dispatch.sh" T-10.652 --dry-run 2>&1)
EXIT_CODE=$?
set -e

if [[ "$EXIT_CODE" == "1" ]]; then
    ok "regression failure in --dry-run exits 1"
else
    fail "exit $EXIT_CODE (expected 1 on regression failure in dry-run)"
fi

if echo "$OUT" | grep -q "regression_failed"; then
    ok "dry-run output contains regression_failed"
else
    fail "dry-run output missing regression_failed (got: $OUT)"
fi

# ---------- Group 7: --execute does state flips on PASS ----------
echo "=== Group 7: --execute does state flips on PASS ==="

cat > "$TASKS_MD" <<'EOF'
# Current Tasks — Loop Engineering

## Active Tasks

### T-10.653 — Test execute state flip
- **status:** pending
- **acceptance:**
  - [ ] stub
- **estimated_cost_usd:** 0.00
- **notes:** state flip test
EOF

OUT=$(DISPATCH_TASKS_MD="$TASKS_MD" \
      DISPATCH_PROGRESS_MD="$TMPDIR/.claude/loop/progress.md" \
      bash "$TMPDIR/scripts/dispatch.sh" T-10.653 --execute 2>&1)
EXIT_CODE=$?

if [[ "$EXIT_CODE" == "0" ]]; then
    ok "execute mode exits 0 on PASS"
else
    fail "exit $EXIT_CODE (expected 0)"
fi

# Verify status was flipped to done
if grep -A1 "### T-10.653" "$TASKS_MD" | grep -q "status:\*\* done"; then
    ok "tasks.md status flipped to done"
else
    fail "tasks.md status NOT flipped"
fi

# ---------- Summary ----------
echo ""
echo "=== Summary: $PASS pass, $FAIL fail ==="
if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
