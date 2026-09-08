#!/usr/bin/env bash
# scripts/streak-tracker.sh — M9 Streak Tracker
#
# Reads .claude/loop/progress.md, computes consecutive-day PASS streak
# (current_streak vs max_streak), writes a deterministic markdown report to
# .claude/loop/logs/streak-report.md.
#
# Streak-break (latest day verdict is NEEDS_FIX / BLOCKED / FAIL /
# BUDGET_ABORT) sets exit code 2 so M8 notification channel can pipe on
# `$? -eq 2` without parsing the report file.
#
# Pure bash + awk (per M7 SPEC architecture note — mirrors M6
# worktree-helper.sh pattern, zero LLM cost).
#
# Idempotent: re-running produces byte-identical content EXCEPT for the
# `generated_at` timestamp line. Metric body (streak values) is deterministic.
#
# Day boundary = UTC calendar day (per M9 SPEC Open Question Q2).
#
# Usage:
#   bash scripts/streak-tracker.sh            # write report, exit 0/2
#   bash scripts/streak-tracker.sh --dry-run  # print report to stdout

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROGRESS_MD="${REPO_ROOT}/.claude/loop/progress.md"
LOGS_DIR="${REPO_ROOT}/.claude/loop/logs"
REPORT="${LOGS_DIR}/streak-report.md"

# --- Args ---
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help)
            sed -n '2,22p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "unknown arg: $arg" >&2; exit 1 ;;
    esac
done

# --- Pre-flight ---
if [[ ! -f "$PROGRESS_MD" ]]; then
    echo "fatal: progress.md not found at $PROGRESS_MD" >&2
    exit 1
fi

# --- Extract all entries and compute streak stats in a single awk pass ---
# Output: window_start window_end total_passes total_breaks current_streak max_streak
# last_paused_at last_tick_at healthy most_recent_day
read -r WINDOW_START WINDOW_END TOTAL_PASSES TOTAL_BREAKS \
          CURRENT_STREAK MAX_STREAK LAST_PAUSED_AT LAST_TICK_AT \
          HEALTHY MOST_RECENT_DAY < <(awk \
    '
    /^## [0-9]{4}-[0-9]{2}-[0-9]{2}/ {
        # Extract UTC date from timestamp: ## 2026-09-07T21:52:33Z | ...
        # date is at chars 4-13 (10 chars: YYYY-MM-DD)
        date = substr($0, 4, 10)

        # Extract verdict: last field after final |
        n = split($0, parts, "|")
        verdict = trim(parts[n])

        # Track first and last seen dates
        if (window_start == "" || date < window_start) window_start = date
        if (date > window_end) window_end = date

        # Store latest verdict per date (last entry wins)
        last_verdict[date] = verdict
        dates[date] = 1
    }
    END {
        # Sort dates
        n_dates = 0
        for (d in dates) date_list[++n_dates] = d
        for (i = 1; i <= n_dates; i++)
            for (j = i+1; j <= n_dates; j++)
                if (date_list[i] > date_list[j]) {
                    tmp = date_list[i]; date_list[i] = date_list[j]; date_list[j] = tmp
                }

        # Compute streak
        current_streak = 0
        max_streak = 0
        run_streak = 0
        last_tick_at = "—"
        last_paused_at = "—"
        total_passes = 0
        total_breaks = 0
        healthy = "yes"
        most_recent_day = window_end

        for (i = 1; i <= n_dates; i++) {
            d = date_list[i]
            v = last_verdict[d]

            if (v == "PASS") {
                total_passes++
                last_tick_at = d
                run_streak++
                if (run_streak > max_streak) max_streak = run_streak
            } else {
                total_breaks++
                if (last_paused_at == "—") last_paused_at = d
                run_streak = 0
            }
        }

        # current_streak: count consecutive PASS days from today backwards
        # If most recent day is not PASS, streak is 0 (broken)
        most_recent_verdict = last_verdict[most_recent_day]
        if (most_recent_verdict == "PASS") {
            current_streak = 1
            for (i = n_dates; i >= 1; i--) {
                d = date_list[i]
                if (d == most_recent_day) continue  # already counted
                prev = last_verdict[d]
                if (prev == "PASS") current_streak++
                else break
            }
        } else {
            current_streak = 0
            healthy = "no"
        }

        if (window_start == "") window_start = "—"
        if (window_end == "") window_end = "—"

        printf "%s %s %d %d %d %d %s %s %s %s\n",
            window_start, window_end, total_passes, total_breaks,
            current_streak, max_streak, last_paused_at, last_tick_at,
            healthy, most_recent_day
    }
    function trim(s) {
        sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s
    }
    ' "$PROGRESS_MD")

# Default empty values
[[ -z "$WINDOW_START" ]] && WINDOW_START="—"
[[ -z "$WINDOW_END" ]] && WINDOW_END="—"
[[ -z "$TOTAL_PASSES" ]] && TOTAL_PASSES=0
[[ -z "$TOTAL_BREAKS" ]] && TOTAL_BREAKS=0
[[ -z "$CURRENT_STREAK" ]] && CURRENT_STREAK=0
[[ -z "$MAX_STREAK" ]] && MAX_STREAK=0
[[ -z "$LAST_PAUSED_AT" ]] && LAST_PAUSED_AT="—"
[[ -z "$LAST_TICK_AT" ]] && LAST_TICK_AT="—"
[[ -z "$HEALTHY" ]] && HEALTHY="yes"
[[ -z "$MOST_RECENT_DAY" ]] && MOST_RECENT_DAY="—"

# Exit code: 0 = healthy, 2 = streak-break
if [[ "$HEALTHY" == "no" ]]; then
    EXIT_CODE=2
else
    EXIT_CODE=0
fi

# --- Report assembly ---
TODAY=$(date -u +%Y-%m-%d)
GENERATED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REPORT_BODY="# Streak Report — ${TODAY}

## Status
- **current_streak:** ${CURRENT_STREAK}
- **max_streak:** ${MAX_STREAK}
- **last_paused_at:** ${LAST_PAUSED_AT}
- **last_tick_at:** ${LAST_TICK_AT}

## Detail
- **window_start:** ${WINDOW_START}
- **window_end:** ${WINDOW_END}
- **total_passes:** ${TOTAL_PASSES}
- **total_breaks:** ${TOTAL_BREAKS}
- **healthy:** ${HEALTHY}
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
