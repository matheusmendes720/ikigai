"""Verify loop-engineering infrastructure files exist (T-0.1)."""

from pathlib import Path

import pytest


def find_repo_root(start: Path) -> Path:
    """Walk upward from start until a directory containing .claude/loop/constitution.md."""
    current = start.resolve()
    while True:
        if (current / ".claude" / "loop" / "constitution.md").exists():
            return current
        parent = current.parent
        if parent == current:
            raise FileNotFoundError("repo root not found")
        current = parent


REPO_ROOT = find_repo_root(Path(__file__))

INFRA_FILES = [
    ".claude/loop/roadmap.md",
    ".claude/loop/constitution.md",
    ".claude/loop/progress.md",
    ".claude/loop/loop-tick.sh",
    ".claude/loop/loop-tick.bat",
    ".claude/skills/loop-engineering/SKILL.md",
    ".claude/agents/loop/orchestrator.md",
    ".claude/agents/loop/worker.md",
    ".claude/agents/loop/verifier.md",
    "scripts/worktree-helper.sh",
]


@pytest.mark.parametrize("rel_path", INFRA_FILES)
def test_infra_file_exists(rel_path: str) -> None:
    """Each required infrastructure file exists and is non-empty."""
    path = REPO_ROOT / rel_path
    assert path.exists(), f"{rel_path} does not exist"
    assert path.is_file(), f"{rel_path} is not a file"
    assert path.stat().st_size > 0, f"{rel_path} is empty"


def test_progress_md_append_only_marker() -> None:
    """progress.md contains the append-only guard line."""
    path = REPO_ROOT / ".claude/loop/progress.md"
    content = path.read_text(encoding="utf-8")
    marker = "<!-- Append below this line. NEVER edit above. -->"
    assert marker in content, "progress.md missing append-only marker"
