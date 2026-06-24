"""IKIGAi vector entity — one of 5 vectors with score history."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from ikigai.enums import VectorType
from ikigai.types import ScoreValue, UEID


class VectorTrend(str, Enum):
    """Trend direction of a vector."""

    UP = "up"
    STABLE = "stable"
    DOWN = "down"


class VectorScorePoint(BaseModel):
    """Single score measurement in time."""

    model_config = ConfigDict(frozen=True)

    date: datetime
    score: ScoreValue
    evidence: str = ""  # what justifies this score


class IKIGAiVectorEntity(BaseModel):
    """One of 5 IKIGAi vectors (passion/skill/market/revenue/course).

    Supports fractal sub-vectors via `vector_type` like 'skill.python' — the
    canonical name (VectorType enum value) is the prefix.
    """

    model_config = ConfigDict(extra="allow")

    # Identity
    ueid: UEID
    vector_type: VectorType
    name: str
    description: str = ""

    # Scores (0-100)
    current_score: ScoreValue = Field(default_factory=lambda: ScoreValue(value=50.0, unit="percent"))
    target_score: ScoreValue = Field(default_factory=lambda: ScoreValue(value=80.0, unit="percent"))
    score_history: list[VectorScorePoint] = Field(default_factory=list)

    # Substrate
    activities: list[str] = Field(default_factory=list)
    projects: list[UEID] = Field(default_factory=list)
    habits: list[UEID] = Field(default_factory=list)

    # Metadata
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trend: VectorTrend = VectorTrend.STABLE
    weight: float = Field(default=0.2, ge=0.0, le=1.5)

    @property
    def is_subvector(self) -> bool:
        """True if this is a sub-vector (e.g., 'skill.python')."""
        return "." in self.vector_type.value or self.vector_type.value not in {
            v.value for v in VectorType
        }

    def add_score(self, score: ScoreValue, evidence: str = "") -> None:
        """Append a new score point and update current_score."""
        point = VectorScorePoint(date=datetime.now(timezone.utc), score=score, evidence=evidence)
        self.score_history.append(point)
        self.current_score = score
        self.last_updated = point.date

    def gap_to_target(self) -> float:
        """Difference between target and current (positive = below target)."""
        return self.target_score.value - self.current_score.value


__all__ = ["VectorTrend", "VectorScorePoint", "IKIGAiVectorEntity"]
