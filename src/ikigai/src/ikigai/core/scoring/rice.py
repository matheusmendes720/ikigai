"""RICE scoring + RICE+IKIGAi task priority."""

from __future__ import annotations

from ikigai.entities.plan.task import TaskEntity


def compute_rice_score(reach: float, impact: float, confidence: float, effort: float) -> float:
    """RICE = (R × I × C) / E.

    Args:
        reach: 1-10.
        impact: 0.25-3.
        confidence: 0-1.
        effort: hours (>0).

    Returns:
        RICE score (raw, unbounded).
    """
    if not 1 <= reach <= 10:
        raise ValueError(f"reach must be in [1, 10], got {reach}")
    if not 0.25 <= impact <= 3:
        raise ValueError(f"impact must be in [0.25, 3], got {impact}")
    if not 0 <= confidence <= 1:
        raise ValueError(f"confidence must be in [0, 1], got {confidence}")
    if effort < 0:
        raise ValueError(f"effort must be >= 0, got {effort}")
    return (reach * impact * confidence) / max(effort, 0.5)


# W_IKIGAI: weight multiplier by vector (per meta_heuristics.md §6.2)
W_IKIGAI_BY_VECTOR = {
    "passion": 1.0,
    "skill": 1.2,
    "market": 1.5,
    "revenue": 1.5,
    "course": 0.8,
}


def _deadline_weight(days_to_deadline: int | None) -> float:
    """Deadline weight per meta_heuristics.md §6.3."""
    if days_to_deadline is None:
        return 1.0
    if days_to_deadline < 7:
        return 1.5
    if days_to_deadline < 30:
        return 1.2
    if days_to_deadline < 90:
        return 1.0
    return 0.8


def compute_task_priority(
    task: TaskEntity,
    w_ikigai: float = 1.0,
    days_to_deadline: int | None = None,
) -> float:
    """Compute final task priority = RICE × w_ikigai × w_deadline.

    Args:
        task: TaskEntity.
        w_ikigai: IKIGAi vector weight (from entity or vector).
        days_to_deadline: optional days until deadline.

    Returns:
        Priority score.
    """
    rice = task.rice_score
    w_deadline = _deadline_weight(days_to_deadline)
    return rice * w_ikigai * w_deadline


__all__ = ["compute_rice_score", "compute_task_priority", "W_IKIGAI_BY_VECTOR"]
