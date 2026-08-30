"""OverrideRecord — SPEC D12 typed audit trail entry."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class OverrideRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    at: datetime
    by: str  # agent | human:<name>
    field_path: str  # dotted path
    previous_value: Any
    new_value: Any
    reason: str


__all__ = ["OverrideRecord"]
