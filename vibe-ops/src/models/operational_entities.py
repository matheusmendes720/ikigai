from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal

class OperationalMode(BaseModel):
    mode: str
    constraints: Dict[str, Any]

class PolicyRule(BaseModel):
    id: str
    condition: str
    action: str
