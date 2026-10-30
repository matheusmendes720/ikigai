from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ReviewEvent(BaseModel):
    id: str
    event_type: str
    timestamp: datetime


class PolicyDecision(BaseModel):
    id: str
    regime: Literal["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]
    reason: str


class DecisionRecord(BaseModel):
    id: str
    timestamp: datetime
    decision: PolicyDecision


class TimeBlock(BaseModel):
    id: str
    label: str
    duration_minutes: int
