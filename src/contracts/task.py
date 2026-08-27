"""Task, Project, and Deliverable contracts.

These are the PRIMARY planning entities used by the Deep Agent harness
to fill interfaces. They are canonical — imported by both operational/
entities/ and vibe-ops/models/.

Source of truth:
- tasks: IRA backlog, roadmap items, daily actions
- projects: revenue-bearing work, study projects
- deliverables: concrete outputs with definition-of-done
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from contracts.common import EntityType, Period, Priority, RegimeState, StrEnum, UEID


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


class Task(BaseModel):
    """A single actionable unit of work.

    This is the primary output of the Deep Agent — it transforms NL
    planning from vault/ into structured tasks that interfaces can
    display.

    A Task lives at a specific execution horizon (today/tomorrow/week/
    onda/sprint) and carries rich description context so interfaces
    don't have to re-resolve references.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(max_length=2000)] = ""
    """Rich description with context, references to parent project, and
    definition-of-done. May include wikilinks (resolvable by interfaces)."""

    entity_type: Literal["task"] = "task"

    horizon: Period
    """Execution horizon — determines which interface view shows this task."""

    priority: Priority = Priority.MEDIUM
    project_id: UEID | None = None
    """Parent project, if any."""

    depends_on: list[UEID] = Field(default_factory=list)
    """Task IDs that must complete before this one starts."""

    estimated_minutes: int | None = None
    """Pomodoro estimate. None = unscheduled."""

    done: bool = False
    """User marks this done in the interface."""

    done_at: datetime | None = None
    """When the user marked it done."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    def mark_done(self) -> Task:
        """Return a new Task with done=True and done_at=now."""
        return self.model_copy(
            update={"done": True, "done_at": datetime.utcnow()}
        )


# ---------------------------------------------------------------------------
# Subtask
# ---------------------------------------------------------------------------


class Subtask(BaseModel):
    """A sub-component of a Task."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    task_id: UEID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    done: bool = False
    done_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# ChecklistItem
# ---------------------------------------------------------------------------


class ChecklistItem(BaseModel):
    """A checklist line within a Task description."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    task_id: UEID
    label: Annotated[str, Field(min_length=1, max_length=300)]
    checked: bool = False
    checked_at: datetime | None = None


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Project(BaseModel):
    """A bounded piece of work with a goal and milestones."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(max_length=3000)] = ""

    entity_type: Literal["project"] = "project"

    status: ProjectStatus = ProjectStatus.ACTIVE

    # Revenue / mastery
    revenue_impact: Annotated[float, Field(ge=0.0)] = 0.0
    """Estimated monthly revenue impact (R$)."""

    xp_points: Annotated[int, Field(ge=0)] = 0
    """Story-points or XP for gamification."""

    mastery_level: Annotated[int, Field(ge=1, le=5)] = 1
    """1=beginner, 5=expert. Drives study_project linkage."""

    # Structural
    milestones: list[UEID] = Field(default_factory=list)
    deliverables: list[UEID] = Field(default_factory=list)

    # IKIGAi vectors (which of the 5 vectors this serves)
    ikigai_vector: str | None = None
    """One of: passion, skill, market, revenue, course."""

    # Vault reference
    vault_path: str | None = None
    """Path in vault/ to the canonical planning doc."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------


class Milestone(BaseModel):
    """A significant checkpoint within a Project."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    project_id: UEID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    target_date: date | None = None
    done: bool = False
    done_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Deliverable
# ---------------------------------------------------------------------------


class Deliverable(BaseModel):
    """A concrete output from a Project or Milestone.

    This is what the Deep Agent decomposes from NL planning —
    a specific artifact (document, code, dataset, report) with a
    definition-of-done.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    project_id: UEID
    milestone_id: UEID | None = None
    title: Annotated[str, Field(min_length=1, max_length=300)]
    description: Annotated[str, Field(max_length=2000)] = ""

    entity_type: Literal["deliverable"] = "deliverable"

    done: bool = False
    done_at: datetime | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
