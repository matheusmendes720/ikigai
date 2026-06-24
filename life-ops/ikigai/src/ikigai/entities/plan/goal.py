"""Goal entity — 1-3 year goal with success metrics."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from ikigai.entities.base import PlanEntity
from ikigai.enums import EntityType, StatusType


class GoalEntity(PlanEntity):
    """Mid-term goal (1-3 years / 365-1095 days)."""

    entity_type: Literal[EntityType.GOAL] = EntityType.GOAL  # type: ignore[assignment]
    horizon_days: Literal[365, 547, 730, 913, 1095]  # type: ignore[valid-type]

    # Goal-specific fields
    success_metrics: list[str] = []
    review_frequency_days: int = 90  # quarterly review

    @model_validator(mode="after")
    def _validate_goal_status(self) -> "GoalEntity":
        allowed = {
            StatusType.DRAFT,
            StatusType.ACTIVE,
            StatusType.PAUSED,
            StatusType.ACHIEVED,
            StatusType.ABANDONED,
            StatusType.ARCHIVED,
        }
        if self.status not in allowed:
            raise ValueError(
                f"GoalEntity status must be one of {sorted(s.value for s in allowed)}, "
                f"got {self.status.value}"
            )
        return self


__all__ = ["GoalEntity"]
