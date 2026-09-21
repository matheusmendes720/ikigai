"""heuristics node — apply heuristics to planning context.

M12 (T-13.3): ``mcp_bridge.ikigai_heuristics`` was deleted from
``mcp_bridge.py``. Replaced the dead call with a direct
``error_channel`` write per Phase 8.2 SPEC §3 to surface the missing
bridge immediately instead of silently degrading via try/except.

If this node ever needs to come back, wire a real MCP bridge wrapper
(in bridge + server.py's ``@MCP.tool`` registry) before re-introducing
the call here. The drift detector
``test_mcp_bridge_wrapped_tool_count_matches_canonical`` will catch the
regression.

Historical H1-H6 helpers that lived in this module were removed in the
ruff cleanup pass (2026-09-21). They were never invoked by the no-op
``heuristics_node`` (gated behind ``if False:`` since the IKIGAI v2
deep-dive bugs 2026-09-10, B6 fix). The arithmetic referenced archived
PAV constants (``_c()``) and prompt renderers that no longer exist in
this scope. See git history pre-2026-09-21 for the historical code.
"""

from __future__ import annotations

from typing import Any

from ..state import IKIGAiStateDict


def heuristics_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Surface missing bridge via direct error_channel write.

    M12 removed ``mcp_bridge.ikigai_heuristics``. See module docstring.
    """
    return {
        "heuristics": None,
        "error_channel": [
            "mcp_bridge.ikigai_heuristics not available post-V5-E "
            "(M12 deleted wrapper); see src/ikigai/src/agents/v2/mcp_bridge.py docstring"
        ],
        "last_step": "heuristics",
    }
