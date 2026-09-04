"""Cross-cycle memory migrations — W4.6 implementation of ADR-028 R11.

This module owns the schema-migration surface for the memory layer.
Per ADR-028 R11, ``schema_version`` is **monotonic, never reused**. The
current version is 1 (set by ``MEMORY_SCHEMA_VERSION`` in
``memory_schema.py``). Future versions follow the ADR-027 R9 pattern:

- Backward-compatible additions (e.g., a new field on
  ``DailyIntentionRecord``) → ``schema_version`` STAYS AT 1; the new
  field is ``NotRequired`` and old code reads new rows fine.
- Breaking changes (rename, drop, type change) → ``schema_version``
  INCREMENTS. Migration function ``_migrate_v1_to_v2(row)`` reads v1
  JSON, transforms to v2 shape, writes back. Migration runs **on read**
  (lazy); old rows persist for audit.

Public API:
- ``_migrate_v1_to_v2(row)`` — stub that raises ``NotImplementedError``
  until v2 ships (per ADR-028 R11 stub).
- ``apply_migrations(row, target_version)`` — applies oldest-first
  migrations until the row reaches ``target_version``. If v1→v2 is
  the only transition, this delegates to ``_migrate_v1_to_v2``.

Architectural reference:
- ADR-028 R11 — schema versioning (monotonic, lazy migration, stub)
- ADR-027 R9 — checkpoint migration pattern (parallel implementation)
- ADR-013 — planner-only; migrations are pure data transforms

Drift invariants enforced (test_canonical_scope.py):
- W4.7 — drift invariant (o) verifies migration stub raises NotImplementedError
  for v2 target.
"""

from __future__ import annotations

import logging
from typing import Any

from .memory_schema import MEMORY_SCHEMA_VERSION

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Migration stubs
# ---------------------------------------------------------------------------


def _migrate_v1_to_v2(row: dict[str, Any]) -> dict[str, Any]:
    """Migrate a v1 memory row to v2 shape (stub — ADR-028 R11).

    Per ADR-028 R11 + W4.6 brief §"Critical content" item 4: this stub
    MUST raise ``NotImplementedError`` until v2 ships. Implementers do
    NOT silently implement it — they update this stub ONLY when v2 is
    locked by a future ADR amendment, and only AFTER that ADR's W-task
    lands.

    Args:
        row: A v1-shaped row dict (memory table columns + optional
            ``schema_version`` field).

    Returns:
        A v2-shaped row dict (TBD — currently unreachable).

    Raises:
        NotImplementedError: Always — v2 is not yet specified.
    """
    raise NotImplementedError(
        "memory_migrations._migrate_v1_to_v2 is a stub per ADR-028 R11. "
        "Implement ONLY when v2 schema is locked by a future ADR amendment "
        "and the corresponding W-task lands. Do not silently implement."
    )


def apply_migrations(row: dict[str, Any], target_version: int) -> dict[str, Any]:
    """Apply oldest-first migrations until the row reaches ``target_version``.

    Per ADR-028 R11 + ADR-027 R9 (parallel pattern): migrations run
    **on read** (lazy). The current version is 1; v2 is not yet
    specified, so calling ``apply_migrations(row, target_version=2)``
    will trigger the v1→v2 stub and raise ``NotImplementedError``.

    Args:
        row: A memory row dict (in-memory representation, NOT raw DB).
        target_version: The schema version the caller wants to read at.
            Must be ≥ 1. If the row's ``schema_version`` is already
            ``target_version``, returns the row unchanged.

    Returns:
        The migrated row dict (same dict if no migration needed;
        a new dict if a migration ran). Callers should NOT mutate the
        returned dict in place.

    Raises:
        ValueError: If ``target_version`` < 1.
        NotImplementedError: If ``target_version >= 2`` (v2 not yet
            specified — stub raises per ADR-028 R11).

    Note:
        This function is **pure** — no DB calls, no I/O. Migration
        logic is decoupled from persistence (per ADR-013 planner-only).
    """
    if not isinstance(target_version, int) or target_version < 1:
        raise ValueError(f"target_version must be an integer >= 1, got {target_version!r}")

    current_version = int(row.get("schema_version", MEMORY_SCHEMA_VERSION))
    if current_version > target_version:
        # Future row read by old code: rare, but possible. The old code
        # would only see fields it knows about (TypedDict ignores unknown
        # keys), so we return the row as-is. A drift warning is logged
        # for visibility.
        log.warning(
            "apply_migrations: row schema_version=%d > target_version=%d; "
            "returning row as-is (old code reading future row — "
            "ADR-028 R11 forward-compat invariant)",
            current_version,
            target_version,
        )
        return row

    # Walk oldest-first migrations until row reaches target_version.
    # Currently the only transition is v1 -> v2 (stub). When v3 ships,
    # add v2 -> v3 here.
    migrated = dict(row)
    while int(migrated.get("schema_version", MEMORY_SCHEMA_VERSION)) < target_version:
        current = int(migrated.get("schema_version", MEMORY_SCHEMA_VERSION))
        if current == 1 and target_version >= 2:
            # v1 -> v2 transition: defer to stub (raises NotImplementedError).
            migrated = _migrate_v1_to_v2(migrated)
            # If the stub ever returns, advance the schema_version.
            migrated["schema_version"] = 2
            log.info("apply_migrations: row migrated v1 -> v2")
            continue
        # Unknown transition — guard against silent corruption.
        raise NotImplementedError(
            f"apply_migrations: no migration defined for "
            f"v{current} -> v{current + 1} (target_version={target_version}); "
            f"add a stub in memory_migrations.py when the next version is "
            f"locked by an ADR amendment (ADR-028 R11)"
        )

    return migrated


__all__ = [
    "_migrate_v1_to_v2",
    "apply_migrations",
]
