"""Project entity — 1-6 month project (forward-compat with CLUSTER_PROJ)."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from ikigai.entities.base import PlanEntity
from ikigai.enums import EntityType, StatusType


class ProjectEntity(PlanEntity):
    """Project (1-6 months / 30-180 days). Forward-compat placeholder for CLUSTER_PROJ.

    Once CLUSTER_PROJ is built, projects can be 'claimed' via claimed_by='cluster_proj'.
    Until then, this entity is fully usable as a planning unit.
    """

    entity_type: Literal[EntityType.PROJECT] = EntityType.PROJECT  # type: ignore[assignment]
    horizon_days: Literal[30, 60, 90, 120, 150, 180]  # type: ignore[valid-type]

    # Project-specific fields (forward-compat)
    tech_stack: list[str] = []
    repo_url: str | None = None
    target_revenue_brl: float | None = None
    actual_revenue_brl: float = 0.0

    @model_validator(mode="after")
    def _validate_project_status(self) -> "ProjectEntity":
        allowed = {
            StatusType.DRAFT,
            StatusType.PLANNED,
            StatusType.ACTIVE,
            StatusType.IN_PROGRESS,
            StatusType.PAUSED,
            StatusType.BLOCKED,
            StatusType.COMPLETED,
            StatusType.CANCELLED,
        }
        if self.status not in allowed:
            raise ValueError(
                f"ProjectEntity status must be one of {sorted(s.value for s in allowed)}, "
                f"got {self.status.value}"
            )
        return self


__all__ = ["ProjectEntity"]
