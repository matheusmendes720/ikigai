"""Pydantic v2 frozen models for solverforge-calendar tools.

Per spec §10 (decisions): all cross-process types use Pydantic v2 strict
(frozen=True, extra="forbid"). UEID imported from src/contracts.common.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Re-export UEID from canonical contracts location
from src.contracts.common import UEID


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SfScheduleInput(_Base):
    """Input for sf_schedule — add or update a scheduled event."""
    ueid: UEID
    title: str = Field(..., max_length=200)
    start_at: datetime
    end_at: datetime | None = None
    rrule: str | None = None  # RFC 5545
    blocked_by: list[UEID] = []
    tags: list[str] = []
    ikigai: dict[str, Any] = {}


class SfScheduleOutput(_Base):
    ueid: UEID
    id: str  # fork-internal PK (uuid4 hex)
    status: Literal["scheduled", "conflict", "blocked"]
    scheduled_at: datetime
    conflicts: list[UEID] = []
    warnings: list[str] = []


class SfReplanInput(_Base):
    horizon_start: datetime
    horizon_end: datetime  # max 14 days from horizon_start
    affected_ueids: list[UEID] = []
    strategy: Literal["minimize_moves", "earliest_first", "load_balance"] = "minimize_moves"
    hard_constraints: list[str] = []


class SfPlanDiff(_Base):
    ueid: UEID
    action: Literal["moved", "kept", "removed"]
    before: datetime | None
    after: datetime | None
    reason: str


class SfReplanOutput(_Base):
    plan_id: UUID
    horizon_start: datetime
    horizon_end: datetime
    diff: list[SfPlanDiff]
    unresolvable: list[UEID] = []
    runtime_ms: int


class SfAvailabilityInput(_Base):
    window_start: datetime
    window_end: datetime  # max 14 days
    min_slot_minutes: int = 30  # min 15; max 480
    exclude_ueids: list[UEID] = []


class SfTimeSlot(_Base):
    start: datetime
    end: datetime


class SfAvailabilityOutput(_Base):
    window_start: datetime
    window_end: datetime
    free_slots: list[SfTimeSlot]
    busy_intervals: list[SfTimeSlot]
