"""Skill node — specific skill within the SKILL vector."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from ikigai.types import ScoreValue, UEID


class SkillLevel(str, Enum):
    """Skill proficiency level."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillCategory(str, Enum):
    """Skill category for grouping."""

    PROGRAMMING = "programming"
    DATA = "data"
    CLOUD = "cloud"
    DEVOPS = "devops"
    SOFT_SKILL = "soft_skill"
    DOMAIN = "domain"
    TOOL = "tool"
    OTHER = "other"


class SkillNode(BaseModel):
    """A specific skill within the SKILL vector (fractal sub-vector)."""

    model_config = ConfigDict(extra="allow")

    ueid: UEID
    name: str
    category: SkillCategory = SkillCategory.OTHER
    level: SkillLevel = SkillLevel.BEGINNER
    level_score: ScoreValue = Field(default_factory=lambda: ScoreValue(value=10.0, unit="percent"))
    market_demand: ScoreValue = Field(default_factory=lambda: ScoreValue(value=50.0, unit="percent"))
    learning_hours: float = 0.0
    last_practiced: date | None = None
    prerequisites: list[UEID] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects_using: list[UEID] = Field(default_factory=list)
    vector_contribution: float = 0.0  # weight in SKILL vector (0-1)

    # Tracking
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def promote_to(self, new_level: SkillLevel) -> None:
        """Promote skill to a new level."""
        if new_level == self.level:
            return
        level_scores = {
            SkillLevel.BEGINNER: 25.0,
            SkillLevel.INTERMEDIATE: 50.0,
            SkillLevel.ADVANCED: 75.0,
            SkillLevel.EXPERT: 95.0,
        }
        self.level = new_level
        self.level_score = ScoreValue(value=level_scores[new_level], unit="percent")
        self.last_updated = datetime.now(timezone.utc)


__all__ = ["SkillNode", "SkillLevel", "SkillCategory"]
