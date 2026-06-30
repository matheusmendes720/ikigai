"""FalsifiableHypothesis entity (T6).

Source: .omo/plans/vault-bidirectional-sync.md (T6 / B5.1)
Strategic framework: docs/chat-Framework de Planejamento Estrategico.txt

A FalsifiableHypothesis encodes a testable claim tied to a Dream, with
explicit evidence threshold, leading/lagging indicators, and refactor
triggers. The engine evaluates these via HypothesisEvaluator (T7) and
emits verdicts back to the vault as dream frontmatter.
"""
from __future__ import annotations

import datetime as _dt
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return _dt.datetime.now(_dt.timezone.utc)


HypothesisStatus = Literal[
    "active",
    "validated",
    "falsified",
    "pivoted",
    "abandoned",
]

HypothesisVerdict = Literal[
    "validated",
    "falsified",
    "pivoted",
    "no_change",
]


class FalsifiableHypothesis(BaseModel):
    """A testable claim tied to a Dream with explicit falsification criteria."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(pattern=r'^fh_[a-z0-9_]+$')
    dream_id: str = Field(pattern=r'^dr_[a-z0-9_]+$')
    hypothesis_text: str = Field(min_length=10, max_length=1000)
    evidence_threshold: str = Field(
        min_length=5,
        description="What observation would prove this hypothesis false",
    )
    measurement_window_days: int = Field(ge=1, le=3650, default=90)
    leading_indicators: List[str] = Field(
        default_factory=list,
        description="Axis 2: behaviors we control",
    )
    lagging_indicators: List[str] = Field(
        default_factory=list,
        description="Axis 2: outcome metrics we observe",
    )
    refactor_triggers: List[str] = Field(
        default_factory=list,
        description="Axis 3: env changes that would force a pivot",
    )
    kill_switch_date: Optional[date] = None
    status: HypothesisStatus = "active"
    last_evaluated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    vault_path: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class HypothesisEvaluation(BaseModel):
    """A single evaluation event for a FalsifiableHypothesis."""
    model_config = ConfigDict(extra="allow")

    hypothesis_id: str = Field(pattern=r'^fh_[a-z0-9_]+$')
    evaluated_at: datetime = Field(default_factory=_utcnow)
    verdict: HypothesisVerdict
    score: float = Field(ge=0.0, le=1.0)
    notes: str = ""
    leading_met: int = 0
    lagging_met: int = 0
    leading_total: int = 0
    lagging_total: int = 0