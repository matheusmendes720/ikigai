"""Task entity — 1-7 day task with priority (forward-compat with TW)."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import model_validator

from ikigai.entities.base import PlanEntity
from ikigai.enums import EntityType, StatusType


class TaskPriority(str, Enum):
    """RICE+IKIGAi priority levels."""

    URGENT = "urgent"  # < 7 days
    HIGH = "high"  # [7, 30) days
    MEDIUM = "medium"  # [30, 90) days
    LOW = "low"  # >= 90 days


class TaskStatus(str, Enum):
    """Task-specific status (extends StatusType)."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskEntity(PlanEntity):
    """Task (1-7 days). Forward-compat placeholder for Taskwarrior integration."""

    entity_type: Literal[EntityType.TASK] = EntityType.TASK  # type: ignore[assignment]
    horizon_days: Literal[1, 2, 3, 4, 5, 6, 7]  # type: ignore[valid-type]

    # Task-specific fields
    priority: TaskPriority = TaskPriority.MEDIUM
    rice_reach: float = 1.0  # RICE: 1-10
    rice_impact: float = 0.5  # RICE: 0.25-3
    rice_confidence: float = 0.8  # RICE: 0-1
    rice_effort_h: float = 1.0  # RICE: hours
    due_date: str | None = None  # ISO date string
    tw_uuid: str | None = None  # Taskwarrior UUID (forward-compat)

    @property
    def rice_score(self) -> float:
        """RICE score = (R × I × C) / E."""
        return (self.rice_reach * self.rice_impact * self.rice_confidence) / max(self.rice_effort_h, 0.5)

    @model_validator(mode="after")
    def _validate_task_status(self) -> "TaskEntity":
        allowed = {
            StatusType.DRAFT,
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.BLOCKED,
            TaskStatus.DONE,
            TaskStatus.CANCELLED,
        }
        if self.status not in allowed:
            raise ValueError(
                f"TaskEntity status must be one of {sorted(s.value for s in allowed)}, "
                f"got {self.status.value}"
            )
        if not 1 <= self.rice_reach <= 10:
            raise ValueError(f"rice_reach must be in [1, 10], got {self.rice_reach}")
        if not 0.25 <= self.rice_impact <= 3:
            raise ValueError(f"rice_impact must be in [0.25, 3], got {self.rice_impact}")
        if not 0 <= self.rice_confidence <= 1:
            raise ValueError(f"rice_confidence must be in [0, 1], got {self.rice_confidence}")
        if self.rice_effort_h < 0:
            raise ValueError(f"rice_effort_h must be >= 0, got {self.rice_effort_h}")
        return self


__all__ = ["TaskEntity", "TaskPriority", "TaskStatus"]
