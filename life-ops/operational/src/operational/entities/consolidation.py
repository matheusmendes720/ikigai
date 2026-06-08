"""Daily consolidation, weekly aggregate and alert entities (PRD-05 §2).

This module defines the **leaf Pydantic models** that aggregate the
per-day signal into composite scores and roll up the trailing seven
days into a weekly summary. They are part of the
``operational.entities`` package and are intentionally **leaves** of the
import graph — no other operational module imports from them, and they
import only from ``operational.enums``, ``operational.types`` and
``operational.entities.metric`` (which is also a leaf).

Three entities are exposed:

* :class:`MetricAlert` — a discrete alert about a single metric
  (level, message, value, threshold, resolved flag).
* :class:`DailyConsolidation` — the day's composite scores
  (``energy_score``, ``productivity_score``, ``health_score`` and the
  derived ``overall_score``), the ``sleep_debt_hours``, the rolling
  7-day trends, the auto-generated ``alerts`` and ``recommendations``.
* :class:`WeeklyAggregate` — the rollup of up to seven
  :class:`DailyConsolidation` references, with averages, totals, the
  ``best_streak_habit`` and the derived ``week_label``.

Source documents:

* **PRD-05** ``vibe-ops/planning/PRD-05-metrics-health.md`` §2 — entity
  shapes, ranges, defaults, score formulas, alert thresholds.
* **ADR-004** — composite-score weighting (0.3/0.4/0.3).
* **PRD-06** — relation between daily scores and the policy state
  machine (downstream consumer, not modelled here).

Conventions:

* Pydantic v2 strict mode (``frozen`` for immutable entities,
  ``frozen=False`` + ``validate_assignment=True`` for mutable entities
  such as :class:`MetricAlert`).
* Google-style docstrings, line-length 100, ``__all__`` explicit.
* All constraints enforced via ``Field`` (``max_length``, ``ge``, ``le``)
  and explicit validators.
* No business logic beyond the pure computed fields. Alert / trend
  *generation* belongs to the consolidation service layer; this module
  only carries the resulting structured records.
* No circular imports — entities are leaves.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from operational.enums import AlertLevel, WeekLabel
from operational.types import UEID  # noqa: TC001

__all__ = ["DailyConsolidation", "MetricAlert", "WeeklyAggregate"]


# ---------------------------------------------------------------------------
# Module-level validation constants
# ---------------------------------------------------------------------------

#: Number of days in a weekly aggregate. Used by the week-span validator.
_WEEK_SPAN_DAYS: int = 6

#: Maximum number of days that can appear in a :class:`WeeklyAggregate`.
#: Equal to one calendar week.
_WEEK_MAX_DAYS: int = 7

#: Maximum length of a single recommendation string.
_RECOMMENDATION_MAX: int = 200

#: Maximum length of a metric alert message.
_ALERT_MESSAGE_MAX: int = 500

#: Maximum length of a metric name on an alert (matches the column width
#: in PRD-05 §5).
_ALERT_METRIC_MAX: int = 100

#: Recommended nightly sleep duration, in hours. Used to compute
#: ``sleep_debt_hours``.
_TARGET_SLEEP_HOURS: float = 8.0

#: Lower bound of the :class:`WeekLabel` ``EXCELENTE`` bucket (PRD-05 §2.6).
_WL_EXCELENTE_MIN: float = 85.0

#: Lower bound of the :class:`WeekLabel` ``BOM`` bucket (PRD-05 §2.6).
_WL_BOM_MIN: float = 70.0

#: Lower bound of the :class:`WeekLabel` ``MEDIO`` bucket (PRD-05 §2.6).
_WL_MEDIO_MIN: float = 50.0

#: Lower bound of the :class:`WeekLabel` ``RUIM`` bucket (PRD-05 §2.6).
_WL_RUIM_MIN: float = 30.0


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
# MetricAlert
# ---------------------------------------------------------------------------


class MetricAlert(BaseModel):
    """A single metric alert (PRD-05 §2.4).

    Captures a discrete alert raised by the consolidation service when
    a metric crosses one of the thresholds defined in PRD-05 §5. The
    ``resolved`` flag is mutable so that the user — or an automated
    remediation script — can mark the alert as acted upon; setting
    ``resolved=True`` for the first time auto-stamps ``resolved_at`` to
    the current wall-clock time.

    This model is **mutable** (``frozen=False``,
    ``validate_assignment=True``) so that ``resolved`` / ``resolved_at``
    can be updated. All other fields are immutable.

    Attributes:
        id: Universal Entity ID. Convention: ``"alt_YYYYMMDD_NNN"``.
        level: Severity tier (``INFO`` / ``WARNING`` / ``CRITICAL``).
        metric: Metric name (e.g. ``"sleep_debt_hours"``,
            ``"habit_compliance_pct"``). Max 100 chars.
        message: Human-readable description. Max 500 chars.
        value: Current value of the metric at the time of the alert.
        threshold: Threshold that was crossed.
        created_at: Wall-clock timestamp at construction. Required.
        resolved: Whether the alert has been acted upon. ``False`` by
            default.
        resolved_at: Wall-clock timestamp of resolution. Auto-set when
            ``resolved`` is flipped from ``False`` to ``True``.

    Raises:
        ValidationError: If any field constraint is violated.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        validate_assignment=True,
    )

    id: UEID
    level: AlertLevel
    metric: Annotated[str, Field(min_length=1, max_length=_ALERT_METRIC_MAX)]
    message: Annotated[str, Field(min_length=1, max_length=_ALERT_MESSAGE_MAX)]
    value: float
    threshold: float
    created_at: datetime
    resolved: bool = False
    resolved_at: datetime | None = None

    @model_validator(mode="after")
    def _auto_stamp_resolved_at(self) -> MetricAlert:
        """Auto-stamp ``resolved_at`` the first time ``resolved`` flips to ``True``.

        Behaviour:
            * If ``resolved=True`` and ``resolved_at`` is ``None`` →
              set ``resolved_at`` to ``datetime.now(UTC)``.
            * If ``resolved=False`` → leave ``resolved_at`` as is
              (do not silently clear it; an audit trail of "this alert
              was once resolved" may be useful).
            * If both ``resolved`` and ``resolved_at`` are already set
              (e.g. rehydrated from storage) → leave them alone.

        Returns:
            MetricAlert: The same instance, with ``resolved_at``
            possibly updated.
        """
        if self.resolved and self.resolved_at is None:
            object.__setattr__(self, "resolved_at", _utc_now_naive())
        return self

    def resolve(self) -> MetricAlert:
        """Mark the alert as resolved and stamp ``resolved_at``.

        Idempotent: calling :meth:`resolve` on an already-resolved
        alert is a no-op (the original timestamp is preserved).

        Returns:
            MetricAlert: The same instance, with ``resolved=True`` and
            ``resolved_at`` populated.
        """
        if not self.resolved:
            object.__setattr__(self, "resolved", True)
            object.__setattr__(self, "resolved_at", _utc_now_naive())
        return self


