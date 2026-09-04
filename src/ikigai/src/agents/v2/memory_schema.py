"""Cross-cycle memory schema — W4.6 implementation of ADR-028.

This module owns the **persistence schema** for the IKIGAi v2 graph's
cross-cycle memory layer. Per ADR-028 R1, it provides:

- 4 SQLite tables (``memory_daily_intentions``, ``memory_weekly_aggregations``,
  ``memory_monthly_syntheses``, ``memory_quarterly_strategies``)
- 4 WAL PRAGMAs at connection (R12: journal_mode=WAL, synchronous=NORMAL,
  busy_timeout=5000, foreign_keys=ON)
- 4 TypedDict records (R6) — one per memory type
- ``MEMORY_SCHEMA_VERSION = 1`` (R11 — monotonic, never reused)

The memory layer is **planner-only** (ADR-013): this module stores planner
state (UEIDs, body markdown, actor, timestamps), never computed values. The
schema is **append-only** per ``CLAUDE.md`` §"Refactor Protocol".

Architectural reference:
- ADR-028 — Cross-cycle memory layer (R1, R6, R11, R12)
- ADR-013 — planner-only; memory is pure data, NO computation
- ADR-014 — 4-part UEID canonical format (R3)
- ADR-025 — actor injection (R4: actor flows from manifest)
- ADR-012 — vault_write sole writer
- ADR-019 — algorithm_constants.json single source of truth
- ADR-027 — separate DB from checkpoint DB
- ADR-026 — memory writes are skill-internal (sub-agents do not write directly)

Drift invariants enforced (test_canonical_scope.py):
- W4.7 — new drift invariant (o): memory DB PRAGMAs present, JSON-key
  absence, 4-part UEID regex on every ``*_ueid`` field.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import NotRequired, TypedDict

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level constants (NOT algorithm tuning — these are identity/wire-format)
# ---------------------------------------------------------------------------

# Canonical schema version. Initial version 1, monotonic per ADR-028 R11.
MEMORY_SCHEMA_VERSION: int = 1

# Default DB filename (relative to <project_root>/data/). Per ADR-028 R1
# the memory DB lives at <root>/data/ikigai_memory.db, separate from the
# checkpoint DB (<root>/data/ikigai_checkpoints.db per ADR-027 R1).
MEMORY_DEFAULT_DB_FILENAME: str = "ikigai_memory.db"

# Canonical 4-part UEID regex (per ADR-014 + ADR-028 R3). Used to validate
# ``*_ueid`` primary keys AND every element of ``source_ueids`` lists at
# INSERT time. 5-part UEIDs are REJECTED per ADR-014 R3.
_UEID_REGEX = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")

# Allowed actor values (per ADR-025 R2 + ADR-028 R4).
_VALID_ACTORS: frozenset[str] = frozenset({"user", "agent", "system"})


# ---------------------------------------------------------------------------
# Table-name constants (per ADR-028 R1)
# ---------------------------------------------------------------------------

MEMORY_TABLE_DAILY: str = "memory_daily_intentions"
MEMORY_TABLE_WEEKLY: str = "memory_weekly_aggregations"
MEMORY_TABLE_MONTHLY: str = "memory_monthly_syntheses"
MEMORY_TABLE_QUARTERLY: str = "memory_quarterly_strategies"

# All 4 memory tables in pyramid order (Sonho -> Daily).
ALL_MEMORY_TABLES: tuple[str, ...] = (
    MEMORY_TABLE_DAILY,
    MEMORY_TABLE_WEEKLY,
    MEMORY_TABLE_MONTHLY,
    MEMORY_TABLE_QUARTERLY,
)


# ---------------------------------------------------------------------------
# TypedDicts — 4 per-record schemas (ADR-028 R6)
# ---------------------------------------------------------------------------


class DailyIntentionRecord(TypedDict, total=True):
    """One row in ``memory_daily_intentions`` (ADR-028 R6).

    Written by the ikigai-daily skill (actor=user per ADR-025 R2). The
    ``ts`` is a Unix epoch timestamp (REAL) for range-query efficiency;
    callers convert date ranges at the read boundary (see memory_read).
    """

    daily_ueid: str  # 4-part UEID (PRIMARY KEY)
    body_markdown: str
    sha256: str
    vault_path: str
    actor: str  # "user" | "agent" | "system"
    source_ueids: list[str]  # always [] for daily (leaf of pyramid)
    ts: float  # Unix epoch seconds


class WeeklyAggregation(TypedDict, total=True):
    """One row in ``memory_weekly_aggregations`` (ADR-028 R6).

    Written by the ikigai-weekly skill (actor=agent). ``source_ueids``
    is a non-empty list of 4-part daily UEIDs that were aggregated.
    """

    weekly_ueid: str  # 4-part UEID (PRIMARY KEY)
    body_markdown: str
    sha256: str
    vault_path: str
    actor: str
    source_ueids: list[str]  # list of 4-part daily_ueids
    ts: float


class MonthlySynthesis(TypedDict, total=True):
    """One row in ``memory_monthly_syntheses`` (ADR-028 R6).

    Written by the ikigai-monthly skill (actor=agent). ``source_ueids``
    is a list of 4-part weekly UEIDs that were synthesized.
    """

    monthly_ueid: str  # 4-part UEID (PRIMARY KEY)
    body_markdown: str
    sha256: str
    vault_path: str
    actor: str
    source_ueids: list[str]  # list of 4-part weekly_ueids
    ts: float


class QuarterlyStrategy(TypedDict, total=True):
    """One row in ``memory_quarterly_strategies`` (ADR-028 R6).

    Written by the ikigai-quarterly skill (actor=agent). ``source_ueids``
    is a list of 4-part monthly UEIDs that were strategized.
    """

    quarterly_ueid: str  # 4-part UEID (PRIMARY KEY)
    body_markdown: str
    sha256: str
    vault_path: str
    actor: str
    source_ueids: list[str]  # list of 4-part monthly_ueids
    ts: float


# Optional migration row shape — used by memory_migrations.apply_migrations.
class MigrationRow(TypedDict, total=False):
    """Shape consumed by ``apply_migrations`` (ADR-028 R11)."""

    ueid: str
    schema_version: NotRequired[int]


# ---------------------------------------------------------------------------
# Helpers — UEID + actor validation (R3)
# ---------------------------------------------------------------------------


def _is_valid_ueid(value: object) -> bool:
    """Return True iff value is a 4-part UEID per ADR-014."""
    return isinstance(value, str) and _UEID_REGEX.match(value) is not None


def _is_valid_actor(value: object) -> bool:
    """Return True iff value is one of {'user', 'agent', 'system'} per ADR-025 R2."""
    return isinstance(value, str) and value in _VALID_ACTORS


def _validate_source_ueids(source_ueids: list[str] | None) -> str:
    """Validate every element of ``source_ueids`` is a 4-part UEID.

    Returns the JSON-encoded string ready for INSERT (empty list -> "[]").
    Raises ValueError on any invalid element.
    """
    if source_ueids is None:
        return "[]"
    if not isinstance(source_ueids, list):
        raise ValueError(f"source_ueids must be a list, got {type(source_ueids).__name__}")
    for idx, ueid in enumerate(source_ueids):
        if not _is_valid_ueid(ueid):
            raise ValueError(
                f"source_ueids[{idx}]={ueid!r} is not a 4-part UEID "
                f"(ADR-014 + ADR-028 R3); rejecting write"
            )
    return json.dumps(list(source_ueids), ensure_ascii=False)


def _decode_source_ueids(raw: str | bytes | None) -> list[str]:
    """Decode a stored ``source_ueids`` JSON string back to a list.

    Returns [] on empty/null/non-JSON input (defensive).
    """
    if raw is None or raw == "" or raw == "[]":
        return []
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        decoded = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(decoded, list):
        return []
    return [str(u) for u in decoded]


# ---------------------------------------------------------------------------
# Schema bootstrap — 4 PRAGMAs + 4 CREATE TABLE statements (R1, R12)
# ---------------------------------------------------------------------------

# Per-record CREATE TABLE statements. Each enforces:
#   - *ueid is TEXT PRIMARY KEY (validated at INSERT by memory_write)
#   - body_markdown / sha256 / vault_path are NOT NULL
#   - actor is NOT NULL with CHECK constraint
#   - source_ueids defaults to '[]' (JSON list)
#   - ts is REAL NOT NULL (Unix epoch seconds)
#
# NOTE on column naming: per W4.6 brief §"Critical content" item 1, the
# 7 column list is: ueid (PK), body_markdown, sha256, vault_path, actor,
# source_ueids, ts. The primary-key column is named after the memory
# type (daily_ueid, weekly_ueid, monthly_ueid, quarterly_ueid) — which
# is more discriminating than the bare 'ueid' name and matches ADR-028 R1.

_CREATE_TABLE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS memory_daily_intentions (
        daily_ueid    TEXT PRIMARY KEY,
        body_markdown TEXT NOT NULL,
        sha256        TEXT NOT NULL,
        vault_path    TEXT NOT NULL,
        actor         TEXT NOT NULL CHECK(actor IN ('user', 'agent', 'system')),
        source_ueids  TEXT NOT NULL DEFAULT '[]',
        ts            REAL NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_weekly_aggregations (
        weekly_ueid   TEXT PRIMARY KEY,
        body_markdown TEXT NOT NULL,
        sha256        TEXT NOT NULL,
        vault_path    TEXT NOT NULL,
        actor         TEXT NOT NULL CHECK(actor IN ('user', 'agent', 'system')),
        source_ueids  TEXT NOT NULL DEFAULT '[]',
        ts            REAL NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_monthly_syntheses (
        monthly_ueid  TEXT PRIMARY KEY,
        body_markdown TEXT NOT NULL,
        sha256        TEXT NOT NULL,
        vault_path    TEXT NOT NULL,
        actor         TEXT NOT NULL CHECK(actor IN ('user', 'agent', 'system')),
        source_ueids  TEXT NOT NULL DEFAULT '[]',
        ts            REAL NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_quarterly_strategies (
        quarterly_ueid TEXT PRIMARY KEY,
        body_markdown  TEXT NOT NULL,
        sha256         TEXT NOT NULL,
        vault_path     TEXT NOT NULL,
        actor          TEXT NOT NULL CHECK(actor IN ('user', 'agent', 'system')),
        source_ueids   TEXT NOT NULL DEFAULT '[]',
        ts             REAL NOT NULL
    )
    """,
)


