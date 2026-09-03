"""Task entity — 1-7 day task with priority (forward-compat with TW).

.. deprecated::
    `TaskEntity` is a PAV/PAE-internal model (RICE scoring fields) that
    has no production callers post the PAV archive (2026-08-31). New
    plan-output code should use the canonical `contracts.Task` instead.

    `TaskEntity` is kept for the test suite that pins RICE scoring behavior
    (`tests/test_entities.py` + `tests/test_heuristics.py`). Deprecation
    warnings are suppressed in those test files via
    `pytest.ini::filterwarnings = ignore::DeprecationWarning:ikigai.entities.plan.task`.
"""

from __future__ import annotations

import warnings
from enum import StrEnum
from typing import Any, Literal

from pydantic import model_validator

from ikigai.entities.base import PlanEntity
from ikigai.enums import EntityType, StatusType

_DEPRECATION_MSG = (
    "TaskEntity is a PAV/PAE-internal model with no production callers post "
    "PAV archive (2026-08-31). Use contracts.Task (src/contracts/task.py) for "
    "new plan-output code. See zazzy-plotting-flask.md §4.1.A.8."
)


class TaskPriority(StrEnum):
    """RICE+IKIGAi priority levels."""

    URGENT = "urgent"  # < 7 days
    HIGH = "high"  # [7, 30) days
    MEDIUM = "medium"  # [30, 90) days
    LOW = "low"  # >= 90 days


class TaskStatus(StrEnum):
    """Task-specific status (extends StatusType)."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskEntity(PlanEntity):
    """Task (1-7 days). Forward-compat placeholder for Taskwarrior integration.

    .. deprecated::
        Use `contracts.Task` (`src/contracts/task.py`) for new plan-output
        code. See module docstring.
    """

    entity_type: Literal[EntityType.TASK] = EntityType.TASK
    horizon_days: Literal[1, 2, 3, 4, 5, 6, 7]
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
        """RICE score = (R x I x C) / E."""
        return (self.rice_reach * self.rice_impact * self.rice_confidence) / max(
            self.rice_effort_h, 0.5
        )

    def model_post_init(self, __context: Any) -> None:
        """Fire DeprecationWarning exactly once per construction (Pydantic v2 hook)."""
        super().model_post_init(__context)
        warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)

    @model_validator(mode="after")
    def _validate_task_status(self) -> TaskEntity:
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
