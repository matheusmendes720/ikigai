"""Tests for vault_write actor parameter (Plan A Task 6).

Per spec 2026-09-03-sonho-tree-hybrid-design §vault_write actor parameter.
"""
import json
import tempfile
from pathlib import Path

from src.ikigai.src.mcp_server.tools_vault import vault_write


def test_vault_write_accepts_actor_default_user(monkeypatch) -> None:
    """Default actor is 'user' when not specified."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        monkeypatch.setattr(
            "src.ikigai.src.mcp_server.tools_vault._resolve_vault_root",
            lambda: tmp_path,
        )
        result = vault_write(
            vault_path="test/test.md",
            frontmatter={"title": "T"},
            body="body",
        )
        parsed = json.loads(result)
        assert parsed.get("written") is True
        audit_log = tmp_path / "test" / ".vault_audit.log"
        assert audit_log.exists()
        content = audit_log.read_text()
        assert "actor=user" in content
        assert "path=test/test.md" in content


def test_vault_write_accepts_actor_agent(monkeypatch) -> None:
    """Actor='agent' is recorded in audit log."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        monkeypatch.setattr(
            "src.ikigai.src.mcp_server.tools_vault._resolve_vault_root",
            lambda: tmp_path,
        )
        result = vault_write(
            vault_path="test/test.md",
            frontmatter={"title": "T"},
            body="body",
            actor="agent",
        )
        parsed = json.loads(result)
        assert parsed.get("written") is True
        audit_log = tmp_path / "test" / ".vault_audit.log"
        assert audit_log.exists()
        content = audit_log.read_text()
        assert "actor=agent" in content


def test_vault_write_rejects_invalid_actor(monkeypatch) -> None:
    """Invalid actor returns JSON error."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        monkeypatch.setattr(
            "src.ikigai.src.mcp_server.tools_vault._resolve_vault_root",
            lambda: tmp_path,
        )
        result = vault_write(
            vault_path="test/test.md",
            frontmatter={"title": "T"},
            body="body",
            actor="hacker",  # type: ignore
        )
        parsed = json.loads(result)
        assert "error" in parsed
        assert "actor must be one of" in parsed["error"]
