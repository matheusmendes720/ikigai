"""Comprehensive unit tests for ``operational.entities.metric``.

Covers:

* :class:`SleepRecord` — creation, duration computation (with and without
  midnight crossing), field ranges, source literal, immutability,
  unknown-field rejection.
* :class:`EnergyReading` — creation, enum/literal fields, optional
  fields, immutability.
* :class:`DailyLog` — creation, computed fields (habit compliance, avg
  energy, peak energy time, daily score), mutable ``updated_at``
  auto-management, ``extra="forbid"``, field validation, mutable
  updates via ``touch()``.

All tests are pure unit tests (no I/O). Markers: implicit ``unit``.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import ClassVar

import pytest
from pydantic import ValidationError

from operational.entities.metric import DailyLog, EnergyReading, SleepRecord
from operational.enums import EnergyLevel


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


_DT: ClassVar[datetime] = datetime(2026, 6, 7, 8, 0)
_DATE: ClassVar[date] = date(2026, 6, 7)


def _make_sleep(
    *,
    bedtime: time = time(22, 0),
    wake_time: time = time(6, 0),
    quality: int = 8,
    date_: date = _DATE,
    sleep_id: str = "slp_test",
) -> SleepRecord:
    """Build a minimal :class:`SleepRecord` for tests."""
    return SleepRecord(
        id=sleep_id,
        date=date_,
        bedtime=bedtime,
        wake_time=wake_time,
        quality_score=quality,
        created_at=_DT,
    )


def _make_energy(  # noqa: PLR0913
    *,
    level: EnergyLevel = EnergyLevel.MEDIUM,
    context: str = "morning",
    date_: date = _DATE,
    energy_id: str = "erg_test",
    mood: int | None = None,
    focus: int | None = None,
    stress: int | None = None,
) -> EnergyReading:
    """Build a minimal :class:`EnergyReading` for tests."""
    return EnergyReading(
        id=energy_id,
        date=date_,
        timestamp=_DT,
        level=level,
        context=context,  # type: ignore[arg-type]
        mood=mood,
        focus=focus,
        stress=stress,
        created_at=_DT,
    )


# ---------------------------------------------------------------------------
# SleepRecord
# ---------------------------------------------------------------------------


class TestSleepRecord:
    """Specific tests for :class:`SleepRecord`."""

    def test_create_minimal_sleep_record(self) -> None:
        """All optional fields use their default values."""
        sr = _make_sleep()
        assert sr.id == "slp_test"
        assert sr.date == _DATE
        assert sr.bedtime == time(22, 0)
        assert sr.wake_time == time(6, 0)
        assert sr.quality_score == 8
        assert sr.deep_sleep_pct is None
        assert sr.rem_sleep_pct is None
        assert sr.interruptions == 0
        assert sr.notes == ""
        assert sr.source == "MANUAL"
        assert sr.created_at == _DT

    def test_sleep_duration_no_midnight_cross(self) -> None:
        """22:00 → 06:00 across the same date is 8 hours."""
        sr = _make_sleep(bedtime=time(22, 0), wake_time=time(6, 0))
        assert sr.duration_hours == 8.0

    def test_sleep_duration_midnight_cross(self) -> None:
        """23:30 → 07:00 crossing midnight is 7.5 hours."""
        sr = _make_sleep(bedtime=time(23, 30), wake_time=time(7, 0))
        assert sr.duration_hours == 7.5

    def test_sleep_duration_same_day(self) -> None:
        """01:00 → 09:00 (no midnight crossing) is 8 hours."""
        sr = _make_sleep(bedtime=time(1, 0), wake_time=time(9, 0))
        assert sr.duration_hours == 8.0

    def test_sleep_duration_nap_30_minutes(self) -> None:
        """14:00 → 14:30 is 0.5 hours."""
        sr = _make_sleep(bedtime=time(14, 0), wake_time=time(14, 30))
        assert sr.duration_hours == 0.5

    def test_sleep_duration_night_shift(self) -> None:
        """02:00 (yesterday) → 10:00 (today) crossing midnight twice = 8h."""
        sr = _make_sleep(
            date_=date(2026, 6, 7),
            bedtime=time(2, 0),
            wake_time=time(10, 0),
        )
        # wake > bed, so no midnight crossing applied -> 8 hours
        assert sr.duration_hours == 8.0

    @pytest.mark.parametrize("quality", [1, 5, 10])
    def test_sleep_quality_range_valid(self, quality: int) -> None:
        """Quality score accepts 1, 5, 10 (boundaries)."""
        sr = _make_sleep(quality=quality)
        assert sr.quality_score == quality

    @pytest.mark.parametrize("quality", [0, -1, 11, 100])
    def test_sleep_quality_range_rejected(self, quality: int) -> None:
        """Quality score rejects 0, -1, 11, 100."""
        with pytest.raises(ValidationError):
            _make_sleep(quality=quality)

    def test_sleep_deep_rem_optional(self) -> None:
        """``deep_sleep_pct`` and ``rem_sleep_pct`` are accepted."""
        sr = SleepRecord(
            id="slp_deep",
            date=_DATE,
            bedtime=time(22, 0),
            wake_time=time(6, 0),
            quality_score=8,
            deep_sleep_pct=25.0,
            rem_sleep_pct=20.0,
            created_at=_DT,
        )
        assert sr.deep_sleep_pct == 25.0
        assert sr.rem_sleep_pct == 20.0

    @pytest.mark.parametrize("pct", [-1.0, 100.1, 200.0])
    def test_sleep_deep_pct_rejected_out_of_range(self, pct: float) -> None:
        """``deep_sleep_pct`` rejects values outside [0, 100]."""
        with pytest.raises(ValidationError):
            SleepRecord(
                id="slp_x",
                date=_DATE,
                bedtime=time(22, 0),
                wake_time=time(6, 0),
                quality_score=8,
                deep_sleep_pct=pct,
                created_at=_DT,
            )

    @pytest.mark.parametrize(
        "source",
        ["MANUAL", "GARMIN", "OURA", "APPLE_HEALTH"],
    )
    def test_sleep_source_literal_accepted(self, source: str) -> None:
        """All four source literals are accepted."""
        sr = SleepRecord(
            id="slp_src",
            date=_DATE,
            bedtime=time(22, 0),
            wake_time=time(6, 0),
            quality_score=8,
            source=source,  # type: ignore[arg-type]
            created_at=_DT,
        )
        assert sr.source == source

    @pytest.mark.parametrize("source", ["FITBIT", "withings", "MANUAL_X"])
    def test_sleep_source_literal_rejected(self, source: str) -> None:
        """Unknown source values are rejected."""
        with pytest.raises(ValidationError):
            SleepRecord(
                id="slp_src_bad",
                date=_DATE,
                bedtime=time(22, 0),
                wake_time=time(6, 0),
                quality_score=8,
                source=source,  # type: ignore[arg-type]
                created_at=_DT,
            )

    def test_sleep_interruptions_default_zero(self) -> None:
        """Default interruptions is 0."""
        sr = _make_sleep()
        assert sr.interruptions == 0

    def test_sleep_interruptions_negative_rejected(self) -> None:
        """Negative interruption count is rejected."""
        with pytest.raises(ValidationError):
            SleepRecord(
                id="slp_int",
                date=_DATE,
                bedtime=time(22, 0),
                wake_time=time(6, 0),
                quality_score=8,
                interruptions=-1,
                created_at=_DT,
            )

    def test_sleep_notes_max_length_enforced(self) -> None:
        """Notes exceeding 500 chars are rejected."""
        with pytest.raises(ValidationError):
            SleepRecord(
                id="slp_notes",
                date=_DATE,
                bedtime=time(22, 0),
                wake_time=time(6, 0),
                quality_score=8,
                notes="x" * 501,
                created_at=_DT,
            )

    def test_sleep_notes_max_length_accepted(self) -> None:
        """Notes of exactly 500 chars are accepted."""
        sr = SleepRecord(
            id="slp_notes2",
            date=_DATE,
            bedtime=time(22, 0),
            wake_time=time(6, 0),
            quality_score=8,
            notes="x" * 500,
            created_at=_DT,
        )
        assert len(sr.notes) == 500

    def test_sleep_is_frozen(self) -> None:
        """``SleepRecord`` is immutable."""
        sr = _make_sleep()
        with pytest.raises(ValidationError):
            sr.quality_score = 5  # type: ignore[misc]

    def test_sleep_rejects_unknown_fields(self) -> None:
        """``extra='forbid'`` rejects unknown fields."""
        with pytest.raises(ValidationError):
            SleepRecord(
                id="slp_x",
                date=_DATE,
                bedtime=time(22, 0),
                wake_time=time(6, 0),
                quality_score=8,
                created_at=_DT,
                unknown_field="oops",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# EnergyReading
# ---------------------------------------------------------------------------


class TestEnergyReading:
    """Specific tests for :class:`EnergyReading`."""

    def test_create_energy_reading(self) -> None:
        """A minimal reading is created successfully."""
        e = _make_energy()
        assert e.id == "erg_test"
        assert e.date == _DATE
        assert e.timestamp == _DT
        assert e.level is EnergyLevel.MEDIUM
        assert e.context == "morning"
        assert e.mood is None
        assert e.focus is None
        assert e.stress is None
        assert e.notes == ""

    @pytest.mark.parametrize(
        "level",
        [EnergyLevel.HIGH, EnergyLevel.MEDIUM, EnergyLevel.LOW],
    )
    def test_energy_level_enum(self, level: EnergyLevel) -> None:
        """All three :class:`EnergyLevel` values are accepted."""
        e = _make_energy(level=level)
        assert e.level is level

    @pytest.mark.parametrize(
        "context",
        ["morning", "afternoon", "evening"],
    )
    def test_energy_context_literal(self, context: str) -> None:
        """All three context literals are accepted."""
        e = _make_energy(context=context)
        assert e.context == context

    @pytest.mark.parametrize("context", ["noon", "night", "MORNING", ""])
    def test_energy_context_literal_rejected(self, context: str) -> None:
        """Unknown context literals are rejected."""
        with pytest.raises(ValidationError):
            _make_energy(context=context)

    @pytest.mark.parametrize("mood", [1, 3, 5])
    def test_energy_mood_valid_range(self, mood: int) -> None:
        """Mood accepts 1, 3, 5."""
        e = _make_energy(mood=mood)
        assert e.mood == mood

    @pytest.mark.parametrize("mood", [0, 6, -1])
    def test_energy_mood_rejected_out_of_range(self, mood: int) -> None:
        """Mood rejects 0, 6, -1."""
        with pytest.raises(ValidationError):
            _make_energy(mood=mood)

    @pytest.mark.parametrize("focus", [1, 5, 10])
    def test_energy_focus_valid_range(self, focus: int) -> None:
        """Focus accepts 1, 5, 10."""
        e = _make_energy(focus=focus)
        assert e.focus == focus

    @pytest.mark.parametrize("focus", [0, 11, 100])
    def test_energy_focus_rejected_out_of_range(self, focus: int) -> None:
        """Focus rejects 0, 11, 100."""
        with pytest.raises(ValidationError):
            _make_energy(focus=focus)

    @pytest.mark.parametrize("stress", [1, 5, 10])
    def test_energy_stress_valid_range(self, stress: int) -> None:
        """Stress accepts 1, 5, 10."""
        e = _make_energy(stress=stress)
        assert e.stress == stress

    @pytest.mark.parametrize("stress", [0, 11, 100])
    def test_energy_stress_rejected_out_of_range(self, stress: int) -> None:
        """Stress rejects 0, 11, 100."""
        with pytest.raises(ValidationError):
            _make_energy(stress=stress)

    def test_energy_notes_max_length(self) -> None:
        """Notes max length is 500."""
        e = EnergyReading(
            id="erg_notes",
            date=_DATE,
            timestamp=_DT,
            level=EnergyLevel.HIGH,
            context="morning",
            notes="x" * 500,
            created_at=_DT,
        )
        assert len(e.notes) == 500
        # 501 chars must be rejected
        with pytest.raises(ValidationError):
            EnergyReading(
                id="erg_notes2",
                date=_DATE,
                timestamp=_DT,
                level=EnergyLevel.HIGH,
                context="morning",
                notes="x" * 501,
                created_at=_DT,
            )

    def test_energy_is_frozen(self) -> None:
        """``EnergyReading`` is immutable."""
        e = _make_energy()
        with pytest.raises(ValidationError):
            e.level = EnergyLevel.LOW  # type: ignore[misc]

    def test_energy_rejects_unknown_fields(self) -> None:
        """``extra='forbid'`` rejects unknown fields."""
        with pytest.raises(ValidationError):
            EnergyReading(
                id="erg_x",
                date=_DATE,
                timestamp=_DT,
                level=EnergyLevel.HIGH,
                context="morning",
                created_at=_DT,
                bogus="oops",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# DailyLog
# ---------------------------------------------------------------------------


class TestDailyLog:
    """Specific tests for :class:`DailyLog`."""

    def test_create_minimal_daily_log(self) -> None:
        """A minimal :class:`DailyLog` is created with sensible defaults."""
        log = DailyLog(
            id="day_test",
            date=_DATE,
            created_at=_DT,
        )
        assert log.sleep is None
        assert log.energy_readings == []
        assert log.tasks_completed == 0
        assert log.tasks_created == 0
        assert log.time_tracked_hours == 0.0
        assert log.focus_sessions == 0
        assert log.habits_done == 0
        assert log.habits_total == 0
        assert log.study_minutes == 0
        assert log.pomodoros == 0
        assert log.exercise_done is False
        assert log.exercise_minutes == 0
        assert log.water_glasses == 0
        assert log.meals_logged == 0
        assert log.notes == ""
        assert log.mood_morning is None
        assert log.mood_evening is None
        # created_at is preserved, updated_at is auto-set
        assert log.created_at == _DT
        assert log.updated_at is not None

    # ---- habit_compliance_pct -------------------------------------------

    @pytest.mark.parametrize(
        ("done", "total", "expected"),
        [
            (0, 0, 0.0),
            (0, 4, 0.0),
            (1, 4, 25.0),
            (2, 4, 50.0),
            (3, 4, 75.0),
            (4, 4, 100.0),
            (5, 10, 50.0),
            (10, 10, 100.0),
        ],
    )
    def test_daily_log_habit_compliance_pct(
        self, done: int, total: int, expected: float,
    ) -> None:
        """``habit_compliance_pct`` is ``done/total * 100``."""
        log = DailyLog(
            id="day_hc",
            date=_DATE,
            habits_done=done,
            habits_total=total,
            created_at=_DT,
        )
        assert log.habit_compliance_pct == pytest.approx(expected)

    def test_daily_log_habit_compliance_zero_total(self) -> None:
        """``habits_total == 0`` returns 0.0 (no division by zero)."""
        log = DailyLog(
            id="day_zero",
            date=_DATE,
            habits_done=0,
            habits_total=0,
            created_at=_DT,
        )
        assert log.habit_compliance_pct == 0.0

    # ---- avg_energy mapping --------------------------------------------

    def test_daily_log_avg_energy_mapping_high(self) -> None:
        """A single HIGH reading yields avg_energy = 100."""
        log = DailyLog(
            id="day_h",
            date=_DATE,
            energy_readings=[_make_energy(level=EnergyLevel.HIGH)],
            created_at=_DT,
        )
        assert log.avg_energy == 100.0

    def test_daily_log_avg_energy_mapping_medium(self) -> None:
        """A single MEDIUM reading yields avg_energy = 60."""
        log = DailyLog(
            id="day_m",
            date=_DATE,
            energy_readings=[_make_energy(level=EnergyLevel.MEDIUM)],
            created_at=_DT,
        )
        assert log.avg_energy == 60.0

    def test_daily_log_avg_energy_mapping_low(self) -> None:
        """A single LOW reading yields avg_energy = 30."""
        log = DailyLog(
            id="day_l",
            date=_DATE,
            energy_readings=[_make_energy(level=EnergyLevel.LOW)],
            created_at=_DT,
        )
        assert log.avg_energy == 30.0

    def test_daily_log_avg_energy_mixed(self) -> None:
        """Mixed levels produce a weighted average (H+M+L) / 3 = 63.33."""
        log = DailyLog(
            id="day_mix",
            date=_DATE,
            energy_readings=[
                _make_energy(level=EnergyLevel.HIGH, energy_id="erg_mix_h"),
                _make_energy(level=EnergyLevel.MEDIUM, energy_id="erg_mix_m"),
                _make_energy(level=EnergyLevel.LOW, energy_id="erg_mix_l"),
            ],
            created_at=_DT,
        )
        assert log.avg_energy == pytest.approx(63.333333333333336)

    def test_daily_log_avg_energy_no_readings(self) -> None:
        """No readings → ``avg_energy`` is ``None``."""
        log = DailyLog(
            id="day_empty",
            date=_DATE,
            energy_readings=[],
            created_at=_DT,
        )
        assert log.avg_energy is None

    # ---- peak_energy_time ------------------------------------------------

    def test_daily_log_peak_energy_time_morning(self) -> None:
        """Highest average in 'morning' yields 'morning'."""
        log = DailyLog(
            id="day_peak_m",
            date=_DATE,
            energy_readings=[
                _make_energy(
                    level=EnergyLevel.HIGH, context="morning", energy_id="erg_pk_mh",
                ),
                _make_energy(
                    level=EnergyLevel.LOW, context="afternoon", energy_id="erg_pk_al",
                ),
                _make_energy(
                    level=EnergyLevel.LOW, context="evening", energy_id="erg_pk_el",
                ),
            ],
            created_at=_DT,
        )
        assert log.peak_energy_time == "morning"

    def test_daily_log_peak_energy_time_afternoon(self) -> None:
        """Highest average in 'afternoon' yields 'afternoon'."""
        log = DailyLog(
            id="day_peak_a",
            date=_DATE,
            energy_readings=[
                _make_energy(
                    level=EnergyLevel.LOW, context="morning", energy_id="erg_pk_aml",
                ),
                _make_energy(
                    level=EnergyLevel.HIGH, context="afternoon", energy_id="erg_pk_ah",
                ),
                _make_energy(
                    level=EnergyLevel.LOW, context="evening", energy_id="erg_pk_aev",
                ),
            ],
            created_at=_DT,
        )
        assert log.peak_energy_time == "afternoon"

    def test_daily_log_peak_energy_time_evening(self) -> None:
        """Highest average in 'evening' yields 'evening'."""
        log = DailyLog(
            id="day_peak_e",
            date=_DATE,
            energy_readings=[
                _make_energy(
                    level=EnergyLevel.LOW, context="morning", energy_id="erg_pk_eml",
                ),
                _make_energy(
                    level=EnergyLevel.LOW, context="afternoon", energy_id="erg_pk_eal",
                ),
                _make_energy(
                    level=EnergyLevel.HIGH, context="evening", energy_id="erg_pk_eh",
                ),
            ],
            created_at=_DT,
        )
        assert log.peak_energy_time == "evening"

    def test_daily_log_peak_energy_time_no_readings(self) -> None:
        """No readings → ``peak_energy_time`` is ``None``."""
        log = DailyLog(
            id="day_peak_none",
            date=_DATE,
            energy_readings=[],
            created_at=_DT,
        )
        assert log.peak_energy_time is None

    # ---- daily_score -----------------------------------------------------

    def test_daily_log_daily_score_no_energy(self) -> None:
        """``daily_score`` is ``None`` when no energy readings exist."""
        log = DailyLog(
            id="day_ds0",
            date=_DATE,
            energy_readings=[],
            created_at=_DT,
        )
        assert log.daily_score is None

    def test_daily_log_daily_score_no_sleep(self) -> None:
        """``daily_score`` with energy but no sleep record (sleep=None branch)."""
        log = DailyLog(
            id="day_no_sleep",
            date=_DATE,
            sleep=None,
            energy_readings=[_make_energy(level=EnergyLevel.MEDIUM)],
            tasks_completed=4,
            tasks_created=8,
            pomodoros=2,
            exercise_done=False,
            water_glasses=2,
            created_at=_DT,
        )
        # energy: 60 (MEDIUM), no sleep => no penalty => 60
        # productivity: 4/8*60=30 + 0*25=0 + 2/8*15=3.75 = 33.75
        # health: sleep_score=0*0.5=0 + exercise=0 + water=2/8*15=3.75 = 3.75
        # daily = 60*0.3 + 33.75*0.4 + 3.75*0.3 = 18 + 13.5 + 1.125 = 32.625
        assert log.daily_score == pytest.approx(32.625)

    def test_daily_log_daily_score_known_formula(self) -> None:
        """``daily_score`` is the weighted average E/P/H."""
        sleep = _make_sleep(bedtime=time(22, 0), wake_time=time(6, 0))
        log = DailyLog(
            id="day_ds",
            date=_DATE,
            sleep=sleep,
            energy_readings=[_make_energy(level=EnergyLevel.HIGH)],
            tasks_completed=4,
            tasks_created=8,
            time_tracked_hours=4.0,
            pomodoros=4,
            exercise_done=True,
            water_glasses=4,
            created_at=_DT,
        )
        # energy: 100 (HIGH), sleep=8h, no penalty => 100
        # productivity: 4/8*60=30 + 4/8*25=12.5 + 4/8*15=7.5 = 50.0
        # health: sleep_score=80*0.5=40 + exercise=25 + water=4/8*15=7.5 = 72.5
        # daily = 100*0.3 + 50*0.4 + 72.5*0.3 = 30 + 20 + 21.75 = 71.75
        assert log.daily_score == pytest.approx(71.75)

    def test_daily_log_daily_score_with_sleep_debt_penalty(self) -> None:
        """Sleep debt penalises the energy component by 10/h."""
        # 4h sleep => debt = 4h => penalty = 40
        sleep = _make_sleep(bedtime=time(2, 0), wake_time=time(6, 0))
        log = DailyLog(
            id="day_sd",
            date=_DATE,
            sleep=sleep,
            energy_readings=[_make_energy(level=EnergyLevel.HIGH)],
            created_at=_DT,
        )
        # Expected: energy=60 (HIGH - 40 sleep-debt penalty),
        # productivity=0 (no tasks/time/pomodoros), health=40
        # (sleep_score*0.5 only). daily = 60*0.3 + 0*0.4 + 40*0.3 = 30.0
        assert log.daily_score == pytest.approx(30.0)

    def test_daily_log_daily_score_zero_state(self) -> None:
        """All-zero day with no sleep, no readings, no tasks."""
        log = DailyLog(
            id="day_zero",
            date=_DATE,
            created_at=_DT,
        )
        # No readings -> None
        assert log.daily_score is None

    def test_daily_log_daily_score_health_only(self) -> None:
        """With only LOW energy and full health day, score is bounded."""
        log = DailyLog(
            id="day_h",
            date=_DATE,
            sleep=_make_sleep(),
            energy_readings=[_make_energy(level=EnergyLevel.LOW)],
            tasks_completed=8,
            tasks_created=8,
            time_tracked_hours=8.0,
            pomodoros=8,
            exercise_done=True,
            water_glasses=8,
            created_at=_DT,
        )
        # energy = 30 (no sleep debt penalty because sleep=8h)
        # productivity = 8/8*60=60 + 8/8*25=25 + 8/8*15=15 = 100
        # health = 80*0.5=40 + 25 + 8/8*15=15 = 80
        # daily = 30*0.3 + 100*0.4 + 80*0.3 = 9 + 40 + 24 = 73
        assert log.daily_score == pytest.approx(73.0)

    # ---- updated_at auto-management ------------------------------------

    def test_daily_log_updated_at_auto_set(self) -> None:
        """``updated_at`` is auto-set on construction when not provided."""
        log = DailyLog(
            id="day_uat",
            date=_DATE,
            created_at=_DT,
        )
        assert log.updated_at is not None
        assert isinstance(log.updated_at, datetime)

    def test_daily_log_updated_at_preserved_when_provided(self) -> None:
        """Explicit ``updated_at`` is preserved."""
        explicit = datetime(2025, 1, 1, 12, 0, 0)
        log = DailyLog(
            id="day_explicit",
            date=_DATE,
            created_at=_DT,
            updated_at=explicit,
        )
        assert log.updated_at == explicit

    def test_daily_log_updated_at_changes_on_assignment(self) -> None:
        """``validate_assignment=True`` re-runs validators on update."""
        log = DailyLog(
            id="day_mut",
            date=_DATE,
            created_at=_DT,
        )
        before = log.updated_at
        log.tasks_completed = 5
        # updated_at should be refreshed to a later time
        assert log.updated_at is not None
        assert log.updated_at >= before

    def test_daily_log_touch_method(self) -> None:
        """``touch()`` refreshes ``updated_at`` to a later instant."""
        log = DailyLog(
            id="day_touch",
            date=_DATE,
            created_at=_DT,
        )
        before = log.updated_at
        log.touch()
        assert log.updated_at is not None
        assert log.updated_at >= before

    def test_daily_log_touch_returns_self(self) -> None:
        """``touch()`` returns the instance for chaining."""
        log = DailyLog(
            id="day_touch_chain",
            date=_DATE,
            created_at=_DT,
        )
        assert log.touch() is log

    # ---- extra="forbid" and validation ---------------------------------

    def test_daily_log_rejects_unknown_fields(self) -> None:
        """``extra='forbid'`` rejects unknown fields."""
        with pytest.raises(ValidationError):
            DailyLog(
                id="day_unk",
                date=_DATE,
                created_at=_DT,
                unknown="oops",  # type: ignore[call-arg]
            )

    def test_daily_log_rejects_negative_tasks(self) -> None:
        """``tasks_completed`` rejects negatives."""
        with pytest.raises(ValidationError):
            DailyLog(
                id="day_neg",
                date=_DATE,
                tasks_completed=-1,
                created_at=_DT,
            )

    def test_daily_log_rejects_mood_out_of_range(self) -> None:
        """``mood_morning`` rejects 0 and 6."""
        with pytest.raises(ValidationError):
            DailyLog(
                id="day_mood",
                date=_DATE,
                mood_morning=0,
                created_at=_DT,
            )
        with pytest.raises(ValidationError):
            DailyLog(
                id="day_mood2",
                date=_DATE,
                mood_morning=6,
                created_at=_DT,
            )

    def test_daily_log_notes_max_length(self) -> None:
        """``notes`` of 1001 chars is rejected."""
        with pytest.raises(ValidationError):
            DailyLog(
                id="day_notes",
                date=_DATE,
                notes="x" * 1001,
                created_at=_DT,
            )

    def test_daily_log_is_mutable(self) -> None:
        """``DailyLog`` is mutable (``frozen=False``)."""
        log = DailyLog(
            id="day_mut2",
            date=_DATE,
            created_at=_DT,
        )
        log.tasks_completed = 10
        log.water_glasses = 8
        assert log.tasks_completed == 10
        assert log.water_glasses == 8
