#!/usr/bin/env bash
# tests/test_cost_dashboard.sh — end-to-end test for scripts/cost-dashboard.sh
#
# Acceptance: specs/M7-cost-dashboard/SPEC.md criterion #5 — "tests cover:
# aggregation correctness / spike alarm / idempotent re-run".
#
# Test design (per spec):
#   1. Aggregation: seed synthetic progress.md with 2 today + 1 yesterday
#      entries (cost_usd: 0.50, 1.30, 0.20), run dashboard, assert parsed
#      output matches expected metrics (ticks_day=3, usd_total=$2.00,
#      usd_avg_per_tick=$0.67).
#   2. Spike alarm: seed today entries summing > $10, assert exit code = 2
#      and report contains `spike_alarm: SPIKE`.
#   3. Idempotent re-run: run twice, assert metric body identical
#      (`generated_at` excluded from comparison).
#
# Implementation: copies the script into a temp dir so its REPO_ROOT
# resolution (`$(dirname "$0")/..`) lands on the temp dir. No script
# modification needed — keeps the production script exactly as spec'd.
#
# POSIX + Git Bash compatible. Pure shell, no Python deps.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPT="$PROJECT_ROOT/scripts/cost-dashboard.sh"

PASS=0
FAIL=0
fail() { echo "FAIL: $*"; FAIL=$((FAIL + 1)); }
ok()   { echo "PASS: $*"; PASS=$((PASS + 1)); }

# Temp sandbox: <tmp>/scripts/cost-dashboard.sh + <tmp>/.claude/loop/{progress.md,logs/cost-report.md}
# Script's REPO_ROOT resolution uses $(dirname "$0")/.., so placing the script at
# <tmp>/scripts/ makes REPO_ROOT resolve to <tmp> — matches spec's expected layout.
TMPDIR="$(mktemp -d -t cost-dashboard-test.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT
mkdir -p "$TMPDIR/scripts" "$TMPDIR/.claude/loop/logs"
cp "$SCRIPT" "$TMPDIR/scripts/cost-dashboard.sh"
PROGRESS="$TMPDIR/.claude/loop/progress.md"
REPORT="$TMPDIR/.claude/loop/logs/cost-report.md"
RUN() { bash "$TMPDIR/scripts/cost-dashboard.sh" "$@"; }

TODAY=$(date -u +%Y-%m-%d)
YESTERDAY=$(date -u -d 'yesterday' +%Y-%m-%d 2>/dev/null \
             || date -u -v-1d +%Y-%m-%d 2>/dev/null || echo "")

# ---------- Test 1: aggregation correctness ----------
echo "=== Test 1: aggregation correctness ==="
cat > "$PROGRESS" <<EOF
## ${YESTERDAY} | yesterday-tick | PASS
- commit: aaa
- cost_usd: 0.20

## ${TODAY} | today-tick-1 | PASS
- commit: bbb
- cost_usd: 0.50

## ${TODAY} | today-tick-2 | PASS
- commit: ccc
- cost_usd: 1.30
EOF

if RUN >/dev/null 2>&1; then
    ok "run exit 0"
else
    fail "run exit non-zero"
    cat "$REPORT" || true
    exit 1
fi

# Parse report
TICKS=$(awk '/^- \*\*ticks_day:/ {print $3}' "$REPORT")
TOTAL=$(awk '/^- \*\*usd_total:/ {print $3}' "$REPORT" | tr -d '$')
AVG=$(awk '/^- \*\*usd_avg_per_tick:/ {print $3}' "$REPORT" | tr -d '$')

if [[ "$TICKS" == "3" ]]; then ok "ticks_day=3 (2 today + 1 yesterday)"; else fail "ticks_day=$TICKS (expected 3)"; fi
if [[ "$TOTAL" == "2.00" ]]; then ok "usd_total=\$2.00 (0.50+1.30+0.20)"; else fail "usd_total=$TOTAL (expected 2.00)"; fi
if [[ "$AVG" == "0.67" ]]; then ok "usd_avg_per_tick=\$0.67"; else fail "usd_avg=$AVG (expected 0.67)"; fi

# ---------- Test 2: spike alarm ----------
echo "=== Test 2: spike alarm (usd_total > \$10) ==="
cat > "$PROGRESS" <<EOF
## ${TODAY} | big-tick-1 | PASS
- cost_usd: 6.00

## ${TODAY} | big-tick-2 | PASS
- cost_usd: 5.50
EOF

set +e
RUN >/dev/null 2>&1
EXIT_CODE=$?
set -e

if [[ "$EXIT_CODE" == "2" ]]; then ok "exit code 2 (spike)"; else fail "exit code $EXIT_CODE (expected 2)"; fi

if grep -q "spike_alarm:\*\* SPIKE" "$REPORT"; then
    ok "report contains spike_alarm SPIKE line"
else
    fail "report missing spike_alarm SPIKE line"
    cat "$REPORT"
fi

# ---------- Test 3: idempotent re-run ----------
echo "=== Test 3: idempotent re-run (metric body identical) ==="
cat > "$PROGRESS" <<EOF
## ${TODAY} | idem-tick-1 | PASS
- cost_usd: 0.10

## ${TODAY} | idem-tick-2 | PASS
- cost_usd: 0.20
EOF

RUN >/dev/null 2>&1
cp "$REPORT" "$TMPDIR/report-1.md"
sleep 1
RUN >/dev/null 2>&1
cp "$REPORT" "$TMPDIR/report-2.md"

# Diff excluding the generated_at line (wall-clock metadata)
DIFF=$(diff <(grep -v '^- \*\*generated_at:' "$TMPDIR/report-1.md") \
            <(grep -v '^- \*\*generated_at:' "$TMPDIR/report-2.md") || true)

if [[ -z "$DIFF" ]]; then
    ok "metric body identical across re-runs (timestamps excluded)"
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
