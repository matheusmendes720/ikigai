"""balance node — compute load balance.

M12 (T-13.3): ``mcp_bridge.ikigai_balance`` was deleted from
``mcp_bridge.py``. Replaced the dead call with a direct
``error_channel`` write per Phase 8.2 SPEC §3 to surface the missing
bridge immediately instead of silently degrading via try/except.

If this node ever needs to come back, wire a real MCP bridge wrapper
(in bridge + server.py's ``@MCP.tool`` registry) before re-introducing
the call here. The drift detector
``test_mcp_bridge_wrapped_tool_count_matches_canonical`` will catch the
regression.
"""

from __future__ import annotations

from typing import Any

from ..state import IKIGAiStateDict


def balance_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Surface missing bridge via direct error_channel write.

    M12 removed ``mcp_bridge.ikigai_balance``. See module docstring.
    """
    return {
        "balance": None,
        "error_channel": [
            "mcp_bridge.ikigai_balance not available post-V5-E "
            "(M12 deleted wrapper); see src/ikigai/src/agents/v2/mcp_bridge.py docstring"
        ],
        "last_step": "balance",
    }
