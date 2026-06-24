"""H6: Cross-cluster priority — RICE + IKIGAi weights."""

from __future__ import annotations

from ikigai.core.scoring.rice import (
    W_IKIGAI_BY_VECTOR,
    _deadline_weight,
    compute_rice_score,
)
from ikigai.entities.plan.task import TaskEntity


def compute_weighted_priority(
    task: TaskEntity,
    w_ikigai_by_vector: dict[str, float] | None = None,
    days_to_deadline: int | None = None,
) -> float:
    """Compute final task priority = RICE × w_ikigai × w_deadline.

    Args:
        task: TaskEntity with ikigai_vectors in primary_score or vector_weights_snapshot.
        w_ikigai_by_vector: override for IKIGAi weights by vector.
        days_to_deadline: optional days until deadline.
    """
    weights_map = w_ikigai_by_vector or W_IKIGAI_BY_VECTOR
    rice = compute_rice_score(task.rice_reach, task.rice_impact, task.rice_confidence, task.rice_effort_h)
    w_deadline = _deadline_weight(days_to_deadline)

    # Aggregate w_ikigai from task's vectors
    if task.ikigai_vectors:
        w_ikigai = max(weights_map.get(v.value, 1.0) for v in task.ikigai_vectors)
    else:
        w_ikigai = 1.0

    return rice * w_ikigai * w_deadline


def rank_tasks(tasks: list[TaskEntity], **kwargs) -> list[TaskEntity]:
    """Sort tasks by weighted priority (descending)."""
    scored = [(compute_weighted_priority(t, **kwargs), t) for t in tasks]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored]


__all__ = ["compute_weighted_priority", "rank_tasks"]
