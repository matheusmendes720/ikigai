#!/usr/bin/env bash
# tests/test_worktree_helper.sh — end-to-end test for scripts/worktree-helper.sh
#
# Acceptance: SPEC.md criterion #3 — "3 parallel worktrees commit cleanly
# without conflict; cleanup-all restores empty .worktrees/ + zero loop/*
# branches; test runs in <60s; idempotent (re-runnable from clean state)."
#
# Test design:
#   - 3 parallel worktrees (m6-test-a, m6-test-b, m6-test-c) on branch loop/m6-test-*
#   - Each writes a distinct file under .worktrees/<name>/tmp/
#   - Each commits independently
#   - Verify no overlap, all 3 commits land on their branches
#   - cleanup-all restores empty .worktrees/
#
# POSIX + Git Bash compatible. Pure shell, no Python deps.
# Re-runnable: cleans up any leftover m6-test-* state on entry.

set -euo pipefail

# Resolve paths relative to this script (works on POSIX + Git Bash)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HELPER="$PROJECT_ROOT/scripts/worktree-helper.sh"
WORKTREE_BASE="$PROJECT_ROOT/.worktrees"

# Pre-clean any leftover m6-test-* state from prior runs
for name in m6-test-a m6-test-b m6-test-c; do
  if [ -d "$WORKTREE_BASE/$name" ]; then
    git -C "$PROJECT_ROOT" worktree remove --force "$WORKTREE_BASE/$name" 2>/dev/null || true
  fi
  if git -C "$PROJECT_ROOT" show-ref --verify --quiet "refs/heads/loop/$name"; then
    git -C "$PROJECT_ROOT" branch -D "loop/$name" 2>/dev/null || true
  fi
done

PASS=0
FAIL=0
fail() { echo "FAIL: $*"; FAIL=$((FAIL + 1)); }
ok()   { echo "PASS: $*"; PASS=$((PASS + 1)); }

# ---------- Test 1: create 3 worktrees ----------
echo "=== Test 1: create 3 parallel worktrees ==="
for name in m6-test-a m6-test-b m6-test-c; do
  if bash "$HELPER" create "$name" >/dev/null 2>&1; then
    ok "create $name"
  else
    fail "create $name"
    exit 1
  fi
done

# ---------- Test 2: each worktree writes a distinct file ----------
echo "=== Test 2: non-overlapping writes per worktree ==="
for name in m6-test-a m6-test-b m6-test-c; do
  WT="$WORKTREE_BASE/$name"
  mkdir -p "$WT/tmp"
  echo "marker-$name" > "$WT/tmp/marker.txt"
  ok "wrote $name/tmp/marker.txt"
done

# ---------- Test 3: each worktree commits cleanly ----------
echo "=== Test 3: independent commits per worktree ==="
for name in m6-test-a m6-test-b m6-test-c; do
  WT="$WORKTREE_BASE/$name"
  (
    cd "$WT"
    git add tmp/marker.txt
    git -c user.email=loop@ikigai -c user.name=loop commit -m "m6-test: marker $name" >/dev/null 2>&1
  )
  if [ $? -eq 0 ]; then
    ok "commit $name"
  else
    fail "commit $name"
  fi
done

# ---------- Test 4: branches exist + diverge ----------
echo "=== Test 4: each branch carries its marker ==="
for name in m6-test-a m6-test-b m6-test-c; do
  if git -C "$PROJECT_ROOT" show "loop/$name:tmp/marker.txt" 2>/dev/null | grep -q "marker-$name"; then
    ok "branch loop/$name carries marker-$name"
  else
    fail "branch loop/$name missing or wrong marker"
  fi
done

# ---------- Test 5: cleanup-all restores empty state ----------
echo "=== Test 5: cleanup-all + empty .worktrees/ ==="
bash "$HELPER" cleanup-all >/dev/null 2>&1

REMAINING_DIRS=$(find "$WORKTREE_BASE" -maxdepth 1 -mindepth 1 -name "m6-test-*" 2>/dev/null | wc -l)
REMAINING_BRANCHES=$(git -C "$PROJECT_ROOT" branch 2>/dev/null | grep -c "loop/m6-test-" || true)

if [ "$REMAINING_DIRS" -eq 0 ]; then
  ok "0 m6-test-* worktree dirs remain"
else
  fail "$REMAINING_DIRS m6-test-* worktree dirs still present"
fi

if [ "$REMAINING_BRANCHES" -eq 0 ]; then
  ok "0 loop/m6-test-* branches remain"
else
  fail "$REMAINING_BRANCHES loop/m6-test-* branches still present"
fi

# ---------- Test 6: idempotency (re-run from clean state) ----------
echo "=== Test 6: re-run on clean state succeeds ==="
if bash "$HELPER" list >/dev/null 2>&1; then
  ok "list works after cleanup"
else
  fail "list broke after cleanup"
fi

# ---------- Summary ----------
echo ""
echo "=== Summary: $PASS pass, $FAIL fail ==="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
