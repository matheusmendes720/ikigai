"""Objective entity — 3-12 month objective with key results."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from ikigai.entities.base import PlanEntity
from ikigai.enums import EntityType, StatusType


class ObjectiveEntity(PlanEntity):
    """Short-term objective (3-12 months / 90-365 days)."""

    entity_type: Literal[EntityType.OBJECTIVE] = EntityType.OBJECTIVE  # type: ignore[assignment]
    horizon_days: Literal[90, 120, 150, 180, 240, 365]  # type: ignore[valid-type]

    # Objective-specific fields (OKR-style)
    key_results: list[str] = []
    progress_pct: float = 0.0  # 0-100

    @model_validator(mode="after")
    def _validate_objective_status(self) -> "ObjectiveEntity":
        allowed = {
            StatusType.DRAFT,
            StatusType.PLANNED,
            StatusType.ACTIVE,
            StatusType.IN_PROGRESS,
            StatusType.BLOCKED,
            StatusType.DONE,
            StatusType.ABANDONED,
        }
        if self.status not in allowed:
            raise ValueError(
                f"ObjectiveEntity status must be one of {sorted(s.value for s in allowed)}, "
                f"got {self.status.value}"
            )
        if not 0 <= self.progress_pct <= 100:
            raise ValueError(f"progress_pct must be in [0, 100], got {self.progress_pct}")
        return self


__all__ = ["ObjectiveEntity"]
