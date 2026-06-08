"""Tests for :mod:`operational.meta.factories`."""
from __future__ import annotations

from datetime import date, datetime, time

from operational.entities.habit import Habit
from operational.entities.journal import JournalEntry
from operational.entities.metric import SleepRecord
from operational.entities.routine import Routine
from operational.entities.time_block import TimeBlock
from operational.enums import HabitCategory, Period, RoutineType
from operational.meta.factories import (
    make_habit,
    make_journal_entry,
    make_routine,
    make_sleep_record,
    make_time_block,
)
from operational.types import UEID


class TestMakeRoutine:
    def test_defaults(self) -> None:
        r = make_routine()
        assert isinstance(r, Routine)
        assert r.name == "Factory Routine"
        assert r.period is Period.MANHA
        assert r.routine_type is RoutineType.CORE
        assert r.start_time == time(6, 0)
        assert r.end_time == time(6, 50)

    def test_custom_id(self) -> None:
        r = make_routine(id=UEID("rou_custom"))
        assert r.id == "rou_custom"

    def test_overrides(self) -> None:
        r = make_routine(name="Override", mandatory=False)
        assert r.name == "Override"
        assert r.mandatory is False


class TestMakeTimeBlock:
    def test_defaults(self) -> None:
        t = make_time_block()
        assert isinstance(t, TimeBlock)
        assert t.period is Period.MANHA
        assert t.label == ""

    def test_custom_period(self) -> None:
        t = make_time_block(period=Period.TARDE)
        assert t.period is Period.TARDE

    def test_fixed_duration(self) -> None:
        start = datetime(2026, 6, 7, 10, 0)
        t = make_time_block(start=start, end=datetime(2026, 6, 7, 10, 30))
        assert t.duration_minutes == 30


class TestMakeHabit:
    def test_defaults(self) -> None:
        h = make_habit()
        assert isinstance(h, Habit)
        assert h.name == "Factory Habit"
        assert h.category is HabitCategory.PHYSIOLOGICAL
        assert h.resistance == 5.0
        assert h.weight_in_qhe == 0.25

    def test_custom(self) -> None:
        h = make_habit(name="Drink water", resistance=2.0, weight_in_qhe=0.5)
        assert h.name == "Drink water"
        assert h.resistance == 2.0


class TestMakeJournalEntry:
    def test_defaults(self) -> None:
        j = make_journal_entry()
        assert isinstance(j, JournalEntry)
        assert j.date == date.today()

    def test_custom_date(self) -> None:
        j = make_journal_entry(entry_date=date(2026, 6, 7))
        assert j.date == date(2026, 6, 7)
        assert "day_2026_06_07" in j.id

    def test_with_text(self) -> None:
        j = make_journal_entry(entry_text="My day")
        assert j.entry_text == "My day"


class TestMakeSleepRecord:
    def test_defaults(self) -> None:
        s = make_sleep_record()
        assert isinstance(s, SleepRecord)
        assert s.quality_score == 8
        assert s.bedtime == time(23, 0)
        assert s.wake_time == time(7, 0)

    def test_custom(self) -> None:
        s = make_sleep_record(
            quality_score=6,
            bedtime=time(0, 0),
            wake_time=time(8, 0),
        )
        assert s.quality_score == 6
        assert s.bedtime == time(0, 0)
