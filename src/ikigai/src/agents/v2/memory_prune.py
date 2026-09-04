"""Cross-cycle memory prune — W4.6 implementation of ADR-028 R8.

This module owns the prune-on-write logic for the memory layer.
Per ADR-028 R8:

- ``memory_daily_intentions`` is pruned after ``MEMORY_RETENTION_DAILY_DAYS`` (30)
- ``memory_weekly_aggregations`` is pruned after ``MEMORY_RETENTION_WEEKLY_DAYS`` (90)
- ``memory_monthly_syntheses`` is pruned after ``MEMORY_RETENTION_MONTHLY_DAYS`` (365)
- ``memory_quarterly_strategies`` is **never** pruned (SONHO-level artifacts)

Pruning is **not** a cron; it's an **inline prune-on-write** trigger.
When a monthly cycle writes a new monthly synthesis, it prunes
``memory_daily_intentions`` rows older than ``MEMORY_RETENTION_DAILY_DAYS``.
This avoids a separate scheduler and ensures retention is always up-to-date.

Public API:
- ``prune_daily_intentions(memory_db, retention_days)`` — deletes rows
  where ``ts < now - retention_days`` (Unix epoch seconds).
- ``prune_on_write(memory_db, table, retention_days_key)`` — loads the
  retention value from ``algorithm_constants.json`` via
  ``load_constants.get(key)`` and prunes the corresponding table.

Per ADR-019 R6 + W4.6 brief §"Critical content" item 5: ``prune_on_write``
loads retention from JSON (NOT Python ``DEFAULT_MEMORY_*`` constants).
The drift detector's invariant (l) extends at W4.7 ship to cover these
4 new JSON keys' absence from ``.py`` files.

Architectural reference:
- ADR-028 R8 (retention policy) + R10 (failure modes)
- ADR-019 (algorithm_constants.json single source of truth)
- ADR-013 (planner-only — pure SQL DELETE, no computation)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from .memory_schema import (
    ALL_MEMORY_TABLES,
    MEMORY_TABLE_DAILY,
    MEMORY_TABLE_MONTHLY,
    MEMORY_TABLE_QUARTERLY,
    MEMORY_TABLE_WEEKLY,
    memory_init,
)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)


# Retention key -> table mapping (ADR-028 R8).
# The 4 keys MUST live in algorithm_constants.json + load_constants._defensive_default
# (per ADR-019 R6 + W4.6 brief §"Critical content" item 5).
_RETENTION_KEY_FOR_TABLE: dict[str, str] = {
    MEMORY_TABLE_DAILY: "MEMORY_RETENTION_DAILY_DAYS",
    MEMORY_TABLE_WEEKLY: "MEMORY_RETENTION_WEEKLY_DAYS",
    MEMORY_TABLE_MONTHLY: "MEMORY_RETENTION_MONTHLY_DAYS",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def prune_daily_intentions(
    memory_db: Path | str,
    retention_days: int,
    *,
    now_epoch: float | None = None,
) -> int:
    """Delete ``memory_daily_intentions`` rows older than ``retention_days``.

    Per ADR-028 R8 + R10: pruning is bounded by ``retention_days``. Rows
    with ``ts < now - retention_days * 86400`` are deleted. Returns the
    number of rows deleted.

    Args:
        memory_db: Path to the memory SQLite file (or ``":memory:"``).
        retention_days: Maximum age in days for rows to keep. Must be
            a positive integer. Rows older than ``retention_days`` are
            pruned. Pass ``0`` to prune ALL rows (full wipe).
        now_epoch: Optional override for the current time (Unix epoch
            seconds). Defaults to ``time.time()``. Exposed for testing.

    Returns:
        Number of rows deleted.

    Raises:
        ValueError: If ``retention_days`` is not a non-negative integer.
        sqlite3.OperationalError: If the DB is locked or the DELETE fails.
    """
    if not isinstance(retention_days, int) or retention_days < 0:
        raise ValueError(f"retention_days must be a non-negative integer, got {retention_days!r}")
    if now_epoch is None:
        now_epoch = time.time()

    cutoff = now_epoch - (retention_days * 86400.0)
    conn = memory_init(memory_db)
    try:
        cur = conn.execute(f"DELETE FROM {MEMORY_TABLE_DAILY} WHERE ts < ?", (cutoff,))
        deleted = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    if deleted > 0:
        log.info(
            "prune_daily_intentions: deleted %d rows (retention_days=%d, cutoff=%s)",
            deleted,
            retention_days,
            cutoff,
        )
    return deleted


def prune_weekly_aggregations(
    memory_db: Path | str,
    retention_days: int,
    *,
    now_epoch: float | None = None,
) -> int:
    """Delete ``memory_weekly_aggregations`` rows older than ``retention_days``.

    Args:
        memory_db: Path to the memory SQLite file (or ``":memory:"``).
        retention_days: Maximum age in days for rows to keep.
        now_epoch: Optional override for the current time (Unix epoch
            seconds). Defaults to ``time.time()``. Exposed for testing.

    Returns:
        Number of rows deleted.
    """
    if not isinstance(retention_days, int) or retention_days < 0:
        raise ValueError(f"retention_days must be a non-negative integer, got {retention_days!r}")
    if now_epoch is None:
        now_epoch = time.time()
    cutoff = now_epoch - (retention_days * 86400.0)
    conn = memory_init(memory_db)
    try:
        cur = conn.execute(f"DELETE FROM {MEMORY_TABLE_WEEKLY} WHERE ts < ?", (cutoff,))
        deleted = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return deleted


def prune_monthly_syntheses(
    memory_db: Path | str,
    retention_days: int,
    *,
    now_epoch: float | None = None,
) -> int:
    """Delete ``memory_monthly_syntheses`` rows older than ``retention_days``.

    Args:
        memory_db: Path to the memory SQLite file (or ``":memory:"``).
        retention_days: Maximum age in days for rows to keep.
        now_epoch: Optional override for the current time.

    Returns:
        Number of rows deleted.
    """
    if not isinstance(retention_days, int) or retention_days < 0:
        raise ValueError(f"retention_days must be a non-negative integer, got {retention_days!r}")
    if now_epoch is None:
        now_epoch = time.time()
    cutoff = now_epoch - (retention_days * 86400.0)
    conn = memory_init(memory_db)
    try:
        cur = conn.execute(f"DELETE FROM {MEMORY_TABLE_MONTHLY} WHERE ts < ?", (cutoff,))
        deleted = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return deleted


def prune_quarterly_strategies(
    memory_db: Path | str,
    retention_days: int,
    *,
    now_epoch: float | None = None,
) -> int:
    """Delete ``memory_quarterly_strategies`` rows older than ``retention_days``.

    Per ADR-028 R8: quarterly strategies are **never** pruned by default
    (they are SONHO-level artifacts). However, this function is provided
    for tests + the rare case where a user wants to set an explicit
    ``MEMORY_RETENTION_QUARTERLY_DAYS`` value. If ``retention_days`` is
    0 or negative, this is a no-op (quarterly retention is "forever"
    by default per R8 — never auto-prune).

    Args:
        memory_db: Path to the memory SQLite file.
        retention_days: Maximum age in days. If ``<= 0``, returns 0
            without pruning (quarterly retention is opt-in).
        now_epoch: Optional override for the current time.

    Returns:
        Number of rows deleted (0 if ``retention_days <= 0``).
    """
    if not isinstance(retention_days, int) or retention_days <= 0:
        # Quarterly is "forever" by default — opt-in retention.
        return 0
    if now_epoch is None:
        now_epoch = time.time()
    cutoff = now_epoch - (retention_days * 86400.0)
    conn = memory_init(memory_db)
    try:
        cur = conn.execute(f"DELETE FROM {MEMORY_TABLE_QUARTERLY} WHERE ts < ?", (cutoff,))
        deleted = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return deleted


# Dispatcher table -> prune function.
_PRUNE_DISPATCH: dict[str, Any] = {
    MEMORY_TABLE_DAILY: prune_daily_intentions,
    MEMORY_TABLE_WEEKLY: prune_weekly_aggregations,
    MEMORY_TABLE_MONTHLY: prune_monthly_syntheses,
    MEMORY_TABLE_QUARTERLY: prune_quarterly_strategies,
}


def prune_on_write(
    memory_db: Path | str,
    table: str,
    retention_days_key: str,
    *,
    now_epoch: float | None = None,
) -> int:
    """Inline prune-on-write trigger (ADR-028 R8).

    Loads the retention value from ``algorithm_constants.json`` via
    ``load_constants.get(key)`` (per ADR-019 R6) and prunes the
    corresponding table. Returns the number of rows deleted.

    Per ADR-028 R8: this is the canonical prune entry point. Skill nodes
    call it inline after a successful ``memory_write``. Retention keys
    MUST be loaded from JSON (NOT Python ``DEFAULT_MEMORY_*`` constants).

    Args:
        memory_db: Path to the memory SQLite file (or ``":memory:"``).
        table: One of the 4 ``MEMORY_TABLE_*`` constants.
        retention_days_key: The JSON key in ``algorithm_constants.json``
            (e.g. ``MEMORY_RETENTION_DAILY_DAYS``). Must match the table.
        now_epoch: Optional override for the current time.

    Returns:
        Number of rows deleted.

    Raises:
        ValueError: If ``table`` is not a known memory table, or
            ``retention_days_key`` does not match the expected key for
            that table, or the JSON lookup fails.
    """
    if table not in ALL_MEMORY_TABLES:
        raise ValueError(
            f"table {table!r} is not a recognized memory table; "
            f"expected one of {list(ALL_MEMORY_TABLES)} (ADR-028 R1)"
        )

    expected_key = _RETENTION_KEY_FOR_TABLE.get(table)
    if expected_key is None:
        # Quarterly retention is opt-in. If the caller passes an
        # explicit ``MEMORY_RETENTION_QUARTERLY_DAYS`` key, honor it;
        # otherwise skip (forever retention).
        if table == MEMORY_TABLE_QUARTERLY:
            expected_key = "MEMORY_RETENTION_QUARTERLY_DAYS"
        else:
            raise ValueError(f"no retention key mapped for table {table!r} (ADR-028 R8)")

    if retention_days_key != expected_key:
        raise ValueError(
            f"retention_days_key {retention_days_key!r} does not match expected "
            f"key for table {table!r}: expected {expected_key!r} (ADR-028 R8)"
        )

    # Load retention value from JSON (per ADR-019 R6 — JSON is SOT).
    from .prompts.load_constants import get as _algo_const

    try:
        raw_value = _algo_const(retention_days_key)
    except KeyError as exc:
        raise ValueError(
            f"retention key {retention_days_key!r} not found in "
            f"algorithm_constants.json (ADR-019 R6); add the key to "
            f"JSON + load_constants._defensive_default()"
        ) from exc

    # Quarterly retention is "forever" by default (None in JSON).
    if raw_value is None:
        if table == MEMORY_TABLE_QUARTERLY:
            log.debug(
                "prune_on_write: %s retention is None (forever) — no pruning",
                table,
            )
            return 0
        raise ValueError(
            f"retention value for {retention_days_key!r} is None; expected a non-negative integer"
        )

    retention_days = int(raw_value)

    prune_fn = _PRUNE_DISPATCH[table]
    return prune_fn(memory_db, retention_days, now_epoch=now_epoch)


__all__ = [
    "prune_daily_intentions",
    "prune_monthly_syntheses",
    "prune_on_write",
    "prune_quarterly_strategies",
    "prune_weekly_aggregations",
]
