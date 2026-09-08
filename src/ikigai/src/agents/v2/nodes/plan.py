"""plan node — prospective channel: draft next actions for current tier.

PHASE 8.2: calls mcp_bridge.ikigai_plan.
"""

from __future__ import annotations

from typing import Any

from src.ikigai.src.agents.v2 import mcp_bridge
from ..state import IKIGAiStateDict


def plan_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Build plan via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_plan(cycle_id=state.get("cycle_id", ""))
        return {"plan": result, "error_channel": []}
    except Exception as e:
        return {"plan": None, "error_channel": [f"plan: {e}"]}
