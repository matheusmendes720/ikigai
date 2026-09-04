"""tag_and_persist node — writes proposed entity to vault with structured frontmatter.

Per spec 2026-09-03-sonho-tree-hybrid-design §Architecture.
Sits between N6 plan and N8 commit in the v2 graph.

Phase 8.2: persistence is routed through the MCP ``vault_write`` tool
(B6.7 — ONLY vault writer per attribution §7). Direct vault writes from
graph nodes are forbidden by drift invariant (g); ``vault_write`` records
the actor (user/agent/system) in the audit log at vault root.
"""

from __future__ import annotations

from typing import Any, cast

from mcp_server.tools_vault import vault_write

from ..state import IKIGAiStateDict


def tag_and_persist_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Persist a proposed BasePlanContract entity to vault.

    Reads ``proposed_entity``, ``vault_path``, and ``actor`` from the graph
    state, builds a structured frontmatter dict from the entity's typed
    fields, and calls ``vault_write`` (the sole vault writer). Body is
    taken from ``entity.description`` (always present on BasePlanContract).

    Args:
        state: IKIGAiStateDict. Must contain ``proposed_entity`` and
            ``vault_path``; ``actor`` defaults to ``"agent"`` because this
            is an agent-driven node.

    Returns:
        State update dict with ``persisted: True`` and ``last_step`` set,
        merged on top of the existing state by LangGraph.

    Raises:
        KeyError: if ``proposed_entity`` or ``vault_path`` are missing.
        ValueError: propagated from ``vault_write`` for invalid paths or
            empty writes (returned as JSON error by the MCP layer).
    """
    entity = cast(Any, state["proposed_entity"])
    vault_path = state["vault_path"]
    actor = state.get("actor", "agent")  # default agent for an agent node

    # Normalize UEID values to plain str — yaml.SafeDumper (used by
    # python-frontmatter / vault_write_impl) cannot serialize the UEID
    # str subclass even though UEID(str) is a str subclass.
    parent_ueid = entity.parent_ueid

    frontmatter: dict[str, Any] = {
        "id": str(entity.id),
        "title": entity.title,
        "tier": entity.tier,
        "parent_ueid": str(parent_ueid) if parent_ueid is not None else None,
        "ikigai_vectors": entity.ikigai_vectors,
        "pae_cycle_phase": entity.pae_cycle_phase,
        "pae_tier": entity.pae_tier,
        "horizon_days": entity.horizon_days,
        "tags": entity.tags,
        "created_at": entity.created_at.isoformat(),
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        "actor": actor,
    }

    body = entity.description  # BasePlanContract: description: str = ""

    vault_write(
        vault_path=vault_path,
        frontmatter=frontmatter,
        body=body,
        actor=actor,
    )

    return {
        **state,
        "persisted": True,
        "last_step": "tag_and_persist",
    }
