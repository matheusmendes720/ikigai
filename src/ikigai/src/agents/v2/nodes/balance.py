from src.ikigai.src.agents.v2 import mcp_bridge

from ..state import IKIGAiStateDict


def balance_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Compute load balance via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_balance(load=state.get("load", 0.0))
        return {"balance": result, "error_channel": []}
    except Exception as e:
        return {"balance": None, "error_channel": [f"balance: {e}"]}
