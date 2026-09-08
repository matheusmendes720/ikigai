"""reflect node — retrospective channel: aggregate completed work.

PHASE 8.2: calls mcp_bridge.ikigai_reflect.
"""

from __future__ import annotations

from typing import Any

from src.ikigai.src.agents.v2 import mcp_bridge
from ..state import IKIGAiStateDict


def reflect_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Reflect on cycle via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_reflect(cycle_id=state.get("cycle_id", ""))
        return {"reflect": result, "error_channel": []}
    except Exception as e:
        return {"reflect": None, "error_channel": [f"reflect: {e}"]}
