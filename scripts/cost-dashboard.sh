#!/usr/bin/env bash
# scripts/cost-dashboard.sh — M7 Cost Dashboard
#
# Reads .claude/loop/progress.md, aggregates cost entries for today +
# yesterday UTC, writes a deterministic markdown report to
# .claude/loop/logs/cost-report.md.
#
# Spike alarm (>$10/day default, configurable via COST_DASHBOARD_SPIKE_USD)
# sets exit code 2 so M8 notification channel can pipe on `$? -eq 2`
# without parsing the report file.
#
# Pure bash + awk (per M7 SPEC architecture note — mirrors M6
# worktree-helper.sh pattern, keeps loop's cost_cap_usd=0.50 headroom intact).
#
# Idempotent: re-running within the same UTC day produces byte-identical
# content EXCEPT for the `generated_at` timestamp line. Metric body
# (ticks / usd_total / usd_avg / spike_alarm) is deterministic.
#
# Usage:
#   bash scripts/cost-dashboard.sh            # write report, exit 0/2
#   bash scripts/cost-dashboard.sh --dry-run  # print report to stdout

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROGRESS_MD="${REPO_ROOT}/.claude/loop/progress.md"
LOGS_DIR="${REPO_ROOT}/.claude/loop/logs"
REPORT="${LOGS_DIR}/cost-report.md"

# --- Args ---
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help)
            sed -n '2,16p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "unknown arg: $arg" >&2; exit 1 ;;
    esac
done

# --- Date setup (today + yesterday UTC) ---
TODAY=$(date -u +%Y-%m-%d)
# GNU date (Linux, Git Bash) vs BSD date (macOS): handle both
YESTERDAY=$(date -u -d 'yesterday' +%Y-%m-%d 2>/dev/null \
             || date -u -v-1d +%Y-%m-%d 2>/dev/null \
             || echo "")
if [[ -z "$YESTERDAY" ]]; then
    echo "fatal: cannot compute yesterday's date (need GNU or BSD date)" >&2
    exit 1
fi

# --- Pre-flight ---
if [[ ! -f "$PROGRESS_MD" ]]; then
    echo "fatal: progress.md not found at $PROGRESS_MD" >&2
    exit 1
fi

# --- Aggregation (single awk pass, deterministic) ---
# Output: space-separated "<count> <total_usd> <avg_usd>" on one line.
read -r TICKS_DAY USD_TOTAL USD_AVG < <(awk \
    -v today="$TODAY" \
    -v yesterday="$YESTERDAY" '
    /^## [0-9]{4}-[0-9]{2}-[0-9]{2}/ {
        date = substr($0, 4, 10)
        if (date == today || date == yesterday) keep = 1
        else keep = 0
        next
    }
    keep && /^- cost_usd: / {
        val = $3 + 0
        count++
        total += val
        keep = 0
    }
    END {
        if (count == 0) avg = 0.0
        else avg = total / count
        printf "%d %.2f %.2f\n", count, total, avg
    }
' "$PROGRESS_MD")

# Default to 0/0.00/0.00 when awk output is empty (no matching entries)
[[ -z "$TICKS_DAY" ]] && TICKS_DAY=0
[[ -z "$USD_TOTAL" ]] && USD_TOTAL="0.00"
[[ -z "$USD_AVG" ]] && USD_AVG="0.00"

# --- Spike alarm check (awk avoids `bc` dependency on Windows Git Bash) ---
SPIKE_THRESHOLD="${COST_DASHBOARD_SPIKE_USD:-10.0}"
SPIKE_FLAG=$(awk -v t="$USD_TOTAL" -v thr="$SPIKE_THRESHOLD" \
    'BEGIN { print (t + 0 > thr + 0) ? 1 : 0 }')

if [[ "$SPIKE_FLAG" == "1" ]]; then
    SPIKE_ALARM="SPIKE (>\$${SPIKE_THRESHOLD}/day: \$${USD_TOTAL})"
    EXIT_CODE=2
else
    SPIKE_ALARM="none"
    EXIT_CODE=0
fi

# --- Report assembly ---
GENERATED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REPORT_BODY="# Cost Report — ${TODAY}

- **ticks_day:** ${TICKS_DAY}
- **usd_total:** \$${USD_TOTAL}
- **usd_avg_per_tick:** \$${USD_AVG}
- **spike_alarm:** ${SPIKE_ALARM}
- **generated_at:** ${GENERATED_AT}
"

# --- Output ---
if [[ "$DRY_RUN" == "1" ]]; then
    printf "%s" "$REPORT_BODY"
    exit "$EXIT_CODE"
fi

mkdir -p "$LOGS_DIR"
printf "%s" "$REPORT_BODY" > "$REPORT"
exit "$EXIT_CODE"
