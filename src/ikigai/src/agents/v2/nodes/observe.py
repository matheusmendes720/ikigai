from __future__ import annotations

from datetime import date
from typing import Any

from src.ikigai.src.agents.v2 import mcp_bridge

from ..state import IKIGAiStateDict


def observe_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Read Q_HE observation via MCP bridge. Replaces prompt-chain stub."""
    try:
        result = mcp_bridge.ikigai_observe_pav_state(
            date=state.get("date") or date.today().isoformat()
        )
        return {"observation": result}
    except Exception as e:
        return {"observation": None, "error_type": type(e).__name__, "error_message": f"observe: {e}"}


def _build_agent_response(state: IKIGAiStateDict) -> str:
    """Build a readable agent response from current IKIGAI state."""
    vs = state.get("vector_scores", {})
    lines = [
        f"Regime: {state.get('regime_state', '?')}  |  Q_HE: {state.get('q_he_score', 0):.4f}",
        f"Phase: {state.get('phase', '?')}  |  Verdict: {state.get('balancer_verdict', '?')}",
        "",
        "IKIGAi Vectors:",
    ]
    for vec, score in vs.items():
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        lines.append(f"   {vec.capitalize():12s}  [{bar}]  {score:.1f}")
    lines.append(f"   {'Meta-vector':12s}  {state.get('meta_vector_score', 0):.1f}")
    corrections = state.get("corrections", [])
    if corrections:
        lines.append(f"\nCorrections ({len(corrections)}):")
        for c in corrections[-3:]:
            lines.append(f"   [{c.get('heuristic')}] {c.get('description', '')}")
    else:
        lines.append("\nNo corrections — system balanced")
    prospective = state.get("prospective_buffer", [])
    if prospective:
        lines.append(f"\nProspective buffer ({len(prospective)}):")
        for p in prospective[-3:]:
            lines.append(f"   - {p}")
    return "\n".join(lines)
