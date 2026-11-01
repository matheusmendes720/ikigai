"""Search latency over a 10k corpus (SPEC-02 T2.7).

The numbers this file produces are the ones that decide whether the store is
usable: a structured search has to stay under 50ms at p95 and a semantic one
under 150ms. If the corpus cannot be built here, the test skips and reports
that the number was NOT measured — an invented p95 would be worse than none.
"""

from __future__ import annotations

import importlib.util
import shutil
import time
from datetime import UTC, datetime

import pytest

from src.contracts.dom import ArtifactKind, SearchQuery

_HAS_DRIVER = importlib.util.find_spec("psycopg") is not None
_HAS_CONTAINERS = importlib.util.find_spec("testcontainers") is not None
_HAS_DOCKER = shutil.which("docker") is not None

requires_store = pytest.mark.skipif(
    not (_HAS_DRIVER and _HAS_CONTAINERS and _HAS_DOCKER),
    reason="needs psycopg, testcontainers and Docker to reach a real Postgres",
)

CORPUS = 10_000
SAMPLES = 50
STRUCTURED_P95_MS = 50.0
SEMANTIC_P95_MS = 150.0


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    index = max(int(len(ordered) * 0.95) - 1, 0)
    return ordered[index]


@pytest.fixture(scope="module")
def store_dsn() -> str:
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        dsn = postgres.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
        _seed(dsn)
        yield dsn


def _seed(dsn: str) -> None:
    import psycopg

    from src.contracts.migrations.apply import BOOTSTRAP_SQL, apply_pending

    with psycopg.connect(dsn) as conn:
        conn.execute(BOOTSTRAP_SQL)
        apply_pending(conn)
        conn.execute(
            "insert into ikig.artifacts (uid, kind, title, body, body_hash, quarter, status, "
            "revision, client_id, created_at, updated_at) "
            "select 'kpi:bench-' || g || ':a1b2c3d4:0123456789abcdef', "
            "case when g % 3 = 0 then 'kpi' when g % 3 = 1 then 'nota' else 'okr' end, "
            "'bench ' || g, 'texto de benchmark numero ' || g, md5(g::text), 'Q4-2026', "
            "'ativo', 1, 'bench', now(), now() "
            f"from generate_series(1, {CORPUS}) g"
        )
        conn.execute(
            "update ikig.artifacts set embedding = "
            "(('[' || array_to_string(array_fill((mod(hashtext(uid), 100) / 100.0)::float8, "
            f"array[1536]), ',') || ']'))::vector "
            "where uid ~ '^kpi:bench-[0-9]+:' "
            "and (split_part(split_part(uid, ':', 2), '-', 2)::int % 10) = 0"
        )


@requires_store
async def test_structured_search_p95(store_dsn: str) -> None:
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient(store_dsn)
    repo = ArtifactRepository(client)
    try:
        query = SearchQuery(kinds=(ArtifactKind.KPI,), quarter="Q4-2026", limit=20)
        samples: list[float] = []
        for _ in range(SAMPLES):
            started = time.perf_counter()
            result = await repo.search(query)
            samples.append((time.perf_counter() - started) * 1000)
        assert result.artifacts, "the corpus produced no rows"

        p95 = _p95(samples)
        assert p95 < STRUCTURED_P95_MS, f"structured search p95 was {p95:.1f}ms"
    finally:
        await client.close()


@requires_store
async def test_full_text_search_p95(store_dsn: str) -> None:
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient(store_dsn)
    repo = ArtifactRepository(client)
    try:
        query = SearchQuery(text="benchmark numero", limit=20)
        samples: list[float] = []
        for _ in range(SAMPLES):
            started = time.perf_counter()
            await repo.search(query)
            samples.append((time.perf_counter() - started) * 1000)

        p95 = _p95(samples)
        assert p95 < STRUCTURED_P95_MS, f"full-text search p95 was {p95:.1f}ms"
    finally:
        await client.close()


@requires_store
async def test_semantic_search_p95(store_dsn: str) -> None:
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient(store_dsn)
    repo = ArtifactRepository(client)
    try:
        query = SearchQuery(text="texto de benchmark numero", semantic=True, limit=20)
        samples: list[float] = []
        for _ in range(SAMPLES):
            started = time.perf_counter()
            await repo.search(query)
            samples.append((time.perf_counter() - started) * 1000)

        p95 = _p95(samples)
        assert p95 < SEMANTIC_P95_MS, f"semantic search p95 was {p95:.1f}ms"
    finally:
        await client.close()
