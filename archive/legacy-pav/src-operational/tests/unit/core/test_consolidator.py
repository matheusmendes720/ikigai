"""Comprehensive unit tests for :mod:`operational.core.consolidator`.

Covers (Sprint 4B — Core Layer Part 2):

* :class:`DailyConsolidationResult` — frozen dataclass shape.
* :func:`compute_energy_score` — empty / H / M / L / mixed readings,
  sleep penalty (zero / partial / full).
* :func:`compute_productivity_score` — zero / high tasks, time
  bonus, focus bonus, max bonuses.
* :func:`compute_health_score` — no sleep, with sleep, water
  saturation, exercise bonus.
* :func:`compute_overall_score` — weighting formula, clamping.
* :func:`compute_sleep_debt` — 8h / 6h / 0h / no record.
* :func:`generate_alerts` — sleep debt (WARN/CRIT), habit
  compliance (WARN/CRIT), productivity (WARN/CRIT), empty result.
* :func:`generate_recommendations` — low energy / productivity /
  health, excelente, recovery.
* :func:`consolidate_daily` — full end-to-end, no sleep, no
  energy readings, excellent day, critical day.
* :class:`Consolidator` — delegates to module-level functions.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import ClassVar

import pytest

from operational.core.consolidator import (
    Consolidator,
    DailyConsolidationResult,
    compute_energy_score,
    compute_health_score,
    compute_overall_score,
    compute_productivity_score,
    compute_sleep_debt,
    consolidate_daily,
    generate_alerts,
    generate_recommendations,
)
from operational.entities.consolidation import DailyConsolidation
from operational.entities.metric import DailyLog, EnergyReading, SleepRecord
from operational.enums import AlertLevel, EnergyLevel

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_DT: ClassVar[datetime] = datetime(2026, 6, 7, 8, 0)
_DATE: ClassVar[date] = date(2026, 6, 7)


def _sleep(
    *,
    bedtime: time = time(22, 0),
    wake_time: time = time(6, 0),
    quality: int = 8,
    sleep_id: str = "slp_test",
) -> SleepRecord:
    """Build a :class:`SleepRecord` for testing."""
    return SleepRecord(
        id=sleep_id,
        date=_DATE,
        bedtime=bedtime,
        wake_time=wake_time,
        quality_score=quality,
        created_at=_DT,
    )


def _energy(
    level: EnergyLevel,
    *,
    context: str = "morning",
    energy_id: str = "erg_test",
) -> EnergyReading:
    """Build a :class:`EnergyReading` for testing."""
    return EnergyReading(
        id=energy_id,
        date=_DATE,
        timestamp=_DT,
        level=level,
        context=context,  # type: ignore[arg-type]
        created_at=_DT,
    )


def _log(  # noqa: PLR0913
    *,
    sleep: SleepRecord | None = None,
    energy_readings: list[EnergyReading] | None = None,
    tasks_completed: int = 0,
    tasks_created: int = 0,
    time_tracked_hours: float = 0.0,
    pomodoros: int = 0,
    exercise_done: bool = False,
    water_glasses: int = 0,
    habits_done: int = 0,
    habits_total: int = 0,
    log_id: str = "day_test",
) -> DailyLog:
    """Build a :class:`DailyLog` for testing."""
    return DailyLog(
        id=log_id,
        date=_DATE,
        sleep=sleep,
        energy_readings=energy_readings if energy_readings is not None else [],
        tasks_completed=tasks_completed,
        tasks_created=tasks_created,
        time_tracked_hours=time_tracked_hours,
        pomodoros=pomodoros,
        exercise_done=exercise_done,
        water_glasses=water_glasses,
        habits_done=habits_done,
        habits_total=habits_total,
        created_at=_DT,
        updated_at=_DT,
    )


# ===========================================================================
# Module surface
# ===========================================================================


class TestModuleSurface:
    """The :mod:`consolidator` module exports the expected public symbols."""

    def test_all_exports_present(self) -> None:
        from operational.core import consolidator

        expected = {
            "Consolidator",
            "DailyConsolidationResult",
            "compute_energy_score",
            "compute_health_score",
            "compute_overall_score",
            "compute_productivity_score",
            "compute_sleep_debt",
            "consolidate_daily",
            "generate_alerts",
            "generate_recommendations",
        }
        assert set(consolidator.__all__) == expected


# ===========================================================================
# DailyConsolidationResult dataclass
# ===========================================================================


class TestDailyConsolidationResult:
    """:class:`DailyConsolidationResult` is a frozen dataclass."""

    def test_create_result(self) -> None:
        r = DailyConsolidationResult(
            energy_score=80.0,
            productivity_score=70.0,
            health_score=90.0,
            overall_score=78.0,
            sleep_debt_hours=0.0,
            alerts=(),
            recommendations=(),
        )
        assert r.energy_score == 80.0
        assert r.productivity_score == 70.0
        assert r.health_score == 90.0
        assert r.overall_score == 78.0
        assert r.sleep_debt_hours == 0.0
        assert r.alerts == ()
        assert r.recommendations == ()

    def test_frozen(self) -> None:
        r = DailyConsolidationResult(
            energy_score=80.0,
            productivity_score=70.0,
            health_score=90.0,
            overall_score=78.0,
            sleep_debt_hours=0.0,
            alerts=(),
            recommendations=(),
        )
        with pytest.raises((AttributeError, Exception)):
            r.energy_score = 0.0  # type: ignore[misc]


# ===========================================================================
# compute_energy_score
# ===========================================================================


class TestComputeEnergyScore:
    """:func:`compute_energy_score` computes the energy composite (PRD-05 §4)."""

    def test_no_readings_returns_zero(self) -> None:
        log = _log()
        assert compute_energy_score(log) == 0.0

    def test_high_reading_returns_100(self) -> None:
        log = _log(energy_readings=[_energy(EnergyLevel.HIGH)])
        assert compute_energy_score(log) == 100.0

    def test_medium_reading_returns_60(self) -> None:
        log = _log(energy_readings=[_energy(EnergyLevel.MEDIUM)])
        assert compute_energy_score(log) == 60.0

    def test_low_reading_returns_30(self) -> None:
        log = _log(energy_readings=[_energy(EnergyLevel.LOW)])
        assert compute_energy_score(log) == 30.0

    def test_mixed_two_high_one_low(self) -> None:
        """Mean of 100, 100, 30 = 76.67."""
        log = _log(
            energy_readings=[
                _energy(EnergyLevel.HIGH, energy_id="erg_h1"),
                _energy(EnergyLevel.HIGH, energy_id="erg_h2", context="afternoon"),
                _energy(EnergyLevel.LOW, energy_id="erg_l1", context="evening"),
            ]
        )
        result = compute_energy_score(log)
        assert result == pytest.approx(76.666, rel=0.01)

    def test_mixed_three_equal(self) -> None:
        """Mean of H, M, L = (100+60+30)/3 = 63.33."""
        log = _log(
            energy_readings=[
                _energy(EnergyLevel.HIGH, energy_id="erg_h"),
                _energy(EnergyLevel.MEDIUM, energy_id="erg_m", context="afternoon"),
                _energy(EnergyLevel.LOW, energy_id="erg_l", context="evening"),
            ]
        )
        assert compute_energy_score(log) == pytest.approx(63.333, rel=0.01)

    def test_sleep_penalty_8h_no_debt(self) -> None:
        """8h sleep -> no penalty."""
        log = _log(
            sleep=_sleep(),
            energy_readings=[_energy(EnergyLevel.HIGH)],
        )
        assert compute_energy_score(log) == 100.0

    def test_sleep_penalty_6h(self) -> None:
        """6h sleep -> (8-6) * 10 = 20 penalty."""
        log = _log(
            sleep=_sleep(bedtime=time(0, 0), wake_time=time(6, 0)),
            energy_readings=[_energy(EnergyLevel.HIGH)],
        )
        # 100 - 20 = 80
        assert compute_energy_score(log) == 80.0

    def test_sleep_penalty_4h(self) -> None:
        """4h sleep -> (8-4) * 10 = 40 penalty."""
        log = _log(
            sleep=_sleep(bedtime=time(2, 0), wake_time=time(6, 0)),
            energy_readings=[_energy(EnergyLevel.HIGH)],
        )
        # 100 - 40 = 60
        assert compute_energy_score(log) == 60.0

    def test_sleep_penalty_0h_clamped(self) -> None:
        """Sleep 0h would exceed penalty — result clamped to 0."""
        log = _log(
            sleep=_sleep(bedtime=time(6, 0), wake_time=time(6, 0)),
            energy_readings=[_energy(EnergyLevel.HIGH)],
        )
        # 100 - 80 = 20, no clamp needed
        assert compute_energy_score(log) == 20.0

    def test_sleep_penalty_full_overshoot(self) -> None:
        """Sleep at 0h with L reading: 30 - 80 -> clamped to 0."""
        log = _log(
            sleep=_sleep(bedtime=time(6, 0), wake_time=time(6, 0)),
            energy_readings=[_energy(EnergyLevel.LOW)],
        )
        # 30 - 80 = -50 -> max(0, ...) = 0
        assert compute_energy_score(log) == 0.0

    def test_no_sleep_no_penalty(self) -> None:
        """Without a sleep record, no penalty is applied."""
        log = _log(energy_readings=[_energy(EnergyLevel.HIGH)])
        assert compute_energy_score(log) == 100.0


# ===========================================================================
# compute_productivity_score
# ===========================================================================


class TestComputeProductivityScore:
    """:func:`compute_productivity_score` computes the productivity composite."""

    def test_zero_tasks_zero_score(self) -> None:
        log = _log(tasks_completed=0, tasks_created=0)
        # base = 0/1 * 60 = 0; time_bonus = 0; focus_bonus = 0
        assert compute_productivity_score(log) == 0.0

    def test_high_tasks_full_base(self) -> None:
        """10 of 10 tasks -> base = 60."""
        log = _log(tasks_completed=10, tasks_created=10)
        assert compute_productivity_score(log) == 60.0

    def test_high_tasks_with_partial_time(self) -> None:
        """10 of 10 tasks, 4h tracked -> 60 + 12.5 + 0 = 72.5."""
        log = _log(
            tasks_completed=10, tasks_created=10, time_tracked_hours=4.0
        )
        assert compute_productivity_score(log) == 72.5

    def test_time_bonus_capped_at_25(self) -> None:
        """8h tracked -> time_bonus = 25 (max)."""
        log = _log(
            tasks_completed=10, tasks_created=10, time_tracked_hours=8.0
        )
        assert compute_productivity_score(log) == 85.0  # 60 + 25

    def test_time_bonus_above_8h_clamps(self) -> None:
        """12h tracked -> time_bonus still = 25 (clamped)."""
        log = _log(
            tasks_completed=10, tasks_created=10, time_tracked_hours=12.0
        )
        assert compute_productivity_score(log) == 85.0

    def test_focus_bonus_full(self) -> None:
        """8 pomodoros -> focus_bonus = 15 (max)."""
        log = _log(
            tasks_completed=10, tasks_created=10, pomodoros=8
        )
        assert compute_productivity_score(log) == 75.0  # 60 + 0 + 15

    def test_focus_bonus_above_8_clamps(self) -> None:
        """12 pomodoros -> focus_bonus = 15 (clamped)."""
        log = _log(
            tasks_completed=10, tasks_created=10, pomodoros=12
        )
        assert compute_productivity_score(log) == 75.0

    def test_full_max_score(self) -> None:
        """10/10 + 8h + 8 pomodoros = 60 + 25 + 15 = 100."""
        log = _log(
            tasks_completed=10, tasks_created=10,
            time_tracked_hours=8.0, pomodoros=8,
        )
        assert compute_productivity_score(log) == 100.0

    def test_completion_rate_50_percent(self) -> None:
        """5 of 10 -> base = 30."""
        log = _log(tasks_completed=5, tasks_created=10)
        assert compute_productivity_score(log) == 30.0

    def test_overshoot_completion_not_clamped(self) -> None:
        """15 completed of 10 created -> base = 90 (formula does not clamp)."""
        log = _log(tasks_completed=15, tasks_created=10)
        # The PRD-05 formula has no clamp on the base term. The 25+15
        # bonuses are clamped, but the base is not — over-completion
        # is rewarded (e.g. retroactive tasks). Result: 90.
        assert compute_productivity_score(log) == 90.0

    def test_zero_created_divide_by_one_protection(self) -> None:
        """tasks_created=0 -> max(0, 1) = 1, base = 0."""
        log = _log(tasks_completed=0, tasks_created=0)
        assert compute_productivity_score(log) == 0.0


# ===========================================================================
# compute_health_score
# ===========================================================================


class TestComputeHealthScore:
    """:func:`compute_health_score` computes the health composite."""

    def test_no_sleep_no_exercise_no_water(self) -> None:
        log = _log()
        assert compute_health_score(log) == 0.0

    def test_exercise_only(self) -> None:
        """Exercise alone -> 25."""
        log = _log(exercise_done=True)
        assert compute_health_score(log) == 25.0

    def test_water_full(self) -> None:
        """8 glasses of water -> 15 (max water contribution)."""
        log = _log(water_glasses=8)
        assert compute_health_score(log) == 15.0

    def test_water_above_8_clamps(self) -> None:
        """12 glasses -> 15 (clamped)."""
        log = _log(water_glasses=12)
        assert compute_health_score(log) == 15.0

    def test_water_partial(self) -> None:
        """4 of 8 glasses -> 7.5."""
        log = _log(water_glasses=4)
        assert compute_health_score(log) == 7.5

    def test_sleep_quality_8_no_exercise_no_water(self) -> None:
        """Sleep quality 8 -> 8 * 10 = 80 sleep_score; * 0.5 = 40."""
        log = _log(sleep=_sleep(quality=8))
        assert compute_health_score(log) == 40.0

    def test_sleep_quality_10_perfect(self) -> None:
        """Sleep quality 10 -> 100 sleep_score; * 0.5 = 50."""
        log = _log(sleep=_sleep(quality=10))
        assert compute_health_score(log) == 50.0

    def test_full_health(self) -> None:
        """Sleep 8 + exercise + 8 water = 40 + 25 + 15 = 80."""
        log = _log(
            sleep=_sleep(quality=8),
            exercise_done=True,
            water_glasses=8,
        )
        assert compute_health_score(log) == 80.0


# ===========================================================================
# compute_overall_score
# ===========================================================================


class TestComputeOverallScore:
    """:func:`compute_overall_score` weights the three sub-scores (ADR-004)."""

    def test_perfect_scores(self) -> None:
        assert compute_overall_score(100, 100, 100) == 100.0

    def test_zero_scores(self) -> None:
        assert compute_overall_score(0, 0, 0) == 0.0

    def test_only_productivity(self) -> None:
        """100 prod, 0 elsewhere -> 0.4 * 100 = 40."""
        assert compute_overall_score(0, 100, 0) == 40.0

    def test_only_energy(self) -> None:
        """100 energy, 0 elsewhere -> 0.3 * 100 = 30."""
        assert compute_overall_score(100, 0, 0) == 30.0

    def test_only_health(self) -> None:
        """100 health, 0 elsewhere -> 0.3 * 100 = 30."""
        assert compute_overall_score(0, 0, 100) == 30.0

    def test_weighted_average(self) -> None:
        """80*0.3 + 70*0.4 + 90*0.3 = 24 + 28 + 27 = 79."""
        assert compute_overall_score(80, 70, 90) == 79.0

    def test_clamping_negative_clamps_to_zero(self) -> None:
        """Negative inputs are clamped to 0."""
        assert compute_overall_score(-10, 50, 50) == 35.0  # 0*0.3+50*0.4+50*0.3

    def test_clamping_above_100_clamps(self) -> None:
        """Inputs above 100 are clamped to 100."""
        assert compute_overall_score(150, 150, 150) == 100.0

    @pytest.mark.parametrize(
        ("energy", "prod", "health", "expected"),
        [
            (100, 100, 100, 100.0),
            (0, 0, 0, 0.0),
            (50, 50, 50, 50.0),
            (80, 70, 90, 79.0),
        ],
    )
    def test_parametric(self, energy: float, prod: float, health: float, expected: float) -> None:
        assert compute_overall_score(energy, prod, health) == pytest.approx(expected, rel=0.01)


# ===========================================================================
# compute_sleep_debt
# ===========================================================================


class TestComputeSleepDebt:
    """:func:`compute_sleep_debt` returns hours of sleep deficit."""

    def test_eight_hours_no_debt(self) -> None:
        log = _log(sleep=_sleep())
        assert compute_sleep_debt(log) == 0.0

    def test_six_hours_two_debt(self) -> None:
        log = _log(sleep=_sleep(bedtime=time(0, 0), wake_time=time(6, 0)))
        assert compute_sleep_debt(log) == 2.0

    def test_zero_hours_eight_debt(self) -> None:
        log = _log(sleep=_sleep(bedtime=time(6, 0), wake_time=time(6, 0)))
        assert compute_sleep_debt(log) == 8.0

    def test_no_sleep_record_eight_debt(self) -> None:
        """No sleep -> assume full target deficit (8h)."""
        log = _log()
        assert compute_sleep_debt(log) == 8.0

    def test_oversleep_no_debt(self) -> None:
        """More than 8h -> 0 debt (capped at 0)."""
        log = _log(sleep=_sleep(bedtime=time(20, 0), wake_time=time(6, 0)))
        # 10h sleep -> max(0, 8-10) = 0
        assert compute_sleep_debt(log) == 0.0


# ===========================================================================
# generate_alerts
# ===========================================================================


class TestGenerateAlerts:
    """:func:`generate_alerts` emits alerts per PRD-05 §5 thresholds."""

    def test_empty_when_all_ok(self) -> None:
        """No sleep debt, full habit compliance, full productivity."""
        alerts = generate_alerts(0.0, 100.0, 100.0, now=_DT)
        assert alerts == []

    def test_sleep_debt_warning(self) -> None:
        """4.5h debt -> WARNING."""
        alerts = generate_alerts(4.5, 100.0, 100.0, now=_DT)
        assert len(alerts) == 1
        assert alerts[0].level is AlertLevel.WARNING
        assert alerts[0].metric == "sleep_debt_hours"
        assert alerts[0].value == 4.5
        assert alerts[0].threshold == 4.0

    def test_sleep_debt_critical(self) -> None:
        """8.5h debt -> CRITICAL."""
        alerts = generate_alerts(8.5, 100.0, 100.0, now=_DT)
        assert len(alerts) == 1
        assert alerts[0].level is AlertLevel.CRITICAL
        assert alerts[0].value == 8.5
        assert alerts[0].threshold == 8.0

    def test_sleep_debt_at_threshold_4_not_warning(self) -> None:
        """Exactly 4h debt -> not triggered (strict >)."""
        alerts = generate_alerts(4.0, 100.0, 100.0, now=_DT)
        assert alerts == []

    def test_sleep_debt_just_above_4(self) -> None:
        alerts = generate_alerts(4.01, 100.0, 100.0, now=_DT)
        assert len(alerts) == 1
        assert alerts[0].level is AlertLevel.WARNING

    def test_habit_compliance_warning(self) -> None:
        """55% compliance -> WARNING (below 60)."""
        alerts = generate_alerts(0.0, 55.0, 100.0, now=_DT)
        assert len(alerts) == 1
        assert alerts[0].level is AlertLevel.WARNING
        assert alerts[0].metric == "habit_compliance_pct"
        assert alerts[0].value == 55.0
        assert alerts[0].threshold == 60.0

    def test_habit_compliance_critical(self) -> None:
        """30% compliance -> CRITICAL (below 40)."""
        alerts = generate_alerts(0.0, 30.0, 100.0, now=_DT)
        assert len(alerts) == 1
        assert alerts[0].level is AlertLevel.CRITICAL
        assert alerts[0].threshold == 40.0

    def test_habit_compliance_at_60_not_warning(self) -> None:
        alerts = generate_alerts(0.0, 60.0, 100.0, now=_DT)
        assert alerts == []

    def test_productivity_warning(self) -> None:
        """30 score -> WARNING (below 40)."""
        alerts = generate_alerts(0.0, 100.0, 30.0, now=_DT)
        assert len(alerts) == 1
        assert alerts[0].level is AlertLevel.WARNING
        assert alerts[0].metric == "productivity_score"
        assert alerts[0].value == 30.0
        assert alerts[0].threshold == 40.0

    def test_productivity_critical(self) -> None:
        """20 score -> CRITICAL (below 25)."""
        alerts = generate_alerts(0.0, 100.0, 20.0, now=_DT)
        assert len(alerts) == 1
        assert alerts[0].level is AlertLevel.CRITICAL
        assert alerts[0].threshold == 25.0

    def test_multiple_alerts(self) -> None:
        """All three criticals -> 3 alerts."""
        alerts = generate_alerts(10.0, 20.0, 10.0, now=_DT)
        assert len(alerts) == 3
        levels = {a.level for a in alerts}
        assert levels == {AlertLevel.CRITICAL}

    def test_alerts_have_unique_ids(self) -> None:
        """Each alert gets a unique id."""
        a1 = generate_alerts(5.0, 100.0, 100.0, now=_DT)
        a2 = generate_alerts(5.0, 100.0, 100.0, now=_DT)
        assert a1[0].id != a2[0].id

    def test_alerts_carry_now_timestamp(self) -> None:
        alerts = generate_alerts(5.0, 100.0, 100.0, now=_DT)
        assert alerts[0].created_at == _DT

    def test_default_now_uses_datetime_now(self) -> None:
        """When ``now`` is not provided, ``datetime.now()`` is used."""
        alerts = generate_alerts(5.0, 100.0, 100.0)
        assert isinstance(alerts[0].created_at, datetime)


# ===========================================================================
# generate_recommendations
# ===========================================================================


class TestGenerateRecommendations:
    """:func:`generate_recommendations` returns actionable strings."""

    def test_empty_when_all_scores_at_floor(self) -> None:
        """50, 50, 50 -> overall 50 -> no recommendation."""
        recs = generate_recommendations(50.0, 50.0, 50.0, 50.0)
        assert recs == []

    def test_low_energy_recommendation(self) -> None:
        recs = generate_recommendations(40.0, 60.0, 60.0, 53.0)
        assert "Considere dormir mais cedo hoje" in recs

    def test_low_productivity_recommendation(self) -> None:
        recs = generate_recommendations(60.0, 30.0, 60.0, 45.0)
        assert "Investigar bloqueios de produtividade" in recs

    def test_low_health_recommendation(self) -> None:
        recs = generate_recommendations(60.0, 60.0, 40.0, 51.0)
        assert "Revisar habitos de saude (agua, exercicio, sono)" in recs

    def test_excellent_recommendation(self) -> None:
        recs = generate_recommendations(90.0, 90.0, 90.0, 90.0)
        assert "Excelente! Manter a rotina" in recs

    def test_recovery_recommendation(self) -> None:
        recs = generate_recommendations(20.0, 20.0, 20.0, 20.0)
        assert "Considerar dia de recuperacao" in recs

    def test_multiple_recommendations(self) -> None:
        recs = generate_recommendations(40.0, 30.0, 40.0, 35.0)
        # Low energy + low productivity + low health + overall < 30? 35 not < 30
        assert "Considere dormir mais cedo hoje" in recs
        assert "Investigar bloqueios de produtividade" in recs
        assert "Revisar habitos de saude (agua, exercicio, sono)" in recs
        # 35 not < 30, so no recovery rec

    def test_recommendation_lengths(self) -> None:
        """All recommendations fit within the 200-char cap."""
        recs = generate_recommendations(0.0, 0.0, 0.0, 0.0)
        for rec in recs:
            assert len(rec) <= 200


# ===========================================================================
# consolidate_daily — end-to-end
# ===========================================================================


class TestConsolidateDaily:
    """:func:`consolidate_daily` orchestrates the full consolidation."""

    def test_full_consolidation(self) -> None:
        log = _log(
            sleep=_sleep(quality=8),
            energy_readings=[
                _energy(EnergyLevel.HIGH, energy_id="erg_h"),
                _energy(EnergyLevel.MEDIUM, energy_id="erg_m", context="afternoon"),
            ],
            tasks_completed=5,
            tasks_created=10,
            time_tracked_hours=4.0,
            pomodoros=4,
            exercise_done=True,
            water_glasses=6,
            habits_done=8,
            habits_total=10,
        )
        c = consolidate_daily(log, now=_DT)
        assert isinstance(c, DailyConsolidation)
        assert c.daily_log_id == log.id
        assert 0.0 <= c.energy_score <= 100.0
        assert 0.0 <= c.productivity_score <= 100.0
        assert 0.0 <= c.health_score <= 100.0
        assert c.sleep_debt_hours == 0.0
        # The overall_score property should match the formula
        assert c.overall_score == pytest.approx(
            c.energy_score * 0.3 + c.productivity_score * 0.4 + c.health_score * 0.3
        )
        # created_at is from the `now` kwarg
        assert c.created_at == _DT

    def test_no_sleep_record(self) -> None:
        log = _log(
            energy_readings=[_energy(EnergyLevel.HIGH)],
            tasks_completed=10,
            tasks_created=10,
        )
        c = consolidate_daily(log, now=_DT)
        # sleep_debt = 8 (worst case)
        assert c.sleep_debt_hours == 8.0
        # Energy score has no penalty
        assert c.energy_score == 100.0
        # Health = 0 (no sleep, no exercise, no water)
        assert c.health_score == 0.0

    def test_no_energy_readings(self) -> None:
        log = _log(
            sleep=_sleep(quality=8),
            tasks_completed=5,
            tasks_created=10,
        )
        c = consolidate_daily(log, now=_DT)
        assert c.energy_score == 0.0

    def test_excellent_day_no_alerts(self) -> None:
        """A perfect day yields no alerts (but may have recommendations)."""
        log = _log(
            sleep=_sleep(quality=10, bedtime=time(21, 0), wake_time=time(6, 0)),
            energy_readings=[
                _energy(EnergyLevel.HIGH, energy_id="erg_h"),
            ],
            tasks_completed=10,
            tasks_created=10,
            time_tracked_hours=8.0,
            pomodoros=8,
            exercise_done=True,
            water_glasses=8,
            habits_done=10,
            habits_total=10,
        )
        c = consolidate_daily(log, now=_DT)
        assert c.alerts == []
        # Overall should be very high
        assert c.overall_score >= 85.0

    def test_critical_day_triggers_alerts(self) -> None:
        """A bad day yields multiple alerts."""
        log = _log(
            sleep=_sleep(bedtime=time(6, 0), wake_time=time(6, 0), quality=1),
            energy_readings=[_energy(EnergyLevel.LOW)],
            tasks_completed=1,
            tasks_created=20,
            time_tracked_hours=0.0,
            pomodoros=0,
            exercise_done=False,
            water_glasses=0,
            habits_done=2,
            habits_total=10,
        )
        c = consolidate_daily(log, now=_DT)
        # Should have at least 2 alerts (sleep + compliance)
        assert len(c.alerts) >= 2
        levels = {a.level for a in c.alerts}
        assert AlertLevel.CRITICAL in levels or AlertLevel.WARNING in levels

    def test_consolidate_uses_log_date_by_default(self) -> None:
        log = _log()
        c = consolidate_daily(log, now=_DT)
        assert c.date == log.date

    def test_consolidate_uses_explicit_date(self) -> None:
        log = _log()
        new_date = date(2026, 6, 10)
        c = consolidate_daily(log, on_date=new_date, now=_DT)
        assert c.date == new_date

    def test_consolidate_recommendations_attached(self) -> None:
        log = _log(
            sleep=_sleep(bedtime=time(6, 0), wake_time=time(6, 0)),
            energy_readings=[_energy(EnergyLevel.LOW)],
        )
        c = consolidate_daily(log, now=_DT)
        # Energy very low (sleep penalty dominates) -> recommendation
        assert len(c.recommendations) > 0


# ===========================================================================
# Consolidator class
# ===========================================================================


class TestConsolidator:
    """:class:`Consolidator` is a namespace class with all static methods."""

    def test_consolidate_delegates(self) -> None:
        log = _log(
            sleep=_sleep(),
            energy_readings=[_energy(EnergyLevel.HIGH)],
        )
        a = Consolidator.consolidate(log, now=_DT)
        b = consolidate_daily(log, now=_DT)
        # Same shape (different ids since they're regenerated).
        assert a.daily_log_id == b.daily_log_id
        assert a.energy_score == b.energy_score
        assert a.productivity_score == b.productivity_score
        assert a.health_score == b.health_score

    def test_compute_energy_delegates(self) -> None:
        log = _log(energy_readings=[_energy(EnergyLevel.HIGH)])
        assert Consolidator.compute_energy(log) == compute_energy_score(log) == 100.0

    def test_compute_productivity_delegates(self) -> None:
        log = _log(tasks_completed=10, tasks_created=10, pomodoros=4)
        assert Consolidator.compute_productivity(log) == compute_productivity_score(log)

    def test_compute_health_delegates(self) -> None:
        log = _log(exercise_done=True, water_glasses=8)
        assert Consolidator.compute_health(log) == compute_health_score(log)

    def test_compute_overall_delegates(self) -> None:
        assert Consolidator.compute_overall(80, 70, 90) == compute_overall_score(80, 70, 90)

    def test_compute_sleep_debt_delegates(self) -> None:
        log = _log(sleep=_sleep(bedtime=time(0, 0), wake_time=time(6, 0)))
        assert Consolidator.compute_sleep_debt(log) == compute_sleep_debt(log) == 2.0


# ===========================================================================
# End-to-end scenarios
# ===========================================================================


class TestEndToEndScenarios:
    """Realistic end-to-end consolidation scenarios."""

    def test_perfect_day(self) -> None:
        log = _log(
            sleep=_sleep(quality=10, bedtime=time(21, 0), wake_time=time(6, 0)),
            energy_readings=[
                _energy(EnergyLevel.HIGH, energy_id="erg_m1"),
                _energy(EnergyLevel.HIGH, energy_id="erg_a1", context="afternoon"),
                _energy(EnergyLevel.HIGH, energy_id="erg_e1", context="evening"),
            ],
            tasks_completed=10,
            tasks_created=10,
            time_tracked_hours=8.0,
            pomodoros=8,
            exercise_done=True,
            water_glasses=10,
            habits_done=10,
            habits_total=10,
        )
        c = consolidate_daily(log, now=_DT)
        assert c.overall_score >= 85.0
        assert c.alerts == []
        # Excellent recommendation
        assert any("Excelente" in r for r in c.recommendations)

    def test_terrible_day(self) -> None:
        log = _log(
            sleep=_sleep(bedtime=time(6, 0), wake_time=time(6, 0), quality=1),
            energy_readings=[_energy(EnergyLevel.LOW)],
            tasks_completed=0,
            tasks_created=10,
            time_tracked_hours=0.0,
            pomodoros=0,
            exercise_done=False,
            water_glasses=0,
            habits_done=1,
            habits_total=10,
        )
        c = consolidate_daily(log, now=_DT)
        assert c.overall_score < 30.0
        # Sleep debt + habit compliance + productivity alerts
        assert len(c.alerts) >= 3
        # Recovery recommendation
        assert any("recuperacao" in r for r in c.recommendations)

    def test_balanced_day(self) -> None:
        log = _log(
            sleep=_sleep(quality=7),
            energy_readings=[
                _energy(EnergyLevel.MEDIUM, energy_id="erg_m1"),
                _energy(EnergyLevel.MEDIUM, energy_id="erg_a1", context="afternoon"),
            ],
            tasks_completed=6,
            tasks_created=10,
            time_tracked_hours=5.0,
            pomodoros=4,
            exercise_done=True,
            water_glasses=6,
            habits_done=7,
            habits_total=10,
        )
        c = consolidate_daily(log, now=_DT)
        # 50-70 range expected
        assert 40.0 <= c.overall_score <= 80.0
