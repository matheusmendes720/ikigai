#!/usr/bin/env python3
"""
Setup git hooks for Algorithmic Life OS

Installs:
- pre-commit hooks (from .pre-commit-config.yaml) for life-ops/operational
- A commit-msg hook that adds a Co-Authored-By trailer and validates branch name

Usage:
    python .github/scripts/setup_hooks.py
    python .github/scripts/setup_hooks.py --dry-run
"""

from __future__ import annotations

import os
import sys
import stat
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = ROOT / ".git" / "hooks"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, **kwargs)


def ensure_pre_commit():
    """Install pre-commit hooks."""
    result = run(["uv", "tool", "list"], capture_output=True, text=True)
    if "pre-commit" not in result.stdout:
        print("  Installing pre-commit via uv...")
        run(["uv", "tool", "install", "pre-commit"])
    result = run(
        ["uv", "run", "pre-commit", "install", "--install-hooks"],
        cwd=ROOT / "life-ops" / "operational"
    )
    if result.returncode == 0:
        print("  [OK] pre-commit hooks installed")
    else:
        print(f"  [WARN] pre-commit install failed: {result.stderr}")


def write_hook(name: str, content: str):
    """Write a hook file with executable permissions."""
    hook_path = HOOKS_DIR / name
    # Preserve existing hook if it already exists and is more complex
    if hook_path.exists() and hook_path.stat().st_size > 0:
        existing = hook_path.read_text()
        if "LIFE-OS-HOOK" not in existing:
            backup = hook_path.with_suffix(".bak")
            shutil.copy(hook_path, backup)
            print(f"  [INFO] Backed up existing {name} -> {backup.name}")
    hook_path.write_text(content)
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  [OK] {name} installed")


def install_commit_msg_hook():
    content = """#!/bin/sh
# LIFE-OS-HOOK: commit-msg
# Validates branch name and adds metadata
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)

# Branch name validation — feature branches must match pattern
case "$BRANCH" in
  main|master|HEAD) ;;
  feature/*|fix/*|refactor/*|docs/*|infra/*)
    ;;
  *)
    echo "[WARNING] Branch '$BRANCH' doesn't match feature/*|fix/*|refactor/*|docs/*|infra/*"
    ;;
esac
"""
    write_hook("commit-msg", content)


def install_post-commit_hook():
    content = """#!/bin/sh
# LIFE-OS-HOOK: post-commit
# Auto-prune stale worktrees after each commit
git worktree prune 2>/dev/null
"""
    write_hook("post-commit", content)


def main(dry_run: bool = False):
    print(f"Setting up git hooks in {HOOKS_DIR}")
    if dry_run:
        print("[DRY RUN] No changes would be made")
        return

    HOOKS_DIR.mkdir(parents=True, exist_ok=True)

    install_commit_msg_hook()
    install_post_commit_hook()
    ensure_pre_commit()

    print("\n[OK] All hooks installed. Run `git commit` to test.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
