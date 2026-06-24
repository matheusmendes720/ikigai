"""Entity factory functions with sensible defaults.

Each factory accepts overrides for any field, making them useful for
both tests and CLI quick-creation flows.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any

from operational.entities.habit import Habit
from operational.entities.journal import JournalEntry
from operational.entities.metric import SleepRecord
from operational.entities.routine import Routine
from operational.entities.time_block import TimeBlock
from operational.enums import HabitCategory, Period, RoutineType
from operational.types import UEID

__all__ = [
    "make_habit",
    "make_journal_entry",
    "make_routine",
    "make_sleep_record",
    "make_time_block",
]


def make_routine(
    *,
    id: UEID | None = None,
    name: str = "Factory Routine",
    period: Period = Period.MANHA,
    routine_type: RoutineType = RoutineType.CORE,
    start_time: time | None = None,
    end_time: time | None = None,
    **overrides: Any,
) -> Routine:
    """Build a Routine with sensible defaults.

    Args:
        id: UEID (auto-generated if ``None``).
        name: Human-readable name.
        period: Period assignment.
        routine_type: Type of routine.
        start_time: Start time (defaults to ``06:00``).
        end_time: End time (defaults to ``06:50``).
        **overrides: Any additional ``Routine`` field overrides.

    Returns:
        A ``Routine`` entity.
    """
    uid = id or UEID(f"rou_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}")
    s = start_time or time(6, 0)
    e = end_time or time(6, 50)
    return Routine(
        id=uid,
        name=name,
        period=period,
        routine_type=routine_type,
        start_time=s,
        end_time=e,
        created_at=datetime.now(UTC),
        **overrides,
    )


def make_time_block(
    *,
    id: UEID | None = None,
    label: str = "",
    start: datetime | None = None,
    end: datetime | None = None,
    period: Period = Period.MANHA,
    **overrides: Any,
) -> TimeBlock:
    """Build a TimeBlock with sensible defaults.

    Default interval is 1 hour starting from ``now``.

    Args:
        id: UEID (auto-generated if ``None``).
        label: Optional label.
        start: Block start (defaults to ``now``).
        end: Block end (defaults to ``start + 1h``).
        period: Period assignment.
        **overrides: Any additional ``TimeBlock`` field overrides.

    Returns:
        A ``TimeBlock`` entity.
    """
    from datetime import timedelta
    now = datetime.now(UTC)
    s = start or now
    e = end if end is not None else s + timedelta(hours=1)
    uid = id or UEID(f"blk_{s.strftime('%Y%m%d_%H%M%S')}")
    return TimeBlock(
        id=uid,
        label=label,
        start=s,
        end=e,
        period=period,
        created_at=now,
        **overrides,
    )


def make_habit(
    *,
    id: UEID | None = None,
    name: str = "Factory Habit",
    category: HabitCategory = HabitCategory.PHYSIOLOGICAL,
    resistance: float = 5.0,
    weight_in_qhe: float = 0.25,
    **overrides: Any,
) -> Habit:
    """Build a Habit with sensible defaults.

    Args:
        id: UEID (auto-generated if ``None``).
        name: Habit name.
        category: Habit category.
        resistance: Resistance level (0-10).
        weight_in_qhe: Weight in QHE formula (0-1).
        **overrides: Any additional ``Habit`` field overrides.

    Returns:
        A ``Habit`` entity.
    """
    uid = id or UEID(f"hab_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}")
    return Habit(
        id=uid,
        name=name,
        category=category,
        resistance=resistance,
        weight_in_qhe=weight_in_qhe,
        created_at=datetime.now(UTC),
        **overrides,
    )


def make_journal_entry(
    *,
    id: UEID | None = None,
    entry_date: date | None = None,
    **overrides: Any,
) -> JournalEntry:
    """Build a JournalEntry with sensible defaults.

    Args:
        id: UEID (auto-generated if ``None``).
        entry_date: Journal date (defaults to today).
        **overrides: Any additional ``JournalEntry`` field overrides.

    Returns:
        A ``JournalEntry`` entity.
    """
    d = entry_date or date.today()
    uid = id or UEID(f"day_{d.strftime('%Y_%m_%d')}")
    return JournalEntry(id=uid, date=d, created_at=datetime.now(UTC), **overrides)


def make_sleep_record(
    *,
    id: UEID | None = None,
    record_date: date | None = None,
    bedtime: time | None = None,
    wake_time: time | None = None,
    quality_score: int = 8,
    **overrides: Any,
) -> SleepRecord:
    """Build a SleepRecord with sensible defaults.

    Defaults to 23:00 bedtime → 07:00 wake, quality 8.

    Args:
        id: UEID (auto-generated if ``None``).
        record_date: Record date (defaults to today).
        bedtime: Bed time (defaults to 23:00).
        wake_time: Wake time (defaults to 07:00).
        quality_score: Self-reported quality (1-10).
        **overrides: Any additional ``SleepRecord`` field overrides.

    Returns:
        A ``SleepRecord`` entity.
    """
    d = record_date or date.today()
    uid = id or UEID(f"sle_{d.strftime('%Y_%m_%d')}")
    bed = bedtime or time(23, 0)
    wake = wake_time or time(7, 0)
    return SleepRecord(
        id=uid,
        date=d,
        bedtime=bed,
        wake_time=wake,
        quality_score=quality_score,
        created_at=datetime.now(UTC),
        **overrides,
    )
