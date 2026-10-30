from typing import Any

from pydantic import BaseModel


class OperationalMode(BaseModel):
    mode: str
    constraints: dict[str, Any]


class PolicyRule(BaseModel):
    id: str
    condition: str
    action: str
