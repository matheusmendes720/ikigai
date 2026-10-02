"""Tests for ikigai_write_vault — LangChain tool wrapping vault_write.

Mirrors the test pattern in test_multi_tool_chain.py for ikigai_read_vault:
import the module, swap ``_get_vault_dir`` via monkeypatch, parse JSON from
``.invoke({...})``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure repo root on sys.path for ``sys_ikigai.*`` imports and the dotted
# ``src.ikigai.src.agents.ikigai_write_vault`` import. Conftest adds these
# already; the explicit guard makes this test file self-contained for direct
# `pytest <file>` invocation.
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (_REPO_ROOT, _REPO_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from src.ikigai.src.agents.ikigai_write_vault import (  # noqa: E402
    ikigai_write_vault,
)
import src.ikigai.src.agents.ikigai_write_vault as ikigai_write_vault_mod  # noqa: E402


@pytest.fixture
def temp_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temp vault and monkeypatch ``_get_vault_dir`` to point at it.

    Mirrors the lazy-resolver monkeypatch in test_multi_tool_chain.py so the
    agent-facing tool can be tested in isolation from the project's real vault.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setattr(ikigai_write_vault_mod, "_get_vault_dir", lambda: vault)
    return vault


def _parse(result: str) -> dict:
    """Parse JSON result from the tool."""
    return json.loads(result)


# ── happy path ──────────────────────────────────────────────────────────────


def test_write_vault_creates_new_file_with_frontmatter_and_body(
    temp_vault: Path,
) -> None:
    """Happy path: write a new file, verify content on disk + JSON shape."""
    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "plans/q3/task-x.md",
                "content": "# Task X\n\nDetails here.\n",
                "frontmatter": {"ueid": "ikigai:task:x:1", "status": "planned"},
                "mode": "create",
            }
        )
    )

    assert result["ok"] is True
    assert result["path"] == "plans/q3/task-x.md"
    assert len(result["sha256"]) == 64  # sha256 hex
    assert result["mtime"] > 0

    target = temp_vault / "plans" / "q3" / "task-x.md"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "ueid: ikigai:task:x:1" in content
    assert "status: planned" in content
    assert "# Task X" in content


def test_write_vault_returns_proper_json_structure_on_success(
    temp_vault: Path,
) -> None:
    """Success result has exactly the four documented fields."""
    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "shape.md",
                "content": "x",
                "frontmatter": {"k": "v"},
                "mode": "create",
            }
        )
    )
    assert set(result.keys()) == {"ok", "path", "sha256", "mtime"}
    assert isinstance(result["ok"], bool)
    assert isinstance(result["path"], str)
    assert isinstance(result["sha256"], str)
    assert isinstance(result["mtime"], (int, float))


# ── append mode ─────────────────────────────────────────────────────────────


def test_write_vault_append_to_existing_file_preserves_original(
    temp_vault: Path,
) -> None:
    """Append mode keeps the original body + frontmatter; new content merged in."""
    target = temp_vault / "log.md"
    target.write_text(
        "---\nueid: ikigai:log:1\ntitle: Original\n---\n# Original body\n",
        encoding="utf-8",
    )

    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "log.md",
                "content": "# New section\n",
                "frontmatter": {"status": "in-progress"},
                "mode": "append",
            }
        )
    )
    assert result["ok"] is True

    content = target.read_text(encoding="utf-8")
    assert "ueid: ikigai:log:1" in content  # preserved
    assert "title: Original" in content  # preserved
    assert "status: in-progress" in content  # merged in
    assert "# Original body" in content  # original body preserved
    assert "# New section" in content  # new body appended


def test_write_vault_append_merges_frontmatter_keys(temp_vault: Path) -> None:
    """Append mode: new frontmatter keys override existing; existing keys kept."""
    target = temp_vault / "fm.md"
    target.write_text(
        "---\nueid: ikigai:fm:1\nexisting_key: old_value\n---\nbody\n",
        encoding="utf-8",
    )

    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "fm.md",
                "content": "more body",
                "frontmatter": {"new_key": "new_value", "existing_key": "new_value"},
                "mode": "append",
            }
        )
    )
    assert result["ok"] is True

    content = target.read_text(encoding="utf-8")
    assert "ueid: ikigai:fm:1" in content  # preserved
    assert "new_key: new_value" in content  # added
    assert "existing_key: new_value" in content  # overridden
    assert "existing_key: old_value" not in content  # old value gone


def test_write_vault_append_to_nonexistent_file_creates_new(
    temp_vault: Path,
) -> None:
    """Append mode on a missing file behaves like a fresh create."""
    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "fresh.md",
                "content": "fresh content",
                "frontmatter": {"k": "v"},
                "mode": "append",
            }
        )
    )
    assert result["ok"] is True

    target = temp_vault / "fresh.md"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "fresh content" in content
    assert "k: v" in content


# ── update mode ─────────────────────────────────────────────────────────────


def test_write_vault_update_mode_replaces_entire_file(temp_vault: Path) -> None:
    """Update mode replaces frontmatter + body wholesale (no merge)."""
    target = temp_vault / "replace.md"
    target.write_text(
        "---\nold_key: data\n---\n# OLD body\n",
        encoding="utf-8",
    )

    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "replace.md",
                "content": "# NEW body\n",
                "frontmatter": {"new_key": "data"},
                "mode": "update",
            }
        )
    )
    assert result["ok"] is True

    content = target.read_text(encoding="utf-8")
    assert "old_key" not in content  # replaced
    assert "new_key: data" in content
    assert "# OLD body" not in content
    assert "# NEW body" in content


# ── create mode ─────────────────────────────────────────────────────────────


def test_write_vault_create_mode_fails_when_file_exists(
    temp_vault: Path,
) -> None:
    """Create mode refuses to clobber — error mentions file, leaves prior content."""
    target = temp_vault / "exists.md"
    target.write_text("original", encoding="utf-8")

    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "exists.md",
                "content": "new",
                "mode": "create",
            }
        )
    )
    assert result["ok"] is False
    assert "already exists" in result["error"]
    assert result["vault_path"] == "exists.md"
    # Original content unchanged.
    assert target.read_text(encoding="utf-8") == "original"


# ── security: path traversal + absolute path ───────────────────────────────


def test_write_vault_rejects_path_traversal(temp_vault: Path) -> None:
    """Path with ``..`` that resolves outside vault/ → rejection (ok=False)."""
    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "../../../etc/passwd.md",
                "content": "bad",
                "mode": "create",
            }
        )
    )
    assert result["ok"] is False
    assert "outside vault" in result["error"]
    assert result["vault_path"] == "../../../etc/passwd.md"


def test_write_vault_rejects_absolute_path(temp_vault: Path) -> None:
    """Absolute paths are rejected by the backend's path-traversal guard."""
    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "C:\\Windows\\System32\\test.md",
                "content": "bad",
                "mode": "create",
            }
        )
    )
    assert result["ok"] is False
    assert "absolute" in result["error"]


