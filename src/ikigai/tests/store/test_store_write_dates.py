"""The store holds the dates the artifact states.

Both `created_at` and `updated_at` are REQUIRED fields of the model, so a
writer has always stated them and the store cannot know better. The store
used to substitute its own clock for `updated_at` and to keep `created_at`
exactly as it was — which means the store held values nobody wrote, and a
comparison that decides whether a row is still correct never matched: the
ingestion rewrote the same rows on every round, forever, on a timer.

The moment of the WRITE is not lost by this: it is the `created_at` of the
revision the write appends.

These tests need no database: a fake connection captures the SQL and the
parameters the repository would send.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.contracts.dom import ArtifactKind, WriteRequest, make_uid
from src.data.repository import ArtifactRepository

CREATED = datetime(2026, 1, 15, tzinfo=UTC)
UPDATED = datetime(2026, 4, 30, tzinfo=UTC)


class _Cursor:
    def __init__(self, rowcount: int = 1) -> None:
        self.rowcount = rowcount
        self.description = None


class FakeConnection:
    """Captures the SQL the repository would send."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _Cursor:
        self.calls.append((sql, tuple(params)))
        return _Cursor()


class FakeClient:
    """A client whose transaction hands out the fake connection."""

    def __init__(self) -> None:
        self.conn = FakeConnection()

    def transaction(self) -> Any:
        client = self

        class _Transaction:
            async def __aenter__(self) -> FakeConnection:
                return client.conn

            async def __aexit__(self, *exc: Any) -> None:
                return None

        return _Transaction()

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict]:
        self.conn.calls.append((sql, tuple(params)))
        return []

    async def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict | None:
        self.conn.calls.append((sql, tuple(params)))
        return None


def _request() -> WriteRequest:
    from src.contracts.dom_kinds import NotaArtifact

    artifact = NotaArtifact.model_validate(
        {
            "uid": str(make_uid(ArtifactKind.NOTA, "nota", "aabbccdd", "0123456789abcdef")),
            "title": "Uma nota",
            "body": "o corpo",
            "body_hash": "0" * 64,
            "created_at": CREATED,
            "updated_at": UPDATED,
            "vault_path": "6_permanentes/uma-nota.md",
        }
    )
    return WriteRequest(
        artifact=artifact,
        expected_revision=1,
        idempotency_key="vault:zones:6_permanentes/uma-nota.md:abc:1",
        client_id="vault-sync",
    )


async def test_the_update_writes_the_dates_the_artifact_states() -> None:
    client = FakeClient()
    repo = ArtifactRepository(client)  # type: ignore[arg-type]

    await repo.upsert(_request())

    update = next(
        (sql, params)
        for sql, params in client.conn.calls
        if sql.startswith("update ikig.artifacts")
    )
    sql, params = update
    assert "created_at=%s" in sql
    assert "updated_at=%s" in sql
    assert "updated_at=now()" not in sql, "the store must not fabricate the date"
    assert CREATED in params
    assert UPDATED in params


async def test_the_create_writes_the_dates_the_artifact_states() -> None:
    client = FakeClient()
    repo = ArtifactRepository(client)  # type: ignore[arg-type]
    request = _request()
    request = request.model_copy(update={"expected_revision": None})

    await repo.upsert(request)

    insert = next(
        (sql, params)
        for sql, params in client.conn.calls
        if sql.startswith("insert into ikig.artifacts")
    )
    sql, params = insert
    assert "created_at" in sql
    assert "updated_at" in sql
    assert CREATED in params
    assert UPDATED in params
