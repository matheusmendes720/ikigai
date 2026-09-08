#!/usr/bin/env bash
# auto-start-loop-tick.sh — idempotent SessionStart hook (POSIX/Git Bash).
#
# Purpose: when Claude Code starts a new session, ensure the loop-tick
# cron schedule is running (started by M1). If it's already running,
# this is a no-op.
#
# Wired into .claude/settings.json SessionStart hook chain (T-9.2).
# Mirror of scripts/auto-start-loop-tick.bat for non-Windows runners.
# Always exits 0 — MUST NOT block session start.

set -u

# Resolve project root. Prefer CLAUDE_PROJECT_DIR (set by Claude Code hooks
# via session-start env injection); fall back to $HOME for user-level installs.
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    PROJECT_ROOT="$CLAUDE_PROJECT_DIR"
elif [ -n "${REPO_ROOT:-}" ]; then
    PROJECT_ROOT="$REPO_ROOT"
elif [ -n "${HOME:-}" ]; then
    PROJECT_ROOT="$HOME"
else
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

DAEMON="$PROJECT_ROOT/.claude/helpers/daemon-manager.sh"

# Silent no-op if daemon-manager.sh is missing.
[ -f "$DAEMON" ] || exit 0

# start-schedule is already idempotent (daemon-manager-schedules.sh checks
# is_running and returns 0 if the schedule is already up).
# Suppress all output; capture + discard.
bash "$DAEMON" start-schedule loop-tick >/dev/null 2>&1 || true

exit 0