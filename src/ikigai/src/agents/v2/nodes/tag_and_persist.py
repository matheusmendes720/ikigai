"""tag_and_persist node — reads tags for UEID via MCP bridge (READ-ONLY).

Per spec 2026-09-03-sonho-tree-hybrid-design §Architecture.
Sits between N6 plan and N8 commit in the v2 graph.

Phase 8.2: vault_write is NOT wired here per SPEC §6 — that is
separate work. This node only reads tags.
"""

from __future__ import annotations

from typing import Any

from src.ikigai.src.agents.v2 import mcp_bridge
from ..state import IKIGAiStateDict


def tag_and_persist_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Read tags for UEID via MCP bridge (READ-ONLY).

    vault_write is NOT wired here per SPEC §6 — that is separate work.
    """
    try:
        result = mcp_bridge.ikigai_tag_and_persist(ueid=state.get("ueid", ""))
        return {"tags": result}
    except Exception as e:
        return {"tags": None, "error_type": type(e).__name__, "error_message": f"tag_and_persist: {e}"}
