"""plan node — prospective channel: draft next actions for current tier."""
from __future__ import annotations

import datetime as dt
from typing import Any

from ..state import IKIGAiStateDict, PlanTier


def plan_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Prospective channel: draft next actions based on current tier and regime.

    Populates `prospective_buffer` with proposed action strings.
    """
    today = dt.date.today()
    tier = _infer_tier(today, state.get("cycle_start"), state.get("cycle_end"))

    regime = state.get("regime_state", "MAINTAIN")
    q_he = state.get("q_he_score", 0.65)

    buffer: list[str] = []

    # Regime-specific planning
    if regime == "PUSH":
        buffer.append(f"[PUSH] Maximize output — target {q_he:.0%} Q_HE")
        buffer.append("Draft next ONDA tasks for completion")
    elif regime == "MAINTAIN":
        buffer.append(f"[MAINTAIN] Sustain — current Q_HE {q_he:.0%}")
        buffer.append("Review weekly progress and adjust if needed")
    elif regime == "REDUCE":
        buffer.append(f"[REDUCE] Wind down — focus on completion over new work")
        buffer.append("Mark ONDA deliverables as done")
    elif regime == "RECOVER":
        buffer.append("[RECOVER] Health priority — reduce cognitive load")
        buffer.append("Pause non-essential tasks")

    # Tier-specific
    if tier == PlanTier.ONDA:
        buffer.append("[ONDA] 45-day sprint — decompose to weekly milestones")
    elif tier == PlanTier.QUARTERLY:
        buffer.append("[QUARTERLY] Draft next ONDA from active goals")
    elif tier == PlanTier.WEEKLY:
        buffer.append("[WEEKLY] Plan this week's tasks from active projects")

    return {
        "prospective_buffer": buffer,
        "last_step": "plan",
    }


def _infer_tier(today: dt.date, cycle_start: str | None, cycle_end: str | None) -> PlanTier:
    """Infer current planning tier from cycle dates."""
    if not cycle_start or not cycle_end:
        return PlanTier.ONDA
    start = dt.date.fromisoformat(cycle_start)
    end = dt.date.fromisoformat(cycle_end)
    total = (end - start).days
    if total <= 0:
        return PlanTier.ONDA
    frac = (today - start).days / total
    if frac < 0.05:
        return PlanTier.SONHO
    if frac < 0.30:
        return PlanTier.QUARTERLY
    if frac < 0.65:
        return PlanTier.ONDA
    if frac < 0.95:
        return PlanTier.WEEKLY
    return PlanTier.DAILY
