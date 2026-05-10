from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

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
