from src.ikigai.src.agents.v2 import mcp_bridge

from ..state import IKIGAiStateDict


def heuristics_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Apply heuristics via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_heuristics(context=state.get("context", {}))
        return {"heuristics": result}
    except Exception as e:
        return {"heuristics": None, "error_type": type(e).__name__, "error_message": f"heuristics: {e}"}


def _h1_energy_required(
    state: IKIGAiStateDict, prompt_state: dict[str, Any]
) -> list[CorrectionSignal]:
    """H1: Energy required = R x (1 - H(t))."""
    corrections: list[CorrectionSignal] = []
    obs = render_h1_energy(prompt_state)
    energy_factor = obs.get("h1_energy", 0.7)
    if energy_factor > 0.4:
        corrections.append(
            {
                "heuristic": "H1",
                "signal_type": "high_energy_required",
                "description": f"Energy factor {energy_factor:.2f} — low habit consistency demands more willpower",
                "target_ueid": None,
                "urgency": "high" if energy_factor > 0.6 else "medium",
                "metadata": {"energy_factor": round(energy_factor, 3)},
            }
        )
    return corrections


def _h2_qhe_composite(
    state: IKIGAiStateDict, prompt_state: dict[str, Any]
) -> list[CorrectionSignal]:
    """H2: Q_HE composite — flag if below regime target."""
    corrections: list[CorrectionSignal] = []
    obs = render_h2_qhe_composite(prompt_state)
    q_he = obs.get("h2_qhe_composite", state.get("q_he_score", 0.65))
    regime = state.get("regime_state", "MAINTAIN")
    targets = _c("REGIME_TARGETS")
    target = targets.get(regime, 0.65)
    deviation = target - q_he
    if deviation > _c("HEURISTICS_H2_DEVIATION_WARN"):
        corrections.append(
            {
                "heuristic": "H2",
                "signal_type": "qhe_below_target",
                "description": f"Q_HE {q_he:.2f} is {deviation:.2f} below {regime} target {target:.2f}",
                "target_ueid": None,
                "urgency": (
                    "critical" if deviation > _c("HEURISTICS_H2_DEVIATION_CRITICAL") else "high"
                ),
                "metadata": {
                    "q_he": round(q_he, 3),
                    "target": target,
                    "deviation": round(deviation, 3),
                },
            }
        )
    return corrections


def _h3_regime_fsm(state: IKIGAiStateDict, prompt_state: dict[str, Any]) -> list[CorrectionSignal]:
    """H3: Regime FSM transitions — hysteresis-gated promotions."""
    corrections: list[CorrectionSignal] = []
    regime = state.get("regime_state", "MAINTAIN")
    days = state.get("days_in_regime", 1)
    is_hysteresis = state.get("is_hysteresis_active", False)
    if regime == "MAINTAIN" and days >= _c("HEURISTICS_H3_MAINTAIN_UPGRADE_DAYS"):
        corrections.append(
            {
                "heuristic": "H3",
                "signal_type": "potential_upgrade",
                "description": (
                    f"{_c('HEURISTICS_H3_MAINTAIN_UPGRADE_DAYS')}+ days in MAINTAIN — "
                    f"consider PUSH if Q_HE > {_c('HEURISTICS_H3_PUSH_QHE_THRESHOLD')}"
                ),
                "target_ueid": None,
                "urgency": "low",
                "metadata": {"regime": regime, "days_in_regime": days},
            }
        )
    elif regime == "PUSH" and days >= _c("HEURISTICS_H3_PUSH_DOWNGRADE_DAYS") and not is_hysteresis:
        corrections.append(
            {
                "heuristic": "H3",
                "signal_type": "potential_downgrade",
                "description": (
                    f"{_c('HEURISTICS_H3_PUSH_DOWNGRADE_DAYS')}+ days in PUSH without "
                    "sustained Q_HE — consider MAINTAIN"
                ),
                "target_ueid": None,
                "urgency": "medium",
                "metadata": {"regime": regime, "days_in_regime": days},
            }
        )
    return corrections


def _h6_severity(state: IKIGAiStateDict, prompt_state: dict[str, Any]) -> list[CorrectionSignal]:
    """H6: Severity = infractions x hours_deviation x consistency."""
    corrections: list[CorrectionSignal] = []
    obs = render_h6_severity(prompt_state)
    _ = obs.get("h6_severity")  # context signal from LLM; arithmetic below is preserved
    q_he = state.get("q_he_score", 0.65)
    workload = state.get("workload_estimate", 2.0)
    capacity = state.get("capacity_estimate", 8.0)
    infractions = 1.0 if workload > capacity * _c("WORKLOAD_OVERLOAD_FACTOR") else 0.0
    hours_dev = (workload - capacity) / max(capacity, 1.0)
    severity = float(infractions) * abs(hours_dev) * q_he
    if severity > _c("HEURISTICS_H6_SEVERITY_WARN"):
        corrections.append(
            {
                "heuristic": "H6",
                "signal_type": "high_severity",
                "description": f"Severity {severity:.2f} — infractions={infractions}, hours_dev={hours_dev:.2f}",
                "target_ueid": None,
                "urgency": (
                    "critical" if severity > _c("HEURISTICS_H6_SEVERITY_CRITICAL") else "high"
                ),
                "metadata": {
                    "severity": round(severity, 3),
                    "infractions": infractions,
                    "hours_dev": round(hours_dev, 3),
                },
            }
        )
    return corrections
