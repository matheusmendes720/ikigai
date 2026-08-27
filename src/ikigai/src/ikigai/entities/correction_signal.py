"""CorrectionSignal — typed IKIGAi cycle output."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ikigai.entities.ueid import UEID


class CorrectionSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heuristic: str
    signal_type: Literal[
        "drift", "overload", "underload", "recover",
        "kill", "abandon", "pivot", "falsify",
    ]
    description: str
    target_ueid: Optional[UEID] = None
    urgency: Literal["low", "medium", "high", "critical"]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


__all__ = ["CorrectionSignal"]
