from __future__ import annotations

from src.ikigai.src.agents.v2 import mcp_bridge

from ..state import IKIGAiStateDict


def balance_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Compute load balance via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_balance(load=state.get("load", 0.0))
        return {"balance": result}
    except Exception as e:
        return {"balance": None, "error_type": type(e).__name__, "error_message": f"balance: {e}"}
