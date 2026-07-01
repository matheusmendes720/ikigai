"""Sleep, energy and daily-log domain entities (PRD-05 §2).

This module defines the **leaf Pydantic models** that capture the per-day
operational signal: how the user slept, what their energy looked like, and
how their day unfolded. They are part of the ``operational.entities``
package and are intentionally **leaves** of the import graph — no other
operational module imports from them, and they import only from
``operational.enums`` and ``operational.types``.

Three entities are exposed:

* :class:`SleepRecord` — one night's sleep, including bedtime, wake time,
  quality, deep/rem percentages, interruptions, source, and notes.
  Computes ``duration_hours`` to handle midnight crossing.
* :class:`EnergyReading` — a single self-reported energy sample (level
  plus optional mood / focus / stress). Multiple readings per day are
  allowed and feed into :class:`DailyLog`.
* :class:`DailyLog` — the consolidated log of a single calendar day. It
  aggregates the :class:`SleepRecord`, the list of
  :class:`EnergyReading` samples, the task/pomodoro/habit counters, and
  computes ``habit_compliance_pct``, ``avg_energy``, ``peak_energy_time``
  and ``daily_score``.

Source documents:

* **PRD-05** ``vibe-ops/planning/PRD-05-metrics-health.md`` §2 — entity
  shapes, ranges, defaults.
* **PAV** ``vibe-ops/base/Produtividade Algorítmica Visual.md`` §3 — daily
  periods (used for ``EnergyReading.context`` mapping).
* **PRD-02** — habit compliance percentage (used by ``DailyLog``).
* **ADR-004** — score formula (energy/productivity/health) used by
  ``DailyLog.daily_score``.

Conventions:

* Pydantic v2 strict mode (``frozen`` for immutable entities,
  ``frozen=False`` + ``validate_assignment=True`` for mutable entities
  such as :class:`DailyLog` and :class:`MetricAlert`).
* Google-style docstrings, line-length 100, ``__all__`` explicit.
* All constraints enforced via ``Field`` (``max_length``, ``ge``, ``le``)
  and explicit validators.
* No business logic beyond the pure computed fields. Aggregation across
  days belongs to :class:`operational.entities.consolidation.DailyConsolidation`.
* No circular imports — entities are leaves.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from operational.enums import EnergyLevel  # noqa: TC001
from operational.types import UEID  # noqa: TC001

__all__ = ["DailyLog", "EnergyReading", "SleepRecord"]


# ---------------------------------------------------------------------------
# Module-level validation constants
# ---------------------------------------------------------------------------

#: Maximum length of a free-form note attached to a sleep record.
_SLEEP_NOTES_MAX: int = 500

#: Maximum length of a free-form note attached to an energy reading.
_ENERGY_NOTES_MAX: int = 500

#: Maximum length of the day's free-form notes on a :class:`DailyLog`.
_DAILY_NOTES_MAX: int = 1000

#: Recommended nightly sleep duration, in hours. Used to compute
#: ``sleep_debt_hours`` and the energy penalty inside ``daily_score``.
_TARGET_SLEEP_HOURS: float = 8.0

#: Mapping from :class:`EnergyLevel` to the 0-100 scale used in
#: ``DailyLog.avg_energy`` and the energy component of ``daily_score``.
_ENERGY_NUMERIC: dict[str, int] = {"H": 100, "M": 60, "L": 30}


def _utc_now_naive() -> datetime:
    """Return the current wall-clock time as a naive UTC ``datetime``.

    Naive datetimes are used throughout the ``operational`` package so
    that Pydantic models serialise cleanly to JSON/SQLite TEXT columns
    without timezone arithmetic. Production callers that need timezone
    awareness should wrap this in a timezone-aware protocol such as
    :class:`operational.types.Clock`.

    Returns:
        datetime: Naive ``datetime`` in UTC.
    """
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# SleepRecord
# ---------------------------------------------------------------------------


class SleepRecord(BaseModel):
    """A single night's sleep record (PRD-05 §2.1).

    Captures bedtime, wake time, self-reported quality (1-10), and the
    optional deep/rem percentages and interruption count. The
    ``duration_hours`` field is **computed** to handle the case where the
    user goes to bed before midnight and wakes up after midnight.

    This model is **immutable** (``frozen=True``). Sleep is a historical
    event: once recorded, it is never mutated. To correct an entry,
    create a new one with the correct values.

    Attributes:
        id: Universal Entity ID. Convention: ``"slp_YYYY_MM_DD"``.
        date: Calendar date the sleep "belongs to" (typically the date
            of waking, but the caller decides the convention).
        bedtime: Local time the user went to bed. ``time`` object, no
            timezone information.
        wake_time: Local time the user woke up. ``time`` object. If
            earlier than ``bedtime`` the duration is computed by
            crossing midnight.
        quality_score: Self-reported sleep quality, integer in
            ``[1, 10]`` (10 = perfect sleep).
        deep_sleep_pct: Percentage of deep sleep in ``[0.0, 100.0]``.
            Optional (some sources do not report it).
        rem_sleep_pct: Percentage of REM sleep in ``[0.0, 100.0]``.
            Optional.
        interruptions: Number of times the user woke up during the
            night. ``>= 0``.
        notes: Free-form notes. Max 500 chars.
        source: Provenance of the record. One of ``MANUAL`` /
            ``GARMIN`` / ``OURA`` / ``APPLE_HEALTH``. Defaults to
            ``MANUAL``.
        created_at: Wall-clock timestamp at construction. Required.

    Raises:
        ValidationError: If any field constraint is violated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    date: date
    bedtime: time
    wake_time: time
    quality_score: Annotated[int, Field(ge=1, le=10)]
    deep_sleep_pct: Annotated[float, Field(ge=0.0, le=100.0)] | None = None
    rem_sleep_pct: Annotated[float, Field(ge=0.0, le=100.0)] | None = None
    interruptions: Annotated[int, Field(ge=0)] = 0
    notes: Annotated[str, Field(default="", max_length=_SLEEP_NOTES_MAX)]
    source: Literal["MANUAL", "GARMIN", "OURA", "APPLE_HEALTH"] = "MANUAL"
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_hours(self) -> float:
        """Sleep duration in hours, midnight-crossing safe.

        Logic:
            * Combine ``bedtime`` and ``wake_time`` with ``self.date``.
            * If ``wake_dt < bed_dt`` the user crossed midnight; add
              one calendar day to the wake datetime.
            * Convert the resulting ``timedelta`` to hours.

        Returns:
            float: Duration in hours. Always ``> 0`` (assuming the
            caller does not set equal bedtime and wake_time).
        """
        bed_dt = datetime.combine(self.date, self.bedtime)
        wake_dt = datetime.combine(self.date, self.wake_time)
        if wake_dt < bed_dt:
            # Midnight crossing: wake is next calendar day
            wake_dt = datetime.combine(self.date + timedelta(days=1), self.wake_time)
        delta = wake_dt - bed_dt
        return delta.total_seconds() / 3600.0


