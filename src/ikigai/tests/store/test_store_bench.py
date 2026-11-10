"""Search latency over a 10k corpus (SPEC-02 T2.7).

The spec names two criteria for this step, and they are different things:

* "busca por índice estruturado é rápida" — a 10k corpus, with the STRUCTURED
  search under 50ms at p95 and the SEMANTIC one under 150ms;
* "o planner usa índice" — `explain analyze` shows an Index Scan, not a Seq
  Scan. A search that greps the table is the same thing the indexes exist to
  prevent, and a latency number alone cannot tell the two apart.

Both need a corpus on which a search is a SEARCH. A term that matches every
row, or a quarter that covers a third of the vault, is answered correctly by
a Seq Scan — the planner is right, and no assertion about index usage could
ever hold. So the corpus here is selective the way a vault is: a phrase on a
few per cent of the rows, a quarter on a few per cent, embeddings on the rest
of the pool.

Three things have to be true for a number here to mean anything:

* the corpus must be ANALYSED, or the planner works blind;
* the statement must be WARMED UP, or the measurement reports the plan change
  the server makes in the first few executions instead of the search;
* the corpus must be selective, or the planner is right to scan.

If the corpus cannot be built here, the test skips and reports that the
number was NOT measured — an invented p95 would be worse than none.

THE PENDING LIST — why the corpus is VACUUMED, and not only ANALYSED

The migrations run first and the seed second, so the GIN index already exists
when the corpus is written: every row of the corpus lands in the index's
PENDING LIST instead of in the index itself. The pending list is merged into
the index by a VACUUM, and until it is merged the planner prices a scan of
that index as if it had to read the whole list — so it refuses the index and
answers the search with a scan of the table.

Measured on this corpus, the same query, before and after the VACUUM:

    before:  Seq Scan on artifacts                    (cost=0.00..507.00)
              index: 138 pages                        execution: 8,3 ms
    after:   Bitmap Index Scan on ix_artifacts_search_vector  (cost=0.00..21.54)
              index: 220 pages                        execution: 1,7 ms

Both answers are correct and both are fast. Only one of them is the search
the indexes exist for, and what separates them is not the corpus — it is
whether the index was settled before anybody asked.

This is what production looks like: the migration builds the index over the
rows that ALREADY EXIST, and a CREATE INDEX writes them straight into the
index rather than into a pending list. The store's index is settled the
moment the migration commits.
"""

from __future__ import annotations

import importlib.util
import shutil
import time
from collections.abc import Sequence
from typing import Any

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
WARMUP = 15
STRUCTURED_P95_MS = 50.0
SEMANTIC_P95_MS = 150.0

# How much of the corpus carries what. A phrase on two per cent of the rows,
# a quarter on one, embeddings on a tenth: the shape of a vault, where a
# search finds a handful and not the whole thing.
PHRASE_EVERY = 50
QUARTER_EVERY = 100
EMBEDDED_EVERY = 10


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    index = max(int(len(ordered) * 0.95) - 1, 0)
    return ordered[index]


def _query_vector(text: str) -> list[float]:
    """The vector of a query, as the service layer would produce it.

    The repository does not embed the query: it RECEIVES the vector (ADR-039),
    because the data layer does not know which model wrote the rows and a
    query vector from another model lands in another space. A test that calls
    the repository directly therefore has to hand it one — and the one it
    hands is the one the service would.
    """
    from src.services.embeddings import local_embedding

    return local_embedding(text)


async def _settle(
    repo: Any,
    query: SearchQuery,
    embedding: Sequence[float] | None = None,
) -> None:
    """Run the query until the statement settles on its plan.

    The driver prepares a statement after a few executions, and the server
    then chooses between a custom plan — the parameter's value known, so the
    planner can price the exact result set — and a generic one, where the
    parameter is unknown. The two are not the same query, so they are not
    the same latency.

    The switch happens in the first handful of executions, and a p95 over
    fifty samples lands squarely inside that band. So the measurement was
    reporting the plan change, not the search. A warm-up is what a benchmark
    owes the statement it measures.
    """
    for _ in range(WARMUP):
        await repo.search(query, embedding=embedding)


