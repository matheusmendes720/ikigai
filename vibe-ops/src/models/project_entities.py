import datetime as _dt
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def _today() -> date:
    return _dt.date.today()


class RoadmapItem(BaseModel):
    id: str = Field(pattern=r"^rdm_[a-z0-9_]+$")
    goal_id: str = Field(pattern=r"^G\d+$")
    title: str = Field(min_length=3, max_length=200)
    storypoints: int = Field(ge=1, default=1)
    status: Literal["planned", "in_progress", "completed"] = "planned"


class BacklogTask(BaseModel):
    id: str = Field(pattern=r"^back_[a-z0-9_]+$")
    roadmap_item_id: str
    description: str
    tasks: list[dict[str, Any]] = Field(default_factory=list)  # List of atomics tasks


class ChangelogEntry(BaseModel):
    id: str = Field(pattern=r"^chg_[a-z0-9_]+$")
    task_uuid_fk: str
    date: _dt.date = Field(default_factory=_today)
    code_metrics: dict[str, Any] = Field(default_factory=dict)
    test_results: dict[str, Any] = Field(default_factory=dict)
    learning_outcomes: list[dict[str, Any]] = Field(default_factory=list)


class Project(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(pattern=r"^proj_[a-z0-9_]+$")
    title: str = Field(min_length=5, max_length=200)
    status: Literal["backlog", "planning", "active", "paused", "completed", "archived"] = "backlog"
    revenue_impact: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"] = "MEDIUM"

    xp_points: int = 0
    mastery_level: Literal["beginner", "intermediate", "advanced", "expert"] = "beginner"
    subject: str | None = None
    learning_phase: Literal["metalearning", "direct_practice", "retrieval", "iteration"] | None = (
        None
    )
    tech_stack: list[str] = Field(default_factory=list)
    milestone: date | None = None
    deliverable: str | None = None
    commercial_goal: str | None = None
    vault_path: str | None = None
    last_synced_at: datetime | None = None


class Skill(BaseModel):
    id: str = Field(pattern=r"^skill_[a-z0-9_]+$")
    name: str = Field(min_length=3, max_length=100)
    current_level: Literal["beginner", "intermediate", "advanced", "expert"] = "beginner"
    target_level: Literal["beginner", "intermediate", "advanced", "expert"] = "intermediate"
