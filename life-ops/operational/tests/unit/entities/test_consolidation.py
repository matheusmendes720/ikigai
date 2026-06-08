"""Comprehensive unit tests for ``operational.entities.consolidation``.

Covers:

* :class:`MetricAlert` — creation, ``AlertLevel`` enum, mutable
  ``resolved``/``resolved_at`` flag, auto-stamp on resolve,
  idempotent resolve, immutability of other fields.
* :class:`DailyConsolidation` — creation, the weighted-average
  ``overall_score`` formula, default empty lists, ``compute_sleep_debt``
  static helper, immutability, ``extra='forbid'``.
* :class:`WeeklyAggregate` — creation, all five :class:`WeekLabel`
  buckets (parametric), week-span validator, ``total_exercise_days``
  cap, immutability.

All tests are pure unit tests (no I/O). Markers: implicit ``unit``.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import ClassVar

import pytest
from pydantic import ValidationError

from operational.entities.consolidation import (
    DailyConsolidation,
    MetricAlert,
    WeeklyAggregate,
)
from operational.enums import AlertLevel, WeekLabel


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


_DT: ClassVar[datetime] = datetime(2026, 6, 7, 8, 0)
_DATE: ClassVar[date] = date(2026, 6, 7)


def _make_alert(  # noqa: PLR0913
    *,
    level: AlertLevel = AlertLevel.WARNING,
    metric: str = "sleep_debt_hours",
    message: str = "Sleep debt too high",
    value: float = 3.0,
    threshold: float = 2.0,
    alert_id: str = "alt_test",
    resolved: bool = False,
    resolved_at: datetime | None = None,
) -> MetricAlert:
    """Build a :class:`MetricAlert` with sensible defaults."""
    return MetricAlert(
        id=alert_id,
        level=level,
        metric=metric,
        message=message,
        value=value,
        threshold=threshold,
        created_at=_DT,
        resolved=resolved,
        resolved_at=resolved_at,
    )


def _make_consolidation(  # noqa: PLR0913
    *,
    energy: float = 80.0,
    productivity: float = 70.0,
    health: float = 90.0,
    sleep_debt: float = 0.0,
    consolidation_id: str = "cnl_test",
    daily_log_id: str = "day_test",
) -> DailyConsolidation:
    """Build a :class:`DailyConsolidation` with sensible defaults."""
    return DailyConsolidation(
        id=consolidation_id,
        date=_DATE,
        daily_log_id=daily_log_id,
        energy_score=energy,
        productivity_score=productivity,
        health_score=health,
        sleep_debt_hours=sleep_debt,
        created_at=_DT,
    )


# ---------------------------------------------------------------------------
# DailyConsolidation
# ---------------------------------------------------------------------------


class TestDailyConsolidation:
    """Specific tests for :class:`DailyConsolidation`."""

    def test_create_daily_consolidation(self) -> None:
        """All defaults and required fields are honoured."""
        c = _make_consolidation()
        assert c.id == "cnl_test"
        assert c.date == _DATE
        assert c.daily_log_id == "day_test"
        assert c.energy_score == 80.0
        assert c.productivity_score == 70.0
        assert c.health_score == 90.0
        assert c.sleep_debt_hours == 0.0
        assert c.productivity_trend is None
        assert c.energy_trend is None
        assert c.alerts == []
        assert c.recommendations == []
        assert c.created_at == _DT

    def test_daily_consolidation_overall_score_formula(self) -> None:
        """``overall_score`` is the weighted average E/P/H."""
        c = _make_consolidation(energy=80, productivity=70, health=90)
        # 0.3*80 + 0.4*70 + 0.3*90 = 24 + 28 + 27 = 79.0
        assert c.overall_score == pytest.approx(79.0)

    @pytest.mark.parametrize(
        ("energy", "productivity", "health", "expected"),
        [
            (100, 100, 100, 100.0),  # 30 + 40 + 30
            (0, 0, 0, 0.0),          # 0
            (50, 50, 50, 50.0),      # 15 + 20 + 15
            (100, 0, 100, 60.0),     # 30 + 0 + 30
            (0, 100, 0, 40.0),       # 0 + 40 + 0
            (33.33, 66.66, 99.99, pytest.approx(0.3 * 33.33 + 0.4 * 66.66 + 0.3 * 99.99)),
        ],
    )
    def test_daily_consolidation_overall_score_parametric(
        self,
        energy: float,
        productivity: float,
        health: float,
        expected: float,
    ) -> None:
        """``overall_score`` applies the formula across boundary values."""
        c = _make_consolidation(
            energy=energy, productivity=productivity, health=health,
        )
        assert c.overall_score == expected

    def test_daily_consolidation_alerts_default_empty(self) -> None:
        """``alerts`` defaults to an empty list."""
        c = _make_consolidation()
        assert c.alerts == []

    def test_daily_consolidation_recommendations_default_empty(self) -> None:
        """``recommendations`` defaults to an empty list."""
        c = _make_consolidation()
        assert c.recommendations == []

    def test_daily_consolidation_with_alerts(self) -> None:
        """Alerts and recommendations can be passed explicitly."""
        a = _make_alert(alert_id="alt_a")
        c = DailyConsolidation(
            id="cnl_with",
            date=_DATE,
            daily_log_id="day_with",
            energy_score=80.0,
            productivity_score=70.0,
            health_score=90.0,
            sleep_debt_hours=1.5,
            alerts=[a],
            recommendations=["Hydrate more", "Sleep earlier"],
            created_at=_DT,
        )
        assert len(c.alerts) == 1
        assert c.alerts[0] is a
        assert c.recommendations == ["Hydrate more", "Sleep earlier"]

    def test_daily_consolidation_trends(self) -> None:
        """Trend fields accept arbitrary floats."""
        c = DailyConsolidation(
            id="cnl_trend",
            date=_DATE,
            daily_log_id="day_trend",
            energy_score=80.0,
            productivity_score=70.0,
            health_score=90.0,
            productivity_trend=5.5,
            energy_trend=-2.3,
            created_at=_DT,
        )
        assert c.productivity_trend == 5.5
        assert c.energy_trend == -2.3

    def test_daily_consolidation_recommendation_max_length(self) -> None:
        """A recommendation over 200 chars is rejected."""
        with pytest.raises(ValidationError):
            DailyConsolidation(
                id="cnl_rec",
                date=_DATE,
                daily_log_id="day_rec",
                energy_score=80.0,
                productivity_score=70.0,
                health_score=90.0,
                recommendations=["x" * 201],
                created_at=_DT,
            )

    @pytest.mark.parametrize("field", ["energy_score", "productivity_score", "health_score"])
    def test_daily_consolidation_score_range_enforced(self, field: str) -> None:
        """Component scores must be in [0, 100]."""
        base = {
            "id": "cnl_b",
            "date": _DATE,
            "daily_log_id": "day_b",
            "energy_score": 80.0,
            "productivity_score": 70.0,
            "health_score": 90.0,
            "created_at": _DT,
        }
        with pytest.raises(ValidationError):
            DailyConsolidation(**{**base, field: -1.0})
        with pytest.raises(ValidationError):
            DailyConsolidation(**{**base, field: 101.0})

    def test_daily_consolidation_sleep_debt_range(self) -> None:
        """``sleep_debt_hours`` rejects negatives."""
        with pytest.raises(ValidationError):
            DailyConsolidation(
                id="cnl_sd",
                date=_DATE,
                daily_log_id="day_sd",
                energy_score=80.0,
                productivity_score=70.0,
                health_score=90.0,
                sleep_debt_hours=-1.0,
                created_at=_DT,
            )

    def test_daily_consolidation_is_frozen(self) -> None:
        """``DailyConsolidation`` is immutable."""
        c = _make_consolidation()
        with pytest.raises(ValidationError):
            c.energy_score = 50.0  # type: ignore[misc]

    def test_daily_consolidation_rejects_unknown_fields(self) -> None:
        """``extra='forbid'`` rejects unknown fields."""
        with pytest.raises(ValidationError):
            DailyConsolidation(
                id="cnl_unk",
                date=_DATE,
                daily_log_id="day_unk",
                energy_score=80.0,
                productivity_score=70.0,
                health_score=90.0,
                created_at=_DT,
                bogus="oops",  # type: ignore[call-arg]
            )

    # ---- compute_sleep_debt static helper -------------------------------

    @pytest.mark.parametrize(
        ("hours", "expected"),
        [
            (8.0, 0.0),   # perfect sleep
            (10.0, 0.0),  # overslept, no debt
            (7.0, 1.0),   # 1h short
            (4.0, 4.0),   # 4h short
            (0.0, 8.0),   # no sleep
            (None, 8.0),  # no record -> full debt
            (-1.0, 9.0),  # negative clamped by formula? (no, 8-(-1)=9)
        ],
    )
    def test_compute_sleep_debt(self, hours: float | None, expected: float) -> None:
        """``compute_sleep_debt`` returns ``max(0, 8 - h)``."""
        assert DailyConsolidation.compute_sleep_debt(hours) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# MetricAlert
# ---------------------------------------------------------------------------


class TestMetricAlert:
    """Specific tests for :class:`MetricAlert`."""

    def test_create_metric_alert(self) -> None:
        """All defaults and required fields are honoured."""
        a = _make_alert()
        assert a.id == "alt_test"
        assert a.level is AlertLevel.WARNING
        assert a.metric == "sleep_debt_hours"
        assert a.message == "Sleep debt too high"
        assert a.value == 3.0
        assert a.threshold == 2.0
        assert a.created_at == _DT
        assert a.resolved is False
        assert a.resolved_at is None

    @pytest.mark.parametrize(
        "level",
        [AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.CRITICAL],
    )
    def test_metric_alert_level_enum(self, level: AlertLevel) -> None:
        """All three :class:`AlertLevel` values are accepted."""
        a = _make_alert(level=level)
        assert a.level is level

    def test_metric_alert_resolved_auto_timestamp(self) -> None:
        """``resolved_at`` is auto-stamped when ``resolved=True`` and unset."""
        a = MetricAlert(
            id="alt_auto",
            level=AlertLevel.WARNING,
            metric="habit_compliance_pct",
            message="Below threshold",
            value=20.0,
            threshold=50.0,
            created_at=_DT,
            resolved=True,
        )
        assert a.resolved is True
        assert a.resolved_at is not None
        assert a.resolved_at >= _DT

    def test_metric_alert_resolved_at_preserved_when_provided(self) -> None:
        """Explicit ``resolved_at`` is preserved."""
        explicit = datetime(2025, 12, 31, 23, 59, 59)
        a = MetricAlert(
            id="alt_exp",
            level=AlertLevel.WARNING,
            metric="x",
            message="y",
            value=1.0,
            threshold=0.5,
            created_at=_DT,
            resolved=True,
            resolved_at=explicit,
        )
        assert a.resolved_at == explicit

    def test_metric_alert_resolved_at_not_set_when_unresolved(self) -> None:
        """``resolved_at`` remains ``None`` when ``resolved=False``."""
        a = _make_alert()
        assert a.resolved is False
        assert a.resolved_at is None

    def test_metric_alert_resolve_method(self) -> None:
        """``resolve()`` flips ``resolved`` and stamps ``resolved_at``."""
        a = _make_alert()
        assert a.resolved is False
        assert a.resolved_at is None
        a.resolve()
        assert a.resolved is True
        assert a.resolved_at is not None

    def test_metric_alert_resolve_is_idempotent(self) -> None:
        """Calling ``resolve()`` twice preserves the original timestamp."""
        a = _make_alert()
        a.resolve()
        first_stamp = a.resolved_at
        a.resolve()  # should be a no-op
        assert a.resolved_at == first_stamp

    def test_metric_alert_metric_min_length(self) -> None:
        """``metric`` rejects empty string."""
        with pytest.raises(ValidationError):
            _make_alert(metric="")

    def test_metric_alert_metric_max_length(self) -> None:
        """``metric`` rejects strings over 100 chars."""
        with pytest.raises(ValidationError):
            _make_alert(metric="x" * 101)

    def test_metric_alert_message_min_length(self) -> None:
        """``message`` rejects empty string."""
        with pytest.raises(ValidationError):
            _make_alert(message="")

    def test_metric_alert_message_max_length(self) -> None:
        """``message`` rejects strings over 500 chars."""
        with pytest.raises(ValidationError):
            _make_alert(message="x" * 501)

    def test_metric_alert_resolved_mutable(self) -> None:
        """``resolved`` can be flipped via assignment."""
        a = _make_alert()
        a.resolved = True
        assert a.resolved is True
        assert a.resolved_at is not None

    def test_metric_alert_other_fields_mutable(self) -> None:
        """``MetricAlert`` is mutable (``frozen=False``) for all fields.

        The spec intentionally keeps :class:`MetricAlert` mutable so that
        ``resolved`` / ``resolved_at`` can be updated in place; this also
        allows correction of ``value`` / ``threshold`` while the alert is
        being triaged.
        """
        a = _make_alert()
        a.value = 99.0
        a.threshold = 0.0
        assert a.value == 99.0
        assert a.threshold == 0.0

    def test_metric_alert_rejects_unknown_fields(self) -> None:
        """``extra='forbid'`` rejects unknown fields."""
        with pytest.raises(ValidationError):
            MetricAlert(
                id="alt_unk",
                level=AlertLevel.INFO,
                metric="x",
                message="y",
                value=1.0,
                threshold=0.5,
                created_at=_DT,
                bogus="oops",  # type: ignore[call-arg]
            )

    def test_metric_alert_can_be_attached_to_consolidation(self) -> None:
        """Alerts are embedded in :class:`DailyConsolidation`."""
        a = _make_alert()
        c = _make_consolidation()
        # mutate via constructing a new one
        c2 = c.model_copy(update={"alerts": [a]})
        assert c2.alerts == [a]


# ---------------------------------------------------------------------------
# WeeklyAggregate
# ---------------------------------------------------------------------------


_MONDAY: ClassVar[date] = date(2026, 6, 1)
_SUNDAY: ClassVar[date] = _MONDAY + timedelta(days=6)


class TestWeeklyAggregate:
    """Specific tests for :class:`WeeklyAggregate`."""

    def test_create_weekly_aggregate(self) -> None:
        """All defaults and required fields are honoured."""
        w = WeeklyAggregate(
            id="wkl_test",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            created_at=_DT,
        )
        assert w.id == "wkl_test"
        assert w.week_start == _MONDAY
        assert w.week_end == _SUNDAY
        assert w.days == []
        assert w.avg_sleep_hours == 0.0
        assert w.avg_sleep_quality == 5.0
        assert w.avg_energy_score == 0.0
        assert w.avg_productivity == 0.0
        assert w.total_tasks_done == 0
        assert w.total_study_minutes == 0
        assert w.total_exercise_days == 0
        assert w.habit_compliance_avg == 0.0
        assert w.best_streak_habit is None
        assert w.week_score == 0.0
        assert w.created_at == _DT

    # ---- week_label buckets ---------------------------------------------

    @pytest.mark.parametrize("score", [85.0, 90.0, 95.0, 100.0])
    def test_weekly_aggregate_week_label_excelente(self, score: float) -> None:
        """``week_score >= 85`` → ``EXCELENTE``."""
        w = WeeklyAggregate(
            id="wkl_exc",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            week_score=score,
            created_at=_DT,
        )
        assert w.week_label is WeekLabel.EXCELENTE

    @pytest.mark.parametrize("score", [70.0, 75.0, 80.0, 84.99])
    def test_weekly_aggregate_week_label_bom(self, score: float) -> None:
        """``70 <= week_score < 85`` → ``BOM``."""
        w = WeeklyAggregate(
            id="wkl_bom",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            week_score=score,
            created_at=_DT,
        )
        assert w.week_label is WeekLabel.BOM

    @pytest.mark.parametrize("score", [50.0, 55.0, 60.0, 69.99])
    def test_weekly_aggregate_week_label_medio(self, score: float) -> None:
        """``50 <= week_score < 70`` → ``MEDIO``."""
        w = WeeklyAggregate(
            id="wkl_med",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            week_score=score,
            created_at=_DT,
        )
        assert w.week_label is WeekLabel.MEDIO

    @pytest.mark.parametrize("score", [30.0, 35.0, 40.0, 49.99])
    def test_weekly_aggregate_week_label_ruim(self, score: float) -> None:
        """``30 <= week_score < 50`` → ``RUIM``."""
        w = WeeklyAggregate(
            id="wkl_ruim",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            week_score=score,
            created_at=_DT,
        )
        assert w.week_label is WeekLabel.RUIM

    @pytest.mark.parametrize("score", [0.0, 10.0, 20.0, 29.99])
    def test_weekly_aggregate_week_label_recuperacao(self, score: float) -> None:
        """``week_score < 30`` → ``RECUPERACAO``."""
        w = WeeklyAggregate(
            id="wkl_rec",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            week_score=score,
            created_at=_DT,
        )
        assert w.week_label is WeekLabel.RECUPERACAO

    def test_weekly_aggregate_week_label_excelente_boundary_exact(self) -> None:
        """``week_score == 85`` (exact boundary) → ``EXCELENTE``."""
        w = WeeklyAggregate(
            id="wkl_b",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            week_score=85.0,
            created_at=_DT,
        )
        assert w.week_label is WeekLabel.EXCELENTE

    def test_weekly_aggregate_week_label_bom_boundary_exact(self) -> None:
        """``week_score == 70`` (exact boundary) → ``BOM``."""
        w = WeeklyAggregate(
            id="wkl_b2",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            week_score=70.0,
            created_at=_DT,
        )
        assert w.week_label is WeekLabel.BOM

    def test_weekly_aggregate_week_label_medio_boundary_exact(self) -> None:
        """``week_score == 50`` (exact boundary) → ``MEDIO``."""
        w = WeeklyAggregate(
            id="wkl_b3",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            week_score=50.0,
            created_at=_DT,
        )
        assert w.week_label is WeekLabel.MEDIO

    def test_weekly_aggregate_week_label_ruim_boundary_exact(self) -> None:
        """``week_score == 30`` (exact boundary) → ``RUIM``."""
        w = WeeklyAggregate(
            id="wkl_b4",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            week_score=30.0,
            created_at=_DT,
        )
        assert w.week_label is WeekLabel.RUIM

    # ---- validators -----------------------------------------------------

    def test_weekly_aggregate_week_must_be_6_days(self) -> None:
        """``week_end - week_start`` must be exactly 6 days."""
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_bad",
                week_start=_MONDAY,
                week_end=_MONDAY + timedelta(days=5),
                week_score=50.0,
                created_at=_DT,
            )

    def test_weekly_aggregate_week_must_be_6_days_overflow(self) -> None:
        """``week_end - week_start`` > 6 days is rejected."""
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_over",
                week_start=_MONDAY,
                week_end=_MONDAY + timedelta(days=7),
                week_score=50.0,
                created_at=_DT,
            )

    def test_weekly_aggregate_week_can_be_same_day_0(self) -> None:
        """``week_end == week_start`` is rejected (0-day span)."""
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_0",
                week_start=_MONDAY,
                week_end=_MONDAY,
                week_score=50.0,
                created_at=_DT,
            )

    def test_weekly_aggregate_week_must_be_6_days_negative(self) -> None:
        """``week_end < week_start`` is rejected."""
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_neg",
                week_start=_MONDAY,
                week_end=_MONDAY - timedelta(days=1),
                week_score=50.0,
                created_at=_DT,
            )

    def test_weekly_aggregate_total_exercise_max_7(self) -> None:
        """``total_exercise_days`` is bounded by [0, 7]."""
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_te",
                week_start=_MONDAY,
                week_end=_SUNDAY,
                total_exercise_days=8,
                week_score=50.0,
                created_at=_DT,
            )

    def test_weekly_aggregate_total_exercise_min_0(self) -> None:
        """``total_exercise_days`` is bounded by [0, 7]."""
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_te2",
                week_start=_MONDAY,
                week_end=_SUNDAY,
                total_exercise_days=-1,
                week_score=50.0,
                created_at=_DT,
            )

    @pytest.mark.parametrize("n", [0, 1, 3, 5, 7])
    def test_weekly_aggregate_total_exercise_valid(self, n: int) -> None:
        """``total_exercise_days`` accepts 0..7 inclusive."""
        w = WeeklyAggregate(
            id=f"wkl_te_{n}",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            total_exercise_days=n,
            week_score=50.0,
            created_at=_DT,
        )
        assert w.total_exercise_days == n

    # ---- field ranges ---------------------------------------------------

    def test_weekly_aggregate_week_score_range(self) -> None:
        """``week_score`` rejects out-of-range values."""
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_ws1",
                week_start=_MONDAY,
                week_end=_SUNDAY,
                week_score=-0.1,
                created_at=_DT,
            )
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_ws2",
                week_start=_MONDAY,
                week_end=_SUNDAY,
                week_score=100.1,
                created_at=_DT,
            )

    def test_weekly_aggregate_sleep_quality_range(self) -> None:
        """``avg_sleep_quality`` rejects out-of-range values."""
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_sq1",
                week_start=_MONDAY,
                week_end=_SUNDAY,
                avg_sleep_quality=0.5,
                week_score=50.0,
                created_at=_DT,
            )
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_sq2",
                week_start=_MONDAY,
                week_end=_SUNDAY,
                avg_sleep_quality=10.5,
                week_score=50.0,
                created_at=_DT,
            )

    def test_weekly_aggregate_days_list(self) -> None:
        """``days`` accepts up to 7 :data:`UEID` references."""
        ids = [f"cnl_2026_06_0{i}" for i in range(1, 8)]
        w = WeeklyAggregate(
            id="wkl_days",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            days=ids,
            week_score=80.0,
            created_at=_DT,
        )
        assert len(w.days) == 7
        assert w.days[0] == "cnl_2026_06_01"

    def test_weekly_aggregate_best_streak_habit(self) -> None:
        """``best_streak_habit`` can hold a habit name."""
        w = WeeklyAggregate(
            id="wkl_streak",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            best_streak_habit="morning_water",
            week_score=80.0,
            created_at=_DT,
        )
        assert w.best_streak_habit == "morning_water"

    def test_weekly_aggregate_is_frozen(self) -> None:
        """``WeeklyAggregate`` is immutable."""
        w = WeeklyAggregate(
            id="wkl_frozen",
            week_start=_MONDAY,
            week_end=_SUNDAY,
            week_score=50.0,
            created_at=_DT,
        )
        with pytest.raises(ValidationError):
            w.week_score = 99.0  # type: ignore[misc]

    def test_weekly_aggregate_rejects_unknown_fields(self) -> None:
        """``extra='forbid'`` rejects unknown fields."""
        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_unk",
                week_start=_MONDAY,
                week_end=_SUNDAY,
                week_score=50.0,
                created_at=_DT,
                bogus="oops",  # type: ignore[call-arg]
            )
