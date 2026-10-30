from datetime import date
from typing import Any

from pydantic import BaseModel


class DailyLog(BaseModel):
    date: date
    notes: str


class DailyConsolidation(BaseModel):
    date: date
    metrics: dict[str, Any]


class WeeklyAggregate(BaseModel):
    week_id: str
    score: float
