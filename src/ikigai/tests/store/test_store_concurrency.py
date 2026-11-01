"""Concurrency against a real Postgres (SPEC-02 T2.6).

This is the test that proves the optimistic write. It needs a real database:
the behaviour under test is the SQL's `where revision = $2` guard, and a
double would only prove that the double behaves as written.

The test skips — loudly — when Docker, testcontainers or the driver are
missing. It never passes silently and it never invents a result.
"""

from __future__ import annotations

import asyncio
import importlib.util
import shutil
from datetime import UTC, datetime

import pytest

from src.contracts.dom import Artifact, ArtifactKind, WriteRequest
from src.contracts.errors import ConflictError

_HAS_DRIVER = importlib.util.find_spec("psycopg") is not None
_HAS_CONTAINERS = importlib.util.find_spec("testcontainers") is not None
_HAS_DOCKER = shutil.which("docker") is not None

requires_store = pytest.mark.skipif(
    not (_HAS_DRIVER and _HAS_CONTAINERS and _HAS_DOCKER),
    reason="needs psycopg, testcontainers and Docker to reach a real Postgres",
)

NOW = datetime.now(UTC)


def _apply_migrations(dsn: str) -> None:
    import psycopg

    from src.contracts.migrations.apply import BOOTSTRAP_SQL, apply_pending

    with psycopg.connect(dsn) as conn:
        conn.execute(BOOTSTRAP_SQL)
        apply_pending(conn)


@pytest.fixture(scope="module")
def store_dsn() -> str:
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        dsn = postgres.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
        _apply_migrations(dsn)
        yield dsn


@requires_store
async def test_two_clients_writing_the_same_artifact(store_dsn: str) -> None:
    """One writer wins, the other is told it lost. Nothing is overwritten."""
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient(store_dsn)
    repo = ArtifactRepository(client)
    uid = "kpi:concorrencia:a1b2c3d4:0123456789abcdef"

    def artifact(title: str) -> Artifact:
        return Artifact(
            uid=uid,
            kind=ArtifactKind.KPI,
            title=title,
            created_at=NOW,
            updated_at=NOW,
        )

    try:
        created = await repo.upsert(
            WriteRequest(
                artifact=artifact("original"),
                expected_revision=None,
                idempotency_key="conc-create",
                client_id="laptop",
            )
        )
        assert created.outcome == "created"

        results = await asyncio.gather(
            repo.upsert(
                WriteRequest(
                    artifact=artifact("do laptop"),
                    expected_revision=1,
                    idempotency_key="conc-a",
                    client_id="laptop",
                )
            ),
            repo.upsert(
                WriteRequest(
                    artifact=artifact("do celular"),
                    expected_revision=1,
                    idempotency_key="conc-b",
                    client_id="phone",
                )
            ),
            return_exceptions=True,
        )

        successes = [r for r in results if not isinstance(r, BaseException)]
        conflicts = [r for r in results if isinstance(r, ConflictError)]

        assert len(successes) == 1, f"exactly one writer must win, got {results}"
        assert len(conflicts) == 1, f"exactly one writer must be told it lost, got {results}"

        stored = await repo.get(uid)
        assert stored is not None
        assert stored.revision == 2
        assert stored.title in {"do laptop", "do celular"}
    finally:
        await client.close()


@requires_store
async def test_the_same_idempotency_key_writes_once(store_dsn: str) -> None:
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient(store_dsn)
    repo = ArtifactRepository(client)
    uid = "kpi:idem:a1b2c3d4:0123456789abcdef"
    artifact = Artifact(
        uid=uid,
        kind=ArtifactKind.KPI,
        title="uma vez",
        created_at=NOW,
        updated_at=NOW,
    )

    try:
        first = await repo.upsert(
            WriteRequest(
                artifact=artifact,
                expected_revision=None,
                idempotency_key="same-key",
                client_id="laptop",
            )
        )
        second = await repo.upsert(
            WriteRequest(
                artifact=artifact,
                expected_revision=None,
                idempotency_key="same-key",
                client_id="laptop",
            )
        )
        assert first.outcome == "created"
        assert second.outcome == "unchanged"
        assert second.revision == first.revision
    finally:
        await client.close()
