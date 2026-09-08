"""plan node — prospective channel: draft next actions for current tier.

PHASE 8.2: calls mcp_bridge.ikigai_plan.
Phase 8.4: extends return dict with 4 keys for tag_and_persist_node.
"""

from __future__ import annotations

from typing import Any

from src.ikigai.src.agents.v2 import mcp_bridge
from ..state import IKIGAiStateDict


def plan_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Build plan via MCP bridge.

    Extends return dict with proposed_entity, vault_path, actor, persisted
    keys consumed by tag_and_persist_node downstream.
    """
    try:
        result = mcp_bridge.ikigai_plan(cycle_id=state.get("cycle_id", ""))
        return {
            "plan": result,
            "proposed_entity": result,  # consumed by tag_and_persist_node
            "vault_path": "",  # filled by plan output
            "actor": "agent",
            "persisted": False,
        }
    except Exception as e:
        return {
            "plan": None,
            "error_type": type(e).__name__,
            "error_message": f"plan: {e}",
            "proposed_entity": None,
            "vault_path": "",
            "actor": "agent",
            "persisted": False,
        }
