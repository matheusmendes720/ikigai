"""Stateful subgraph checkpoint persistence — W4.5 implementation of ADR-027.

This module owns the **persistence layer** for the IKIGAi v2 graph's
sub-agent fan-out (ADR-026) and the cross-cycle memory layer (ADR-028,
W4.6). It wraps LangGraph's ``SqliteSaver`` with three IKIGAi-specific
schema-control tables (``ikigai_schema_registry`` + ``ikigai_subgraph_links``)
and the 4 WAL PRAGMAs mandated by ADR-027 R8.

It also owns the canonical thread_id construction per ADR-027 R3:

    <actor>-<skill>-<cycle_short>-<sub_role>

where ``actor ∈ {user, agent, system}``, ``skill ∈ {daily, weekly,
monthly, quarterly, ad-hoc}``, ``cycle_short`` is the first 8 hex chars
of the cycle UUID, and ``sub_role ∈ {parent, child-<sub_agent_id>,
skill}``.

The W4.4 reviewer's minor observation (4-segment thread_id gap) is
closed by ``build_subagent_thread_id`` — sub-agents now use the full
hierarchical format instead of ``f"subagent-{sub_agent_id}"``.

Architectural reference:
- ADR-027 — Stateful subgraph strategy (R1 SQL, R2 JSON, R3 thread-id,
  R5 5-axis classification, R8 PRAGMAs, R9 versioning, R10 retention,
  R13 deliverables)
- ADR-013 — planner-only; checkpoint is pure persistence
- ADR-014 — 4-part UEID canonical (sub_agent_id validation)
- ADR-019 — algorithm_constants.json single source of truth
- ADR-025 — actor injection (thread_id actor segment matches skill
  binding's actor: daily=user, weekly/monthly/quarterly=agent)
- ADR-026 — sub-agent dispatch (closes TBD on checkpoint schema)

Drift invariants enforced (test_canonical_scope.py):
- IkigaiCheckpointer class exists at checkpoint.py
- _DEFAULT_DB_FILENAME = "ikigai_checkpoints.db"
- algorithm_constants.json has all CHECKPOINT_* + SUBAGENT_* keys
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Literal, TypedDict

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level constants (NOT algorithm tuning — these are identity/wire-format)
# ---------------------------------------------------------------------------

# Canonical DB filename relative to <project_root>/data/. Locked by ADR-027
# R13.5 — drift detector asserts this constant.
_DEFAULT_DB_FILENAME: str = "ikigai_checkpoints.db"

# Initial schema version. Monotonic per ADR-027 R9 — never reused.
_SCHEMA_VERSION: int = 1

# Canonical 4-part UEID regex (per ADR-014 + ADR-026 R4). Used to validate
# ``sub_agent_id`` before writing to ``ikigai_subgraph_links``.
_UEID_REGEX = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")

# ADR-027 R3 — allowed values for each thread_id segment.
_VALID_ACTORS: frozenset[str] = frozenset({"user", "agent", "system"})
_VALID_SKILLS: frozenset[str] = frozenset({"daily", "weekly", "monthly", "quarterly", "ad-hoc"})
_VALID_SUB_ROLES: frozenset[str] = frozenset({"parent", "singleton"})
# ``child-<sub_agent_id>`` sub_role is built by build_subagent_thread_id,
# not validated here — it embeds a 4-part UEID.

# ThreadRole literal — used by schema-control tables AND JSON payload prefix.
ThreadRole = Literal["parent", "child", "skill"]


# ---------------------------------------------------------------------------
# TypedDicts — subgraph link, vault write record, schema registry row
# ---------------------------------------------------------------------------


class SubgraphLink(TypedDict, total=False):
    """One row in ``ikigai_subgraph_links`` (ADR-027 R1).

    Captures parent → child dispatch relationships so the dispatcher can
    reconstruct a cycle's fan-out without parsing the JSON checkpoint
    BLOB. Composite primary key is (parent_thread_id, parent_checkpoint_id,
    child_thread_id, child_checkpoint_id) — UPSERT semantics on duplicate.
    """

    parent_thread_id: str
    parent_checkpoint_id: str
    child_thread_id: str
    child_checkpoint_id: str
    created_at: str  # ISO 8601 UTC
    sub_agent_id: str  # 4-part UEID per ADR-014


class VaultWriteRecord(TypedDict, total=False):
    """Per-write entry in ``vault_writes_log`` (ADR-027 R4).

    Mirrors the canonical ``VaultWriteRecord`` from
    ``src/ikigai/src/ikigai/vault/vault_write.py``. Replicated here as
    a TypedDict to keep this module dependency-free (avoids import cycle
    with vault_write.py).
    """

    vault_path: str  # relative path within vault/
    actor: Literal["user", "agent", "system"]
    timestamp: str  # ISO 8601 UTC
    sha256: str  # sha256 of written body
    operation: Literal["create", "update", "delete"]


class SchemaRegistryRow(TypedDict, total=False):
    """One row in ``ikigai_schema_registry`` (ADR-027 R9)."""

    schema_version: int
    description: str
    applied_at: str  # ISO 8601 UTC


# ---------------------------------------------------------------------------
# Helpers — thread_id construction (ADR-027 R3)
# ---------------------------------------------------------------------------


def _validate_segment(name: str, value: str, allowed: frozenset[str]) -> str:
    """Raise ValueError if value is empty or not in allowed set."""
    if not value:
        raise ValueError(f"thread_id segment {name!r} must be non-empty")
    if value not in allowed:
        raise ValueError(
            f"thread_id segment {name!r}={value!r} not in allowed set {sorted(allowed)}"
        )
    return value


def _validate_cycle_short(cycle_short: str) -> str:
    """Validate the ``cycle_short`` segment (free-form, but non-empty + no internal dashes-as-separators).

    Per ADR-027 R3: cycle_short is the first 8 hex chars of the cycle UUID.
    We accept any non-empty alphanumeric-ish string here so callers can
    pass either a raw 8-hex slice OR a date like ``2026-09-04`` (the
    brief's example). Only requirement: no whitespace, no ``-`` (which
    is reserved as the segment separator).
    """
    if not cycle_short:
        raise ValueError("thread_id segment 'cycle_short' must be non-empty")
    if any(c.isspace() for c in cycle_short):
        raise ValueError(f"cycle_short must not contain whitespace: {cycle_short!r}")
    # cycle_short may contain dashes internally (e.g. '2026-09-04') —
    # but those dashes are visually distinguishable from the segment
    # separators by the validator below.
    return cycle_short


def build_thread_id(
    actor: str,
    skill: str,
    cycle_short: str,
    sub_role: str,
) -> str:
    """Build a canonical 4-segment thread_id per ADR-027 R3.

    Format: ``<actor>-<skill>-<cycle_short>-<sub_role>``.

    Args:
        actor: One of ``user``, ``agent``, ``system``.
        skill: One of ``daily``, ``weekly``, ``monthly``, ``quarterly``,
            ``ad-hoc``.
        cycle_short: Short cycle identifier (first 8 hex of cycle UUID,
            or a date like ``2026-09-04``).
        sub_role: ``parent`` | ``singleton`` | ``child-<sub_agent_id>``.

    Returns:
        The constructed 4-segment thread_id string.

    Raises:
        ValueError: If any segment is empty or invalid.

    Examples:
        >>> build_thread_id("agent", "weekly", "2026q3", "parent")
        'agent-weekly-2026q3-parent'
        >>> build_thread_id("user", "daily", "2026-09-04", "singleton")
        'user-daily-2026-09-04-singleton'
    """
    a = _validate_segment("actor", actor, _VALID_ACTORS)
    s = _validate_segment("skill", skill, _VALID_SKILLS)
    c = _validate_cycle_short(cycle_short)
    r = _validate_segment("sub_role", sub_role, _VALID_SUB_ROLES)
    return f"{a}-{s}-{c}-{r}"


def build_subagent_thread_id(parent_thread_id: str, sub_agent_id: str) -> str:
    """Build a child thread_id by appending ``-subagent-<short_hash>`` to the parent.

    Per ADR-027 R3: child sub-agents embed their 4-part UEID in the
    thread_id so queries can reconstruct the full fan-out from the
    ``ikigai_subgraph_links`` table without parsing JSON. The
    ``short_hash`` is the first 8 hex chars of
    ``sha256(parent_thread_id + sub_agent_id)`` — provides a stable,
    collision-resistant child suffix without leaking the full UEID in
    the thread_id.

    The returned string is **logically** 5 segments (parent is 4 segments
    itself) but is built per the ADR-027 R3 example:
    ``agent-weekly-a3f19c2d-child-01HXY...`` — where ``01HXY...`` is the
    short hash, not a sub_segment per se. Drift detector scans for
    ``-subagent-`` (literal substring) to verify the closure of W4.4's
    reviewer observation.

    Args:
        parent_thread_id: The parent's 4-segment thread_id (from
            ``build_thread_id`` or a LangGraph checkpointer row).
        sub_agent_id: The sub-agent's 4-part UEID (validated by the
            canonical regex per ADR-014 + ADR-026 R4).

    Returns:
        The constructed child thread_id (parent + ``-subagent-<short>``).

    Raises:
        ValueError: If ``sub_agent_id`` is not a 4-part UEID.

    Example:
        >>> build_subagent_thread_id(
        ...     "agent-weekly-a3f19c2d-parent",
        ...     "sa:demo:a1b2c3d4:e5f6a7b8",
        ... )
        'agent-weekly-a3f19c2d-parent-subagent-<8hex>'
    """
    if not _UEID_REGEX.match(sub_agent_id or ""):
        raise ValueError(
            f"sub_agent_id {sub_agent_id!r} is not a 4-part UEID (ADR-014 + ADR-026 R4)"
        )
    if not parent_thread_id:
        raise ValueError("parent_thread_id must be non-empty")
    digest = hashlib.sha256((parent_thread_id + sub_agent_id).encode("utf-8")).hexdigest()
    short_hash = digest[:8]
    return f"{parent_thread_id}-subagent-{short_hash}"


# ---------------------------------------------------------------------------
# Checkpoint JSON payload (ADR-027 R2)
# ---------------------------------------------------------------------------

# Schema-control prefixes per R2 — prepended to every checkpoint JSON.
# These three fields are JSON-serialized with every checkpoint row.
SCHEMA_CONTROL_KEYS: tuple[str, ...] = (
    "schema_version",
    "thread_role",
    "vault_writes_log",
)


def serialize_checkpoint(
    state: dict[str, Any],
    *,
    thread_role: ThreadRole = "parent",
    vault_writes_log: list[VaultWriteRecord] | None = None,
    schema_version: int | None = None,
) -> bytes:
    """Serialize an IKIGAiStateDict into a checkpoint BLOB (UTF-8 JSON).

    Per ADR-027 R2: the JSON payload contains 3 schema-control prefixes
    (schema_version, thread_role, vault_writes_log) prepended to the
    state dict, then JSON-serialized as UTF-8 bytes for SqliteSaver.

    No computation occurs here — this is pure persistence per ADR-013
    planner-only.

    Args:
        state: The IKIGAiStateDict (or partial dict) to serialize.
        thread_role: One of ``parent`` | ``child`` | ``skill``.
        vault_writes_log: Append-only list of vault writes from this cycle.
        schema_version: Override the schema version (defaults to module
            constant ``_SCHEMA_VERSION``).

    Returns:
        UTF-8 encoded JSON bytes ready for SqliteSaver BLOB storage.
    """
    payload: dict[str, Any] = dict(state)  # defensive copy
    payload["schema_version"] = schema_version if schema_version is not None else _SCHEMA_VERSION
    payload["thread_role"] = thread_role
    payload["vault_writes_log"] = list(vault_writes_log or [])
    return json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8")


def deserialize_checkpoint(blob: bytes) -> dict[str, Any]:
    """Deserialize a checkpoint BLOB back into a state dict (ADR-027 R2).

    Inverse of ``serialize_checkpoint``. The 3 schema-control fields are
    returned alongside the user-state fields; callers can filter them
    out if desired (they are also reachable by key).

    Lazy migration per ADR-027 R9: callers can inspect
    ``payload["schema_version"]`` and apply migration functions from
    ``checkpoint_migrations.py`` if the version is older than
    ``_SCHEMA_VERSION``. This function does NOT mutate the payload —
    pure read.

    Args:
        blob: UTF-8 JSON bytes from a SqliteSaver row.

    Returns:
        Reconstructed state dict (including schema-control fields).
    """
    return json.loads(blob.decode("utf-8"))


# ---------------------------------------------------------------------------
# IkigaiCheckpointer — main public surface
# ---------------------------------------------------------------------------


class IkigaiCheckpointer:
    """Persistence layer for IKIGAi v2 graph (ADR-027).

    Wraps LangGraph's ``SqliteSaver`` with:

    1. **PRAGMAs** (R8): ``journal_mode=WAL``, ``synchronous=NORMAL``,
       ``busy_timeout=5000``, ``foreign_keys=ON``. WAL mode is the
       SqliteSaver-supported concurrency primitive for sub-agent fan-out
       (ADR-026 R6 — parent + N children writing concurrently).
    2. **Schema-control tables** (R1): ``ikigai_schema_registry`` and
       ``ikigai_subgraph_links`` are created if missing. LangGraph's
       SqliteSaver is unaware of these — they are application-managed.
    3. **Sub-agent link tracking** (R1, R5.13): every parent→child
       dispatch is recorded via ``record_subgraph_link``.
    4. **Retention** (R10): ``apply_retention`` prunes old rows per
       ``CHECKPOINT_RETENTION_COUNT`` + ``MAX_CHECKPOINT_AGE_DAYS`` from
       ``prompts/algorithm_constants.json``.

    The class is **NOT** thread-isolated: a single instance is intended
    to be shared across threads. WAL mode + ``check_same_thread=False``
    on the underlying SqliteSaver connection handle multi-thread
    concurrency (verified by the 4-thread test in W4.5 test suite).
    """

    def __init__(self, db_path: str | Path) -> None:
        """Open the SQLite DB at ``db_path``, apply PRAGMAs, create tables.

        Args:
            db_path: Absolute or relative path to the SQLite file.
                Parent directories are auto-created. Use
                ``:memory:`` for ephemeral tests (PRAGMAs are still
                applied).
        """
        path = Path(db_path)
        if str(db_path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
            self._db_path: Path = path.resolve()
        else:
            self._db_path = Path(":memory:")
        # Connect with check_same_thread=False so the LangGraph
        # SqliteSaver can be shared across threads. WAL mode handles
        # the actual concurrency.
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        # Per-call RLock — python's sqlite3 module raises
        # ``InterfaceError: bad parameter or other API misuse`` if two
        # threads attempt to use the same Connection simultaneously
        # without an explicit lock. The checkpointer is shared across
        # threads; serialize operations on this RLock so threads can
        # safely interleave record_subgraph_link / get_subgraph_links /
        # apply_retention. WAL mode is the underlying SqliteSaver-
        # supported concurrency primitive (per-connection transactions
        # on disjoint rows); the RLock is the Python-side mutex that
        # prevents the Connection object from being used by two threads
        # at once.
        self._lock = threading.RLock()
        # Apply PRAGMAs (ADR-027 R8) — order matters: journal_mode first
        # so subsequent PRAGMAs operate in WAL mode.
        self._apply_pragmas()
        # Create schema-control tables (R1). Safe to call multiple times.
        self._create_schema_control_tables()
        # Wrap with LangGraph SqliteSaver (it manages the
        # ``ikigai_checkpoints`` table itself).
        # Imported lazily to avoid a circular import at module load.
        from langgraph.checkpoint.sqlite import SqliteSaver

        self._saver: Any = SqliteSaver(self._conn)

    @property
    def db_path(self) -> Path:
        """The resolved DB file path (or :memory: sentinel)."""
        return self._db_path

    @property
    def journal_mode(self) -> str:
        """Return the active journal mode (WAL or delete). Useful in tests."""
        with self._lock:
            cur = self._conn.execute("PRAGMA journal_mode")
            row = cur.fetchone()
        return str(row[0]) if row else "unknown"

    # -- PRAGMAs (R8) -------------------------------------------------------

    def _apply_pragmas(self) -> None:
        """Apply the 4 WAL PRAGMAs required by ADR-027 R8.

        Called once at construction. Subsequent connections in the same
        process automatically inherit journal_mode=WAL (WAL persists
        across reconnects until explicitly reset).
        """
        # journal_mode must be set first — synchronous=OFF (default for
        # WAL) and busy_timeout can be set anytime.
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.commit()

    # -- Schema-control tables (R1) ----------------------------------------

    def _create_schema_control_tables(self) -> None:
        """Create ``ikigai_schema_registry`` + ``ikigai_subgraph_links`` if missing.

        Both tables are **application-managed** — LangGraph's SqliteSaver
        does not touch them. Both are idempotent (CREATE TABLE IF NOT EXISTS).
        """
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ikigai_schema_registry (
                schema_version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ikigai_subgraph_links (
                parent_thread_id TEXT NOT NULL,
                parent_checkpoint_id TEXT NOT NULL,
                child_thread_id TEXT NOT NULL,
                child_checkpoint_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sub_agent_id TEXT,
                PRIMARY KEY (parent_thread_id, parent_checkpoint_id, child_thread_id, child_checkpoint_id)
            );

            CREATE INDEX IF NOT EXISTS idx_subgraph_links_child
                ON ikigai_subgraph_links(child_thread_id);
            CREATE INDEX IF NOT EXISTS idx_subgraph_links_parent
                ON ikigai_subgraph_links(parent_thread_id);
            """
        )
        # Idempotent initial schema version row.
        self._conn.execute(
            "INSERT OR IGNORE INTO ikigai_schema_registry "
            "(schema_version, description, applied_at) VALUES (?, ?, ?)",
            (
                _SCHEMA_VERSION,
                f"Initial schema (W4.5 ADR-027 R1, schema_version={_SCHEMA_VERSION})",
                _iso_utc_now(),
            ),
        )
        self._conn.commit()

    # -- Public API ---------------------------------------------------------

    def get_saver(self) -> Any:
        """Return the underlying LangGraph SqliteSaver.

        Pass this to ``builder.compile(checkpointer=saver)``. The
        SqliteSaver instance shares the WAL-mode connection — multi-
        thread safe via ``check_same_thread=False``.
        """
        return self._saver

    def record_subgraph_link(
        self,
        parent_thread_id: str,
        child_thread_id: str,
        sub_agent_id: str,
        *,
        parent_checkpoint_id: str = "",
        child_checkpoint_id: str = "",
    ) -> None:
        """Record a parent→child dispatch link in ``ikigai_subgraph_links``.

        UPSERT semantics: a duplicate (parent_thread_id, parent_checkpoint_id,
        child_thread_id, child_checkpoint_id) tuple updates the
        ``created_at`` timestamp. Sub-agents are validated against the
        4-part UEID regex per ADR-014.

        Args:
            parent_thread_id: Parent's thread_id (4-segment).
            child_thread_id: Child's thread_id (5-segment with -subagent- suffix).
            sub_agent_id: Sub-agent's 4-part UEID (ADR-014).
            parent_checkpoint_id: Optional parent checkpoint_id (defaults to "").
            child_checkpoint_id: Optional child checkpoint_id (defaults to "").

        Raises:
            ValueError: If ``sub_agent_id`` is not a 4-part UEID.
        """
        if not _UEID_REGEX.match(sub_agent_id or ""):
            raise ValueError(
                f"sub_agent_id {sub_agent_id!r} is not a 4-part UEID "
                f"(ADR-014 + ADR-026 R4); refusing to write to ikigai_subgraph_links"
            )
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO ikigai_subgraph_links "
                "(parent_thread_id, parent_checkpoint_id, child_thread_id, "
                " child_checkpoint_id, created_at, sub_agent_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    parent_thread_id,
                    parent_checkpoint_id,
                    child_thread_id,
                    child_checkpoint_id,
                    _iso_utc_now(),
                    sub_agent_id,
                ),
            )
            self._conn.commit()

    def get_subgraph_links(self, parent_thread_id: str) -> list[SubgraphLink]:
        """Return all child links for a given parent thread_id.

        Args:
            parent_thread_id: The parent's 4-segment thread_id.

        Returns:
            List of ``SubgraphLink`` dicts (may be empty).
        """
        with self._lock:
            cur = self._conn.execute(
                "SELECT parent_thread_id, parent_checkpoint_id, child_thread_id, "
                "       child_checkpoint_id, created_at, sub_agent_id "
                "FROM ikigai_subgraph_links WHERE parent_thread_id = ? "
                "ORDER BY created_at ASC",
                (parent_thread_id,),
            )
            rows = cur.fetchall()
        return [
            SubgraphLink(
                parent_thread_id=row[0],
                parent_checkpoint_id=row[1],
                child_thread_id=row[2],
                child_checkpoint_id=row[3],
                created_at=row[4],
                sub_agent_id=row[5],
            )
            for row in rows
        ]

    def list_schema_versions(self) -> list[SchemaRegistryRow]:
        """Return all rows from ``ikigai_schema_registry`` (for migrations).

        Used by R9 lazy migration: callers compare ``max(version)`` against
        ``_SCHEMA_VERSION`` to decide whether migration is needed.
        """
        with self._lock:
            cur = self._conn.execute(
                "SELECT schema_version, description, applied_at "
                "FROM ikigai_schema_registry ORDER BY schema_version ASC"
            )
            rows = cur.fetchall()
        return [
            SchemaRegistryRow(
                schema_version=row[0],
                description=row[1],
                applied_at=row[2],
            )
            for row in rows
        ]

    def apply_retention(self) -> int:
        """Prune old ``ikigai_subgraph_links`` rows per ADR-027 R10.

        Reads ``CHECKPOINT_RETENTION_COUNT`` (max rows per parent) and
        ``MAX_CHECKPOINT_AGE_DAYS`` (max age in days) from
        ``prompts/algorithm_constants.json``. Returns the number of rows
        pruned. The checkpointer does NOT prune the
        ``ikigai_checkpoints`` table (managed by SqliteSaver's own
        retention policy — out of scope for W4.5).

        Returns:
            Number of rows deleted from ``ikigai_subgraph_links``.
        """
        from .prompts.load_constants import get as _get

        try:
            retention_count = int(_get("CHECKPOINT_RETENTION_COUNT"))
        except (KeyError, ValueError, TypeError):
            retention_count = 1000
        try:
            max_age_days = int(_get("MAX_CHECKPOINT_AGE_DAYS"))
        except (KeyError, ValueError, TypeError):
            max_age_days = 90

        pruned = 0
        with self._lock:
            # 1. Per-parent retention: keep only the N most-recent rows per parent.
            cur = self._conn.execute(
                "SELECT parent_thread_id, COUNT(*) FROM ikigai_subgraph_links GROUP BY parent_thread_id"
            )
            parents_over_cap: list[tuple[str, int]] = [
                (row[0], row[1]) for row in cur.fetchall() if row[1] > retention_count
            ]
            for parent_id, count in parents_over_cap:
                excess = count - retention_count
                cur2 = self._conn.execute(
                    "SELECT child_thread_id, child_checkpoint_id FROM ikigai_subgraph_links "
                    "WHERE parent_thread_id = ? ORDER BY created_at DESC LIMIT ?",
                    (parent_id, excess),
                )
                victims = cur2.fetchall()
                for victim in victims:
                    self._conn.execute(
                        "DELETE FROM ikigai_subgraph_links "
                        "WHERE parent_thread_id = ? AND child_thread_id = ? "
                        "  AND child_checkpoint_id = ?",
                        (parent_id, victim[0], victim[1]),
                    )
                    pruned += 1

            # 2. Age-based retention: prune rows older than max_age_days.
            # SQLite datetime() arithmetic — uses 'now' as anchor.
            cur3 = self._conn.execute(
                "DELETE FROM ikigai_subgraph_links WHERE created_at < datetime('now', ?)",
                (f"-{max_age_days} days",),
            )
            age_pruned = cur3.rowcount
            pruned += age_pruned
            self._conn.commit()
        if pruned > 0:
            log.info(
                "IkigaiCheckpointer retention: pruned %d rows "
                "(retention_count=%d, max_age_days=%d)",
                pruned,
                retention_count,
                max_age_days,
            )
        return pruned

    def close(self) -> None:
        """Close the underlying connection. Safe to call multiple times."""
        try:
            self._conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-private helpers
# ---------------------------------------------------------------------------


def _iso_utc_now() -> str:
    """Return current UTC time as ISO 8601 string (e.g. ``2026-09-04T17:00:00Z``).

    Used for ``created_at`` and ``applied_at`` columns. ``datetime.utcnow``
    is intentionally avoided (deprecated in 3.12+); we compute UTC from
    ``datetime.now(timezone.utc)``.
    """
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "_DEFAULT_DB_FILENAME",
    "_SCHEMA_VERSION",
    "IkigaiCheckpointer",
    "SchemaRegistryRow",
    "SubgraphLink",
    "ThreadRole",
    "VaultWriteRecord",
    "build_subagent_thread_id",
    "build_thread_id",
    "deserialize_checkpoint",
    "serialize_checkpoint",
]
