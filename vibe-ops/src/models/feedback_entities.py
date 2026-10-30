from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class PriorityMatrix(BaseModel):
    id: str = Field(pattern=r"^pm_[a-z0-9_]+$")
    date: date
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class CyberneticFeedback(BaseModel):
    id: str = Field(pattern=r"^cf_[a-z0-9_]+$")
    timestamp: datetime
    target: dict[str, Any]
    sensor: dict[str, Any]
    adjuster: dict[str, Any]
