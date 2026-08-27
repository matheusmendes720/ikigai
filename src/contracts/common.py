"""Common primitives shared across all layers.

Types here are imported by every other contracts module. They have
no domain-specific logic — they are the vocabulary of identity and time.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PlainValidator

# ---------------------------------------------------------------------------
# UEID — Universal Entity Identifier
# ---------------------------------------------------------------------------

_UEID_PATTERN = re.compile(r"^[a-z][a-z0-9]{2,30}_[a-z0-9_]+$")
"""Canonical UEID regex: <prefix>_<slug> with 3-31 total chars."""


def _validate_ueid(value: str) -> str:
    if not _UEID_PATTERN.match(value):
        raise ValueError(
            f"Invalid UEID '{value}'. Must match { _UEID_PATTERN.pattern!r}. "
            "Format: <prefix>_<slug>, 3-31 chars, lowercase."
        )
    return value


UEID = Annotated[str, PlainValidator(_validate_ueid)]
"""Universal Entity Identifier — canonical str type for all entity IDs.

Format: ``<prefix>_<slug>`` where prefix identifies the entity type
(e.g. ``hab``, ``task``, ``proj``, ``wave``, ``cyc``) and slug is a
kebab-case descriptor.

Examples:
    - ``hab_sleep_8h``
    - ``task_byd_market_research``
    - ``proj_vaga_remota_2026``
    - ``wave_W01_Aug_2026``
    - ``cyc_q3_2026``

Canonical prefixes:
    ===============  =========================================
    Prefix            Entity
    ===============  =========================================
    ``hab``           Habit
    ``hst``           HabitState (habit_<id>_<date>)
    ``qhe``           QHEMetrics (qhe_<date>)
    ``task``          Task
    ``sub``           Subtask
    ``chk``           ChecklistItem
    ``proj``          Project
    ``msl``           Milestone
    ``del``           Deliverable
    ``cyc``           PlanningCycle
    ``wave``          Wave (W<num>_<Mon>_<YYYY>)
    ``sprint``        Sprint
    ``slp``           SleepRecord
    ``erg``           EnergyReading
    ``day``           DailyLog
    ``cnl``           DailyConsolidation
    ``wkl``           WeeklyAggregate
    ``pol``           PolicyDecision
    ``rec``           DecisionRecord
    ``set``           PolicySetpoints
    ``blk``           TimeBlock
    ``pmo``           PomodoroConfig
    ``pmor``          PomodoroRound
    ``pms``           PomodoroSession
    ``ind``           AutoIndagacao
    ``aju``           AjusteFino
    ``port``          PortfolioArtifact
    ``ctx``           DayContext
    ``ref``           DailyReflection
    ``lun``           LunchRecord
    ===============  =========================================
"""

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Period(StrEnum):
    """Time horizon of a planning or execution unit."""

    TODAY = "today"
    TOMORROW = "tomorrow"
    THIS_WEEK = "this_week"
    NEXT_WEEK = "next_week"
    THIS_MONTH = "this_month"
    NEXT_MONTH = "next_month"
    THIS_QUARTER = "this_quarter"
    NEXT_QUARTER = "next_quarter"
    THIS_YEAR = "this_year"
    ONDA = "onda"  # 15-day cycle
    SPRINT = "sprint"  # 4-week cycle


class Priority(StrEnum):
    """Urgency/importance axis for task ranking."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EntityType(StrEnum):
    """Discriminator for poly-morphic entity lookups."""

    # Planning
    TASK = "task"
    SUBTASK = "subtask"
    CHECKLIST_ITEM = "checklist_item"
    PROJECT = "project"
    MILESTONE = "milestone"
    DELIVERABLE = "deliverable"
    PLANNING_CYCLE = "planning_cycle"
    WAVE = "wave"
    SPRINT = "sprint"
    # Operational
    HABIT = "habit"
    HABIT_STATE = "habit_state"
    QHE_METRICS = "qhe_metrics"
    SLEEP_RECORD = "sleep_record"
    ENERGY_READING = "energy_reading"
    DAILY_LOG = "daily_log"
    DAILY_CONSOLIDATION = "daily_consolidation"
    WEEKLY_AGGREGATE = "weekly_aggregate"
    POMODORO_CONFIG = "pomodoro_config"
    POMODORO_ROUND = "pomodoro_round"
    POMODORO_SESSION = "pomodoro_session"
    POLICY_DECISION = "policy_decision"
    POLICY_SETPOINTS = "policy_setpoints"
    DECISION_RECORD = "decision_record"
    TIME_BLOCK = "time_block"
    JOURNAL_ENTRY = "journal_entry"
    # Strategic
    DREAM = "dream"
    STUDY_PROJECT = "study_project"
    STUDY_TOPIC = "study_topic"
    STUDY_SESSION = "study_session"
    STUDY_MATERIAL = "study_material"
    ROADMAP_ITEM = "roadmap_item"
    BACKLOG_TASK = "backlog_task"
    PERIOD_REPORT = "period_report"


class RegimeState(StrEnum):
    """Operational regime of the policy FSM."""

    PUSH = "PUSH"
    MAINTAIN = "MAINTAIN"
    REDUCE = "REDUCE"
    RECOVER = "RECOVER"


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    """Return current UTC datetime (naive, for SQLite/JSON compatibility)."""
    from datetime import UTC
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin(BaseModel):
    """Mixin that adds created_at / updated_at to any entity."""

    model_config = {"extra": "forbid"}

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime | None = None
