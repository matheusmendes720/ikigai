"""Routine, Ritual and Transition entities (PAV §3, §5).

This module declares the **time-bounded daily building blocks** of the PAV
operational system. Three closely related entities live here:

* :class:`Routine` — a task assigned to a :class:`Period` (PAV §3). Each
  routine has a start/end time on a single day and a list of weekdays on
  which it is active.
* :class:`Ritual` — a short transitional action (PAV §3 — "rituais de
  transição"). Rituals are usually 1-15 minutes long and can optionally
  trigger a :class:`Routine` (e.g. hydration ritual triggers the morning
  routine).
* :class:`Transition` — a marker between two :class:`Period` values (PAV
  §5). Transitions carry a list of ritual UEIDs that fire during the
  transition window.

All three entities are **immutable Pydantic v2 models** with strict
configuration (``frozen=True``, ``extra="forbid"``) so that any cross-
entity invariant is enforced at construction time. They are intentionally
**leaves** of the package: imports are restricted to :mod:`operational.enums`,
:mod:`operational.types` and :mod:`operational.constants` — no entity
imports another entity, no I/O is performed.

Source of truth:

* **PAV §3** — three daily periods and the routines/rituals that compose them.
* **PAV §5** — period transitions and the rituals fired at each boundary.
* **PRD-01** — entity contract for the operational database schema.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from operational.constants import DEFAULT
from operational.enums import Period, RitualType, RoutineType
from operational.types import UEID  # noqa: TC001  (used as Pydantic field type at runtime)

__all__ = ["VALID_WEEKDAYS", "Ritual", "Routine", "RoutineLog", "Transition", "Weekday"]


# ``__all__`` is alphabetical above; ruff RUF022 may flag — explicit
# alphabetical ordering is intentional and matches the rest of the package.


# ---------------------------------------------------------------------------
# Module-level invariants
# ---------------------------------------------------------------------------

_VALID_WEEKDAYS: frozenset[int] = frozenset({0, 1, 2, 3, 4, 5, 6})
"""Canonical weekday set under Python's ``date.weekday()`` convention.

``0`` is **Monday**, ``6`` is **Sunday**. The set is exposed as
:data:`VALID_WEEKDAYS` for downstream validators and test fixtures.

Note:
    The historical ordering preserved here matches
    :class:`datetime.date.weekday`. PAV does not specify a weekday
    numbering — this is the lowest-friction convention for Python code
    and is documented in the routine-level docstring.
"""

VALID_WEEKDAYS: frozenset[int] = _VALID_WEEKDAYS
"""Public re-export of :data:`_VALID_WEEKDAYS` for downstream consumers."""

Weekday = Annotated[int, Field(ge=0, le=6)]
"""A single weekday integer in the range ``[0, 6]`` (Mon=0 ... Sun=6).

