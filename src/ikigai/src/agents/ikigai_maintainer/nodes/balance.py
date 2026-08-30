"""balance node — hysteresis-aware workload/capacity balancer."""

from __future__ import annotations

from typing import Any

from ..state import (
    IKIGAiStateDict,
    BalancerVerdict,
    HYSTERESIS_UPGRADE_DAYS,
    HYSTERESIS_DOWNGRADE_DAYS,
    DEFAULT_WORKLOAD_OVERLOAD_FACTOR,
    DEFAULT_WORKLOAD_UNDERLOAD_FACTOR,
    DEFAULT_QHE_RECOVER,
)


def balance_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Evaluate workload vs capacity and enforce regime hysteresis.

    Reads:
    - q_he_score
    - workload_estimate
    - capacity_estimate
    - regime_state
    - days_in_regime

    Returns updated balancer_verdict and is_hysteresis_active.
    """
    q_he = state.get("q_he_score", 0.65)
    workload = state.get("workload_estimate", 2.0)
    capacity = state.get("capacity_estimate", 8.0)
    regime = state.get("regime_state", "MAINTAIN")
    days = state.get("days_in_regime", 1)

    workload_ratio = workload / max(capacity, 1.0)

    # Determine verdict
    if q_he < DEFAULT_QHE_RECOVER:
        verdict: str = "RECOVER"
    elif workload_ratio >= DEFAULT_WORKLOAD_OVERLOAD_FACTOR:
        verdict = "OVERLOAD"
    elif workload_ratio <= DEFAULT_WORKLOAD_UNDERLOAD_FACTOR:
        verdict = "UNDERLOAD"
    else:
        verdict = "OK"

    # Hysteresis check — upgrade only after sustained days
    is_hysteresis_active = False
    if regime in ("MAINTAIN", "REDUCE", "RECOVER") and days < HYSTERESIS_UPGRADE_DAYS:
        is_hysteresis_active = True
    elif regime == "PUSH" and days < HYSTERESIS_DOWNGRADE_DAYS:
        is_hysteresis_active = True

    # Emit corrections
    corrections = []
    if verdict == "RECOVER":
        corrections.append(
            {
                "heuristic": "H1",
                "signal_type": "regime_override",
                "description": f"Q_HE {q_he:.2f} below recover threshold {DEFAULT_QHE_RECOVER}",
                "target_ueid": None,
                "urgency": "critical",
                "metadata": {"current_regime": regime, "days_in_regime": days},
            }
        )
    elif verdict == "OVERLOAD":
        corrections.append(
            {
                "heuristic": "H1",
                "signal_type": "workload_overload",
                "description": f"Workload {workload:.1f}h/day exceeds {DEFAULT_WORKLOAD_OVERLOAD_FACTOR}x capacity",
                "target_ueid": None,
                "urgency": "high",
                "metadata": {"workload": workload, "capacity": capacity},
            }
        )

    return {
        "balancer_verdict": verdict,
        "is_hysteresis_active": is_hysteresis_active,
        "last_step": "balance",
        "corrections": corrections,
    }
