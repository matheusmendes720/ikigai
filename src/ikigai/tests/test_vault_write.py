"""vault_write lower-level function — the only vault writer per attribution §7."""
import hashlib
import sys
from pathlib import Path

import pytest

# Ensure repo root on sys.path for imports
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.ikigai.src.ikigai.vault.vault_write import vault_write


@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    """Vault root dir for tests."""
    root = tmp_path / "vault"
    root.mkdir()
    return root


def test_vault_write_creates_markdown_file(vault_root: Path) -> None:
    """vault_write creates a .md file with frontmatter + body."""
    result = vault_write(
        vault_root=vault_root,
        vault_path="plans/q3/task-x.md",
        frontmatter_fields={"ueid": "ikigai:task:x:1", "title": "Task X", "status": "planned"},
        body="# Task X\n\nDetails here.\n",
    )
    assert result["written"] is True
    target = vault_root / "plans" / "q3" / "task-x.md"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "ueid: ikigai:task:x:1" in content
    assert "title: Task X" in content
    assert "# Task X" in content


def test_vault_write_rejects_path_traversal(vault_root: Path) -> None:
    """vault_path with .. that resolves outside vault/ → rejection."""
    with pytest.raises(ValueError, match="path.*outside vault"):
        vault_write(
            vault_root=vault_root,
            vault_path="../../../etc/passwd.md",
            frontmatter_fields={"x": 1},
            body="bad",
        )


def test_vault_write_rejects_absolute_path(vault_root: Path) -> None:
    """Absolute paths rejected (must be relative to vault root)."""
    with pytest.raises(ValueError, match="absolute"):
        vault_write(
            vault_root=vault_root,
            vault_path="C:\\Windows\\System32\\test.md",
            frontmatter_fields={"x": 1},
            body="bad",
        )


def test_vault_write_returns_sha256(vault_root: Path) -> None:
    """sha256 in result is sha256 of final file content."""
    body = "x" * 100
    fm = {"ueid": "ikigai:task:y:2"}
    result = vault_write(
        vault_root=vault_root,
        vault_path="y.md",
        frontmatter_fields=fm,
        body=body,
    )
    target = vault_root / "y.md"
    expected = hashlib.sha256(target.read_bytes()).hexdigest()
    assert result["sha256"] == expected


def test_vault_write_atomic_no_partial_file(vault_root: Path) -> None:
    """Atomic write: no .tmp leftover on success."""
    vault_write(
        vault_root=vault_root,
        vault_path="z.md",
        frontmatter_fields={"x": 1},
        body="z",
    )
    target = vault_root / "z.md"
    assert target.exists()
    assert not (vault_root / "z.tmp").exists()


def test_vault_write_rejects_empty_body_and_frontmatter(vault_root: Path) -> None:
    """Empty body + empty frontmatter → rejection (no-op protection)."""
    with pytest.raises(ValueError, match="empty"):
        vault_write(
            vault_root=vault_root,
            vault_path="empty.md",
            frontmatter_fields={},
            body="",
        )


def test_vault_write_overwrites_existing_atomically(vault_root: Path) -> None:
    """Second write to same path replaces first (Windows-safe)."""
    vault_write(
        vault_root=vault_root,
        vault_path="w.md",
        frontmatter_fields={"v": 1},
        body="first",
    )
    vault_write(
        vault_root=vault_root,
        vault_path="w.md",
        frontmatter_fields={"v": 2},
        body="second",
    )
    content = (vault_root / "w.md").read_text()
    assert "v: 2" in content
    assert "second" in content
    assert "first" not in content
