#!/bin/bash
# notify-wrap.sh - wrap a scheduled command with notification on completion.
# Usage: notify-wrap.sh <name> <title> <cmd...>
#
# Runs the command, captures exit code + duration, then posts a notify
# summary so the user gets pinged on success/failure.
#
# M76: designed to be the "command" for each schedule in schedules.json.
# Replaces the bare `bash loop-tick.sh` etc. with
# `bash .claude/helpers/notify-wrap.sh loop-tick "Loop tick" "bash .claude/loop/loop-tick.sh"`.

set -u

NAME="${1:?usage: notify-wrap.sh NAME TITLE CMD...}"
TITLE="${2:?usage: notify-wrap.sh NAME TITLE CMD...}"
shift 2

if [ "$#" -eq 0 ]; then
    echo "ERROR: notify-wrap.sh requires at least one command after NAME TITLE" >&2
    exit 64
fi

# Run the command, capture exit code + elapsed time.
# Disable -e so the failed-command exit doesn't terminate the wrapper.
START=$(date +%s)
set +e
# bash "$@" single-element quirk: with $#=1, "$@" treats the arg as
# one literal string (e.g. "echo hello" is treated as command name
# "echo hello" not "echo" + "hello"). Use eval for the single-arg
# case which forces shell re-tokenization.
if [ "$#" -eq 1 ]; then
    eval "$1"
else
    "$@"
fi
RC=$?
set -e
END=$(date +%s)
ELAPSED=$((END - START))

if [ "$RC" -eq 0 ]; then
    LEVEL="success"
else
    LEVEL="error"
fi

# Build body with elapsed time + rc
BODY="rc=$RC elapsed=${ELAPSED}s"

# Pick notification command: installed life binary or python -m
if command -v life >/dev/null 2>&1; then
    NOTIFY_CMD="life"
else
    NOTIFY_CMD="python -m life.cli.cli"
fi

# Ensure repo root on PYTHONPATH so life module is importable
THIS_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$THIS_DIR/../.." && pwd)"
export PYTHONPATH="${PYTHONPATH:-}${PYTHONPATH:+:}${REPO_ROOT}/src"

# Post notification (best-effort: never propagate notify failure back to daemon)
$NOTIFY_CMD notify send "$TITLE" "$BODY" --level "$LEVEL" >/dev/null 2>&1 || {
    echo "[notify-wrap] warning: notify call failed (continuing)" >&2
}

exit $RC
