"""Tests for tag_and_persist LangGraph v2 node (Plan A Task 8).

Per spec 2026-09-03-sonho-tree-hybrid-design §Architecture.
The node sits between N6 plan and N8 commit in the v2 graph,
persisting proposed entities to vault via vault_write.

Path corrections applied vs plan (2026-09-03-planning-contract-plan-a.md):
- UEIDs use 4-part canonical format (src/contracts/common.py:34 regex)
- monkeypatch targets tools_vault._resolve_vault_root (not vault.VAULT_ROOT)
- Frontmatter assertion matches frontmatter.dumps() YAML block format
  (not inline "[a, b, c]" which is invalid YAML for python-frontmatter)
- Audit log lives at vault_root (tmp_path), not next to the written file
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.ikigai.src.agents.v2.nodes.tag_and_persist import tag_and_persist_node
from src.ikigai.src.agents.v2.state import IKIGAiStateDict
from src.contracts.sonho import Sonho


_SONHO_UEID = "sn:life-os-v1:abc12345-1234-5678-9abc-def012345678:0123456789abcdef"
_TEST_SONHO_UEID = "sn:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef"
_CREATED_AT = datetime.fromisoformat("2026-09-03T00:00:00+00:00")


def _make_sonho(
    ueid: str, title: str, motivation: str, success_metric: str, actor: str
) -> Sonho:
    return Sonho(
        id=ueid,
        title=title,
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill", "market", "revenue"]
        if ueid == _SONHO_UEID
        else ["skill"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at=_CREATED_AT,
        motivation=motivation,
        success_metric=success_metric,
        actor=actor,
    )


def test_tag_and_persist_writes_sonho_to_vault(tmp_path: Path, monkeypatch) -> None:
    """tag_and_persist_node writes Sonho to vault with structured frontmatter."""
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.tools_vault._resolve_vault_root",
        lambda: tmp_path,
    )

    sonho = _make_sonho(
        ueid=_SONHO_UEID,
        title="Ship Algorithmic Life OS v1",
        motivation="m",
        success_metric="A+B",
        actor="user",
    )

    state = IKIGAiStateDict(
        proposed_entity=sonho,
        vault_path="ikigai/closing-2026/01-q3-2026/00-sonho/sonho-life-os-v1.md",
        actor="user",
        approval_state="approved",
    )

    result = tag_and_persist_node(state)
    assert result["persisted"] is True
    target = (
        tmp_path
        / "ikigai"
        / "closing-2026"
        / "01-q3-2026"
        / "00-sonho"
        / "sonho-life-os-v1.md"
    )
    assert target.exists()
    content = target.read_text()
    # python-frontmatter dumps lists as YAML block sequences, not inline.
    # Verify the ikigai_vectors list is fully present in block format.
    assert "ikigai_vectors:" in content
    assert "- skill" in content
    assert "- market" in content
    assert "- revenue" in content
    assert "pae_cycle_phase: plan" in content
    assert "pae_tier: SONHO" in content
    # Sanity: id/title from entity carried into frontmatter
    assert f"id: {_SONHO_UEID}" in content
    assert "title: Ship Algorithmic Life OS v1" in content


def test_tag_and_persist_records_actor_in_audit(tmp_path: Path, monkeypatch) -> None:
    """tag_and_persist_node records actor in vault_root audit log."""
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.tools_vault._resolve_vault_root",
        lambda: tmp_path,
    )

    sonho = _make_sonho(
        ueid=_TEST_SONHO_UEID,
        title="T",
        motivation="m",
        success_metric="s",
        actor="agent",
    )

    state = IKIGAiStateDict(
        proposed_entity=sonho,
        vault_path="ikigai/test/test.md",
        actor="agent",
        approval_state="approved",
    )

    result = tag_and_persist_node(state)
    assert result["persisted"] is True
    # vault_write_impl writes audit log at vault_root (tmp_path), not next
    # to the target file (per ADR-012 vault-only invariant).
    audit_log = tmp_path / ".vault_audit.log"
    assert audit_log.exists()
    assert "actor=agent" in audit_log.read_text()


def test_tag_and_persist_requires_approval_state(tmp_path: Path, monkeypatch) -> None:
    """tag_and_persist_node raises PermissionError when approval_state is missing."""
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.tools_vault._resolve_vault_root",
        lambda: tmp_path,
    )

    sonho = _make_sonho(
        ueid=_TEST_SONHO_UEID,
        title="T",
        motivation="m",
        success_metric="s",
        actor="agent",
    )

    # State WITHOUT approval_state — must raise PermissionError.
    state = IKIGAiStateDict(
        proposed_entity=sonho,
        vault_path="ikigai/test/test.md",
        actor="agent",
    )

    import pytest

    with pytest.raises(PermissionError, match="approval_state"):
        tag_and_persist_node(state)


def test_tag_and_persist_succeeds_with_approval_state(tmp_path: Path, monkeypatch) -> None:
    """tag_and_persist_node succeeds when approval_state is 'approved'."""
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.tools_vault._resolve_vault_root",
        lambda: tmp_path,
    )

    sonho = _make_sonho(
        ueid=_TEST_SONHO_UEID,
        title="T",
        motivation="m",
        success_metric="s",
        actor="agent",
    )

    state = IKIGAiStateDict(
        proposed_entity=sonho,
        vault_path="ikigai/test/test.md",
        actor="agent",
        approval_state="approved",
    )

    result = tag_and_persist_node(state)
    assert result["persisted"] is True
