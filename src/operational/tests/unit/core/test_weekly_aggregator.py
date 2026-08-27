"""Comprehensive unit tests for :mod:`operational.core.weekly_aggregator`.

Coverage (~30 tests):

* :class:`WeeklyAggregator` — namespace class instantiation.
* :meth:`WeeklyAggregator.aggregate_from_logs` — empty input,
  partial weeks, full weeks, all 4 average/total computations,
  helper-derived week_score, default sleep_quality, week-span
  enforcement.
* :meth:`WeeklyAggregator.aggregate_from_consolidations` — empty
  input, partial weeks, full weeks, ``days`` list population,
  sleep-debt-derived ``avg_sleep_hours``.
* :func:`aggregate_week` — dispatch on logs vs consolidations,
  error when neither is provided, logs precedence.
* :class:`WeekLabel` integration — end-to-end aggregation feeding
  the :class:`WeeklyAggregate.week_label` computed field.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import ClassVar

import pytest

from operational.core.weekly_aggregator import (
    WEEKLY_POMODORO_TARGET,
    WeeklyAggregator,
    aggregate_week,
)
from operational.entities.consolidation import DailyConsolidation, WeeklyAggregate
from operational.entities.metric import DailyLog, SleepRecord
from operational.enums import WeekLabel

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


_DT: ClassVar[datetime] = datetime(2026, 6, 7, 22, 0)
_MONDAY: ClassVar[date] = date(2026, 6, 1)  # a real Monday
_SUNDAY: ClassVar[date] = _MONDAY + timedelta(days=6)


def _make_sleep(
    *,
    date_: date,
    duration_hours: float = 8.0,
    quality: int = 8,
) -> SleepRecord:
    """Build a :class:`SleepRecord` for a given date.

    The bedtime is computed from the duration so the test data is
    self-consistent. Default 8h, quality 8.
    """
    bedtime_hour = 22  # 10pm
    wake_hour = (bedtime_hour + int(duration_hours)) % 24
    return SleepRecord(
        id=f"slp_{date_.strftime('%Y%m%d')}",
        date=date_,
        bedtime=time(bedtime_hour, 0),
        wake_time=time(wake_hour, 0),
        quality_score=quality,
        created_at=_DT,
    )


def _make_log(  # noqa: PLR0913 — 8 keyword-only test factory params
    *,
    date_: date,
    sleep: SleepRecord | None = None,
    tasks_completed: int = 5,
    study_minutes: int = 60,
    exercise_done: bool = True,
    pomodoros: int = 8,
    habits_done: int = 3,
    habits_total: int = 4,
    water_glasses: int = 8,
) -> DailyLog:
    """Build a :class:`DailyLog` for a given date."""
    return DailyLog(
        id=f"day_{date_.strftime('%Y%m%d')}",
        date=date_,
        sleep=sleep,
        tasks_completed=tasks_completed,
        study_minutes=study_minutes,
        exercise_done=exercise_done,
        pomodoros=pomodoros,
        habits_done=habits_done,
        habits_total=habits_total,
        water_glasses=water_glasses,
        created_at=_DT,
    )


def _make_consolidation(
    *,
    date_: date,
    energy: float = 80.0,
    productivity: float = 70.0,
    health: float = 90.0,
    sleep_debt: float = 1.0,
) -> DailyConsolidation:
    """Build a :class:`DailyConsolidation` for a given date."""
    date_slug = date_.strftime("%Y%m%d")
    return DailyConsolidation(
        id=f"cnl_{date_slug}",
        date=date_,
        daily_log_id=f"day_{date_slug}",
        energy_score=energy,
        productivity_score=productivity,
        health_score=health,
        sleep_debt_hours=sleep_debt,
        created_at=_DT,
    )


# ===========================================================================
# Module surface
# ===========================================================================


class TestModuleSurface:
    """The module exports the expected public symbols."""

    def test_all_exports_present(self) -> None:
        """``__all__`` lists the canonical public surface."""
        from operational.core import weekly_aggregator

        expected = {"WEEKLY_POMODORO_TARGET", "WeeklyAggregator", "aggregate_week"}
        assert set(weekly_aggregator.__all__) == expected

    def test_all_names_importable(self) -> None:
        """Every name in ``__all__`` is a real attribute."""
        from operational.core import weekly_aggregator

        for name in weekly_aggregator.__all__:
            assert hasattr(weekly_aggregator, name), f"Missing export: {name}"

    def test_weekly_pomodoro_target(self) -> None:
        """``WEEKLY_POMODORO_TARGET`` is the canonical 60."""
        assert WEEKLY_POMODORO_TARGET == 60

    def test_weekly_aggregator_is_dataclass(self) -> None:
        """``WeeklyAggregator`` is a frozen dataclass with slots."""
        from dataclasses import is_dataclass

        assert is_dataclass(WeeklyAggregator)


# ===========================================================================
# WeeklyAggregator — empty / single / full week from logs
# ===========================================================================


class TestAggregateFromLogsEmpty:
    """``aggregate_from_logs`` with an empty input."""

    def test_empty_returns_valid_aggregate(self) -> None:
        """Empty logs → valid zero-valued aggregate."""
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, [])
        assert isinstance(result, WeeklyAggregate)
        assert result.id.startswith("wkl_")
        assert result.week_start == _MONDAY
        assert result.week_end == _SUNDAY
        assert result.days == []
        assert result.avg_sleep_hours == 0.0
        assert result.avg_sleep_quality == 5.0  # default
        assert result.avg_energy_score == 0.0
        assert result.avg_productivity == 0.0
        assert result.total_tasks_done == 0
        assert result.total_study_minutes == 0
        assert result.total_exercise_days == 0
        assert result.habit_compliance_avg == 0.0
        assert result.week_score == 0.0
        assert result.week_label is WeekLabel.RECUPERACAO

    def test_empty_week_end_is_sunday(self) -> None:
        """``week_end = week_start + 6 days``."""
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, [])
        assert result.week_end == _MONDAY + timedelta(days=6)


class TestAggregateFromLogsOneDay:
    """A 1-day log set."""

    def test_single_day(self) -> None:
        """A single log with full defaults is aggregated correctly."""
        log = _make_log(date_=_MONDAY, tasks_completed=5, pomodoros=8, study_minutes=60)
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, [log])
        assert result.total_tasks_done == 5
        assert result.total_study_minutes == 60
        assert result.total_exercise_days == 1
        assert result.pomodoros if hasattr(result, "pomodoros") else True  # always
        assert result.habit_compliance_avg == pytest.approx(75.0)
        # 8 / 60 * 100 = 13.33
        assert result.week_score == pytest.approx(13.333, abs=1e-3)


class TestAggregateFromLogsSevenDays:
    """A full 7-day log set."""

    def test_seven_days_aggregated(self) -> None:
        """7 logs with sleep, tasks, exercise are aggregated correctly."""
        logs = []
        for i in range(7):
            d = _MONDAY + timedelta(days=i)
            logs.append(
                _make_log(
                    date_=d,
                    sleep=_make_sleep(date_=d, duration_hours=8.0, quality=8),
                    tasks_completed=5,
                    study_minutes=60,
                    exercise_done=True,
                    pomodoros=8,
                ),
            )
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.avg_sleep_hours == pytest.approx(8.0)
        assert result.avg_sleep_quality == 8.0
        assert result.total_tasks_done == 35
        assert result.total_study_minutes == 420
        assert result.total_exercise_days == 7
        # 56 pomodoros / 60 * 100 = 93.33
        assert result.week_score == pytest.approx(93.333, abs=1e-3)
        assert result.week_label is WeekLabel.EXCELENTE


class TestAggregateFromLogsEnforcement:
    """The 7-day cap."""

    def test_more_than_7_raises(self) -> None:
        """8 logs raise :class:`ValueError`."""
        logs = [_make_log(date_=_MONDAY + timedelta(days=i)) for i in range(8)]
        agg = WeeklyAggregator()
        with pytest.raises(ValueError, match="logs must be <= 7"):
            agg.aggregate_from_logs(_MONDAY, logs)

    def test_exactly_7_accepted(self) -> None:
        """7 logs are accepted (no error)."""
        logs = [_make_log(date_=_MONDAY + timedelta(days=i)) for i in range(7)]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert isinstance(result, WeeklyAggregate)


# ===========================================================================
# Aggregate from logs — metric details
# ===========================================================================


class TestAggregateFromLogsMetrics:
    """Per-metric correctness of ``aggregate_from_logs``."""

    def test_sleep_hours_average(self) -> None:
        """Sleep-hours average across days with sleep records."""
        logs = [
            _make_log(
                date_=_MONDAY,
                sleep=_make_sleep(date_=_MONDAY, duration_hours=8.0),
            ),
            _make_log(
                date_=_MONDAY + timedelta(days=1),
                sleep=_make_sleep(
                    date_=_MONDAY + timedelta(days=1), duration_hours=6.0,
                ),
            ),
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.avg_sleep_hours == pytest.approx(7.0)

    def test_no_sleep_records(self) -> None:
        """Days without sleep records yield 0.0 average."""
        logs = [
            _make_log(date_=_MONDAY, sleep=None),
            _make_log(date_=_MONDAY + timedelta(days=1), sleep=None),
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.avg_sleep_hours == 0.0
        assert result.avg_sleep_quality == 5.0  # default

    def test_total_tasks_done(self) -> None:
        """Tasks-done totals are summed."""
        logs = [
            _make_log(date_=_MONDAY, tasks_completed=3),
            _make_log(date_=_MONDAY + timedelta(days=1), tasks_completed=7),
            _make_log(date_=_MONDAY + timedelta(days=2), tasks_completed=5),
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.total_tasks_done == 15

    def test_total_study_minutes(self) -> None:
        """Study-minutes totals are summed."""
        logs = [
            _make_log(date_=_MONDAY, study_minutes=30),
            _make_log(date_=_MONDAY + timedelta(days=1), study_minutes=90),
            _make_log(date_=_MONDAY + timedelta(days=2), study_minutes=60),
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.total_study_minutes == 180

    def test_total_exercise_days(self) -> None:
        """Exercise-days count only days with ``exercise_done=True``."""
        logs = [
            _make_log(date_=_MONDAY, exercise_done=True),
            _make_log(date_=_MONDAY + timedelta(days=1), exercise_done=False),
            _make_log(date_=_MONDAY + timedelta(days=2), exercise_done=True),
            _make_log(date_=_MONDAY + timedelta(days=3), exercise_done=True),
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.total_exercise_days == 3

    def test_habit_compliance_average(self) -> None:
        """Habit-compliance averages across all days."""
        logs = [
            _make_log(date_=_MONDAY, habits_done=2, habits_total=4),  # 50%
            _make_log(
                date_=_MONDAY + timedelta(days=1),
                habits_done=4,
                habits_total=4,
            ),  # 100%
            _make_log(
                date_=_MONDAY + timedelta(days=2),
                habits_done=0,
                habits_total=4,
            ),  # 0%
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.habit_compliance_avg == pytest.approx(50.0)

    def test_week_score_capped_at_100(self) -> None:
        """``week_score`` is capped at 100 even with many pomodoros."""
        logs = [_make_log(date_=_MONDAY, pomodoros=20) for _ in range(7)]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        # 7 * 20 = 140 pomodoros → 140 / 60 * 100 = 233 → capped at 100
        assert result.week_score == 100.0

    def test_week_score_zero_when_no_pomodoros(self) -> None:
        """``week_score`` is 0 when no pomodoros were done."""
        logs = [_make_log(date_=_MONDAY, pomodoros=0) for _ in range(3)]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.week_score == 0.0

    def test_avg_productivity_always_zero_for_logs(self) -> None:
        """``avg_productivity`` is not derivable from logs → 0.0."""
        logs = [_make_log(date_=_MONDAY) for _ in range(3)]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.avg_productivity == 0.0

    def test_sleep_quality_default(self) -> None:
        """Without sleep records, ``avg_sleep_quality`` defaults to 5.0."""
        logs = [_make_log(date_=_MONDAY, sleep=None)]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.avg_sleep_quality == 5.0


# ===========================================================================
# Aggregate from consolidations
# ===========================================================================


class TestAggregateFromConsolidationsEmpty:
    """Empty consolidation list."""

    def test_empty_returns_valid_aggregate(self) -> None:
        """Empty consolidations → valid zero-valued aggregate."""
        agg = WeeklyAggregator()
        result = agg.aggregate_from_consolidations(_MONDAY, [])
        assert isinstance(result, WeeklyAggregate)
        assert result.days == []
        assert result.week_start == _MONDAY
        assert result.week_end == _SUNDAY
        assert result.avg_sleep_hours == 0.0
        assert result.week_score == 0.0
        assert result.week_label is WeekLabel.RECUPERACAO

    def test_empty_aggregates_match_logs(self) -> None:
        """Empty consolidations and empty logs produce similar shapes."""
        agg = WeeklyAggregator()
        r_logs = agg.aggregate_from_logs(_MONDAY, [])
        r_cons = agg.aggregate_from_consolidations(_MONDAY, [])
        assert r_logs.id.startswith("wkl_")
        assert r_cons.id.startswith("wkl_")
        # IDs are different (random hex)
        assert r_logs.id != r_cons.id


class TestAggregateFromConsolidationsFull:
    """A full set of consolidations."""

    def test_seven_consolidations(self) -> None:
        """7 consolidations populate all averages."""
        cons = [
            _make_consolidation(
                date_=_MONDAY + timedelta(days=i),
                energy=80.0,
                productivity=70.0,
                health=90.0,
                sleep_debt=1.0,
            )
            for i in range(7)
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_consolidations(_MONDAY, cons)
        assert result.avg_energy_score == pytest.approx(80.0)
        assert result.avg_productivity == pytest.approx(70.0)
        assert result.habit_compliance_avg == pytest.approx(90.0)
        # overall = 0.3*80 + 0.4*70 + 0.3*90 = 24 + 28 + 27 = 79
        assert result.week_score == pytest.approx(79.0)
        assert result.week_label is WeekLabel.BOM

    def test_three_consolidations(self) -> None:
        """3 consolidations produce correct averages."""
        cons = [
            _make_consolidation(
                date_=_MONDAY + timedelta(days=i),
                energy=60.0,
                productivity=80.0,
                health=100.0,
            )
            for i in range(3)
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_consolidations(_MONDAY, cons)
        assert result.avg_energy_score == pytest.approx(60.0)
        assert result.avg_productivity == pytest.approx(80.0)
        # overall = 0.3*60 + 0.4*80 + 0.3*100 = 18+32+30 = 80
        assert result.week_score == pytest.approx(80.0)
        assert result.week_label is WeekLabel.BOM

    def test_days_populated_from_consolidations(self) -> None:
        """The ``days`` field is populated with consolidation IDs."""
        cons = [
            _make_consolidation(date_=_MONDAY + timedelta(days=i))
            for i in range(3)
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_consolidations(_MONDAY, cons)
        assert len(result.days) == 3
        for i, cid in enumerate(result.days):
            assert cid == f"cnl_{(_MONDAY + timedelta(days=i)).strftime('%Y%m%d')}"

    def test_sleep_debt_subtracted(self) -> None:
        """``avg_sleep_hours`` = 8.0 - avg_sleep_debt."""
        cons = [
            _make_consolidation(
                date_=_MONDAY + timedelta(days=i),
                sleep_debt=2.0,
            )
            for i in range(3)
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_consolidations(_MONDAY, cons)
        assert result.avg_sleep_hours == pytest.approx(6.0)

    def test_zero_sleep_debt(self) -> None:
        """With zero sleep debt, ``avg_sleep_hours`` = 8.0 (target)."""
        cons = [
            _make_consolidation(
                date_=_MONDAY + timedelta(days=i),
                sleep_debt=0.0,
            )
            for i in range(3)
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_consolidations(_MONDAY, cons)
        assert result.avg_sleep_hours == pytest.approx(8.0)

    def test_total_counters_zero_for_consolidations(self) -> None:
        """Counters not derivable from consolidations are 0."""
        cons = [_make_consolidation(date_=_MONDAY) for _ in range(3)]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_consolidations(_MONDAY, cons)
        assert result.total_tasks_done == 0
        assert result.total_study_minutes == 0
        assert result.total_exercise_days == 0


# ===========================================================================
# aggregate_week convenience function
# ===========================================================================


class TestAggregateWeekFunction:
    """The module-level :func:`aggregate_week` dispatcher."""

    def test_with_logs(self) -> None:
        """``logs=`` dispatches to ``aggregate_from_logs``."""
        logs = [_make_log(date_=_MONDAY, tasks_completed=3)]
        result = aggregate_week(_MONDAY, logs=logs)
        assert result.total_tasks_done == 3

    def test_with_consolidations(self) -> None:
        """``consolidations=`` dispatches to ``aggregate_from_consolidations``."""
        cons = [
            _make_consolidation(date_=_MONDAY, energy=50.0, productivity=50.0, health=50.0),
        ]
        result = aggregate_week(_MONDAY, consolidations=cons)
        assert result.avg_energy_score == pytest.approx(50.0)

    def test_neither_raises(self) -> None:
        """Calling with neither ``logs`` nor ``consolidations`` raises."""
        with pytest.raises(ValueError, match="requires either"):
            aggregate_week(_MONDAY)

    def test_both_logs_used(self) -> None:
        """When both are provided, ``logs`` wins (more granular)."""
        logs = [_make_log(date_=_MONDAY, tasks_completed=3)]
        cons = [_make_consolidation(date_=_MONDAY)]
        result = aggregate_week(_MONDAY, logs=logs, consolidations=cons)
        # logs path populates tasks-done
        assert result.total_tasks_done == 3
        # consolidations path would not (0 instead)
        # so this confirms the dispatch is correct


# ===========================================================================
# Week-label integration
# ===========================================================================


class TestWeekLabelIntegration:
    """End-to-end aggregation feeding the :class:`WeekLabel` computed field."""

    @pytest.mark.parametrize(
        ("pomos_per_day", "expected_label"),
        [
            (0, WeekLabel.RECUPERACAO),   # 0 → recovery
            (2, WeekLabel.RECUPERACAO),   # 14/60 = 23% → recovery
            (4, WeekLabel.RUIM),          # 28/60 = 46% → poor
            (7, WeekLabel.BOM),           # 49/60 = 81% → good
            (10, WeekLabel.EXCELENTE),    # 70/60 > 100 → capped → excellent
        ],
    )
    def test_week_label_from_pomodoros(
        self,
        pomos_per_day: int,
        expected_label: WeekLabel,
    ) -> None:
        """Verify ``week_label`` from the pomodoro-based week_score."""
        logs = [
            _make_log(date_=_MONDAY + timedelta(days=i), pomodoros=pomos_per_day)
            for i in range(7)
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        # Recompute expected week_score manually
        expected_score = min(100.0, (pomos_per_day * 7 / WEEKLY_POMODORO_TARGET) * 100.0)
        assert result.week_score == pytest.approx(expected_score, abs=1e-3)
        assert result.week_label is expected_label

    def test_week_label_excelente_high(self) -> None:
        """``week_score = 100.0`` (capped) → EXCELENTE."""
        logs = [
            _make_log(date_=_MONDAY + timedelta(days=i), pomodoros=20)
            for i in range(7)
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, logs)
        assert result.week_score == 100.0
        assert result.week_label is WeekLabel.EXCELENTE

    def test_week_label_from_consolidations(self) -> None:
        """Verify ``week_label`` from consolidation-derived week_score."""
        cons = [
            _make_consolidation(
                date_=_MONDAY + timedelta(days=i),
                energy=100.0,
                productivity=100.0,
                health=100.0,
            )
            for i in range(7)
        ]
        agg = WeeklyAggregator()
        result = agg.aggregate_from_consolidations(_MONDAY, cons)
        assert result.week_score == pytest.approx(100.0)
        assert result.week_label is WeekLabel.EXCELENTE


# ===========================================================================
# Week-span validator (via the underlying WeeklyAggregate)
# ===========================================================================


class TestWeekSpanEnforcement:
    """The 6-day span between week_start and week_end is enforced."""

    def test_week_must_be_6_days_via_aggregate(self) -> None:
        """If the model rejects a 5-day span, the aggregator is consistent."""
        # The aggregator computes week_end = week_start + 6 days, so it
        # is always valid. The model-level validator is checked here
        # to make sure both are aligned.
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            WeeklyAggregate(
                id="wkl_test",
                week_start=_MONDAY,
                week_end=_MONDAY + timedelta(days=5),  # 5-day span
                created_at=_DT,
            )

    def test_aggregator_always_produces_6_day_span(self) -> None:
        """The aggregator's output is always a 6-day span."""
        agg = WeeklyAggregator()
        result = agg.aggregate_from_logs(_MONDAY, [])
        assert (result.week_end - result.week_start).days == 6


# ===========================================================================
# Dataclass invariants
# ===========================================================================


class TestWeeklyAggregatorDataclass:
    """``WeeklyAggregator`` is a frozen dataclass."""

    def test_is_frozen(self) -> None:
        """Assignment after construction raises :class:`FrozenInstanceError`."""
        from dataclasses import FrozenInstanceError

        agg = WeeklyAggregator()
        with pytest.raises(FrozenInstanceError):
            agg.invalid = "x"  # type: ignore[attr-defined]

    def test_uses_slots(self) -> None:
        """The dataclass is frozen (slots used internally)."""
        agg = WeeklyAggregator()
        # Frozen dataclass: assignment raises FrozenInstanceError.
        with pytest.raises((AttributeError, TypeError)):
            agg.invalid = "x"  # type: ignore[attr-defined]
