#!/usr/bin/env bash
# scripts/dispatch.sh — M10 End-to-End Loop Dispatch
#
# Reads .claude/loop/tasks.md, locates a task entry, and runs the full
# worker → verifier → commit → push chain as one atomic unit.
#
# Pure bash (mirrors M6/M7/M8 style — no Python, no new dependencies).
#
# Usage:
#   bash scripts/dispatch.sh <task_id>          # dry-run by default
#   bash scripts/dispatch.sh <task_id> --dry-run   # explicit dry-run
#   bash scripts/dispatch.sh <task_id> --execute    # real execution
#   bash scripts/dispatch.sh --help
#
# Exit codes:
#   0  PASS / already_complete / dry-run completed
#   1  not_found / regression_failed / execution error
#
# For T-10.1 (scaffold): worker/verifier/commit/push steps are stubbed.
# T-10.2 wires the real M6/M7/M8 hooks.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TASKS_MD="${REPO_ROOT}/.claude/loop/tasks.md"

# --- Args ---
DRY_RUN=1
TASK_ID=""
HELP=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)   DRY_RUN=1; shift ;;
        --execute)   DRY_RUN=0; shift ;;
        -h|--help)   HELP=1; shift ;;
        -*)          echo "unknown flag: $1" >&2; exit 1 ;;
        *)           TASK_ID="$1"; shift ;;
    esac
done

# --- Help ---
if [[ "$HELP" == "1" ]]; then
    sed -n '9,17p' "$0" | sed 's/^# \?//'
    exit 0
fi

# --- Pre-flight: task_id required ---
if [[ -z "$TASK_ID" ]]; then
    echo "fatal: <task_id> required (e.g. T-10.1)" >&2
    echo "usage: $0 <task_id> [--dry-run|--execute] [--help]" >&2
    exit 1
fi

if [[ ! -f "$TASKS_MD" ]]; then
    echo "fatal: tasks.md not found at $TASKS_MD" >&2
    exit 1
fi

# --- Find task entry in tasks.md ---
# Tasks look like:
#   ### T-10.1 — Some task title
#   - **status:** pending
#   - **acceptance:**
# We use awk to find the block starting with the task_id header and
# capture the status line. The block ends at the next `### ` or `## `.
find_task_block() {
    local tid="$1"
    awk -v id="$tid" '
        BEGIN { in_block=0; status=""; found=0 }
        /^### / && $2 == id {
            in_block=1
            found=1
            next
        }
        /^##[# ]/ { if (in_block && found) exit; in_block=0 }
        in_block && /^\- \*\*status:\*\*/ {
            sub(/^\- \*\*status:\*\*/, "")
            gsub(/\*/, "")
            gsub(/^[[:space:]]+|[[:space:]]+$/, "")
            status = $0
            print status
            exit
        }
    ' "$TASKS_MD"
}

# --- Regression sweep (determinism gate) ---
# Runs the same sub-suites as M9 acceptance #5.
# Exits 0 on clean run, non-zero on any failure.
run_regression_sweep() {
    local status=0
    local regressionscript="${DISPATCH_REGRESSION_CMD:-}"

    if [[ -n "$regressionscript" ]]; then
        # Test override: use a custom regression command (for testing only)
        bash "$regressionscript" || return 1
        return 0
    fi

    # M6 worktree helper test
    if [[ -f "${REPO_ROOT}/tests/test_worktree_helper.sh" ]]; then
        bash "${REPO_ROOT}/tests/test_worktree_helper.sh" >/dev/null 2>&1 || status=1
    fi

    # M7 cost dashboard test
    if [[ -f "${REPO_ROOT}/tests/test_cost_dashboard.sh" ]]; then
        bash "${REPO_ROOT}/tests/test_cost_dashboard.sh" >/dev/null 2>&1 || status=1
    fi

    # M8 notify test
    if [[ -f "${REPO_ROOT}/tests/test_notify.sh" ]]; then
        bash "${REPO_ROOT}/tests/test_notify.sh" >/dev/null 2>&1 || status=1
    fi

    return $status
}

# --- Main ---
TASK_STATUS=$(find_task_block "$TASK_ID")

if [[ -z "$TASK_STATUS" ]]; then
    echo "not_found: $TASK_ID"
    exit 1
fi

echo "task: $TASK_ID"
echo "status: $TASK_STATUS"

# --- Idempotent replay ---
if [[ "$TASK_STATUS" == "done" ]]; then
    echo "already_complete"
    exit 0
fi

# --- Determinism gate (run before any LLM work) ---
if [[ "$DRY_RUN" == "0" ]]; then
    echo "running regression sweep..."
    if ! run_regression_sweep; then
        echo "regression_failed"
        exit 1
    fi
    echo "regression_sweep: PASS"
fi

# --- Dry-run banner ---
if [[ "$DRY_RUN" == "1" ]]; then
    echo "mode: dry-run"
    echo "would_dispatch: $TASK_ID"
    echo ""
    echo "=== Would run (stubbed in T-10.1, wired in T-10.2) ==="
    echo "  1. [STUB] spawn worker in worktree"
    echo "  2. [STUB] worker implements task"
    echo "  3. [STUB] verifier judges output"
    echo "  4. [STUB] on PASS: commit + push"
    echo "  5. [STUB] on PASS: flip roadmap + tasks.md status"
    echo "  6. [STUB] notify (tick_pass / tick_fail)"
    echo ""
    echo "dry_run_complete"
    exit 0
fi

# --- Execute (T-10.2 wiring goes here) ---
echo "mode: execute"
echo ""
echo "=== T-10.2 will wire: M6 worktree → M7/M8 hooks → EXIT trap ==="

# Placeholder: T-10.2 replaces this with real hook invocations.
# Meanwhile, scaffold reports execution started but nothing ran.
echo "no_op: execute mode requires T-10.2 hook wiring"
exit 0
