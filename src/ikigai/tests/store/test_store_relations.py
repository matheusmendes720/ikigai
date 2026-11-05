"""The edges are written with the artifact, in one transaction.

The write envelope carries the edges (SPEC-03 T3.4, and the skill specs that
need `EVIDENCES`, `PARENT_OF`, `REFERENCES` and `DERIVES_FROM`). The edge and
the node it starts have to land together: an edge whose artifact failed is a
graph that points at nothing, and an edge written on its own is a graph that
outlives the thing it describes.

So the proof here is the rollback. The edge names a destination that does not
exist, the store refuses it, and the artifact that was written in the same
transaction must be gone with it. If the edges were written in their own
transaction, the artifact would survive — and this test would fail.

The test calls the REPOSITORY, not the service: the service refuses a dangling
destination before it writes anything, which is the friendlier error, and it
would hide the transaction from the test.
"""

from __future__ import annotations

import importlib.util
import shutil
from datetime import UTC, datetime
from typing import Any

import pytest

from src.contracts.dom import (
    Artifact,
    ArtifactKind,
    Relation,
    RelationType,
    WriteRequest,
)

_HAS_DRIVER = importlib.util.find_spec("psycopg") is not None
_HAS_CONTAINERS = importlib.util.find_spec("testcontainers") is not None
_HAS_DOCKER = shutil.which("docker") is not None

requires_store = pytest.mark.skipif(
    not (_HAS_DRIVER and _HAS_CONTAINERS and _HAS_DOCKER),
    reason="needs psycopg, testcontainers and Docker to reach a real Postgres",
)

NOW = datetime.now(UTC)

SRC_UID = "nota:fonte:a1b2c3d4:0123456789abcdef"
DST_UID = "nota:destino:a1b2c3d4:0123456789abcdef"
MISSING_UID = "nota:ausente:a1b2c3d4:0123456789abcdef"
DANGLING_UID = "nota:com-aresta:a1b2c3d4:0123456789abcdef"


@pytest.fixture(scope="module")
def store_dsn() -> str:
    from testcontainers.postgres import PostgresContainer

    from src.data.client import with_connect_timeout

    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        dsn = postgres.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
        # The container publishes on IPv4, and 'localhost' resolves to IPv6
        # FIRST — an address nothing listens on, which the driver waits out
        # for the whole OS connect timeout before it tries the next one.
        dsn = dsn.replace("localhost", "127.0.0.1")
        dsn = with_connect_timeout(dsn)
        _prepare(dsn)
        yield dsn


def _prepare(dsn: str) -> None:
    import psycopg

    from src.contracts.migrations.apply import BOOTSTRAP_SQL, apply_pending

    with psycopg.connect(dsn) as conn:
        conn.execute(BOOTSTRAP_SQL)
        apply_pending(conn)


@pytest.fixture
async def repo(store_dsn: str) -> Any:
    """A repository against the real store, with the pool closed after."""
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient(store_dsn)
    try:
        yield ArtifactRepository(client)
    finally:
        await client.close()


def _artifact(uid: str, title: str) -> Artifact:
    # A NOTE has no extension table of its own, so the spine is the whole
    # artifact — the test is about the edges, not about the typed fields.
    return Artifact(
        uid=uid,
        kind=ArtifactKind.NOTA,
        title=title,
        revision=1,
        created_at=NOW,
        updated_at=NOW,
    )


def _write(
    uid: str,
    title: str,
    *,
    key: str,
    relations: tuple[Relation, ...] = (),
) -> WriteRequest:
    return WriteRequest(
        artifact=_artifact(uid, title),
        idempotency_key=key,
        client_id="owner",
        relations=relations,
    )


@requires_store
async def test_the_edges_land_with_the_artifact(repo: Any) -> None:
    await repo.upsert(_write(DST_UID, "Destino", key="rel-dst"))

    await repo.upsert(
        _write(
            SRC_UID,
            "Fonte",
            key="rel-src",
            relations=(
                Relation(
                    src_uid=SRC_UID,
                    dst_uid=DST_UID,
                    rel=RelationType.EVIDENCES,
                    meta={"why": "a fonte prova o destino"},
                ),
            ),
        )
    )

    edges = await repo.list_relations(SRC_UID)
    assert len(edges) == 1, f"the edge did not land: {edges}"
    assert str(edges[0].dst_uid) == DST_UID
    assert edges[0].rel is RelationType.EVIDENCES
    assert edges[0].meta == {"why": "a fonte prova o destino"}


@requires_store
async def test_a_dangling_edge_rolls_the_artifact_back(repo: Any) -> None:
    """The mutation check: the edge and the artifact share a transaction.

    The destination does not exist, so the store refuses the edge. If the
    artifact were written in its own transaction it would survive — and the
    store would hold a node with no graph, which is the state the envelope
    exists to prevent.
    """
    with pytest.raises(Exception):
        await repo.upsert(
            _write(
                DANGLING_UID,
                "Com aresta",
                key="rel-dangling",
                relations=(
                    Relation(
                        src_uid=DANGLING_UID,
                        dst_uid=MISSING_UID,
                        rel=RelationType.EVIDENCES,
                    ),
                ),
            )
        )

    assert await repo.get(DANGLING_UID) is None, (
        "the artifact survived a failed edge — the edges are not in the "
        "artifact's transaction"
    )
