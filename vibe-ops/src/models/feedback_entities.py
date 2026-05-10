from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import date, datetime

class PriorityMatrix(BaseModel):
    id: str = Field(pattern=r'^pm_[a-z0-9_]+$')
    date: date
    candidates: List[Dict[str, Any]] = Field(default_factory=list)

class CyberneticFeedback(BaseModel):
    id: str = Field(pattern=r'^cf_[a-z0-9_]+$')
    timestamp: datetime
    target: Dict[str, Any]
    sensor: Dict[str, Any]
    adjuster: Dict[str, Any]
