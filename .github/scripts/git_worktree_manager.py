#!/usr/bin/env python3
"""
Git Worktree Manager for Algorithmic Life OS

Manages isolated git worktrees for subapps (e.g. operational/ packages as
separate clones for parallel agent work).

Usage:
    python -m github.scripts.git_worktree_manager --list
    python -m github.scripts.git_worktree_manager --add operational-core --path ../life-ops-operational-core
    python -m github.scripts.git_worktree_manager --remove operational-core

For use in CI/CD and multi-agent orchestration contexts.
Requires: GitPython
    pip install GitPython
"""

from __future__ import annotations

import os
import sys
import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]  # repo root
WORKTREE_DIR = ROOT.parent / "life-worktrees"  # parent dir for all worktrees


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def cmd_list():
    """List all worktrees (repo + all worktrees)."""
    result = run(["git", "worktree", "list", "--porcelain"], cwd=ROOT)
    print(result.stdout if result.stdout else "(no worktrees, use --add to create one)")
    return 0


def cmd_add(name: str, branch: str | None, path: Path | None):
    """Create a new worktree for a feature branch."""
    if not branch:
        branch = f"feature/worktree-{name}"

    worktree_path = path or (WORKTREE_DIR / name)
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if branch exists locally or remotely
    result = run(["git", "rev-parse", "--verify", f"refs/heads/{branch}"], cwd=ROOT)
    if result.returncode != 0:
        # Create orphan branch
        print(f"  Creating new branch '{branch}'...")
        run(["git", "checkout", "--orphan", branch], cwd=ROOT)

    result = run(
        ["git", "worktree", "add", "--checkpoint", "-b", branch, str(worktree_path)],
        cwd=ROOT
    )
    if result.returncode != 0:
        print(f"[ERROR] Failed to add worktree: {result.stderr}", file=sys.stderr)
        return 1

    # Install dependencies in the new worktree
    uv_result = run(["uv", "sync"], cwd=worktree_path)
    if uv_result.returncode != 0:
        print(f"[WARN] uv sync failed in worktree: {uv_result.stderr}", file=sys.stderr)
    else:
        print(f"  uv sync complete")

    print(f"[OK] Worktree '{name}' created at {worktree_path}")
    return 0


def cmd_remove(name: str):
    """Remove a worktree."""
    result = run(["git", "worktree", "list", "--porcelain"], cwd=ROOT)
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            wt_path = line.split(" ", 1)[1].strip()
            if name in wt_path:
                run(["git", "worktree", "remove", wt_path], cwd=ROOT)
                print(f"[OK] Removed worktree at {wt_path}")
                return 0
    print(f"[ERROR] No worktree found with name '{name}'", file=sys.stderr)
    return 1


def cmd_prune():
    """Prune stale worktree references."""
    result = run(["git", "worktree", "prune"], cwd=ROOT)
    print(f"[OK] Pruned stale worktree entries")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage git worktrees for subapps")
    parser.add_argument("--list", action="store_true", help="List all worktrees")
    parser.add_argument("--add", metavar="NAME", help="Add a new worktree")
    parser.add_argument("--remove", metavar="NAME", help="Remove a worktree by name")
    parser.add_argument("--branch", metavar="BRANCH", help="Branch name for --add (default: feature/worktree-NAME)")
    parser.add_argument("--path", metavar="PATH", type=Path,
                        help="Path for --add (default: ../life-worktrees/NAME)")
    parser.add_argument("--prune", action="store_true", help="Prune stale worktree references")
    args = parser.parse_args()

    if args.list:
        sys.exit(cmd_list())
    elif args.add:
        sys.exit(cmd_add(args.add, args.branch, args.path))
    elif args.remove:
        sys.exit(cmd_remove(args.remove))
    elif args.prune:
        sys.exit(cmd_prune())
    else:
        parser.print_help()
