"""decompose node — UEID hierarchy traversal (Dream→Task).

PHASE 8.2: calls mcp_bridge.ikigai_decompose.
"""

from __future__ import annotations

from typing import Any

from src.ikigai.src.agents.v2 import mcp_bridge
from ..state import IKIGAiStateDict


def decompose_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Decompose task into subtasks via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_decompose(task_id=state.get("task_id", ""))
        return {"decompose": result}
    except Exception as e:
        return {"decompose": None, "error_type": type(e).__name__, "error_message": f"decompose: {e}"}
