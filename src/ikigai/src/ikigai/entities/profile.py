"""IKIGAi profile — snapshot of all 5 vectors + zones + alignment."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from ikigai.enums import AlignmentLabel, VectorType
from ikigai.types import ScoreValue, UEID


class ProfileSnapshot(BaseModel):
    """Single-point measurement of all 5 vectors + alignment."""

    model_config = ConfigDict(frozen=False)

    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 5 vector scores (0-100)
    passion: ScoreValue = Field(default_factory=lambda: ScoreValue(value=50.0, unit="percent"))
    skill: ScoreValue = Field(default_factory=lambda: ScoreValue(value=50.0, unit="percent"))
    market: ScoreValue = Field(default_factory=lambda: ScoreValue(value=50.0, unit="percent"))
    revenue: ScoreValue = Field(default_factory=lambda: ScoreValue(value=50.0, unit="percent"))
    course: ScoreValue = Field(default_factory=lambda: ScoreValue(value=50.0, unit="percent"))

    # Zones (intersection scores, 0-100)
    vocacao_score: ScoreValue = Field(default_factory=lambda: ScoreValue(value=0.0, unit="percent"))  # passion ∩ skill
    missao_score: ScoreValue = Field(default_factory=lambda: ScoreValue(value=0.0, unit="percent"))  # passion ∩ market
    profissao_score: ScoreValue = Field(default_factory=lambda: ScoreValue(value=0.0, unit="percent"))  # skill ∩ market ∩ revenue
    negocio_score: ScoreValue = Field(default_factory=lambda: ScoreValue(value=0.0, unit="percent"))  # market ∩ revenue

    # Aggregate
    ikigai_score: ScoreValue = Field(default_factory=lambda: ScoreValue(value=50.0, unit="percent"))  # meta-vetor
    alignment_label: AlignmentLabel = AlignmentLabel.CONVERGING

    # Diagnostics
    weakest_vector: VectorType | None = None
    biggest_opportunity: str = ""
    alerts: list[str] = Field(default_factory=list)


class IKIGAiProfile(BaseModel):
    """Full IKIGAi profile: identity + snapshot history."""

    model_config = ConfigDict(extra="allow")

    ueid: UEID
    name: str = "default"
    snapshots: list[ProfileSnapshot] = Field(default_factory=list)

    @property
    def latest(self) -> ProfileSnapshot | None:
        """Return the most recent snapshot."""
        if not self.snapshots:
            return None
        return max(self.snapshots, key=lambda s: s.date)

    def add_snapshot(self, snapshot: ProfileSnapshot) -> None:
        """Append a snapshot."""
        self.snapshots.append(snapshot)


__all__ = ["ProfileSnapshot", "IKIGAiProfile"]
