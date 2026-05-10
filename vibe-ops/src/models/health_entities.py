from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import date

class DailyLog(BaseModel):
    date: date
    notes: str

class DailyConsolidation(BaseModel):
    date: date
    metrics: Dict[str, Any]

class WeeklyAggregate(BaseModel):
    week_id: str
    score: float
