"""SQLite-backed repository — persistent storage for Pydantic entities.

:class:`SqliteRepository[T_Entity]` stores entities as JSON blobs in a
single table (``entities``) keyed by ``(entity_type, id)``.

For a single-user local system this is the right trade-off:
- Simple schema (no per-entity DDL to maintain)
- Full-text search potential on JSON ``data``
- Single file for the whole database
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime, time
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic

from operational.persistence.base import RepositoryBase
from operational.persistence.exceptions import StorageBackendError
from operational.types import T_Entity

if TYPE_CHECKING:
    from operational.types import T_Entity


__all__ = ["SqliteRepository", "get_connection"]


_DATETIME_ISO = "%Y-%m-%dT%H:%M:%S"


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with sane defaults.

    Args:
        db_path: Path to the SQLite database file.  Use ``":memory:"``
            for a temporary in-memory database.

    Returns:
        A :class:`sqlite3.Connection` with WAL mode, foreign keys, and
        a custom JSON serializer.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def _serialize_value(value: Any) -> Any:
    """Convert non-JSON-serializable types for JSON dumps.

    Handles: ``date`` → ISO string, ``datetime`` → ISO string,
    ``time`` → ISO string, ``set`` → list, ``Enum`` → value.
    """
    if isinstance(value, datetime):
        return value.strftime(_DATETIME_ISO)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, set):
        return list(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _deserialize_value(value: Any) -> Any:
    """Reverse of :func:`_serialize_value` — applied after JSON load."""
    return value


class SqliteRepository(RepositoryBase[T_Entity], Generic[T_Entity]):
    """SQLite-backed repository.

    Args:
        model_class: Pydantic model class to deserialize into.
        entity_type: Logical type discriminator stored in the
            ``entity_type`` column (e.g. ``"routine"``, ``"habit"``).
        conn: An open SQLite :class:`sqlite3.Connection`.
        table_name: SQL table name (default ``"entities"``).

    Example:
        >>> from operational.entities.routine import Routine
        >>> conn = get_connection(":memory:")
        >>> repo = SqliteRepository(Routine, "routine", conn)
        >>> repo.count()
        0
    """
    def __init__(
        self,
        model_class: type[T_Entity],
        entity_type: str,
        conn: sqlite3.Connection,
        table_name: str = "entities",
    ) -> None:
        self._model_class = model_class
        self._entity_type = entity_type
        self._conn = conn
        self._table = table_name

    # ------------------------------------------------------------------
    # Storage engine API
    # ------------------------------------------------------------------

    def _load_all(self) -> dict[str, dict[str, Any]]:
        """Load all entities of ``self._entity_type`` from SQLite.

        Returns:
            ``{id: deserialized_dict, ...}``
        """
        query = (
            f"SELECT id, data FROM {self._table} "
            f"WHERE entity_type = ?"
        )
        try:
            rows = self._conn.execute(query, (self._entity_type,)).fetchall()
        except sqlite3.OperationalError as exc:
            # Table may not exist yet — return empty
            if "no such table" in str(exc):
                return {}
            raise StorageBackendError(
                "Failed to load %s entities" % self._entity_type,
                repository=self._entity_type,
                original_error=exc,
            ) from exc

        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            raw_data = json.loads(row["data"])
            raw_data["id"] = row["id"]
            result[row["id"]] = raw_data
        return result

    def _persist_one(self, entity_id: str, data: dict[str, Any]) -> None:
        """Upsert a single entity row."""
        serialized = json.dumps(data, default=_serialize_value, ensure_ascii=False)
        now = datetime.now(UTC).strftime(_DATETIME_ISO)
        query = (
            f"INSERT OR REPLACE INTO {self._table} "
            f"(id, entity_type, data, created_at, updated_at) "
            f"VALUES (?, ?, ?, COALESCE((SELECT created_at FROM {self._table} "
            f"WHERE id = ? AND entity_type = ?), ?), ?)"
        )
        try:
            self._conn.execute(
                query,
                (
                    entity_id,
                    self._entity_type,
                    serialized,
                    entity_id,
                    self._entity_type,
                    now,
                    now,
                ),
            )
            self._conn.commit()
        except sqlite3.OperationalError as exc:
            raise StorageBackendError(
                "Failed to persist %s entity %s" % (self._entity_type, entity_id),
                repository=self._entity_type,
                original_error=exc,
            ) from exc

    def _remove_one(self, entity_id: str) -> None:
        """Delete a single entity row."""
        query = (
            f"DELETE FROM {self._table} "
            f"WHERE id = ? AND entity_type = ?"
        )
        try:
            self._conn.execute(query, (entity_id, self._entity_type))
            self._conn.commit()
        except sqlite3.OperationalError as exc:
            raise StorageBackendError(
                "Failed to delete %s entity %s" % (self._entity_type, entity_id),
                repository=self._entity_type,
                original_error=exc,
            ) from exc

    def _serialize(self, entity: T_Entity) -> dict[str, Any]:
        """Convert entity to a plain dict (strips ``id`` — stored as PK)."""
        raw = entity.model_dump(mode="python")
        raw.pop("id", None)
        return raw

    def _deserialize(self, data: dict[str, Any]) -> T_Entity:
        """Rebuild a Pydantic entity from a plain dict."""
        return self._model_class.model_validate(data)

    # ------------------------------------------------------------------
    # DDL helpers
    # ------------------------------------------------------------------

    def ensure_table(self) -> None:
        """CREATE TABLE IF NOT EXISTS for the entities table.

        Safe to call multiple times.
        """
        ddl = (
            f"CREATE TABLE IF NOT EXISTS {self._table} (\n"
            f"    id TEXT PRIMARY KEY,\n"
            f"    entity_type TEXT NOT NULL,\n"
            f"    data TEXT NOT NULL,\n"
            f"    created_at TEXT NOT NULL,\n"
            f"    updated_at TEXT NOT NULL\n"
            f");\n"
            f"CREATE INDEX IF NOT EXISTS idx_{self._table}_type "
            f"ON {self._table}(entity_type);"
        )
        try:
            self._conn.executescript(ddl)
            self._conn.commit()
        except sqlite3.OperationalError as exc:
            raise StorageBackendError(
                "Failed to create table %s" % self._table,
                repository=self._entity_type,
                original_error=exc,
            ) from exc

    @property
    def entity_type(self) -> str:
        """Logical entity type discriminator (read-only)."""
        return self._entity_type

    def vacuum(self) -> None:
        """Reclaim storage space (VACUUM).  Expensive — call sparingly."""
        try:
            self._conn.execute("VACUUM")
        except sqlite3.OperationalError as exc:
            _vacuum_msg = "VACUUM failed"
            raise StorageBackendError(
                _vacuum_msg,
                repository=self._entity_type,
                original_error=exc,
            ) from exc
