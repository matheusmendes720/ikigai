"""FractalRegime — SPEC D13 4-level fractal regime.

Levels (top-down): global → cluster → vector → sub_vector.
Each level carries its own hysteresis_days per SPEC §8.3 + I10.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FractalRegimeState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["global", "cluster", "vector", "sub_vector"]
    regime: str  # push | maintain | reduce | recover
    days_in_regime: int = Field(ge=0)
    is_hysteresis_active: bool
    hysteresis_days: int = Field(ge=0)


class FractalRegime(BaseModel):
    model_config = ConfigDict(extra="forbid")

    levels: list[FractalRegimeState]  # exactly 4 entries — FR-01


__all__ = ["FractalRegime", "FractalRegimeState"]
