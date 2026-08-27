"""ScoreValue — typed numeric with unit (SPEC I3 percent, I4 ratio)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator


class ScoreUnit(str, Enum):
    PERCENT = "percent"   # SPEC I3: vector scores ∈ [0, 100]
    RATIO = "ratio"       # SPEC I4: Q_HE ∈ [0, 1]


class ScoreValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float
    unit: ScoreUnit

    @model_validator(mode="after")
    def _validate_range(self) -> "ScoreValue":
        if self.unit == ScoreUnit.PERCENT and not (0.0 <= self.value <= 100.0):
            raise ValueError(f"PERCENT score must be in [0, 100]; got {self.value}")
        if self.unit == ScoreUnit.RATIO and not (0.0 <= self.value <= 1.0):
            raise ValueError(f"RATIO score must be in [0, 1]; got {self.value}")
        return self

    @property
    def normalized(self) -> float:
        return self.value / 100.0 if self.unit == ScoreUnit.PERCENT else self.value


__all__ = ["ScoreUnit", "ScoreValue"]
