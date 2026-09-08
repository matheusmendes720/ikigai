from src.ikigai.src.agents.v2 import mcp_bridge

from ..state import IKIGAiStateDict


def observe_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Read Q_HE observation via MCP bridge. Replaces prompt-chain stub."""
    try:
        result = mcp_bridge.ikigai_observe_pav_state(
            date=state.get("date", "2026-09-08")
        )
        return {"observation": result}
    except Exception as e:
        return {"observation": None, "error_type": type(e).__name__, "error_message": f"observe: {e}"}


def _build_agent_response(state: IKIGAiStateDict) -> str:
    """Build a readable agent response from current IKIGAi state."""
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


def _read_workload_from_upi() -> float:
    """Read today's task count from solverforge-calendar-mcp.

    Returns hours/day estimate based on active UPI count.

    TODO(Phase 8.2): replace subprocess call with MCP tool wrapper.
    """
    try:
        result = subprocess.run(
            [
                "solverforge-calendar-mcp",
                "--json",
                "upi_list",
                "--limit",
                "50",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            items = data if isinstance(data, list) else []
            # Estimate 1.5h per active task per day
            active = [i for i in items if i.get("status") not in ("Done", "Cancelled")]
            return len(active) * 1.5
    except Exception:
        pass
    return 2.0
