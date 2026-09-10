from __future__ import annotations

from src.ikigai.src.agents.v2 import mcp_bridge

from ..state import IKIGAiStateDict


def heuristics_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Apply heuristics via MCP bridge.

    B6 fix 2026-09-10: removed 6 dead helper functions (_h1_energy_required,
    _h2_qhe_composite, _h3_regime_fsm, _h6_severity, render_h1_energy,
    render_h2_qhe_composite, render_h6_severity) that referenced a
    non-existent `_c(...)` helper. These functions were dead code
    (heuristics_node only calls mcp_bridge.ikigai_heuristics) and would
    have raised NameError if invoked.

    The historical implementations are preserved in
    archive/recovered-agentic-2026-09-01/ if revival is ever needed.
    """
    try:
        result = mcp_bridge.ikigai_heuristics(context=state.get("context", {}))
        return {"heuristics": result}
    except Exception as e:
        return {"heuristics": None, "error_type": type(e).__name__, "error_message": f"heuristics: {e}"}
