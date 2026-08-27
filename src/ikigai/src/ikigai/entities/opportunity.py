"""Opportunity signal — market opportunity within MARKET vector."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from ikigai.enums import VectorType
from ikigai.types import ScoreValue, UEID


class OpportunityStatus(str, Enum):
    """Lifecycle of an opportunity."""

    DETECTED = "detected"  # just noticed
    EVALUATING = "evaluating"  # under analysis
    PURSUING = "pursuing"  # actively working on
    WON = "won"  # closed-won
    LOST = "lost"  # closed-lost


class OpportunitySignal(BaseModel):
    """Market opportunity (job, freelance, partnership, product)."""

    model_config = ConfigDict(extra="allow")

    ueid: UEID
    title: str
    source: str  # LinkedIn, Upwork, Direct, Network, etc.
    signal_type: str  # JOB | FREELANCE | PARTNERSHIP | PRODUCT

    required_skills: list[str] = Field(default_factory=list)
    estimated_revenue_brl: float | None = None
    estimated_hours: float | None = None
    deadline: date | None = None

    fit_score: ScoreValue = Field(default_factory=lambda: ScoreValue(value=0.5, unit="ratio"))  # 0-1
    status: OpportunityStatus = OpportunityStatus.DETECTED

    ikigai_alignment: dict[VectorType, float] = Field(default_factory=dict)  # vector → alignment (0-1)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str | None = None


__all__ = ["OpportunitySignal", "OpportunityStatus"]