def memory_init(memory_db: Path | str) -> sqlite3.Connection:
    """Open the memory SQLite DB, apply 4 PRAGMAs, create 4 tables if missing.

    Per ADR-028 R12: WAL mode + 4 PRAGMAs mirror the checkpoint DB
    (ADR-027 R8) — same concurrency primitives for parallel writes.
    Per ADR-028 R1: 4 tables are created if missing (idempotent).

    Args:
        memory_db: Absolute or relative path to the SQLite file. Parent
            directories are auto-created. Use ``":memory:"`` for
            ephemeral tests (PRAGMAs are still applied).

    Returns:
        An open ``sqlite3.Connection`` with the 4 PRAGMAs set and 4
        tables created. The caller is responsible for closing the
        connection.

    Note:
        WAL mode persists across reconnects. Subsequent calls to
        ``memory_init`` on the same file will see journal_mode=WAL
        already set (idempotent).
    """
    path_str = str(memory_db)
    if path_str != ":memory:":
        path = Path(memory_db)
        path.parent.mkdir(parents=True, exist_ok=True)
        resolved = str(path.resolve())
    else:
        resolved = path_str

    # check_same_thread=False mirrors ADR-027 R8 — allows the same
    # connection to be shared across threads under WAL mode.
    conn = sqlite3.connect(resolved, check_same_thread=False)

    # Apply the 4 PRAGMAs (ADR-028 R12). Order matters: journal_mode
    # first so subsequent PRAGMAs operate in WAL mode.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")

    # Create the 4 memory tables if missing (ADR-028 R1).
    for stmt in _CREATE_TABLE_STATEMENTS:
        conn.execute(stmt)
    conn.commit()

    log.info(
        "memory_init: opened %s with 4 PRAGMAs + 4 tables (schema_version=%d)",
        resolved,
        MEMORY_SCHEMA_VERSION,
    )
    return conn


__all__ = [
    "ALL_MEMORY_TABLES",
    "MEMORY_DEFAULT_DB_FILENAME",
    "MEMORY_SCHEMA_VERSION",
    "MEMORY_TABLE_DAILY",
    "MEMORY_TABLE_MONTHLY",
    "MEMORY_TABLE_QUARTERLY",
    "MEMORY_TABLE_WEEKLY",
    "DailyIntentionRecord",
    "MigrationRow",
    "MonthlySynthesis",
    "QuarterlyStrategy",
    "WeeklyAggregation",
    "memory_init",
]
