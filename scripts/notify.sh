#!/usr/bin/env bash
# scripts/notify.sh — M8 Notification Channel
#
# Sends a single message via HTTP webhook (ntfy.sh by default) when the
# loop needs human intervention: M7 spike alarm (cost > $10/day), tick
# FAIL/NEEDS_FIX/BLOCKED/tick_pass, or a manual test message. Topic name IS the
# auth secret — pick something unguessable (16+ chars).
#
# Pure bash + curl (per M8 SPEC architecture note — mirrors M6/M7
# pattern, keeps loop's cost_cap_usd intact, no Python).
#
# Idempotent: dedupes by (reason, sha256(message)). Re-sending the same
# reason+message within LOOP_NOTIFY_COOLDOWN_SEC (default 600s = 10min)
# suppresses the duplicate (exit 0, log "suppressed by cooldown").
#
# Usage:
#   bash scripts/notify.sh --reason spike_alarm --message "..."
#   bash scripts/notify.sh --reason test --message "ping" --dry-run
#   bash scripts/notify.sh --reason tick_fail --message "..." --priority high

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_FILE="${REPO_ROOT}/.claude/loop/logs/notify-state.json"

# --- Defaults from env ---
TOPIC="${LOOP_NOTIFY_TOPIC:-}"
SERVER="${LOOP_NOTIFY_SERVER:-https://ntfy.sh}"
PRIORITY="${LOOP_NOTIFY_PRIORITY:-default}"
COOLDOWN_SEC="${LOOP_NOTIFY_COOLDOWN_SEC:-600}"

# --- Arg parsing (while loop — `for arg in "$@"` with `shift` inside is the
# classic bash pitfall: the for iterator and shift advance $@ concurrently
# and consume args in the wrong order). ---
REASON=""
MESSAGE=""
DRY_RUN=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reason)        REASON="${2:-}"; shift 2 ;;
        --message)       MESSAGE="${2:-}"; shift 2 ;;
        --priority)      PRIORITY="${2:-}"; shift 2 ;;
        --dry-run)       DRY_RUN=1; shift ;;
        -h|--help)
            sed -n '2,21p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "unknown arg: $1" >&2; exit 1 ;;
    esac
done

# --- Pre-flight ---
if [[ -z "$REASON" ]]; then
    echo "fatal: --reason required (e.g. spike_alarm, tick_fail, needs_fix, test)" >&2
    exit 1
fi
if [[ -z "$MESSAGE" ]]; then
    echo "fatal: --message required" >&2
    exit 1
fi
if [[ -z "$TOPIC" ]]; then
    # Disabled mode: exit 0 silently (per SPEC §1 — operators may not have
    # a topic configured during early M8 rollout; the script should be a
    # no-op in that case, not a fatal error).
    echo "info: LOOP_NOTIFY_TOPIC not set, notification suppressed" >&2
    exit 0
fi

# --- Idempotency: hash message, check cooldown ---
# sha256sum (GNU) vs shasum -a 256 (BSD/macOS)
MSG_HASH=$(printf "%s" "$MESSAGE" | (sha256sum 2>/dev/null || shasum -a 256 2>/dev/null || true) | awk '{print $1}')
if [[ -z "$MSG_HASH" ]]; then
    echo "fatal: cannot compute sha256 (need sha256sum or shasum)" >&2
    exit 1
fi
KEY="${REASON}:${MSG_HASH}"
NOW=$(date -u +%s)

if [[ -f "$STATE_FILE" ]]; then
    LAST_SENT=$(awk -v k="$KEY" '$1 == k {print $2}' "$STATE_FILE" 2>/dev/null || true)
    if [[ -n "$LAST_SENT" ]]; then
        AGE=$(( NOW - LAST_SENT ))
        if (( AGE < COOLDOWN_SEC )); then
            echo "info: suppressed by cooldown (${AGE}s < ${COOLDOWN_SEC}s for ${KEY})" >&2
            exit 0
        fi
    fi
fi

# --- Build curl command (printed in dry-run, executed otherwise) ---
TITLE="[life-oss] ${REASON} — $(printf '%s' "$MESSAGE" | head -1 | cut -c1-60)"
URL="${SERVER}/${TOPIC}"
CURL_ARGS=(
    -fsS
    -X POST
    -H "Title: ${TITLE}"
    -H "Priority: ${PRIORITY}"
    -H "Tags: ${REASON}"
    --data-binary "${MESSAGE}"
    "${URL}"
)

# --- Output ---
if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN: would execute:"
    # Build single-line space-separated curl invocation for human inspection
    # (printf with one %s per array element would print each flag on its own
    # line — unreadable). Args containing spaces are not expected here.
    printf '  curl'; for a in "${CURL_ARGS[@]}"; do printf ' %s' "$a"; done; printf '\n'
    exit 0
fi

# --- Pre-flight: curl must exist ---
if ! command -v curl >/dev/null 2>&1; then
    echo "fatal: curl not found in PATH (notify requires curl to POST)" >&2
    exit 1
fi

# --- Send ---
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' "${CURL_ARGS[@]}" || true)
if [[ -z "$HTTP_CODE" || "$HTTP_CODE" -ge 400 ]]; then
    echo "fatal: ntfy returned HTTP ${HTTP_CODE:-no-response} for ${URL}" >&2
    exit 2
fi

# --- Persist state (mkdir if missing) ---
mkdir -p "$(dirname "$STATE_FILE")"
# Single-line append (idempotency table is append-only; periodic cleanup is
# out of scope — file stays small since keys are hash-deduplicated)
echo "${KEY} ${NOW}" >> "$STATE_FILE"

echo "ok: sent (http=${HTTP_CODE}, key=${KEY})" >&2
exit 0
