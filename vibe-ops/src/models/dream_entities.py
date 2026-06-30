"""Dream entity.

Source: .omo/plans/vault-bidirectional-sync.md (T6 / Dream entity)
Strategic framework: docs/chat-Framework de Planejamento Estrategico.txt

A Dream is a long-horizon outcome (5+ years) tied to FalsifiableHypothesis
rows via dream_id. The dream carries no IKB/ID semantics — it's the
anchor for hypothesis evaluation.
"""
from __future__ import annotations

import datetime as _dt
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return _dt.datetime.now(_dt.timezone.utc)


class Dream(BaseModel):
    """Long-horizon outcome anchor — 5+ year ambition."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(pattern=r'^dr_[a-z0-9_]+$')
    title: str = Field(min_length=3, max_length=200)
    ikigai_vector: Optional[str] = Field(
        None,
        description="Which IKIGAi vector drives this dream (passion/skill/market/revenue)",
    )
    horizon_years: int = Field(ge=1, le=20, default=5)
    falsification_criteria: Optional[str] = Field(
        None,
        description="What observation would prove this dream unreachable",
    )
    leading_indicators: List[str] = Field(default_factory=list)
    lagging_indicators: List[str] = Field(default_factory=list)
    milestones: List[str] = Field(
        default_factory=list,
        description="Year-by-year milestone list, e.g. ['Y1: <goal>', 'Y3: <goal>']",
    )
    status: str = Field(
        default="active",
        description="active | paused | abandoned | achieved",
    )
    vault_path: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    last_synced_at: Optional[datetime] = None