#!/usr/bin/env bash
# tests/test_streak_tracker.sh — end-to-end test for scripts/streak-tracker.sh
#
# Acceptance: specs/M9-production-mode/SPEC.md criterion #4 — "tests cover:
# cold-start / healthy / break / idempotent".
#
# Test design (per spec):
#   1. cold-start: empty progress.md -> report has 0-day state, exit 0
#   2. healthy:    3 consecutive UTC days of PASS -> current_streak=3,
#                  max_streak=3, last_paused_at="—", exit 0
#   3. break:      today has NEEDS_FIX -> current_streak=0 (or 1 if yesterday
#                  was PASS), healthy=no, exit 2
#   4. idempotent: re-run produces byte-identical metric body (only
#                  generated_at differs)
#
# Implementation: copies the script into a temp dir so its REPO_ROOT
# resolution (`$(dirname "$0")/..`) lands on the temp dir. Mirrors
# test_cost_dashboard.sh pattern; no script modification.
#
# POSIX + Git Bash compatible. Pure shell, no Python deps.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPT="$PROJECT_ROOT/scripts/streak-tracker.sh"

PASS=0
FAIL=0
fail() { echo "FAIL: $*"; FAIL=$((FAIL + 1)); }
ok()   { echo "PASS: $*"; PASS=$((PASS + 1)); }

# Temp sandbox: <tmp>/scripts/streak-tracker.sh + <tmp>/.claude/loop/{progress.md,logs/streak-report.md}
TMPDIR="$(mktemp -d -t streak-tracker-test.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT
mkdir -p "$TMPDIR/scripts" "$TMPDIR/.claude/loop/logs"
cp "$SCRIPT" "$TMPDIR/scripts/streak-tracker.sh"
PROGRESS="$TMPDIR/.claude/loop/progress.md"
REPORT="$TMPDIR/.claude/loop/logs/streak-report.md"
RUN() { bash "$TMPDIR/scripts/streak-tracker.sh" "$@"; }

# Date helpers (GNU date first, BSD fallback for macOS portability)
TODAY=$(date -u +%Y-%m-%d)
YESTERDAY=$(date -u -d 'yesterday' +%Y-%m-%d 2>/dev/null \
             || date -u -v-1d +%Y-%m-%d 2>/dev/null || echo "")
DAY_BEFORE=$(date -u -d '2 days ago' +%Y-%m-%d 2>/dev/null \
             || date -u -v-2d +%Y-%m-%d 2>/dev/null || echo "")
if [[ -z "$YESTERDAY" || -z "$DAY_BEFORE" ]]; then
    echo "fatal: cannot compute yesterday/2-days-ago dates (need GNU or BSD date)" >&2
    exit 1
fi

# ---------- Test 1: cold-start (empty progress.md) ----------
echo "=== Test 1: cold-start (empty progress.md) ==="
cat > "$PROGRESS" <<EOF
# Empty progress.md — no tick entries
EOF

set +e
RUN >/dev/null 2>&1
EXIT_CODE=$?
set -e

if [[ "$EXIT_CODE" == "0" ]]; then
    ok "cold-start exit 0 (no entries, no break)"
else
    fail "cold-start exit $EXIT_CODE (expected 0)"
fi

# Verify report has 0-day state
CS=$(awk '/^- \*\*current_streak:/ {print $3}' "$REPORT" 2>/dev/null || echo "0")
MS=$(awk '/^- \*\*max_streak:/ {print $3}' "$REPORT" 2>/dev/null || echo "0")
if [[ "$CS" == "0" && "$MS" == "0" ]]; then
    ok "current_streak=0 max_streak=0 (cold-start)"
else
    fail "cold-start metrics: current=$CS max=$MS (expected 0/0)"
    cat "$REPORT" || true
fi

# ---------- Test 2: healthy streak (3 consecutive UTC days, all PASS) ----------
echo "=== Test 2: healthy (3 consecutive UTC days of PASS) ==="
cat > "$PROGRESS" <<EOF
## ${DAY_BEFORE}T08:00:00Z | day1-tick | PASS
- cost_usd: 0.10

## ${DAY_BEFORE}T12:00:00Z | day1-tick-2 | PASS
- cost_usd: 0.20

