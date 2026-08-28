"""Planning cycle contracts — Wave, Sprint, PlanningCycle, VaultEvent.

These represent the TEMPORAL planning hierarchy used by the Deep Agent
to propagate tasks across horizons.

Source:
- strategics/Hierarquia de Objetivos.md
- strategics/Planejamento (Estratégico e Tático).md
- vault/ikigai/closing-2026/ structure
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import EntityType, Period, Priority, StrEnum, UEID


# ---------------------------------------------------------------------------
# Wave
# ---------------------------------------------------------------------------

_WAVE_ID_PATTERN = re.compile(r"^W\d+_[A-Za-z]{3}_\d{4}$")


def _validate_wave_id(v: str) -> str:
    if not _WAVE_ID_PATTERN.match(v):
        raise ValueError(f"Invalid Wave ID {v!r}. Expected e.g. W01_Aug_2026.")
    return v


WaveId = Annotated[str, Field(min_length=8, max_length=15)]


class WaveStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Wave(BaseModel):
    """A 15-day execution cycle within a PlanningCycle.

    A Wave is the quantum of execution planning — short enough to
    allow pivoting, long enough to produce meaningful deliverables.
    Each Wave belongs to exactly one PlanningCycle and has a fixed
    15-day window.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: WaveId
    wave_number: Annotated[int, Field(ge=1)]
    title: Annotated[str, Field(min_length=1, max_length=200)]

    entity_type: Literal["wave"] = "wave"

    parent_cycle_id: str  # e.g. cyc_q3_2026
    parent_objective_id: str | None = None  # e.g. obj_primeira_vaga

    start_date: date
    duration_days: Annotated[int, Field(ge=1, le=90)] = 15
    end_date: date

    status: WaveStatus = WaveStatus.PLANNED

    # Completion/intake
    c_comp: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    """Completion percentage (0-1)."""

    ic: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    """Intake/quality score (0-1)."""

    tags: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Sprint
# ---------------------------------------------------------------------------

_SPRINT_ID_PATTERN = re.compile(r"^SP\d+_[A-Za-z]{3}_\d{4}$")


class SprintStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    REVIEW = "review"
    COMPLETED = "completed"


class Sprint(BaseModel):
    """A 4-week execution sprint within a PlanningCycle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[str, Field(pattern=_SPRINT_ID_PATTERN.pattern)]
    sprint_number: Annotated[int, Field(ge=1)]
    title: Annotated[str, Field(min_length=1, max_length=200)]

    entity_type: Literal["sprint"] = "sprint"

    parent_cycle_id: str
    start_date: date
    end_date: date

    status: SprintStatus = SprintStatus.PLANNED

    c_comp: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    ic: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# PlanningCycle
# ---------------------------------------------------------------------------

_CYCLE_ID_PATTERN = re.compile(r"^C\d+_[A-Za-z]{3}_\d{4}$")


class PlanningCycleStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class PlanningCycle(BaseModel):
    """A quarterly planning cycle (Q1-Q4) — the top of the temporal hierarchy.

    A PlanningCycle contains 6 Waves (each 15 days) and represents
    one fiscal quarter. It maps to the closing-2026 structure:
    vault/ikigai/closing-2026/01-q3-2026/, etc.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[str, Field(pattern=_CYCLE_ID_PATTERN.pattern)]
    cycle_number: Annotated[int, Field(ge=1)]
    title: Annotated[str, Field(min_length=1, max_length=200)]

    entity_type: Literal["planning_cycle"] = "planning_cycle"

    # Hierarchy
    parent_phase_id: str | None = None
    parent_objective_id: str | None = None

    start_date: date
    end_date: date

    status: PlanningCycleStatus = PlanningCycleStatus.DRAFT

    # Waves (referenced by ID)
    waves: list[WaveId] = Field(default_factory=list)

    # IKIGAi alignment
    aligned_half_quarter: Annotated[int, Field(ge=1, le=2)] | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# VaultEvent — planned vs actual tracking
# ---------------------------------------------------------------------------

_EventVerb = Literal[
    "created",
    "updated",
    "done",
    "blocked",
    "unblocked",
    "archived",
]


class VaultEvent(BaseModel):
    """A timestamped event on a vault entity — used for planned vs actual tracking.

    The Deep Agent writes VaultEvents when it processes the vault.
    Interfaces write VaultEvents when the user acts on a task.
    The Deep Agent reads VaultEvents to compute burndown, execution rate,
    and to detect gaps between planned and actual.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    entity_type: EntityType
    entity_id: str  # the UEID of the entity this event is about

    verb: _EventVerb
    """The action that happened."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Source of the event
    source: Literal["deep_agent", "interface", "manual", "vault_sync"]
    """Who/what generated this event."""

    # Context
    details: Annotated[str, Field(max_length=500)] = ""
    """Human-readable details, e.g. 'moved from ONDA 2 to ONDA 3'."""

    # For planning fidelity tracking
    planned_date: date | None = None
    """The date this was scheduled to happen (from vault planning)."""

    actual_date: date | None = None
    """The date this actually happened (from interface or vault_sync)."""

    @property
    def is_late(self) -> bool:
        if self.planned_date is None or self.actual_date is None:
            return False
        return self.actual_date > self.planned_date