class _RecordingClient:
    """A client that remembers the SQL and forwards it to the real one.

    The plan is explained for the SQL the repository ACTUALLY sends, not for
    a copy of it written in the test: a test that keeps its own copy of the
    query is a test of the copy.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[Any]:
        self.calls.append((sql, tuple(params)))
        return await self._inner.execute(sql, params)

    async def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        self.calls.append((sql, tuple(params)))
        return await self._inner.fetch_one(sql, params)


@pytest.fixture(scope="module")
def store_dsn() -> str:
    from testcontainers.postgres import PostgresContainer

    from src.data.client import with_connect_timeout

    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        dsn = postgres.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
        # The container publishes on IPv4, and 'localhost' resolves to IPv6
        # FIRST — an address nothing listens on, which the driver waits out
        # for the whole OS connect timeout (measured here: 130 seconds)
        # before it tries the next one. The address is named, and the attempt
        # is bounded, so the seed does not spend two minutes on an address
        # that cannot answer.
        dsn = dsn.replace("localhost", "127.0.0.1")
        dsn = with_connect_timeout(dsn)
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
            "'bench ' || g, "
            "case when g % " + str(PHRASE_EVERY) + " = 0 then 'texto de benchmark numero ' || g "
            "else 'registro comum do vault ' || g end, "
            "md5(g::text), "
            "case when g % " + str(QUARTER_EVERY) + " = 0 then 'Q4-2026' else 'Q3-2026' end, "
            "'ativo', 1, 'bench', now(), now() "
            f"from generate_series(1, {CORPUS}) g"
        )
        conn.execute(
            "update ikig.artifacts set embedding = "
            "(('[' || array_to_string(array_fill((mod(hashtext(uid), 100) / 100.0)::float8, "
            "array[1536]), ',') || ']'))::vector "
            "where uid ~ '^kpi:bench-[0-9]+:' "
            "and (split_part(split_part(uid, ':', 2), '-', 2)::int % "
            + str(EMBEDDED_EVERY)
            + ") = 0"
        )
        # The corpus is analysed before it is queried. A table that has just
        # been written to has no statistics, and a planner working blind does
        # not pick the plan the indexes were built for. Autovacuum analyses
        # this in the deployment; the bench has to do it itself, or it
        # measures a planner that has never seen the corpus it searches.
        conn.execute("analyze ikig.artifacts")
        # And it is VACUUMED, which is a different thing and matters more
        # than it looks.
        #
        # The corpus was written AFTER the index was created, so it is all
        # in the GIN's pending list — and the planner prices an index with a
        # pending list as if it had to read the whole list. It therefore
        # refuses the index and scans the table: the search still answers,
        # still fast, but not through the index the store was given.
        #
        # The VACUUM merges the pending list into the index (measured on this
        # corpus: the index grows from 138 to 220 pages) and the planner
        # picks the index again. This is what production looks like — the
        # migration builds the index over the rows that already exist, and
        # a CREATE INDEX writes them straight into the index.
        conn.commit()
        conn.autocommit = True
        try:
            conn.execute("vacuum (analyze) ikig.artifacts")
        finally:
            conn.autocommit = False


@requires_store
async def test_structured_search_p95(store_dsn: str) -> None:
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient(store_dsn)
    repo = ArtifactRepository(client)
    try:
        query = SearchQuery(kinds=(ArtifactKind.KPI,), quarter="Q4-2026", limit=20)
        await _settle(repo, query)
        samples: list[float] = []
        for _ in range(SAMPLES):
            started = time.perf_counter()
            result = await repo.search(query)
            samples.append((time.perf_counter() - started) * 1000)
        assert result.artifacts, "the corpus produced no rows"

        p95 = _p95(samples)
        # The number is the acceptance criterion, so it is printed whether or
        # not the assertion holds: a p95 that only exists inside a failure
        # message is not a measurement anyone can check.
        print(f"structured search p95 = {p95:.1f}ms over {SAMPLES} samples of {CORPUS} rows")
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
        await _settle(repo, query)
        samples: list[float] = []
        for _ in range(SAMPLES):
            started = time.perf_counter()
            await repo.search(query)
            samples.append((time.perf_counter() - started) * 1000)

        p95 = _p95(samples)
        print(f"full-text search p95 = {p95:.1f}ms over {SAMPLES} samples of {CORPUS} rows")
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
        embedding = _query_vector(query.text or "")
        await _settle(repo, query, embedding)
        samples: list[float] = []
        for _ in range(SAMPLES):
            started = time.perf_counter()
            await repo.search(query, embedding=embedding)
            samples.append((time.perf_counter() - started) * 1000)

        p95 = _p95(samples)
        print(f"semantic search p95 = {p95:.1f}ms over {SAMPLES} samples of {CORPUS} rows")
        assert p95 < SEMANTIC_P95_MS, f"semantic search p95 was {p95:.1f}ms"
    finally:
        await client.close()


@requires_store
async def test_the_planner_uses_an_index(store_dsn: str) -> None:
    """SPEC-02 T2.7: `explain analyze` shows an Index Scan, not a Seq Scan.

    The latency numbers cannot tell a search from a grep: both can be fast
    on a small table, and both can be slow on a large one. This is the
    criterion that tells them apart, and it is the one the indexes exist for.

    The plan is explained for the SQL the repository sends, captured from the
    repository itself — a test that keeps its own copy of the query is a
    test of the copy.
    """
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient(store_dsn)
    try:
        searches = {
            "structured": (
                SearchQuery(kinds=(ArtifactKind.KPI,), quarter="Q4-2026", limit=20),
                None,
            ),
            "full-text": (SearchQuery(text="benchmark numero", limit=20), None),
            "semantic": (
                SearchQuery(text="texto de benchmark numero", semantic=True, limit=20),
                _query_vector("texto de benchmark numero"),
            ),
        }
        for name, (query, embedding) in searches.items():
            recorder = _RecordingClient(client)
            repo = ArtifactRepository(recorder)
            await repo.search(query, embedding=embedding)
            assert recorder.calls, f"the {name} search sent no SQL"
            sql, params = recorder.calls[0]
            # The plan comes back as one row per line, so it is read in full:
            # a first row alone says "Limit ..." and nothing about the scan
            # underneath it.
            rows = await client.execute(f"explain (analyze) {sql}", params)
            plan = "\n".join(str(row["QUERY PLAN"]) for row in rows)
            print(f"--- the {name} search's plan ---\n{plan}", flush=True)
            assert "Seq Scan" not in plan, (
                f"the {name} search scans the table instead of using an index: "
                f"a search that greps the vault is what the indexes exist to prevent"
            )
            assert "Index Scan" in plan, f"the {name} search used no index at all: {plan}"
    finally:
        await client.close()


@requires_store
async def test_the_search_never_recomputes_the_vector(store_dsn: str) -> None:
    """The vector is READ at query time, never recomputed.

    The plan that made this product slow was a scan that recomputed
    `to_tsvector()` — the Portuguese stemmer — over the body of every row it
    visited: 20 069 ms to stem 1 990 bodies, against 60 ms for the titles
    alone. The materialized column (`0009`) is what makes that plan
    impossible, and this is the assertion that says so BEHAVIOURIALLY:
    whatever plan the planner picks — index, bitmap, scan — the vector is
    read, never computed.

    A test that reads the migration as text can be satisfied by a perfect
    migration and a query that asks for the expression anyway. This one asks
    the server what it actually did, on the SQL the repository sends.
    """
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient(store_dsn)
    try:
        searches = {
            "structured": (
                SearchQuery(kinds=(ArtifactKind.KPI,), quarter="Q4-2026", limit=20),
                None,
            ),
            "full-text": (SearchQuery(text="benchmark numero", limit=20), None),
            "semantic": (
                SearchQuery(text="texto de benchmark numero", semantic=True, limit=20),
                _query_vector("texto de benchmark numero"),
            ),
        }
        for name, (query, embedding) in searches.items():
            recorder = _RecordingClient(client)
            repo = ArtifactRepository(recorder)
            await repo.search(query, embedding=embedding)
            assert recorder.calls, f"the {name} search sent no SQL"
            sql, params = recorder.calls[0]
            rows = await client.execute(f"explain (analyze) {sql}", params)
            plan = "\n".join(str(row["QUERY PLAN"]) for row in rows)
            print(f"--- the {name} search's plan ---\n{plan}", flush=True)
            assert "to_tsvector(" not in plan, (
                f"the {name} search recomputes the vector instead of reading it: "
                f"that is the scan that cost 20 069 ms of stemming over the vault"
            )
    finally:
        await client.close()


@requires_store
async def test_the_store_carries_the_search_index(store_dsn: str) -> None:
    """The GIN over the column is IN THE STORE, not only in the migration file.

    The plan above is only possible if the index exists — and the plan is
    the only thing that proves it is USED. A migration that says it creates
    a GIN over the column, and a store where that index is absent, is a
    store whose searches are greps with extra steps. The catalogue is where
    the difference shows.
    """
    from src.data.client import DataClient

    client = DataClient(store_dsn)
    try:
        rows = await client.execute(
            "select indexdef from pg_indexes "
            "where schemaname = 'ikig' and tablename = 'artifacts' "
            "and indexname = 'ix_artifacts_search_vector'"
        )
        assert rows, (
            "the store has no ix_artifacts_search_vector: every full-text search "
            "is a scan of the table"
        )
        definition = str(rows[0]["indexdef"]).lower()
        assert "using gin (search_vector)" in definition, (
            f"the search index is not a GIN over the column: {definition}"
        )
    finally:
        await client.close()