## ${YESTERDAY}T08:00:00Z | day2-tick | PASS
- cost_usd: 0.15

## ${TODAY}T08:00:00Z | day3-tick | PASS
- cost_usd: 0.25
EOF

set +e
RUN >/dev/null 2>&1
EXIT_CODE=$?
set -e

if [[ "$EXIT_CODE" == "0" ]]; then
    ok "healthy run exit 0 (no break in most recent day)"
else
    fail "healthy run exit $EXIT_CODE (expected 0)"
    cat "$REPORT" || true
fi

CS=$(awk '/^- \*\*current_streak:/ {print $3}' "$REPORT")
MS=$(awk '/^- \*\*max_streak:/ {print $3}' "$REPORT")
LT=$(awk '/^- \*\*last_tick_at:/ {print $3}' "$REPORT")
LP=$(awk '/^- \*\*last_paused_at:/ {print $3}' "$REPORT")

if [[ "$CS" == "3" ]]; then
    ok "current_streak=3 (3 consecutive healthy days)"
else
    fail "current_streak=$CS (expected 3)"
fi
if [[ "$MS" == "3" ]]; then
    ok "max_streak=3 (matches current)"
else
    fail "max_streak=$MS (expected 3)"
fi
if [[ "$LT" == "$TODAY" ]]; then
    ok "last_tick_at=$TODAY (today)"
else
    fail "last_tick_at=$LT (expected $TODAY)"
fi
if [[ "$LP" == "—" || "$LP" == "(none)" ]]; then
    ok "last_paused_at=$LP (no breaks ever)"
else
    fail "last_paused_at=$LP (expected '—' or '(none)')"
fi

# ---------- Test 3: streak-break (most recent day has NEEDS_FIX) ----------
echo "=== Test 3: streak-break (most recent day has NEEDS_FIX) ==="
cat > "$PROGRESS" <<EOF
## ${YESTERDAY}T08:00:00Z | healthy-tick | PASS
- cost_usd: 0.10

## ${TODAY}T08:00:00Z | breaking-tick | NEEDS_FIX
- cost_usd: 0.50
EOF

set +e
RUN >/dev/null 2>&1
EXIT_CODE=$?
set -e

if [[ "$EXIT_CODE" == "2" ]]; then
    ok "streak-break exit 2 (most recent day has NEEDS_FIX)"
else
    fail "streak-break exit $EXIT_CODE (expected 2)"
    cat "$REPORT" || true
fi

CS=$(awk '/^- \*\*current_streak:/ {print $3}' "$REPORT")
LP=$(awk '/^- \*\*last_paused_at:/ {print $3}' "$REPORT")

if [[ "$CS" == "0" ]]; then
    ok "current_streak=0 (broke on today)"
else
    fail "current_streak=$CS (expected 0)"
fi
if [[ "$LP" == "$TODAY" ]]; then
    ok "last_paused_at=$TODAY (most recent break day)"
else
    fail "last_paused_at=$LP (expected $TODAY)"
fi

# ---------- Test 4: idempotent re-run ----------
echo "=== Test 4: idempotent re-run (metric body identical) ==="
cat > "$PROGRESS" <<EOF
## ${TODAY}T08:00:00Z | idem-tick | PASS
- cost_usd: 0.10

## ${TODAY}T12:00:00Z | idem-tick-2 | PASS
- cost_usd: 0.20
EOF

RUN >/dev/null 2>&1
cp "$REPORT" "$TMPDIR/report-1.md"
sleep 1
RUN >/dev/null 2>&1
cp "$REPORT" "$TMPDIR/report-2.md"

# Diff excluding generated_at (wall-clock metadata)
DIFF=$(diff <(grep -v 'generated_at:' "$TMPDIR/report-1.md") \
            <(grep -v 'generated_at:' "$TMPDIR/report-2.md") || true)

if [[ -z "$DIFF" ]]; then
    ok "metric body identical across re-runs (generated_at excluded)"
else
    fail "metric body diverged across re-runs:"
    echo "$DIFF"
fi

# ---------- Summary ----------
echo ""
echo "=== Summary: $PASS pass, $FAIL fail ==="
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
