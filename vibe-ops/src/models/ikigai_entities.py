from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal

class IKIGAiProfile(BaseModel):
    passion: float
    skill: float
    market: float
    revenue: float

class SkillNode(BaseModel):
    id: str
    name: str
    level: int

class OpportunitySignal(BaseModel):
    id: str
    description: str
    vector: str
