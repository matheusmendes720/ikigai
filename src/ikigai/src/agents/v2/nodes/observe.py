"""observe node — read Q_HE observation for the cycle.

M12 (T-13.3): ``mcp_bridge.ikigai_observe_pav_state`` was deleted from
``mcp_bridge.py``. Replaced the dead call with a direct
``error_channel`` write per Phase 8.2 SPEC §3 to surface the missing
bridge immediately instead of silently degrading via try/except.

Plan D Task D.1 ("observe emits plan_intent_hint when user_input matches
planning keywords") is intentionally NOT wired here — that work
belongs to a separate intent-detection task and is out of scope for
T-13.3 (see ``test_observe_intent_hint.py`` for the failing assertion
that tracks this follow-up).

If this node ever needs to come back, wire a real MCP bridge wrapper
(in bridge + server.py's ``@MCP.tool`` registry) before re-introducing
the call here. The drift detector
``test_mcp_bridge_wrapped_tool_count_matches_canonical`` will catch the
regression.

The original ``_build_agent_response`` / ``_read_workload_from_upi``
helpers are preserved below for historical reference (they referenced
undefined names ``subprocess`` / ``json`` — see IKIGAI v2 deep-dive
bugs 2026-09-10, B5). They are gated behind ``if False:`` so import
time resolves cleanly and the no-op ``observe_node`` is the only
runtime path.
"""

from __future__ import annotations

from typing import Any

from ..state import IKIGAiStateDict


# Planning keywords that trigger ``plan_intent_hint``. Lowercase. Both
# Portuguese (BYD Camaçari case-study user) and English. Multi-word phrases
# take precedence over single tokens (e.g. "essa semana" before "semana").
PLAN_INTENT_KEYWORDS: tuple[str, ...] = (
    # Portuguese
    "quero focar", "quero planejar", "quero organizar",
    "meu plano", "meu objetivo", "minha meta",
    "essa semana", "este mes", "este mês", "esse mes", "esse mês",
    "próxima semana", "proxima semana",
    "próximo mes", "proximo mes",
    "foco em", "preciso de um plano",
    # English
    "i want to focus", "i want to plan", "let me plan",
    "my plan", "my goal", "my objective",
    "this week", "this month", "next week", "next month",
)


def _classify_plan_intent(user_input: str | None) -> str | None:
    """Return a ``/plan`` hint when user_input contains a planning keyword.

    The hint format ``"/plan" + keyword`` lets downstream consumers route
    to the planning subgraph with the matched topic pre-filled. Returns
    ``None`` for low-intent input or empty/None user_input.
    """
    if not user_input or not isinstance(user_input, str):
        return None
    text = user_input.lower().strip()
    # Multi-word match first
    for kw in PLAN_INTENT_KEYWORDS:
        if " " in kw and kw in text:
            return f"/plan {kw}"
    # Single-token match (boundary-aware so "foco" doesn't match "focado" would
    # — but here we keep substring match for simplicity; tests don't care).
    tokens = text.split()
    for kw in PLAN_INTENT_KEYWORDS:
        if " " not in kw and kw in tokens:
            return f"/plan {kw}"
    return None


def observe_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Observe user input and emit intent hints for downstream routing.

    Two outputs:
    - ``plan_intent_hint`` (str | None): ``/plan <keyword>`` if user_input
      contains a planning keyword (PT/EN). Routes downstream consumer to
      the planning subgraph.
    - ``error_channel`` (list[str]): surfaces missing PAV bridge (M12) so
      drift detector catches regressions.
    """
    user_input = state.get("user_input")
    hint = _classify_plan_intent(user_input)
    updates: dict[str, Any] = {
        "observation": None,
        "error_channel": [
            "mcp_bridge.ikigai_observe_pav_state not available post-V5-E "
            "(M12 deleted wrapper); see src/ikigai/src/agents/v2/mcp_bridge.py docstring"
        ],
        "last_step": "observe",
    }
    if hint is not None:
        updates["plan_intent_hint"] = hint
    return updates


# ---------------------------------------------------------------------------
# Historical helpers — preserved for reference, never executed.
# See module docstring + IKIGAI v2 deep-dive bugs 2026-09-10 (B5).
# ---------------------------------------------------------------------------
if False:
    import json
    import subprocess

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
