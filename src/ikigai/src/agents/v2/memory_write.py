"""Cross-cycle memory write — W4.6 implementation of ADR-028.

This module provides the write-side surface for the cross-cycle memory
layer per ADR-028 R4 (atomic vault_write + memory_write sequence) and
R8 (strict append-only — no overwrites).

Public API:
- ``memory_write(...)`` — INSERT into a memory table ONLY (no vault write).
  Validates 4-part UEID, actor, and source_ueids. Strict append-only:
  raises ``ValueError`` on UEID conflict (no ``INSERT OR REPLACE``).
- ``memory_write_atomic(...)`` — atomic vault_write + memory_write wrapper
  per ADR-028 R4. On either failure, both writes roll back. This is the
  canonical entry point for skill nodes (per ADR-013 deterministic pipelines).

Per ADR-013 planner-only invariant: this module is pure data — no
computation, no scoring, no heuristics.

Architectural reference:
- ADR-028 R3 (4-part UEID discipline), R4 (atomic dual-write), R8
  (append-only), R10 (failure modes)
- ADR-012 — vault_write sole writer (every memory write flows through)
- ADR-025 — actor injection (R3: actor flows from manifest["actor"])
- ADR-013 — planner-only (no computation in write path)
- ADR-019 — algorithm_constants.json single source of truth (retention
  keys live in JSON, not Python)

Drift invariants enforced (test_canonical_scope.py):
- W4.7 — drift invariant (o) verifies 4 PRAGMAs present after memory_init
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .memory_schema import (
    ALL_MEMORY_TABLES,
    MEMORY_SCHEMA_VERSION,
    MEMORY_TABLE_DAILY,
    MEMORY_TABLE_MONTHLY,
    MEMORY_TABLE_QUARTERLY,
    MEMORY_TABLE_WEEKLY,
    _is_valid_actor,
    _is_valid_ueid,
    _validate_source_ueids,
    memory_init,
)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def memory_write(
    memory_db: Path | str,
    table: str,
    ueid: str,
    body_markdown: str,
    sha256: str,
    vault_path: str,
    actor: str,
    source_ueids: list[str] | None = None,
    ts: float | None = None,
) -> None:
    """INSERT a single row into the named memory table (append-only).

    Per ADR-028 R3 + R4 + R8:
    - Validates ``ueid`` is a 4-part UEID (regex).
    - Validates ``actor`` ∈ ``{"user", "agent", "system"}``.
    - Validates every element of ``source_ueids`` is a 4-part UEID.
    - Validates ``table`` is one of the 4 known memory tables.
    - Strict append-only: raises ``ValueError`` on ``*_ueid`` conflict
      (NO ``INSERT OR REPLACE`` — per ADR-028 R8 append-only invariant).

    Args:
        memory_db: Path to the SQLite file (created via ``memory_init``
            if it does not exist) — or ``":memory:"`` for tests.
        table: One of the 4 ``MEMORY_TABLE_*`` constants
            (``memory_daily_intentions`` etc.).
        ueid: 4-part UEID for the row's primary key column
            (``daily_ueid`` / ``weekly_ueid`` / ``monthly_ueid`` /
            ``quarterly_ueid``).
        body_markdown: Markdown body content (NOT NULL).
        sha256: SHA-256 of ``body_markdown`` (NOT NULL).
        vault_path: Relative path within vault/ (NOT NULL).
        actor: One of ``user``, ``agent``, ``system``.
        source_ueids: Optional list of 4-part UEIDs this row references.
            For daily, this is always empty (``[]``).
        ts: Unix epoch seconds (REAL). Defaults to ``time.time()`` if
            not provided.

    Raises:
        ValueError: If ``ueid``, ``actor``, ``table``, or any element of
            ``source_ueids`` fails validation, OR if a row with the same
            primary key already exists (append-only enforcement).
        sqlite3.IntegrityError: If a CHECK constraint fails (e.g., actor
            not in the allowed set — though we pre-validate).

    Note:
        This function performs ONLY the memory-table INSERT. It does NOT
        call ``vault_write``. Use ``memory_write_atomic`` for the
        canonical dual-write pattern (ADR-028 R4).
    """
    import time as _time

    # Validate table name — must be one of the 4 known memory tables.
    if table not in ALL_MEMORY_TABLES:
        raise ValueError(
            f"table {table!r} is not a recognized memory table; "
            f"expected one of {list(ALL_MEMORY_TABLES)} (ADR-028 R1)"
        )
    # Validate UEID — strict 4-part per ADR-014.
    if not _is_valid_ueid(ueid):
        raise ValueError(
            f"ueid {ueid!r} is not a 4-part UEID (ADR-014 + ADR-028 R3); refusing write"
        )
    # Validate actor.
    if not _is_valid_actor(actor):
        raise ValueError(
            f"actor {actor!r} not in {{'user', 'agent', 'system'}} "
            f"(ADR-025 R2 + ADR-028 R4); refusing write"
        )
    # Validate source_ueids (raises on invalid element).
    source_json = _validate_source_ueids(source_ueids)
    # Validate other NOT NULL fields.
    if not body_markdown:
        raise ValueError("body_markdown must be non-empty (NOT NULL constraint)")
    if not sha256:
        raise ValueError("sha256 must be non-empty (NOT NULL constraint)")
    if not vault_path:
        raise ValueError("vault_path must be non-empty (NOT NULL constraint)")

    # Resolve primary-key column name from table name.
    pk_column = _primary_key_column(table)

    # ts default = now (Unix epoch seconds).
    if ts is None:
        ts = _time.time()

    # Open the connection (memory_init applies 4 PRAGMAs and 4 tables).
    conn = memory_init(memory_db)
    try:
        # Strict append-only: plain INSERT (NO REPLACE). The PRIMARY KEY
        # constraint enforces uniqueness — duplicate INSERT raises
        # sqlite3.IntegrityError, which we re-raise as ValueError for
        # caller ergonomics.
        try:
            conn.execute(
                f"INSERT INTO {table} ({pk_column}, body_markdown, sha256, "
                f"vault_path, actor, source_ueids, ts) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ueid, body_markdown, sha256, vault_path, actor, source_json, ts),
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            # Re-raise as ValueError for append-only conflict, else propagate.
            error_str = str(exc).lower()
            if "unique" in error_str or "primary key" in error_str or "conflict" in error_str:
                raise ValueError(
                    f"append-only violation: {table}.{pk_column}={ueid!r} "
                    f"already exists (ADR-028 R8); refusing overwrite"
                ) from exc
            raise
    finally:
        conn.close()


def memory_write_atomic(
    memory_db: Path | str,
    vault_root: Path | str,
    vault_path: str,
    actor: str,
    table: str,
    ueid: str,
    body_markdown: str,
    sha256: str,
    frontmatter_fields: dict[str, Any] | None = None,
    source_ueids: list[str] | None = None,
    ts: float | None = None,
) -> dict[str, Any]:
    """Atomic vault_write + memory_write wrapper per ADR-028 R4.

    Per ADR-028 R4: both writes MUST succeed atomically OR both MUST
    roll back. On either failure, the caller sees the exception and
    the user re-invokes the skill (no automatic retry — per ADR-013
    deterministic pipelines).

    Steps:
        1. ``vault_write(vault_root, vault_path, frontmatter_fields, body, actor)``
           — writes the markdown file + audit log entry.
        2. ``memory_write(memory_db, table, ueid, body_markdown, sha256,
                            vault_path, actor, source_ueids, ts)``
           — INSERTs the SQLite row.
        3. If step 2 fails, attempt best-effort rollback of step 1
           (delete the just-written file).

    Args:
        memory_db: Path to the memory SQLite file (or ``":memory:"``).
        vault_root: Vault root directory (anchor for path resolution).
        vault_path: Relative path within vault/, e.g.
            ``"closing-2026/.../daily-{date}.md"``.
        actor: ``user`` | ``agent`` | ``system`` (ADR-025 R2).
        table: One of the 4 ``MEMORY_TABLE_*`` constants.
        ueid: 4-part UEID for the primary key column.
        body_markdown: Markdown body content.
        sha256: SHA-256 of ``body_markdown``.
        frontmatter_fields: Optional YAML frontmatter dict for the
            vault file. Defaults to a minimal dict containing
            ``{ueid, actor}`` if not provided.
        source_ueids: Optional list of 4-part UEIDs this row references.
        ts: Unix epoch seconds (REAL). Defaults to ``time.time()``.

    Returns:
        A dict containing the vault_write result (``written``, ``vault_path``,
        ``sha256``, ``actor``) augmented with ``memory_written=True``.

    Raises:
        ValueError: If validation fails (UEID, actor, source_ueids) OR
            if vault_write fails (e.g., path traversal).
        sqlite3.IntegrityError: If the memory INSERT fails for any reason
            (e.g., append-only conflict). The vault file is rolled back
            best-effort before re-raising.
    """
    # Lazy import — vault_write is the canonical writer (ADR-012). Imported
    # lazily to avoid a circular dependency at module load (memory_write
    # may be imported by vault_write-adjacent modules).
    from sys_ikigai.vault.vault_write import vault_write

    vault_root_path = Path(vault_root)
    if frontmatter_fields is None:
        frontmatter_fields = {"ueid": ueid, "actor": actor}

    # Step 1: vault_write (ADR-012 sole-writer). May raise ValueError on
    # invalid path / actor / etc.
    vault_result = vault_write(
        vault_root=vault_root_path,
        vault_path=vault_path,
        frontmatter_fields=frontmatter_fields,
        body=body_markdown,
        actor=actor,  # type: ignore[arg-type]
    )

    # Step 2: memory_write. May raise ValueError on validation or
    # append-only conflict. On any failure, attempt best-effort
    # rollback of the vault file (per ADR-028 R4 atomicity).
    try:
        memory_write(
            memory_db=memory_db,
            table=table,
            ueid=ueid,
            body_markdown=body_markdown,
            sha256=sha256,
            vault_path=vault_path,
            actor=actor,
            source_ueids=source_ueids,
            ts=ts,
        )
    except Exception:
        # Best-effort rollback of vault file. Swallow errors so we don't
        # mask the original exception.
        try:
            target = (vault_root_path / vault_path).resolve()
            if target.exists():
                target.unlink()
        except Exception as rollback_exc:  # pragma: no cover — best-effort
            log.warning(
                "memory_write_atomic rollback failed for vault_path=%s: %s",
                vault_path,
                rollback_exc,
            )
        raise

    # Both writes succeeded.
    result = dict(vault_result)
    result["memory_written"] = True
    result["memory_table"] = table
    result["memory_schema_version"] = MEMORY_SCHEMA_VERSION
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _primary_key_column(table: str) -> str:
    """Return the primary-key column name for the given memory table.

    Per ADR-028 R1: each table's PK is named ``<type>_ueid`` for clarity
    in queries and drift invariants. Daily = ``daily_ueid``,
    Weekly = ``weekly_ueid``, etc.
    """
    mapping: dict[str, str] = {
        MEMORY_TABLE_DAILY: "daily_ueid",
        MEMORY_TABLE_WEEKLY: "weekly_ueid",
        MEMORY_TABLE_MONTHLY: "monthly_ueid",
        MEMORY_TABLE_QUARTERLY: "quarterly_ueid",
    }
    return mapping[table]


__all__ = [
    "memory_write",
    "memory_write_atomic",
]
