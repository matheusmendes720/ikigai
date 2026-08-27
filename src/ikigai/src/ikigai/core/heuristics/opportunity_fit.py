"""H4: Opportunity fit score (Market vector)."""

from __future__ import annotations

from typing import Iterable

from ikigai.enums import VectorType


def compute_opportunity_fit(
    required_skills: Iterable[str],
    user_skills: Iterable[str],
    deadline_days: int | None,
    estimated_revenue_brl: float,
    estimated_hours: float,
    ikigai_alignment: dict[VectorType, float],
    target_rph_brl: float = 30.0,
) -> float:
    """fit_score ∈ [0, 1].

    Components (per meta_heuristics.md §4.2):
    - skills_match (0-1): 40%
    - deadline_feasible (0-1): 20%
    - rph_normalized (0-1): 20%  (R$/hour normalized by target R$30/h)
    - alignment_avg (0-1): 20%
    """
    req = set(required_skills)
    usr = set(user_skills)
    if not req:
        skills_match = 0.0
    else:
        skills_match = len(req & usr) / len(req)

    if deadline_days is None or deadline_days <= 0 or estimated_hours <= 0:
        deadline_feasible = 0.5  # unknown
    else:
        hours_per_day_needed = estimated_hours / deadline_days
        deadline_feasible = 1.0 if hours_per_day_needed <= 2.0 else 0.5

    if estimated_hours <= 0:
        rph_normalized = 0.0
    else:
        rph = estimated_revenue_brl / estimated_hours
        rph_normalized = min(1.0, rph / target_rph_brl)

    if not ikigai_alignment:
        alignment_avg = 0.0
    else:
        alignment_avg = sum(ikigai_alignment.values()) / len(ikigai_alignment)

    fit = (
        skills_match * 0.4
        + deadline_feasible * 0.2
        + rph_normalized * 0.2
        + alignment_avg * 0.2
    )
    return round(min(1.0, max(0.0, fit)), 4)


def classify_opportunity(fit_score: float) -> str:
    """Classify opportunity by fit score (per meta_heuristics.md §4.3).

    >= 0.70: PURSUING
    [0.50, 0.70): EVALUATING
    [0.30, 0.50): DETECTED
    < 0.30: LOST
    """
    if fit_score >= 0.70:
        return "PURSUING"
    if fit_score >= 0.50:
        return "EVALUATING"
    if fit_score >= 0.30:
        return "DETECTED"
    return "LOST"


__all__ = ["compute_opportunity_fit", "classify_opportunity"]
