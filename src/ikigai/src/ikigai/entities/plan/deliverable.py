"""Deliverable entity — concrete artifact output."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import model_validator

from ikigai.entities.base import PlanEntity
from ikigai.enums import EntityType, StatusType


class DeliverableEntity(PlanEntity):
    """Concrete deliverable (artifact, document, code, etc.)."""

    entity_type: Literal[EntityType.DELIVERABLE] = EntityType.DELIVERABLE
    horizon_days: Literal[1, 2, 3, 4, 5, 6, 7, 14, 30]
    artifact_path: Path | None = None
    artifact_type: str = "document"  # document | code | data | media | other
    is_public: bool = False

    @model_validator(mode="after")
    def _validate_deliverable_status(self) -> DeliverableEntity:
        allowed = {
            StatusType.DRAFT,
            StatusType.PLANNED,
            StatusType.IN_PROGRESS,
            StatusType.DONE,
            StatusType.CANCELLED,
        }
        if self.status not in allowed:
            raise ValueError(
                f"DeliverableEntity status must be one of {sorted(s.value for s in allowed)}, "
                f"got {self.status.value}"
            )
        return self


__all__ = ["DeliverableEntity"]
