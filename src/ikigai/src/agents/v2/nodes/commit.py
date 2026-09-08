"""commit node — in-process summary via mcp_bridge.

Phase 8.2: Uses mcp_bridge.ikigai_commit_summary (in-process;
reads prior node outputs from state) instead of direct vault_write.
This node is planner-only per ADR-013 — it does NOT execute PAV math.
"""

from __future__ import annotations

from src.ikigai.src.agents.v2 import mcp_bridge


def commit_node(state: dict) -> dict:
    """Build commit summary via MCP bridge (in-process; reads prior node outputs)."""
    try:
        result = mcp_bridge.ikigai_commit_summary(
            cycle_id=state.get("cycle_id", "")
        )
        return {"commit": result}
    except Exception as e:
        return {"commit": None, "error_type": type(e).__name__, "error_message": f"commit: {e}"}
