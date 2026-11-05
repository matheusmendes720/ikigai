"""The Postgres client: pool, retry, transaction helper, healthcheck.

Nothing here knows what an artifact is. The client moves bytes and manages
connections; the domain lives in `src/services/`.
"""

from __future__ import annotations

import asyncio
import os
import sys
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
    "ensure_compatible_event_loop",
    "incompatible_loop_reason",
    "rows_as_dicts",
    "with_connect_timeout",
]

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_S = 0.2
_DEFAULT_CONNECT_TIMEOUT_S = 10

# The Windows-only classes, resolved once and only on Windows. They do not
# exist on Linux, so they cannot be referenced unconditionally: the name
# would not resolve on the platform that most of this runs on.
_WINDOWS_PROACTOR_LOOP: type[asyncio.AbstractEventLoop] | None = None
_WINDOWS_SELECTOR_POLICY: type[asyncio.AbstractEventLoopPolicy] | None = None
if sys.platform == "win32":
    _WINDOWS_PROACTOR_LOOP = asyncio.ProactorEventLoop
    _WINDOWS_SELECTOR_POLICY = asyncio.WindowsSelectorEventLoopPolicy


class StoreNotConfiguredError(RuntimeError):
    """The store was never configured. Nothing was attempted."""


class StoreUnavailableError(RuntimeError):
    """The store could not be reached after retrying."""


def ensure_compatible_event_loop() -> None:
    """Install an event loop policy the driver can actually use.

    psycopg's async driver waits on the socket with ``add_reader`` and
    ``add_writer``. Windows' default policy builds a ProactorEventLoop,
    which has neither, so the driver refuses that loop outright: "Psycopg
    cannot use the 'ProactorEventLoop' to run in async mode". The refusal
    happens inside the pool's connect task, so the caller only ever sees
    "couldn't get a connection after 30.00 sec" — the cause survives in
    the driver's log alone, and every retry pays the timeout again.

    The policy has to be chosen BEFORE the loop exists, so this is called
    by the process entry points, never from inside a running loop.
    """
    if _WINDOWS_SELECTOR_POLICY is None:
        return
    if isinstance(asyncio.get_event_loop_policy(), _WINDOWS_SELECTOR_POLICY):
        return
    asyncio.set_event_loop_policy(_WINDOWS_SELECTOR_POLICY())


def incompatible_loop_reason(loop: asyncio.AbstractEventLoop) -> str | None:
    """Why this loop cannot drive the driver, or None if it can.

    The same condition the driver itself refuses, named here so the
    failure says what is wrong instead of timing out.
    """
    if _WINDOWS_PROACTOR_LOOP is None:
        return None
    if isinstance(loop, _WINDOWS_PROACTOR_LOOP):
        return (
            "the store's driver cannot use this event loop: psycopg's async "
            "mode refuses Windows' ProactorEventLoop. Install a selector "
            "policy before the loop is created "
            "(asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()))."
        )
    return None


def with_connect_timeout(dsn: str, timeout_s: int = _DEFAULT_CONNECT_TIMEOUT_S) -> str:
    """The DSN with a connect timeout, unless the caller chose one.

    The driver's async connect resolves a hostname into ONE ATTEMPT PER
    ADDRESS and drives them one at a time, each with the DSN's
    `connect_timeout`. With no timeout, an address that never answers — an
    IPv6 address the database is not listening on, say — parks the connect
    indefinitely: the attempt neither succeeds nor fails, so the driver never
    moves on to the next address.

    The pool's own timeout does not help. It governs how long a caller
    WAITS for a connection, not how long a connect may take, so the worker
    stays stuck and the caller sees "couldn't get a connection after 30.00
    sec" — the symptom, with the cause nowhere in it.
    """
    if psycopg is None:
        return dsn
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    try:
        params = conninfo_to_dict(dsn)
    except Exception:  # an unparseable DSN is the caller's problem
        return dsn
    if params.get("connect_timeout"):
        return dsn
    try:
        return make_conninfo(dsn, connect_timeout=timeout_s)
    except Exception:  # the driver's own error is clearer
        return dsn


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
    return [dict(zip(columns, row, strict=True)) for row in rows]


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
        self._dsn = with_connect_timeout(resolved)
        self._min_size = min_size
        self._max_size = max_size
        self._pool: Any = None

    async def connect(self) -> None:
        """Open the pool. Safe to call more than once."""
        if self._pool is not None:
            return
        if AsyncConnectionPool is None:
            raise StoreUnavailableError(
                "psycopg and psycopg-pool are required to reach the store. "
                'Install them with: pip install "psycopg[binary]" psycopg-pool'
            )
        reason = incompatible_loop_reason(asyncio.get_running_loop())
        if reason is not None:
            raise StoreUnavailableError(reason)
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

    async def _retry(self, operation):  # generic callable
        """Retry transient failures with exponential backoff.

        Serialization failures and deadlocks are the database telling two
        writers to try again; they are not errors to surface. A connection that
        dropped is the network, not the query.
        """
        last: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await operation()
            except Exception as exc:  # re-raised below when not transient
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
