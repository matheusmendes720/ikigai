#!/bin/bash
# Worktree Helper — create / list / cleanup isolated git worktrees per sub-agent
#
# Usage:
#   scripts/worktree-helper.sh create m-1.1
#   scripts/worktree-helper.sh list
#   scripts/worktree-helper.sh cleanup <name>
#   scripts/worktree-helper.sh cleanup-all
#
# Each sub-agent gets its own worktree at .worktrees/{name}/
# Prevents parallel sub-agents from stepping on each other.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKTREE_BASE="$PROJECT_ROOT/.worktrees"

mkdir -p "$WORKTREE_BASE"

cmd="${1:-}"
name="${2:-}"

case "$cmd" in
  create)
    if [ -z "$name" ]; then
      echo "Usage: $0 create <name>"
      echo "Example: $0 create m-0.1"
      exit 1
    fi
    WT_PATH="$WORKTREE_BASE/$name"
    if [ -d "$WT_PATH" ]; then
      echo "Worktree already exists: $WT_PATH"
      exit 1
    fi
    # Get current branch
    BASE_BRANCH=$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD)
    NEW_BRANCH="loop/$name"
    echo "Creating worktree: $WT_PATH (branch: $NEW_BRANCH, base: $BASE_BRANCH)"
    git -C "$PROJECT_ROOT" worktree add -b "$NEW_BRANCH" "$WT_PATH" "$BASE_BRANCH"
    echo "Done. Worktree at: $WT_PATH"
    echo "To use: cd $WT_PATH"
    ;;
  list)
    git -C "$PROJECT_ROOT" worktree list
    echo ""
    echo "Loop worktrees:"
    if [ -d "$WORKTREE_BASE" ]; then
      ls -la "$WORKTREE_BASE"
    fi
    ;;
  cleanup)
    if [ -z "$name" ]; then
      echo "Usage: $0 cleanup <name>"
      exit 1
    fi
    WT_PATH="$WORKTREE_BASE/$name"
    if [ ! -d "$WT_PATH" ]; then
      echo "Worktree not found: $WT_PATH"
      exit 1
    fi
    echo "Removing worktree: $WT_PATH"
    git -C "$PROJECT_ROOT" worktree remove --force "$WT_PATH"
    BRANCH="loop/$name"
    if git -C "$PROJECT_ROOT" show-ref --verify --quiet "refs/heads/$BRANCH"; then
      git -C "$PROJECT_ROOT" branch -D "$BRANCH"
    fi
    echo "Done."
    ;;
  cleanup-all)
    echo "Removing ALL loop worktrees:"
    git -C "$PROJECT_ROOT" worktree list --porcelain | grep "worktree $WORKTREE_BASE" | while read -r line; do
      WT_PATH=$(echo "$line" | awk '{print $2}')
      if [ -d "$WT_PATH" ]; then
        echo "  Removing: $WT_PATH"
        git -C "$PROJECT_ROOT" worktree remove --force "$WT_PATH" || true
      fi
    done
    # Remove loop/* branches
    git -C "$PROJECT_ROOT" branch | grep "^  loop/" | while read -r branch; do
      branch=$(echo "$branch" | tr -d ' ')
      git -C "$PROJECT_ROOT" branch -D "$branch" || true
    done
    echo "Done."
    ;;
  *)
    echo "Usage: $0 {create|list|cleanup|cleanup-all} [name]"
    echo ""
    echo "Examples:"
    echo "  $0 create m-0.1     # Create worktree for milestone 0, task 1"
    echo "  $0 list             # List all worktrees"
    echo "  $0 cleanup m-0.1    # Remove a specific worktree"
    echo "  $0 cleanup-all      # Remove all loop worktrees"
    exit 1
    ;;
esac
