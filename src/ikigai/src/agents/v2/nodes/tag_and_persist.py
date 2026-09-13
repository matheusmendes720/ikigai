"""tag_and_persist node — read tags for UEID (READ-ONLY placeholder).

Per spec 2026-09-03-sonho-tree-hybrid-design §Architecture.
Sits between N6 plan and N8 commit in the v2 graph.

M12 (T-13.3): ``mcp_bridge.ikigai_tag_and_persist`` was deleted from
``mcp_bridge.py``. Replaced the dead call with a direct
``error_channel`` write per Phase 8.2 SPEC §3 to surface the missing
bridge immediately instead of silently degrading via try/except.

The ``tag_and_persist`` identifier is registered as a LEGAL_CALLER in
``vault_write_wrapper`` (drift invariant test asserts presence). When
``vault_write`` is wired here per SPEC §6 (separate work), this node
becomes the canonical write-path entry; the LEGAL_CALLERS whitelist
will then allow it to dispatch through the wrapper.

If this node ever needs to come back, wire a real MCP bridge wrapper
(in bridge + server.py's ``@MCP.tool`` registry) before re-introducing
the call here. The drift detector
``test_mcp_bridge_wrapped_tool_count_matches_canonical`` will catch the
regression.
"""

from __future__ import annotations

from typing import Any

from ..state import IKIGAiStateDict


def tag_and_persist_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Surface missing bridge via direct error_channel write.

    M12 removed ``mcp_bridge.ikigai_tag_and_persist``. See module docstring.
    """
    return {
        "tags": None,
        "error_channel": [
            "mcp_bridge.ikigai_tag_and_persist not available post-V5-E "
            "(M12 deleted wrapper); see src/ikigai/src/agents/v2/mcp_bridge.py docstring"
        ],
        "last_step": "tag_and_persist",
    }