# ── round-trip with vault_read ──────────────────────────────────────────────


def test_write_vault_can_be_read_back_with_vault_read(temp_vault: Path) -> None:
    """What was written via the tool can be read back via vault_read."""
    from sys_ikigai.vault.vault_read import vault_read

    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "round-trip.md",
                "content": "# Round trip\n\nBody.\n",
                "frontmatter": {"ueid": "ikigai:round:1", "tag": "test"},
                "mode": "create",
            }
        )
    )
    assert result["ok"] is True

    read_back = vault_read(temp_vault, "round-trip.md")
    assert read_back["frontmatter"]["ueid"] == "ikigai:round:1"
    assert read_back["frontmatter"]["tag"] == "test"
    assert "# Round trip" in read_back["body"]
    assert "Body." in read_back["body"]
    # sha256 returned by the tool matches sha256 returned by vault_read.
    assert read_back["sha256"] == result["sha256"]


# ── input validation ───────────────────────────────────────────────────────


def test_write_vault_invalid_mode_returns_error_json(temp_vault: Path) -> None:
    """Invalid mode string returns ``ok=false`` with a clear error message."""
    result = _parse(
        ikigai_write_vault.invoke(
            {
                "vault_path": "x.md",
                "content": "x",
                "mode": "not-a-real-mode",
            }
        )
    )
    assert result["ok"] is False
    assert "invalid mode" in result["error"]
    assert "not-a-real-mode" in result["error"]