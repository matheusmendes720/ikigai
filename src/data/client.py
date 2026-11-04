"""The Postgres client: pool, retry, transaction helper, healthcheck.

Nothing here knows what an artifact is. The client moves bytes and manages
connections; the domain lives in `src/services/`.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from typing import Any

from src.contracts.store import STORE_DSN_ENV

try:  # pragma: no cover — the driver is an optional runtime dependency
    import psycopg
    from psycopg_pool import AsyncConnectionPool
except ImportError:  # pragma: no cover
    psycopg = None
    AsyncConnectionPool = None

__all__ = [
    "DataClient",
    "StoreNotConfiguredError",
    "StoreUnavailableError",
    "rows_as_dicts",
]

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_S = 0.2


class StoreNotConfiguredError(RuntimeError):
    """The store was never configured. Nothing was attempted."""


class StoreUnavailableError(RuntimeError):
    """The store could not be reached after retrying."""


def rows_as_dicts(cursor: Any, rows: Sequence[Any]) -> list[dict[str, Any]]:
    """The rows as mappings, whatever the row factory is.

    psycopg's default row factory hands back plain TUPLES, and `dict(row)`
    reads a tuple as a sequence of pairs — which fails with "cannot convert
    dictionary update sequence element #0 to a sequence". The columns are in
    the cursor's description, so the conversion is spelled out instead of
    guessed, and it serves a tuple row and a dict row alike.

    The repository reads every row by name (`row["uid"]`), so this is the one
    place that decides what a row IS.
    """
    columns = [column.name for column in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


class DataClient:
    """A pooled connection to the single cloud store."""

    def __init__(
        self,
        dsn: str | None = None,
        *,
        min_size: int = 1,
        max_size: int = 5,
    ) -> None:
        resolved = dsn or os.environ.get(STORE_DSN_ENV)
        if not resolved:
            raise StoreNotConfiguredError(
                f"{STORE_DSN_ENV} is not set. The store connection string comes from the "
                "environment; it is never stored in the repository."
            )
        self._dsn = resolved
        self._min_size = min_size
        self._max_size = max_size
        self._pool: Any = None

    async def connect(self) -> None:
        """Open the pool. Safe to call more than once."""
        if self._pool is not None:
            return
        if AsyncConnectionPool is None:
            raise StoreUnavailableError(
                'psycopg and psycopg-pool are required to reach the store. '
                'Install them with: pip install "psycopg[binary]" psycopg-pool'
            )
        pool = AsyncConnectionPool(
            self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
            open=False,
        )
        await pool.open()
        self._pool = pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def ping(self) -> bool:
        """True when the store answers. Never raises for an unreachable store."""
        try:
            await self.execute("select 1")
        except (StoreUnavailableError, StoreNotConfiguredError):
            return False
        return True

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] = (),
    ) -> list[Mapping[str, Any]]:
        """Run a statement and return its rows."""
        await self.connect()
        return await self._retry(lambda: self._execute_once(sql, params))

    async def fetch_one(
        self,
        sql: str,
        params: Sequence[Any] = (),
    ) -> Mapping[str, Any] | None:
        rows = await self.execute(sql, params)
        return rows[0] if rows else None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Any]:
        """A transaction on a pooled connection. Rolls back if the body raises."""
        await self.connect()
        async with self._pool.connection() as conn:
            async with conn.transaction():
                yield conn

    async def _execute_once(
        self,
        sql: str,
        params: Sequence[Any],
    ) -> list[Mapping[str, Any]]:
        async with self._pool.connection() as conn:
            cursor = await conn.execute(sql, params)
            if cursor.description is None:
                return []
            return rows_as_dicts(cursor, await cursor.fetchall())

    async def _retry(self, operation):  # noqa: ANN001, ANN202 — generic callable
        """Retry transient failures with exponential backoff.

        Serialization failures and deadlocks are the database telling two
        writers to try again; they are not errors to surface. A connection that
        dropped is the network, not the query.
        """
        last: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await operation()
            except Exception as exc:  # noqa: BLE001 — re-raised below when not transient
                if not _is_transient(exc):
                    raise
                last = exc
                await asyncio.sleep(_BACKOFF_BASE_S * (2**attempt))
        raise StoreUnavailableError(
            f"the store did not answer after {_MAX_ATTEMPTS} attempts: {last}"
        ) from last


def _is_transient(exc: Exception) -> bool:
    """Whether the failure is worth retrying."""
    transient = {
        "OperationalError",
        "InterfaceError",
        "SerializationFailure",
        "DeadlockDetected",
        "ConnectionException",
    }
    return any(cls.__name__ in transient for cls in type(exc).__mro__)