Used as the element type of :attr:`Routine.days_of_week`.
"""


# ---------------------------------------------------------------------------
# Routine
# ---------------------------------------------------------------------------


class Routine(BaseModel):
    """A daily routine task (PAV §3).

    A :class:`Routine` is a **time-bounded task** within a :class:`Period`.
    It carries a start and end wall-clock time (assumed to occur on the
    same day — crossing midnight is forbidden by the validator) and a set
    of weekdays on which the routine is active.

    Examples (PAV §3)::

        Routine(
            id="rou_morning_wake",
            name="Acordar 3-5am",
            period=Period.MANHA,
            routine_type=RoutineType.ENTRY,
            start_time=time(3, 0),
            end_time=time(5, 0),
            created_at=datetime(2026, 6, 7, 0, 0),
        )

    Attributes:
        id: :data:`UEID` (e.g. ``"rou_morning_wake"``).
        name: Human-readable name, 1-100 characters, whitespace stripped.
        period: :class:`Period` (MANHA / TARDE / NOITE).
        routine_type: :class:`RoutineType` (ENTRY / CORE / TRANSITION / EXIT).
        start_time: Local start time on the day of the routine.
        end_time: Local end time on the day of the routine. Must be
            strictly greater than ``start_time`` (no overnight crossing).
        description: Free-form description, 0-500 characters.
        mandatory: Whether the routine is required (defaults to ``True``).
        days_of_week: Set of weekday integers (0=Mon ... 6=Sun) on which
            the routine is scheduled. Defaults to all seven days.
        created_at: Wall-clock timestamp of construction.
        archived: ``True`` if the routine has been soft-deleted.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    name: Annotated[str, Field(min_length=1, max_length=100)]
    period: Period
    routine_type: RoutineType
    start_time: time
    end_time: time
    description: Annotated[str, Field(default="", max_length=500)]
    mandatory: bool = True
    days_of_week: set[Weekday] = Field(
        default_factory=lambda: {0, 1, 2, 3, 4, 5, 6},
    )
    created_at: datetime
    archived: bool = False

    @field_validator("days_of_week")
    @classmethod
    def _validate_days_of_week(cls, value: set[int]) -> set[int]:
        """Ensure every element of ``days_of_week`` lies in ``[0, 6]``.

        Args:
            value: Candidate weekday set from Pydantic.

        Returns:
            The validated set, unchanged.

        Raises:
            ValueError: If any element is outside ``[0, 6]``.
        """
        if not isinstance(value, frozenset) and not isinstance(value, set):
            return value
        invalid: set[int] = {d for d in value if d not in _VALID_WEEKDAYS}
        if invalid:
            msg = (
                f"days_of_week must be a subset of {sorted(_VALID_WEEKDAYS)}, "
                f"got invalid entries: {sorted(invalid)}"
            )
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_times(self) -> Routine:
        """Verify ``end_time`` is strictly greater than ``start_time``.

        Returns:
            The model instance (unchanged on success).

        Raises:
            ValueError: If ``end_time <= start_time`` (same-day only).
        """
        if self.end_time <= self.start_time:
            msg = (
                f"end_time ({self.end_time.isoformat()}) must be strictly "
                f"after start_time ({self.start_time.isoformat()})"
            )
            raise ValueError(msg)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_minutes(self) -> int:
        """Routine duration in whole minutes (computed).

        Computed as ``end_time - start_time`` projected onto a single
        calendar day. Overnight routines are rejected by the validator
        above, so the result is always strictly positive.

        Returns:
            Duration in whole minutes (rounded toward zero).
        """
        anchor: date = date(2000, 1, 1)
        delta = datetime.combine(anchor, self.end_time) - datetime.combine(
            anchor, self.start_time,
        )
        return int(delta.total_seconds() // 60)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def active_on_weekend(self) -> bool:
        """Whether the routine runs on Saturday and/or Sunday.

        Returns:
            ``True`` if ``5 in days_of_week`` (Saturday) or
            ``6 in days_of_week`` (Sunday).
        """
        return bool(self.days_of_week & {5, 6})


# ---------------------------------------------------------------------------
# Ritual
# ---------------------------------------------------------------------------


class Ritual(BaseModel):
    """A ritual action (PAV §3 — "rituais de transição").

    Rituals are short actions performed at transitions between periods or
    at the start/end of routines. Examples (PAV §3): "Hidratação",
    "Meditação matinal", "Shutdown ritual", "Review metas".

    Attributes:
        id: :data:`UEID` (e.g. ``"rit_hydration_am"``).
        name: Human-readable name, 1-100 characters.
        ritual_type: :class:`RitualType` (HYDRATION / MEDITATION / ...).
        duration_minutes: Expected duration in minutes. Clamped to
            ``[1, 60]`` by the validator — rituals are short by design.
        triggers_routine_id: Optional :data:`UEID` of a :class:`Routine`
            that this ritual triggers (e.g. the morning hydration ritual
            triggers the morning routine).
        created_at: Wall-clock timestamp of construction.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    name: Annotated[str, Field(min_length=1, max_length=100)]
    ritual_type: RitualType
    duration_minutes: Annotated[int, Field(ge=1, le=60)]
    triggers_routine_id: UEID | None = None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def default_period(self) -> Period | None:
        """The period this ritual naturally belongs to (PAV §3).

        Returns:
            The :class:`Period` declared by :attr:`RitualType.default_period`,
            or ``None`` if the ritual can occur in any period.
        """
        return self.ritual_type.default_period

    @computed_field  # type: ignore[prop-decorator]
    @property
    def triggers_routine(self) -> bool:
        """Whether this ritual triggers a downstream routine.

        Returns:
            ``True`` when :attr:`triggers_routine_id` is set.
        """
        return self.triggers_routine_id is not None


# ---------------------------------------------------------------------------
# Transition
# ---------------------------------------------------------------------------


class Transition(BaseModel):
    """A transition marker between two periods (PAV §5).

    Transitions sit on the boundary between two :class:`Period` values and
    carry the set of :class:`Ritual` UEIDs that fire during the transition
    window (e.g. the manhã→tarde transition runs the "Hidratação pós-foco"
    ritual).

    Attributes:
        id: :data:`UEID` (e.g. ``"trn_manha_tarde"``).
        name: Human-readable name, 1-100 characters.
        from_period: Source :class:`Period`.
        to_period: Destination :class:`Period`. Must differ from
            ``from_period`` (validated).
        rituals: List of :data:`UEID` values referencing
            :class:`Ritual` entities. May be empty.
        duration_minutes: Length of the transition window in minutes.
            Clamped to ``[0, 120]`` — transitions are short.
        created_at: Wall-clock timestamp of construction.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    name: Annotated[str, Field(min_length=1, max_length=100)]
    from_period: Period
    to_period: Period
    rituals: list[UEID] = Field(default_factory=list)
    duration_minutes: Annotated[int, Field(ge=0, le=120)]
    created_at: datetime

    @model_validator(mode="after")
    def _validate_periods(self) -> Transition:
        """Ensure ``from_period`` and ``to_period`` differ.

        Returns:
            The model instance (unchanged on success).

        Raises:
            ValueError: If both periods are equal.
        """
        if self.from_period == self.to_period:
            msg = (
                f"from_period and to_period must differ; both are "
                f"{self.from_period.value!r}"
            )
            raise ValueError(msg)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_ritual_heavy(self) -> bool:
        """Whether this transition carries more than one ritual.

        Returns:
            ``True`` when :attr:`rituals` has strictly more than one
            element. Used by the daily handler to flag "rich" transitions
            that deserve extra attention.
        """
        return len(self.rituals) > 1


# ---------------------------------------------------------------------------
# RoutineLog
# ---------------------------------------------------------------------------


class RoutineLog(BaseModel):
    """A natural-language log of a single routine execution (PAV §3, §10).

    Captures the *what* and *how* of a routine run, separate from the
    :class:`TimeBlock` which captures only the gross entry/exit times.

    Use cases (per the PAV, the user wants both numerical and NL
    records, both between blocks and for entry/exit routines):

    * **Entry routine** (e.g. "Acordar" at 4h):
      "Acordei bem, 7h de sono, energia 9/10, prontíssimo para focar."
    * **Exit routine** (e.g. "Preparar refeições" at 19h):
      "Comi uma salada rápida e preparei 2 marmitas para amanhã."
    * **Core routine** (e.g. "Pomodoro S1"):
      "4 rounds de foco no projeto X, completei 3 tasks críticos."

    Each log is anchored to:

    * a specific :class:`Routine` (via ``routine_id``)
    * optionally a specific :class:`TimeBlock` (via ``block_id``)
    * a specific date
    * a specific period (denormalized for query speed)

    Attributes:
        id: :data:`UEID` (e.g. ``"rlog_manha_2026_06_07_acordar"``).
        routine_id: Reference to the :class:`Routine` that this log describes.
        block_id: Optional reference to the :class:`TimeBlock` that contains
            this routine execution.
        date: The date the routine was performed.
        period: The :class:`Period` in which the routine was performed
            (denormalized for fast querying).
        routine_type: The :class:`RoutineType` (denormalized for filtering).
        text: The natural-language log of the routine execution.
        energia_nivel: Optional energy level (1-10) recorded during this routine.
        foco_nivel: Optional focus level (1-10) recorded during this routine.
        humor: Optional mood (1-5) recorded during this routine.
        created_at: Wall-clock timestamp of construction.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    routine_id: UEID
    block_id: UEID | None = None
    date: date
    period: Period
    routine_type: RoutineType
    text: Annotated[str, Field(min_length=1, max_length=2000)]
    energia_nivel: Annotated[int, Field(ge=1, le=10)] | None = None
    foco_nivel: Annotated[int, Field(ge=1, le=10)] | None = None
    humor: Annotated[int, Field(ge=1, le=5)] | None = None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_entry_routine(self) -> bool:
        """Whether this log is for an ENTRY-type routine."""
        return self.routine_type == RoutineType.ENTRY

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_exit_routine(self) -> bool:
        """Whether this log is for an EXIT-type routine."""
        return self.routine_type == RoutineType.EXIT


# ---------------------------------------------------------------------------
# Module-level invariants
# ---------------------------------------------------------------------------


# Reference DEFAULT to silence linters; the dataclass is part of the public
# surface (re-exported via operational.__init__) and we want any breakage of
# the constant to be caught at import time.
_ = DEFAULT
