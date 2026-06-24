"""Dream entity — 5-10 year vision."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from ikigai.entities.base import PlanEntity
from ikigai.enums import EntityType, StatusType


class DreamEntity(PlanEntity):
    """Long-term vision (5-10 years / 1825-3650 days)."""

    entity_type: Literal[EntityType.DREAM] = EntityType.DREAM  # type: ignore[assignment]
    horizon_days: Literal[1825, 2190, 2555, 2920, 3285, 3650]  # type: ignore[valid-type]

    # Dream-specific fields
    motivation: str | None = None
    success_metric: str | None = None
    core_values: list[str] = []

    @model_validator(mode="after")
    def _validate_dream_status(self) -> "DreamEntity":
        """Dream-specific allowed statuses."""
        allowed = {
            StatusType.SEED,
            StatusType.ACTIVE,
            StatusType.FULFILLED,
            StatusType.ABANDONED,
            StatusType.ARCHIVED,
        }
        if self.status not in allowed:
            raise ValueError(
                f"DreamEntity status must be one of {sorted(s.value for s in allowed)}, "
                f"got {self.status.value}"
            )
        return self


__all__ = ["DreamEntity"]
