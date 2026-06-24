"""Migration runner — applies SQL migration files to a SQLite database.

Usage::

    from operational.persistence.runner import MigrationRunner
    from operational.persistence.sqlite import get_connection

    conn = get_connection("vibe_ops.db")
    runner = MigrationRunner(conn, migration_dir=".../migrations")
    runner.apply_all()
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from operational.persistence.exceptions import MigrationError

__all__ = ["MigrationRunner", "get_applied_migrations"]


class MigrationRunner:
    """Apply SQL migration files to a SQLite connection.

    Args:
        conn: Open SQLite connection.
        migration_dir: Path to the directory containing ``NNN_name.sql``
            files.  Defaults to ``migrations/`` next to this module.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        migration_dir: str | Path | None = None,
    ) -> None:
        self._conn = conn
        if migration_dir is None:
            migration_dir = Path(__file__).resolve().parent / "migrations"
        self._dir = Path(migration_dir)
        self._ensure_meta_table()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_all(self) -> list[str]:
        """Apply all pending migrations in sorted order.

        Returns:
            List of migration names that were applied (empty if all current).
        """
        applied = set(get_applied_migrations(self._conn))
        pending = self._discover_pending(applied)
        results: list[str] = []
        for name, path in pending:
            self._apply_one(name, path)
            results.append(name)
        return results

    def apply_one(self, migration_name: str) -> bool:
        """Apply a single migration by name (e.g. ``"001_initial"``).

        Args:
            migration_name: Migration name without the ``.sql`` extension.

        Returns:
            ``True`` if the migration was applied, ``False`` if already applied.

        Raises:
            MigrationError: If the migration file is not found or fails.
        """
        if migration_name in get_applied_migrations(self._conn):
            return False
        path = self._dir / f"{migration_name}.sql"
        if not path.exists():
            msg = f"Migration file not found: {path}"
            raise MigrationError(
                msg,
                migration_name=migration_name,
                reason="file not found",
            )
        self._apply_one(migration_name, path)
        return True

    def applied(self) -> list[str]:
        """Return the list of already-applied migration names."""
        return get_applied_migrations(self._conn)

    def pending(self) -> list[str]:
        """Return the list of migration names not yet applied."""
        applied = set(get_applied_migrations(self._conn))
        return [name for name, _ in self._discover_pending(applied)]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_meta_table(self) -> None:
        """Create the ``_migrations`` metadata table if it does not exist."""
        ddl = (
            "CREATE TABLE IF NOT EXISTS _migrations (\n"
            "    id         INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "    name       TEXT NOT NULL UNIQUE,\n"
            "    applied_at TEXT NOT NULL,\n"
            "    checksum   TEXT,\n"
            "    success    INTEGER NOT NULL DEFAULT 1\n"
            ")"
        )
        try:
            self._conn.execute(ddl)
            self._conn.commit()
        except sqlite3.OperationalError as exc:
            _meta_msg = "Failed to create _migrations metadata table"
            raise MigrationError(
                _meta_msg,
                migration_name="_init",
                reason=str(exc),
            ) from exc

    def _discover_pending(
        self,
        already_applied: set[str],
    ) -> list[tuple[str, Path]]:
        """Find all ``NNN_name.sql`` files not in ``already_applied``.

        Sorted by name (natural numeric order if ``NNN_`` prefix is used).
        """
        if not self._dir.is_dir():
            return []
        sql_files = sorted(self._dir.glob("*.sql"))
        pending: list[tuple[str, Path]] = []
        for path in sql_files:
            name = path.stem
            if name not in already_applied:
                pending.append((name, path))
        return pending

    def _apply_one(self, name: str, path: Path) -> None:
        """Execute a single SQL migration file and record it."""
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")

        try:
            self._conn.executescript(sql)
        except sqlite3.OperationalError as exc:
            # Record failure
            self._conn.execute(
                "INSERT INTO _migrations (name, applied_at, checksum, success) "
                "VALUES (?, ?, ?, 0)",
                (name, now, checksum),
            )
            self._conn.commit()
            msg = f"Migration {name!r} failed to execute"
            raise MigrationError(
                msg,
                migration_name=name,
                reason=str(exc),
            ) from exc

        self._conn.execute(
            "INSERT INTO _migrations (name, applied_at, checksum, success) "
            "VALUES (?, ?, ?, 1)",
            (name, now, checksum),
        )
        self._conn.commit()


def get_applied_migrations(conn: sqlite3.Connection) -> list[str]:
    """Return the list of successfully applied migration names.

    Args:
        conn: Open SQLite connection.

    Returns:
        Sorted list of migration names (chronological).
    """
    try:
        rows = conn.execute(
            "SELECT name FROM _migrations WHERE success = 1 ORDER BY id",
        ).fetchall()
        return [row["name"] for row in rows]
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return []
        _query_msg = "Failed to query applied migrations"
        raise MigrationError(
            _query_msg,
            migration_name="_query",
            reason=str(exc),
        ) from exc
