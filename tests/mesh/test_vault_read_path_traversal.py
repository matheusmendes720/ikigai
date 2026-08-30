"""Security tests for vault_read path traversal guards.

Mirrors vault_write's path traversal protection (vault_write.py:66-75).
vault_read is the read-side companion to vault_write — same security model.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def test_absolute_path_rejected(tmp_path: Path) -> None:
    """Absolute paths are rejected with ValueError."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    # Use a Windows-aware absolute path that is recognized as absolute on
    # both POSIX and Windows. On Windows, "/etc/passwd" is a relative path
    # (with a leading slash) — only "C:\\..." style paths are absolute.
    abs_path = "C:\\Windows\\System32\\test.md" if __import__("os").name == "nt" else "/etc/passwd"
    with pytest.raises(ValueError, match="absolute path rejected"):
        vault_read(tmp_path, abs_path)


def test_parent_traversal_rejected(tmp_path: Path) -> None:
    """Paths resolving outside vault_root raise ValueError."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    with pytest.raises(ValueError, match="resolves outside vault root"):
        vault_read(vault, "../../../etc/passwd")


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    """Symlinks pointing outside vault_root are rejected (resolve() catches it)."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# outside")
    (vault / "sneaky.md").symlink_to(outside)

    with pytest.raises(ValueError, match="resolves outside vault root"):
        vault_read(vault, "sneaky.md")