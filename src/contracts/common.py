"""Common primitives shared across all layers.

Types here are imported by every other contracts module. They have
no domain-specific logic — they are the vocabulary of identity and time.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum as StrEnum

from pydantic import BaseModel, Field

__all__ = [
    "UEID",
    "Period",
    "Priority",
    "EntityType",
    "RegimeState",
    "StrEnum",
    "TimestampMixin",
]

# ---------------------------------------------------------------------------
# UEID — Universal Entity Identifier
# ---------------------------------------------------------------------------


from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

_UEID_PATTERN = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")
"""UEID regex: 4-part format type:slug:uuid:hash.

Canonical 5-part format (`<namespace>:<entity_type>:<slug>:<uuid_short>:
<content_hash_short>`) lives at `src/ikigai/src/ikigai/types.py:UEID` per
`ueid-5part-canonical-decision-2026-08-31`. This 4-part regex is the
legacy alias — accepted for vault reads only, never written. Phase 1 of
zazzy-plotting-flask.md unifies the canonical; until that ships, this
regex remains the contract surface for legacy adapters.
"""


class UEID(str):
    """Universal Entity Identifier — canonical str type for all entity IDs.

    Format: ``<type>:<slug>:<uuid>:<hash>`` where:
    - type: 2-5 lowercase letters (e.g. ``tsk``, ``proj``, ``hab``)
    - slug: lowercase alphanumeric with dashes (e.g. ``byd-case-review``)
    - uuid: lowercase hex with dashes (e.g. ``abc12345-1234-5678-9abc-def012345678``)
    - hash: lowercase hex (e.g. ``0123456789abcdef``)

    Examples:
        - ``tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef``
        - ``hab:sleep-8h:11111111-2222-3333-4444-555555555555:ffffffffffffffff``
        - ``proj:vaga-remota-2026:00000000-0000-0000-0000-000000000000:0000000000000000``

    Canonical types:
        ===============  =========================================
        Type             Entity
        ===============  =========================================
        ``tsk``          Task
        ``sub``           Subtask
        ``chk``           ChecklistItem
        ``proj``          Project
        ``msl``           Milestone
        ``del``           Deliverable
        ``hab``           Habit
        ``hst``           HabitState
        ``qhe``           QHEMetrics
        ``cyc``           PlanningCycle
        ``wave``          Wave
        ``sprint``        Sprint
        ===============  =========================================
    """

    def __new__(cls, value: str) -> "UEID":
        if not _UEID_PATTERN.match(value):
            raise ValueError(
                f"Invalid UEID '{value}'. Must match {_UEID_PATTERN.pattern!r}. "
                "Format: type:slug:uuid:hash (all lowercase, 4 parts separated by colons)."
            )
        return super().__new__(cls, value)

    @classmethod
    def from_legacy(cls, value: str) -> "UEID":
        """Parse either a canonical 4-part UEID or a legacy 2-part underscore ID.

        Canonical 4-part format (e.g. ``tsk:foo:00000000-...:0000000000...``) is
        passed directly to the constructor.

        Legacy 2-part underscore format (e.g. ``tsk_morning_water``) is converted
        to canonical 4-part by mapping the prefix to ``type`` and the suffix to
        ``slug`` (underscores in the suffix become dashes). UUID and hash are
        zero-filled placeholders.

        Raises:
            ValueError: if the value matches neither format.

        Examples:
            >>> UEID.from_legacy("tsk:foo:00000000-0000-0000-0000-000000000000:0000000000000000")
            UEID('tsk:foo:00000000-0000-0000-0000-000000000000:0000000000000000')
            >>> UEID.from_legacy("tsk_morning_water")
            UEID('tsk:morning-water:00000000-0000-0000-0000-000000000000:0000000000000000')
        """
        # Fast path: canonical 4-part colon format
        if _UEID_PATTERN.match(value):
            return cls(value)

        # Legacy 2-part underscore format: type_slug
        LEGACY_PATTERN = re.compile(r"^[a-z]{2,5}_[a-z0-9][a-z0-9_-]*$")
        if LEGACY_PATTERN.match(value):
            type_part, slug_part = value.split("_", 1)
            canonical = (
                f"{type_part}:"
                f"{slug_part.replace('_', '-')}:"
                f"00000000-0000-0000-0000-000000000000:"
                f"0000000000000000"
            )
            return cls(canonical)

        raise ValueError(
            f"Invalid UEID '{value}'. Must match either:\n"
            f"  Canonical (4-part): {_UEID_PATTERN.pattern!r}\n"
            f"  Legacy (2-part underscore): ^[a-z]{{2,5}}_[a-z0-9][a-z0-9_-]*$"
        )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """Tell Pydantic how to handle UEID in model fields."""
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
        )


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
