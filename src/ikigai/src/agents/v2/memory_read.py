"""Cross-cycle memory read — W4.6 implementation of ADR-028.

This module provides the read-side surface for the cross-cycle memory
layer per ADR-028 R5 (retrieval patterns).

Public API:
- ``read_daily_intentions(week_range, actor=None)`` — R5 daily read.
- ``read_weekly_aggregations(month_range, actor=None)`` — R5 weekly read.
- ``read_monthly_syntheses(quarter_range, actor=None)`` — R5 monthly read.
- ``read_quarterly_strategies(year, actor=None)`` — R5 quarterly read.

Permission model (ADR-028 R5): default-deny actor scoping. ``actor=None``
returns records from ALL actors (agent introspection). ``actor="agent"``
returns only agent-written records. ``actor="user"`` returns only
user-written records (rare; weekly rarely reads user records).

Per ADR-013 planner-only invariant: this module is pure data — no
computation, no scoring, no heuristics. Retrieval is deterministic
(``WHERE ts BETWEEN ...``).

Architectural reference:
- ADR-028 R5 (retrieval patterns) + R7 (pyramid data flow)
- ADR-025 actor tagging (R2: daily = user, weekly/monthly/quarterly = agent)
- ADR-013 planner-only (read functions are pure data)
- ADR-027 R6 (cross-cycle state passing: query-based handoffs, not mutations)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from .memory_schema import (
    MEMORY_TABLE_DAILY,
    MEMORY_TABLE_MONTHLY,
    MEMORY_TABLE_QUARTERLY,
    MEMORY_TABLE_WEEKLY,
    DailyIntentionRecord,
    MonthlySynthesis,
    QuarterlyStrategy,
    WeeklyAggregation,
    _decode_source_ueids,
    _is_valid_actor,
    memory_init,
)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)

Actor = Literal["user", "agent", "system"]


# ---------------------------------------------------------------------------
# Date-range helpers (range -> Unix epoch seconds)
# ---------------------------------------------------------------------------


def _date_to_epoch(d: date) -> float:
    """Convert a ``datetime.date`` to Unix epoch seconds (UTC midnight).

    Used to translate ``(date, date)`` ranges into REAL ``ts`` bounds
    for SQL ``BETWEEN`` filtering. Per ADR-028 R5: ts is REAL (Unix epoch
    seconds); date boundaries are inclusive at midnight UTC.
    """
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()


# ---------------------------------------------------------------------------
# Internal — generic query helper
# ---------------------------------------------------------------------------


def _read_records(
    memory_db: Path | str,
    table: str,
    pk_column: str,
    ts_start: float,
    ts_end: float,
    actor: str | None,
) -> list[dict]:
    """Query rows from a memory table within a ts range, optionally filtered by actor.

    Returns a list of dict-shaped records (TypedDict-compatible) ordered
    by ``ts ASC`` (per ADR-028 R5 — chronological order).
    """
    # Validate actor before opening DB (fail fast).
    if actor is not None and not _is_valid_actor(actor):
        raise ValueError(f"actor {actor!r} not in {{'user', 'agent', 'system'}} (ADR-025 R2)")

    conn = memory_init(memory_db)
    try:
        if actor is None:
            cur = conn.execute(
                f"SELECT {pk_column}, body_markdown, sha256, vault_path, actor, "
                f"source_ueids, ts FROM {table} "
                f"WHERE ts BETWEEN ? AND ? ORDER BY ts ASC",
                (ts_start, ts_end),
            )
        else:
            cur = conn.execute(
                f"SELECT {pk_column}, body_markdown, sha256, vault_path, actor, "
                f"source_ueids, ts FROM {table} "
                f"WHERE ts BETWEEN ? AND ? AND actor = ? ORDER BY ts ASC",
                (ts_start, ts_end, actor),
            )
        rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "ueid": row[0],
            "body_markdown": row[1],
            "sha256": row[2],
            "vault_path": row[3],
            "actor": row[4],
            "source_ueids": _decode_source_ueids(row[5]),
            "ts": float(row[6]),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Public read functions — R5 (one per memory type)
# ---------------------------------------------------------------------------


def read_daily_intentions(
    memory_db: Path | str,
    week_range: tuple[date, date],
    actor: Actor | None = None,
) -> list[DailyIntentionRecord]:
    """Read daily intentions for a date range (ADR-028 R5).

    Args:
        memory_db: Path to the memory SQLite file (or ``":memory:"``).
        week_range: ``(start_date, end_date)`` inclusive range.
        actor: Optional actor filter (``user`` | ``agent`` | ``system``).
            ``None`` returns records from all actors.

    Returns:
        List of ``DailyIntentionRecord`` dicts ordered by ``ts ASC``.
    """
    start_date, end_date = week_range
    if start_date > end_date:
        raise ValueError(f"week_range start_date {start_date!r} is after end_date {end_date!r}")
    ts_start = _date_to_epoch(start_date)
    # end_date is inclusive — add 1 day to make the upper bound exclusive.
    ts_end_exclusive = _date_to_epoch(end_date) + 86400.0
    rows = _read_records(
        memory_db=memory_db,
        table=MEMORY_TABLE_DAILY,
        pk_column="daily_ueid",
        ts_start=ts_start,
        ts_end=ts_end_exclusive,
        actor=actor,
    )
    return [DailyIntentionRecord(**r) for r in rows]  # type: ignore[misc]


def read_weekly_aggregations(
    memory_db: Path | str,
    month_range: tuple[date, date],
    actor: Actor | None = None,
) -> list[WeeklyAggregation]:
    """Read weekly aggregations for a date range (ADR-028 R5).

    Args:
        memory_db: Path to the memory SQLite file (or ``":memory:"``).
        month_range: ``(start_date, end_date)`` inclusive range.
        actor: Optional actor filter.

    Returns:
        List of ``WeeklyAggregation`` dicts ordered by ``ts ASC``.
    """
    start_date, end_date = month_range
    if start_date > end_date:
        raise ValueError(f"month_range start_date {start_date!r} is after end_date {end_date!r}")
    ts_start = _date_to_epoch(start_date)
    ts_end_exclusive = _date_to_epoch(end_date) + 86400.0
    rows = _read_records(
        memory_db=memory_db,
        table=MEMORY_TABLE_WEEKLY,
        pk_column="weekly_ueid",
        ts_start=ts_start,
        ts_end=ts_end_exclusive,
        actor=actor,
    )
    return [WeeklyAggregation(**r) for r in rows]  # type: ignore[misc]


def read_monthly_syntheses(
    memory_db: Path | str,
    quarter_range: tuple[date, date],
    actor: Actor | None = None,
) -> list[MonthlySynthesis]:
    """Read monthly syntheses for a date range (ADR-028 R5).

    Args:
        memory_db: Path to the memory SQLite file (or ``":memory:"``).
        quarter_range: ``(start_date, end_date)`` inclusive range.
        actor: Optional actor filter.

    Returns:
        List of ``MonthlySynthesis`` dicts ordered by ``ts ASC``.
    """
    start_date, end_date = quarter_range
    if start_date > end_date:
        raise ValueError(f"quarter_range start_date {start_date!r} is after end_date {end_date!r}")
    ts_start = _date_to_epoch(start_date)
    ts_end_exclusive = _date_to_epoch(end_date) + 86400.0
    rows = _read_records(
        memory_db=memory_db,
        table=MEMORY_TABLE_MONTHLY,
        pk_column="monthly_ueid",
        ts_start=ts_start,
        ts_end=ts_end_exclusive,
        actor=actor,
    )
    return [MonthlySynthesis(**r) for r in rows]  # type: ignore[misc]


def read_quarterly_strategies(
    memory_db: Path | str,
    year: int,
    actor: Actor | None = None,
) -> list[QuarterlyStrategy]:
    """Read quarterly strategies for a calendar year (ADR-028 R5).

    Args:
        memory_db: Path to the memory SQLite file (or ``":memory:"``).
        year: 4-digit calendar year (e.g. ``2026``).
        actor: Optional actor filter.

    Returns:
        List of ``QuarterlyStrategy`` dicts ordered by ``ts ASC``.
    """
    if not isinstance(year, int) or year < 1970 or year > 9999:
        raise ValueError(f"year must be an integer in [1970, 9999], got {year!r}")
    # Calendar year bounds: Jan 1 00:00 UTC -> Jan 1 of next year 00:00 UTC.
    ts_start = _date_to_epoch(date(year, 1, 1))
    ts_end_exclusive = _date_to_epoch(date(year + 1, 1, 1))
    rows = _read_records(
        memory_db=memory_db,
        table=MEMORY_TABLE_QUARTERLY,
        pk_column="quarterly_ueid",
        ts_start=ts_start,
        ts_end=ts_end_exclusive,
        actor=actor,
    )
    return [QuarterlyStrategy(**r) for r in rows]  # type: ignore[misc]


__all__ = [
    "read_daily_intentions",
    "read_monthly_syntheses",
    "read_quarterly_strategies",
    "read_weekly_aggregations",
]
