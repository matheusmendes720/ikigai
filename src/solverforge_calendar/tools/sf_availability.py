"""sf_availability — query free slots in a window.

Read-only, no overlap detection (just lists busy intervals and subtracts).
Caches last query for 60s in-memory dict (not LRU).
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from solverforge_calendar.db import SolverforgeDB
from solverforge_calendar.models import (
    SfAvailabilityInput,
    SfAvailabilityOutput,
    SfTimeSlot,
)

_CACHE: dict[tuple, tuple[float, SfAvailabilityOutput]] = {}
_CACHE_TTL_S = 60.0


def _db() -> SolverforgeDB:
    data_dir = Path(os.environ.get("SOLVERFORGE_DATA_DIR", "data/solverforge_calendar"))
    return SolverforgeDB(data_dir / "unified_planning.db")


def handle(args: dict) -> dict:
    inp = SfAvailabilityInput.model_validate(args)
    if inp.exclude_ueids:
        # exclude_ueids is a hint for cache key only; behavior is per impl
        pass

    cache_key = (
        inp.window_start,
        inp.window_end,
        inp.min_slot_minutes,
        tuple(inp.exclude_ueids),
    )
    if cache_key in _CACHE:
        ts, cached = _CACHE[cache_key]
        if time.time() - ts < _CACHE_TTL_S:
            return cached.model_dump(mode="json")

    db = _db()
    busy = db.list_busy_in_window(start=inp.window_start, end=inp.window_end)
    busy_intervals = sorted(
        [
            SfTimeSlot(
                start=datetime.fromisoformat(b["start_at"]),
                end=datetime.fromisoformat(b["end_at"]),
            )
            for b in busy
            if b["end_at"]
        ],
        key=lambda s: s.start,
    )
    free_slots = _compute_free_slots(
        window_start=inp.window_start,
        window_end=inp.window_end,
        busy=busy_intervals,
        min_slot_minutes=inp.min_slot_minutes,
    )
    output = SfAvailabilityOutput(
        window_start=inp.window_start,
        window_end=inp.window_end,
        free_slots=free_slots,
        busy_intervals=busy_intervals,
    )
    _CACHE[cache_key] = (time.time(), output)
    return output.model_dump(mode="json")


def _compute_free_slots(
    *,
    window_start: datetime,
    window_end: datetime,
    busy: list[SfTimeSlot],
    min_slot_minutes: int,
) -> list[SfTimeSlot]:
    """Subtract busy intervals from [window_start, window_end); split into slots."""
    min_slot = timedelta(minutes=min_slot_minutes)
    free = []
    cursor = window_start
    for b in sorted(busy, key=lambda s: s.start):
        if b.start > cursor:
            gap = b.start - cursor
            if gap >= min_slot:
                free.append(SfTimeSlot(start=cursor, end=b.start))
            elif gap > timedelta(0):
                free.append(SfTimeSlot(start=cursor, end=cursor + gap))
        cursor = max(cursor, b.end) if b.end else cursor
    if window_end > cursor:
        gap = window_end - cursor
        if gap >= min_slot:
            free.append(SfTimeSlot(start=cursor, end=window_end))
        elif gap > timedelta(0):
            free.append(SfTimeSlot(start=cursor, end=cursor + gap))
    return free
