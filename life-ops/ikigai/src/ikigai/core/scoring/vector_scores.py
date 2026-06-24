"""5-vector scoring — passion, skill, market, revenue, course.

All functions return ScoreValue (percent, 0-100).
"""

from __future__ import annotations

import math
from typing import Iterable

from ikigai.constants import NSM
from ikigai.enums import VectorType
from ikigai.types import ScoreValue


def score_passion(streak_days: float, lambda_rate: float = NSM.LAMBDA) -> ScoreValue:
    """H(t) = 1 - e^(-λ · streak), λ = 0.093 D⁻¹.

    Args:
        streak_days: consecutive days of habit engagement.
        lambda_rate: learning rate (default from NSM).

    Returns:
        ScoreValue in [0, 100].
    """
    if streak_days < 0:
        raise ValueError(f"streak_days must be >= 0, got {streak_days}")
    if lambda_rate < 0:
        raise ValueError(f"lambda_rate must be >= 0, got {lambda_rate}")
    h = 1.0 - math.exp(-lambda_rate * streak_days)
    return ScoreValue(value=round(h * 100, 2), unit="percent")


def score_skill(
    skill_level_scores: Iterable[float],
    market_demand_weights: Iterable[float],
    learning_momentum: float = 0.0,
    project_completion: float = 0.0,
) -> ScoreValue:
    """Skill vector = weighted sum of (level_score × demand) + momentum + completion.

    Formula (per ikigai_4_vectors.md §1.2):
        skill_score = Σ(level × demand) × 0.5 + momentum × 0.3 + completion × 0.2

    All inputs in [0, 100].
    """
    skills = list(skill_level_scores)
    demands = list(market_demand_weights)
    if len(skills) != len(demands):
        raise ValueError(
            f"skill_level_scores ({len(skills)}) and market_demand_weights ({len(demands)}) must have same length"
        )
    if not 0 <= learning_momentum <= 100:
        raise ValueError(f"learning_momentum must be in [0, 100], got {learning_momentum}")
    if not 0 <= project_completion <= 100:
        raise ValueError(f"project_completion must be in [0, 100], got {project_completion}")

    if not skills:
        return ScoreValue(value=0.0, unit="percent")

    weighted = sum((s * d) / 100.0 for s, d in zip(skills, demands, strict=True))
    avg_weighted = weighted / len(skills)  # normalize to [0, 100]

    skill_score = avg_weighted * 0.5 + learning_momentum * 0.3 + project_completion * 0.2
    return ScoreValue(value=round(min(100.0, max(0.0, skill_score)), 2), unit="percent")


def score_market(
    fit_avg: float,
    skills_demand_avg: float,
    opportunities_pipeline: float,
) -> ScoreValue:
    """Market vector = fit × 0.4 + demand × 0.4 + pipeline × 0.2.

    All inputs in [0, 100].
    """
    for name, v in [("fit_avg", fit_avg), ("skills_demand_avg", skills_demand_avg), ("opportunities_pipeline", opportunities_pipeline)]:
        if not 0 <= v <= 100:
            raise ValueError(f"{name} must be in [0, 100], got {v}")
    market_score = fit_avg * 0.4 + skills_demand_avg * 0.4 + opportunities_pipeline * 0.2
    return ScoreValue(value=round(min(100.0, market_score), 2), unit="percent")


def score_revenue(revenue_actual: float, revenue_target: float, pipeline_health: float = 0.0) -> ScoreValue:
    """Revenue vector = (actual / target) × 70 + pipeline × 30.

    Args:
        revenue_actual: actual revenue in BRL.
        revenue_target: target revenue in BRL (use >= 1 to avoid division by zero).
        pipeline_health: 0-100.
    """
    if revenue_target < 1:
        revenue_target = 1.0  # avoid div-by-zero
    if not 0 <= pipeline_health <= 100:
        raise ValueError(f"pipeline_health must be in [0, 100], got {pipeline_health}")
    if revenue_actual < 0:
        raise ValueError(f"revenue_actual must be >= 0, got {revenue_actual}")
    if revenue_target < 0:
        raise ValueError(f"revenue_target must be >= 0, got {revenue_target}")

    ratio = revenue_actual / revenue_target
    revenue_score = ratio * 70.0 + pipeline_health * 0.3
    return ScoreValue(value=round(min(100.0, max(0.0, revenue_score)), 2), unit="percent")


def score_course(
    attendance_rate: float,
    assignments_on_time: float,
    exam_avg: float,
) -> ScoreValue:
    """Course vector = attendance × 0.5 + assignments × 0.3 + exams × 0.2.

    All inputs in [0, 100].
    """
    for name, v in [("attendance_rate", attendance_rate), ("assignments_on_time", assignments_on_time), ("exam_avg", exam_avg)]:
        if not 0 <= v <= 100:
            raise ValueError(f"{name} must be in [0, 100], got {v}")
    course_score = attendance_rate * 0.5 + assignments_on_time * 0.3 + exam_avg * 0.2
    return ScoreValue(value=round(min(100.0, course_score), 2), unit="percent")


def compute_vector_scores(
    passion_streak_days: float = 0.0,
    skill_inputs: tuple[list[float], list[float], float, float] | None = None,
    market_inputs: tuple[float, float, float] | None = None,
    revenue_inputs: tuple[float, float, float] | None = None,
    course_inputs: tuple[float, float, float] | None = None,
) -> dict[VectorType, ScoreValue]:
    """Compute all 5 vector scores.

    Returns dict[VectorType, ScoreValue].
    """
    scores: dict[VectorType, ScoreValue] = {
        VectorType.PASSION: score_passion(passion_streak_days),
    }

    if skill_inputs is not None:
        skills, demands, momentum, completion = skill_inputs
        scores[VectorType.SKILL] = score_skill(skills, demands, momentum, completion)
    else:
        scores[VectorType.SKILL] = ScoreValue(value=50.0, unit="percent")

    if market_inputs is not None:
        fit, demand, pipeline = market_inputs
        scores[VectorType.MARKET] = score_market(fit, demand, pipeline)
    else:
        scores[VectorType.MARKET] = ScoreValue(value=50.0, unit="percent")

    if revenue_inputs is not None:
        actual, target, health = revenue_inputs
        scores[VectorType.REVENUE] = score_revenue(actual, target, health)
    else:
        scores[VectorType.REVENUE] = ScoreValue(value=50.0, unit="percent")

    if course_inputs is not None:
        attendance, assignments, exams = course_inputs
        scores[VectorType.COURSE] = score_course(attendance, assignments, exams)
    else:
        scores[VectorType.COURSE] = ScoreValue(value=50.0, unit="percent")

    return scores


__all__ = [
    "score_passion",
    "score_skill",
    "score_market",
    "score_revenue",
    "score_course",
    "compute_vector_scores",
]