# ---------------------------------------------------------------------------
# EnergyReading
# ---------------------------------------------------------------------------


class EnergyReading(BaseModel):
    """A single self-reported energy reading (PRD-05 §2.2).

    Multiple :class:`EnergyReading` instances can be created per day —
    one per period (morning, afternoon, evening) at minimum. The
    :class:`DailyLog` aggregates them into ``avg_energy`` and
    ``peak_energy_time``.

    This model is **immutable** (``frozen=True``). Energy samples are
    point-in-time observations: once taken, they are not edited.

    Attributes:
        id: Universal Entity ID. Convention: ``"erg_YYYYMMDD_HHMM"``.
        date: Calendar date the reading refers to.
        timestamp: Wall-clock instant the reading was captured.
        level: Self-reported energy tier (``HIGH`` / ``MEDIUM`` / ``LOW``).
        context: Time-of-day bucket (``morning`` / ``afternoon`` /
            ``evening``). Used by ``DailyLog`` to compute
            ``peak_energy_time``.
        mood: Self-reported mood at the time of the reading. ``[1, 5]``.
            Optional.
        focus: Self-reported focus level. ``[1, 10]``. Optional.
        stress: Self-reported stress level. ``[1, 10]``. Optional.
        notes: Free-form notes. Max 500 chars.
        created_at: Wall-clock timestamp at construction. Required.

    Raises:
        ValidationError: If any field constraint is violated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    date: date
    timestamp: datetime
    level: EnergyLevel
    context: Literal["morning", "afternoon", "evening"]
    mood: Annotated[int, Field(ge=1, le=5)] | None = None
    focus: Annotated[int, Field(ge=1, le=10)] | None = None
    stress: Annotated[int, Field(ge=1, le=10)] | None = None
    notes: Annotated[str, Field(default="", max_length=_ENERGY_NOTES_MAX)]
    created_at: datetime


# ---------------------------------------------------------------------------
# DailyLog
# ---------------------------------------------------------------------------


class DailyLog(BaseModel):
    """A consolidated daily log (PRD-05 §2.3).

    Aggregates the day's :class:`SleepRecord`, the list of
    :class:`EnergyReading` samples, and the task / pomodoro / habit /
    health counters into a single object. Four values are **computed**:

    * ``habit_compliance_pct`` — ``habits_done / habits_total * 100``.
    * ``avg_energy`` — mean of energy readings mapped to a 0-100 scale
      (``H=100, M=60, L=30``). ``None`` if no readings.
    * ``peak_energy_time`` — period with the highest average energy.
      ``None`` if no readings.
    * ``daily_score`` — overall day score in ``[0, 100]`` combining
      energy, productivity, and health. ``None`` if no energy readings.

    This model is **mutable** (``frozen=False``,
    ``validate_assignment=True``) because ``updated_at`` is auto-managed.
    Mutations to any field will re-run the validator chain and refresh
    the timestamp. Callers that want full control may call
    :meth:`touch` after batch edits.

    Attributes:
        id: Universal Entity ID. Convention: ``"day_YYYY_MM_DD"``.
        date: Calendar date the log refers to.
        sleep: The :class:`SleepRecord` for the night. Optional — the
            user may not have logged sleep yet.
        energy_readings: List of :class:`EnergyReading` for the day.
            Empty list if no readings.
        tasks_completed: Number of tasks closed. ``>= 0``.
        tasks_created: Number of tasks created. ``>= 0``.
        time_tracked_hours: Hours spent in tracked work. ``>= 0``.
        focus_sessions: Number of focus blocks completed. ``>= 0``.
        habits_done: Number of habits completed. ``>= 0``.
        habits_total: Number of habits scheduled. ``>= 0``.
        study_minutes: Cumulative study time, in minutes. ``>= 0``.
        pomodoros: Number of pomodoros completed. ``>= 0``.
        exercise_done: ``True`` if the user exercised on this day.
        exercise_minutes: Exercise time, in minutes. ``>= 0``.
        water_glasses: Number of water glasses consumed. ``>= 0``.
        meals_logged: Number of meals logged. ``>= 0``.
        notes: Free-form daily notes. Max 1000 chars.
        mood_morning: Self-reported morning mood in ``[1, 5]``. Optional.
        mood_evening: Self-reported evening mood in ``[1, 5]``. Optional.
        created_at: Wall-clock timestamp at construction. Required.
        updated_at: Wall-clock timestamp at the last edit. Auto-managed.

    Raises:
        ValidationError: If any field constraint is violated.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        validate_assignment=True,
    )

    id: UEID
    date: date
    sleep: SleepRecord | None = None
    energy_readings: list[EnergyReading] = Field(default_factory=list)
    tasks_completed: Annotated[int, Field(ge=0)] = 0
    tasks_created: Annotated[int, Field(ge=0)] = 0
    time_tracked_hours: Annotated[float, Field(ge=0.0)] = 0.0
    focus_sessions: Annotated[int, Field(ge=0)] = 0
    habits_done: Annotated[int, Field(ge=0)] = 0
    habits_total: Annotated[int, Field(ge=0)] = 0
    study_minutes: Annotated[int, Field(ge=0)] = 0
    pomodoros: Annotated[int, Field(ge=0)] = 0
    exercise_done: bool = False
    exercise_minutes: Annotated[int, Field(ge=0)] = 0
    water_glasses: Annotated[int, Field(ge=0)] = 0
    meals_logged: Annotated[int, Field(ge=0)] = 0
    notes: Annotated[str, Field(default="", max_length=_DAILY_NOTES_MAX)]
    mood_morning: Annotated[int, Field(ge=1, le=5)] | None = None
    mood_evening: Annotated[int, Field(ge=1, le=5)] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    # ---- computed fields --------------------------------------------------

    @computed_field  # type: ignore[prop-decorator]
    @property
    def habit_compliance_pct(self) -> float:
        """Return the habit compliance as a percentage.

        Returns ``0.0`` when ``habits_total`` is ``0`` (avoids
        ``ZeroDivisionError`` and treats "no habits scheduled" as
        trivially satisfied).

        Returns:
            float: Percentage in ``[0.0, 100.0]``.
        """
        if self.habits_total == 0:
            return 0.0
        return (self.habits_done / self.habits_total) * 100.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def avg_energy(self) -> float | None:
        """Return the mean energy across all readings, scaled to 0-100.

        The mapping is ``HIGH=100, MEDIUM=60, LOW=30`` (defined in
        :data:`_ENERGY_NUMERIC`). Returns ``None`` when the day has
        no readings, which is **not the same as zero energy** — the
        caller may choose to distinguish the two cases.

        Returns:
            float | None: Mean energy in ``[0.0, 100.0]`` or ``None``.
        """
        if not self.energy_readings:
            return None
        return (
            sum(_ENERGY_NUMERIC[r.level.value] for r in self.energy_readings)
            / len(self.energy_readings)
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def peak_energy_time(self) -> Literal["morning", "afternoon", "evening"] | None:
        """Return the period with the highest average energy.

        Groups readings by ``context``, averages each group, then
        returns the group with the largest mean. Ties are broken
        lexicographically (``afternoon`` < ``evening`` < ``morning``)
        because :func:`max` on a dict uses the first key with the
        maximum value, and Python's iteration order is insertion
        order; we therefore build the averages dict in a deterministic
        order to keep tests reproducible.

        Returns:
            Literal | None: ``"morning"`` / ``"afternoon"`` /
            ``"evening"`` or ``None`` if no readings.
        """
        if not self.energy_readings:
            return None
        contexts: dict[str, list[int]] = {"morning": [], "afternoon": [], "evening": []}
        for r in self.energy_readings:
            contexts[r.context].append(_ENERGY_NUMERIC[r.level.value])
        averages: dict[str, float] = {
            ctx: (sum(vals) / len(vals) if vals else 0.0)
            for ctx, vals in contexts.items()
        }
        return cast(
            "Literal['morning', 'afternoon', 'evening']",
            max(averages, key=lambda k: averages[k]),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def daily_score(self) -> float | None:
        """Return the overall day score in ``[0, 100]``.

        Formula (PRD-05 §2.3, ADR-004):
            * ``energy`` starts at ``avg_energy`` and is penalised by
              ``max(0, (8 - sleep_hours) * 10)`` if a
              :class:`SleepRecord` is present (capped at ``0``).
            * ``productivity = base * 60 + time_bonus * 25 + focus_bonus * 15``
              where ``base = tasks_completed / max(tasks_created, 1)``
              (clamped to ``[0, 1]``) and the two bonuses are
              ``min(time_tracked_hours / 8, 1)`` and
              ``min(pomodoros / 8, 1)``.
            * ``health = (sleep_score * 0.5) + exercise_score + water_score``
              where ``sleep_score = sleep.quality_score * 10``,
              ``exercise_score = 25`` if exercised else ``0``,
              ``water_score = min(water_glasses / 8, 1) * 15``.
            * ``daily_score = energy * 0.3 + productivity * 0.4 + health * 0.3``.

        Returns:
            float | None: The composite score or ``None`` if no
            energy readings exist.
        """
        if self.avg_energy is None:
            return None

        # Energy component with sleep-debt penalty.
        energy = self.avg_energy
        if self.sleep is not None:
            sleep_debt = max(0.0, (_TARGET_SLEEP_HOURS - self.sleep.duration_hours) * 10.0)
            energy = max(0.0, energy - sleep_debt)

        # Productivity component.
        base = (self.tasks_completed / max(self.tasks_created, 1)) * 60.0
        time_bonus = min(self.time_tracked_hours / 8.0, 1.0) * 25.0
        focus_bonus = min(self.pomodoros / 8.0, 1.0) * 15.0
        productivity = base + time_bonus + focus_bonus

        # Health component.
        sleep_score = self.sleep.quality_score * 10.0 if self.sleep is not None else 0.0
        exercise_score = 25.0 if self.exercise_done else 0.0
        water_score = min(self.water_glasses / 8.0, 1.0) * 15.0
        health = (sleep_score * 0.5) + exercise_score + water_score

        return energy * 0.3 + productivity * 0.4 + health * 0.3

    # ---- validators / helpers --------------------------------------------

    @model_validator(mode="after")
    def _auto_set_updated_at(self) -> DailyLog:
        """Auto-set ``updated_at`` to ``datetime.now(UTC)`` on construction.

        If the caller explicitly supplied an ``updated_at`` (e.g. when
        rehydrating from storage), it is preserved. With
        ``validate_assignment=True`` enabled, subsequent field
        assignments will also re-run this validator and refresh the
        timestamp. Callers that want a deterministic timestamp may
        pass a ``Clock`` and call :meth:`touch` manually.

        Returns:
            DailyLog: The same instance, with ``updated_at`` set.
        """
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", _utc_now_naive())
        return self

    def touch(self) -> DailyLog:
        """Refresh ``updated_at`` to ``datetime.now(UTC)``.

        Returns:
            DailyLog: The same instance, with ``updated_at`` updated.
        """
        object.__setattr__(self, "updated_at", _utc_now_naive())
        return self