# ---------------------------------------------------------------------------
# DailyConsolidation
# ---------------------------------------------------------------------------


class DailyConsolidation(BaseModel):
    """A daily consolidation of metrics (PRD-05 §2.5).

    A :class:`DailyConsolidation` is the **immutable record** of what
    the consolidation service computed for a given day. It carries the
    three input scores (``energy_score``, ``productivity_score``,
    ``health_score``), the derived ``overall_score`` (weighted average
    with weights 0.3 / 0.4 / 0.3), the ``sleep_debt_hours``, the
    rolling 7-day trends, the auto-generated ``alerts`` and
    ``recommendations``, and a reference back to the parent
    :class:`operational.entities.metric.DailyLog`.

    This model is **immutable** (``frozen=True``). A consolidation
    captures a snapshot in time; if the underlying :class:`DailyLog`
    changes, a *new* :class:`DailyConsolidation` is produced.

    Attributes:
        id: Universal Entity ID. Convention: ``"cnl_YYYYMMDD"``.
        date: Calendar date the consolidation refers to.
        daily_log_id: :data:`UEID` of the source
            :class:`operational.entities.metric.DailyLog`.
        energy_score: Energy composite in ``[0.0, 100.0]``.
        productivity_score: Productivity composite in ``[0.0, 100.0]``.
        health_score: Health composite in ``[0.0, 100.0]``.
        sleep_debt_hours: Cumulative sleep debt, ``max(0, 8 - h)``.
        productivity_trend: Productivity score minus the trailing
            7-day mean. ``None`` if the rolling window is incomplete.
        energy_trend: Energy score minus the trailing 7-day mean.
            ``None`` if the rolling window is incomplete.
        alerts: Auto-generated alerts from threshold checks. Empty
            by default.
        recommendations: Auto-generated recommendations. Empty by
            default. Each entry max 200 chars.
        created_at: Wall-clock timestamp at construction. Required.

    Raises:
        ValidationError: If any field constraint is violated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    date: date
    daily_log_id: UEID
    energy_score: Annotated[float, Field(ge=0.0, le=100.0)]
    productivity_score: Annotated[float, Field(ge=0.0, le=100.0)]
    health_score: Annotated[float, Field(ge=0.0, le=100.0)]
    sleep_debt_hours: Annotated[float, Field(ge=0.0)] = 0.0
    productivity_trend: float | None = None
    energy_trend: float | None = None
    alerts: list[MetricAlert] = Field(default_factory=list)
    recommendations: list[Annotated[str, Field(max_length=_RECOMMENDATION_MAX)]] = Field(
        default_factory=list,
    )
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def overall_score(self) -> float:
        """Return the weighted average of the three component scores.

        Formula (PRD-05 §2.5):
            ``overall = 0.3 * energy + 0.4 * productivity + 0.3 * health``

        Returns:
            float: The overall day score in ``[0.0, 100.0]``.
        """
        return (
            self.energy_score * 0.3
            + self.productivity_score * 0.4
            + self.health_score * 0.3
        )

    @staticmethod
    def compute_sleep_debt(sleep_hours: float | None) -> float:
        """Return the sleep debt in hours for a given sleep duration.

        Args:
            sleep_hours: Hours slept, or ``None`` if no sleep was
                recorded. ``None`` is treated as the worst case
                (full target deficit).

        Returns:
            float: Sleep debt in hours, ``>= 0``. ``8.0`` when
            ``sleep_hours`` is ``None``.
        """
        if sleep_hours is None:
            return _TARGET_SLEEP_HOURS
        return max(0.0, _TARGET_SLEEP_HOURS - sleep_hours)


# ---------------------------------------------------------------------------
# WeeklyAggregate
# ---------------------------------------------------------------------------


class WeeklyAggregate(BaseModel):
    """A weekly aggregation of metrics (PRD-05 §2.6).

    A :class:`WeeklyAggregate` is the immutable rollup of up to seven
    :class:`DailyConsolidation` references, with averages, totals and
    a derived :class:`WeekLabel` based on the overall ``week_score``.

    This model is **immutable** (``frozen=True``). A weekly rollup
    captures a snapshot; if the underlying days change, a *new*
    :class:`WeeklyAggregate` is produced.

    Attributes:
        id: Universal Entity ID. Convention: ``"wkl_YYYYMMDD"`` where
            the date is the Monday of the week.
        week_start: Monday of the week (inclusive).
        week_end: Sunday of the week (inclusive). Must be exactly
            6 days after ``week_start`` (enforced by validator).
        days: :data:`UEID` references to the seven
            :class:`DailyConsolidation` records for this week. May
            contain fewer than 7 entries for incomplete weeks.
        avg_sleep_hours: Mean sleep duration across the week. ``>= 0``.
        avg_sleep_quality: Mean sleep quality score in ``[1.0, 10.0]``.
        avg_energy_score: Mean energy score in ``[0.0, 100.0]``.
        avg_productivity: Mean productivity score in ``[0.0, 100.0]``.
        total_tasks_done: Sum of tasks completed during the week.
        total_study_minutes: Sum of study minutes for the week.
        total_exercise_days: Number of days with exercise. ``[0, 7]``.
        habit_compliance_avg: Mean habit compliance percentage in
            ``[0.0, 100.0]``.
        best_streak_habit: Name of the habit with the longest streak
            in the week. Optional (only set if the user tracks
            streaks).
        week_score: Overall week score in ``[0.0, 100.0]``. Drives
            :attr:`week_label`.
        created_at: Wall-clock timestamp at construction. Required.

    Raises:
        ValidationError: If any field constraint is violated, or if
            ``week_end`` is not exactly 6 days after ``week_start``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    week_start: date  # Monday
    week_end: date  # Sunday
    days: list[UEID] = Field(default_factory=list)
    avg_sleep_hours: Annotated[float, Field(ge=0.0)] = 0.0
    avg_sleep_quality: Annotated[float, Field(ge=1.0, le=10.0)] = 5.0
    avg_energy_score: Annotated[float, Field(ge=0.0, le=100.0)] = 0.0
    avg_productivity: Annotated[float, Field(ge=0.0, le=100.0)] = 0.0
    total_tasks_done: Annotated[int, Field(ge=0)] = 0
    total_study_minutes: Annotated[int, Field(ge=0)] = 0
    total_exercise_days: Annotated[int, Field(ge=0, le=_WEEK_MAX_DAYS)] = 0
    habit_compliance_avg: Annotated[float, Field(ge=0.0, le=100.0)] = 0.0
    best_streak_habit: Annotated[str, Field(max_length=100)] | None = None
    week_score: Annotated[float, Field(ge=0.0, le=100.0)] = 0.0
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def week_label(self) -> WeekLabel:
        """Return the :class:`WeekLabel` derived from :attr:`week_score`.

        Buckets (PRD-05 §2.6):
            * ``>= 85`` → ``EXCELENTE``
            * ``>= 70`` → ``BOM``
            * ``>= 50`` → ``MEDIO``
            * ``>= 30`` → ``RUIM``
            * ``<  30`` → ``RECUPERACAO``

        Returns:
            WeekLabel: The matching bucket.
        """
        if self.week_score >= _WL_EXCELENTE_MIN:
            return WeekLabel.EXCELENTE
        if self.week_score >= _WL_BOM_MIN:
            return WeekLabel.BOM
        if self.week_score >= _WL_MEDIO_MIN:
            return WeekLabel.MEDIO
        if self.week_score >= _WL_RUIM_MIN:
            return WeekLabel.RUIM
        return WeekLabel.RECUPERACAO

    @model_validator(mode="after")
    def _validate_week_span(self) -> WeeklyAggregate:
        """Ensure ``week_end`` is exactly 6 days after ``week_start``.

        Returns:
            WeeklyAggregate: The same instance, validated.

        Raises:
            ValueError: If the day-span is not exactly 6.
        """
        span = (self.week_end - self.week_start).days
        if span != _WEEK_SPAN_DAYS:
            msg = (
                f"week_end - week_start must be exactly {_WEEK_SPAN_DAYS} days "
                f"(one calendar week), got {span} days "
                f"(start={self.week_start.isoformat()}, "
                f"end={self.week_end.isoformat()})"
            )
            raise ValueError(msg)
        return self
