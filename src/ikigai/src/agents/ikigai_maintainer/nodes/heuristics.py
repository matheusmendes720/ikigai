"""heuristics node — H1-H6 deterministic algorithms.

Each heuristic evaluates one aspect of the plan state and emits corrections.
"""

from __future__ import annotations

from typing import Any

from ..state import IKIGAiStateDict, CorrectionSignal


def heuristics_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Apply H1–H6 deterministic heuristics.

    H1: Energy required = R × (1 − H(t))            [habit_engine]
    H2: Q_HE composite = f(H, E, streak)            [habit_engine]
    H3: Regime FSM — PUSH→MAINTAIN→REDUCE→RECOVER   [policy_engine]
    H4: Market fit score (skill × opportunity)      [score_vectors]
    H5: Skill velocity (learning × demand)          [score_vectors]
    H6: Severity = infractions × hours_dev × consistency  [policy_engine]

    Returns corrections list (appended to existing).
    """
    corrections: list[CorrectionSignal] = list(state.get("corrections", []))

    # H1: Energy required from habit consistency
    corrections.extend(_h1_energy_required(state))

    # H2: Q_HE composite already computed in observe — emit if abnormal
    corrections.extend(_h2_qhe_composite(state))

    # H3: Regime transitions
    corrections.extend(_h3_regime_fsm(state))

    # H6: Severity
    corrections.extend(_h6_severity(state))

    return {
        "corrections": corrections,
        "last_step": "heuristics",
    }


def _h1_energy_required(state: IKIGAiStateDict) -> list[CorrectionSignal]:
    """H1: Energy required = R × (1 − H(t)).

    If consistency is low, more energy will be needed to maintain output.
    """
    corrections: list[CorrectionSignal] = []
    q_he = state.get("q_he_score", 0.65)

    # Energy requirement proxy: inverse of Q_HE
    energy_factor = 1.0 - q_he
    if energy_factor > 0.4:
        corrections.append(
            {
                "heuristic": "H1",
                "signal_type": "high_energy_required",
                "description": f"Energy factor {energy_factor:.2f} — low habit consistency demands more willpower",
                "target_ueid": None,
                "urgency": "high" if energy_factor > 0.6 else "medium",
                "metadata": {"energy_factor": round(energy_factor, 3), "q_he": round(q_he, 3)},
            }
        )
    return corrections


def _h2_qhe_composite(state: IKIGAiStateDict) -> list[CorrectionSignal]:
    """H2: Q_HE composite — flag if below regime target."""
    corrections: list[CorrectionSignal] = []
    q_he = state.get("q_he_score", 0.65)
    regime = state.get("regime_state", "MAINTAIN")

    targets = {"PUSH": 0.85, "MAINTAIN": 0.65, "REDUCE": 0.45, "RECOVER": 0.25}
    target = targets.get(regime, 0.65)
    deviation = target - q_he

    if deviation > 0.15:
        corrections.append(
            {
                "heuristic": "H2",
                "signal_type": "qhe_below_target",
                "description": f"Q_HE {q_he:.2f} is {deviation:.2f} below {regime} target {target:.2f}",
                "target_ueid": None,
                "urgency": "critical" if deviation > 0.3 else "high",
                "metadata": {
                    "q_he": round(q_he, 3),
                    "target": target,
                    "deviation": round(deviation, 3),
                },
            }
        )
    return corrections


def _h3_regime_fsm(state: IKIGAiStateDict) -> list[CorrectionSignal]:
    """H3: Regime FSM transitions — hysteresis-gated promotions."""
    corrections: list[CorrectionSignal] = []
    regime = state.get("regime_state", "MAINTAIN")
    days = state.get("days_in_regime", 1)
    is_hysteresis = state.get("is_hysteresis_active", False)

    # Only suggest upgrade when hysteresis is clear
    if regime == "MAINTAIN" and days >= 14:
        corrections.append(
            {
                "heuristic": "H3",
                "signal_type": "potential_upgrade",
                "description": "14+ days in MAINTAIN — consider PUSH if Q_HE > 0.80",
                "target_ueid": None,
                "urgency": "low",
                "metadata": {"regime": regime, "days_in_regime": days},
            }
        )
    elif regime == "PUSH" and days >= 10 and not is_hysteresis:
        corrections.append(
            {
                "heuristic": "H3",
                "signal_type": "potential_downgrade",
                "description": "10+ days in PUSH without sustained Q_HE — consider MAINTAIN",
                "target_ueid": None,
                "urgency": "medium",
                "metadata": {"regime": regime, "days_in_regime": days},
            }
        )
    return corrections


def _h6_severity(state: IKIGAiStateDict) -> list[CorrectionSignal]:
    """H6: Severity = infractions × hours_deviation × consistency."""
    corrections: list[CorrectionSignal] = []
    q_he = state.get("q_he_score", 0.65)
    workload = state.get("workload_estimate", 2.0)
    capacity = state.get("capacity_estimate", 8.0)

    # Infractions: workload > 1.2x capacity
    infractions = 1.0 if workload > capacity * 1.2 else 0.0
    # Hours deviation: negative = under hours
    hours_dev = (workload - capacity) / max(capacity, 1.0)
    # Consistency: inverse of Q_HE variance from target
    consistency = q_he

    severity = infractions * abs(hours_dev) * consistency

    if severity > 0.5:
        corrections.append(
            {
                "heuristic": "H6",
                "signal_type": "high_severity",
                "description": f"Severity {severity:.2f} — infractions={infractions}, hours_dev={hours_dev:.2f}",
                "target_ueid": None,
                "urgency": "critical" if severity > 1.0 else "high",
                "metadata": {
                    "severity": round(severity, 3),
                    "infractions": infractions,
                    "hours_dev": round(hours_dev, 3),
                },
            }
        )
    return corrections
