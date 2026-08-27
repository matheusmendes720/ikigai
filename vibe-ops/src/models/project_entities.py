import datetime as _dt
from datetime import date, datetime
from typing import Literal, List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


def _today() -> date:
    return _dt.date.today()


class RoadmapItem(BaseModel):
    id: str = Field(pattern=r'^rdm_[a-z0-9_]+$')
    goal_id: str = Field(pattern=r'^G\d+$')
    title: str = Field(min_length=3, max_length=200)
    storypoints: int = Field(ge=1, default=1)
    status: Literal["planned", "in_progress", "completed"] = "planned"


class BacklogTask(BaseModel):
    id: str = Field(pattern=r'^back_[a-z0-9_]+$')
    roadmap_item_id: str
    description: str
    tasks: List[Dict[str, Any]] = Field(default_factory=list)  # List of atomics tasks


class ChangelogEntry(BaseModel):
    id: str = Field(pattern=r'^chg_[a-z0-9_]+$')
    task_uuid_fk: str
    date: _dt.date = Field(default_factory=_today)
    code_metrics: Dict[str, Any] = Field(default_factory=dict)
    test_results: Dict[str, Any] = Field(default_factory=dict)
    learning_outcomes: List[Dict[str, Any]] = Field(default_factory=list)


class Project(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(pattern=r'^proj_[a-z0-9_]+$')
    title: str = Field(min_length=5, max_length=200)
    status: Literal["backlog", "planning", "active", "paused", "completed", "archived"] = "backlog"
    revenue_impact: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"] = "MEDIUM"

    xp_points: int = 0
    mastery_level: Literal["beginner", "intermediate", "advanced", "expert"] = "beginner"
    subject: Optional[str] = None
    learning_phase: Optional[Literal["metalearning", "direct_practice", "retrieval", "iteration"]] = None
    tech_stack: List[str] = Field(default_factory=list)
    milestone: Optional[date] = None
    deliverable: Optional[str] = None
    commercial_goal: Optional[str] = None
    vault_path: Optional[str] = None
    last_synced_at: Optional[datetime] = None

class Skill(BaseModel):
    id: str = Field(pattern=r'^skill_[a-z0-9_]+$')
    name: str = Field(min_length=3, max_length=100)
    current_level: Literal["beginner", "intermediate", "advanced", "expert"] = "beginner"
    target_level: Literal["beginner", "intermediate", "advanced", "expert"] = "intermediate"
