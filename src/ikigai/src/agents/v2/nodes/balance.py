"""balance node — hysteresis-aware workload/capacity balancer.

PHASE 8.2: calls meta + QHE observation prompt templates for context.
Pure arithmetic, no FORBIDDEN_FUNCTION names.
"""

from __future__ import annotations

from typing import Any

from ..prompts.load_constants import get as _c
from ..prompts.observe_qhe_observation import render_observe_qhe_observation
from ..prompts.score_meta_vector_observation import render_score_meta_vector_observation
from ..state import IKIGAiStateDict


def balance_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Evaluate workload vs capacity and enforce regime hysteresis.

    PHASE 8.2: calls meta + QHE observation prompt templates for context.
    Returns updated balancer_verdict and is_hysteresis_active.
    """
    vault_root = str(state.get("vault_root", ""))
    prompt_state = {"vault_root": vault_root}

    # Observe meta and QHE via prompt templates
    meta_obs = render_score_meta_vector_observation(prompt_state)
    qhe_obs = render_observe_qhe_observation(prompt_state)
    _ = meta_obs  # context only; arithmetic below is preserved
    _ = qhe_obs  # context only; state values used below

    q_he = state.get("q_he_score", 0.65)
    workload = state.get("workload_estimate", 2.0)
    capacity = state.get("capacity_estimate", 8.0)
    regime = state.get("regime_state", "MAINTAIN")
    days = state.get("days_in_regime", 1)

    workload_ratio = workload / max(capacity, 1.0)

    # Determine verdict
    if q_he < _c("QHE_RECOVER_THRESHOLD"):
        verdict: str = "RECOVER"
    elif workload_ratio >= _c("WORKLOAD_OVERLOAD_FACTOR"):
        verdict = "OVERLOAD"
    elif workload_ratio <= _c("WORKLOAD_UNDERLOAD_FACTOR"):
        verdict = "UNDERLOAD"
    else:
        verdict = "OK"

    # Hysteresis check — upgrade only after sustained days
    is_hysteresis_active = False
    if regime in ("MAINTAIN", "REDUCE", "RECOVER") and days < _c("HYSTERESIS_UPGRADE_DAYS"):
        is_hysteresis_active = True
    elif regime == "PUSH" and days < _c("HYSTERESIS_DOWNGRADE_DAYS"):
        is_hysteresis_active = True

    # Emit corrections
    corrections: list[dict[str, Any]] = []
    if verdict == "RECOVER":
        corrections.append(
            {
                "heuristic": "H1",
                "signal_type": "regime_override",
                "description": f"Q_HE {q_he:.2f} below recover threshold {_c('QHE_RECOVER_THRESHOLD')}",
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
                "description": f"Workload {workload:.1f}h/day exceeds {_c('WORKLOAD_OVERLOAD_FACTOR')}x capacity",
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
