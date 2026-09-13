"""commit node — in-process summary of the cycle (planner-only per ADR-013).

M12 (T-13.3): ``mcp_bridge.ikigai_commit_summary`` was deleted from
``mcp_bridge.py``. Replaced the dead call with a direct
``error_channel`` write per Phase 8.2 SPEC §3 to surface the missing
bridge immediately instead of silently degrading via try/except.

This node stays in the graph as a terminal-state producer (downstream
nodes ``dispatch_sub_agents`` and ``surface_intentions`` route through
it). The commit_summary it produced via the wrapper is now surfaced as
an error_channel entry — the graph pipeline continues with an explicit
record of the missing wrapper instead of a silent no-op.

If this node ever needs to come back, wire a real MCP bridge wrapper
(in bridge + server.py's ``@MCP.tool`` registry) before re-introducing
the call here. The drift detector
``test_mcp_bridge_wrapped_tool_count_matches_canonical`` will catch the
regression.
"""

from __future__ import annotations

from typing import Any

from ..state import IKIGAiStateDict


def commit_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Surface missing bridge via direct error_channel write.

    M12 removed ``mcp_bridge.ikigai_commit_summary``. See module docstring.
    """
    return {
        "commit": None,
        "commit_summary": None,
        "error_channel": [
            "mcp_bridge.ikigai_commit_summary not available post-V5-E "
            "(M12 deleted wrapper); see src/ikigai/src/agents/v2/mcp_bridge.py docstring"
        ],
        "last_step": "commit",
    }
