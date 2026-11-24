"""The date window against the REAL store.

A recording client can prove that a clause was WRITTEN. It cannot prove the two
things a window actually promises, and both of them live in the database:

1. **The bounds are closed.** Whether a row stamped exactly on `since` comes
   back is a fact about `>=` and `<=` in Postgres. A `>` typed as a `>=` passes
   every assertion on the clause's text and silently drops the boundary row —
   so the rows here are stamped ON the bounds, not near them.
2. **The window and the page share one axis.** The cursor carries a timestamp
   as text and casts it; a window that disagreed with the ordering would repeat
   or skip rows on the second page with no error anywhere. The pagination test
   below is the one that would catch it.
3. **The cast means what it says.** `%s::timestamptz` against a `timestamptz`
   column is what makes a zone-aware parameter the same instant on both sides
   of the wire.

Needs psycopg, testcontainers and Docker; it says so when it skips, which is
what a skipped test that reports itself is for.
"""

from __future__ import annotations

import importlib.util
import shutil
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.contracts.dom import Artifact, ArtifactKind, SearchQuery, WriteRequest

_HAS_DRIVER = importlib.util.find_spec("psycopg") is not None
_HAS_CONTAINERS = importlib.util.find_spec("testcontainers") is not None
_HAS_DOCKER = shutil.which("docker") is not None

requires_store = pytest.mark.skipif(
    not (_HAS_DRIVER and _HAS_CONTAINERS and _HAS_DOCKER),
    reason="needs psycopg, testcontainers and Docker to reach a real Postgres",
)

QUARTER = "Q2-2026"

# Five rows an hour apart, and the window's bounds are TWO OF THOSE STAMPS. That
# is the whole design of the fixture: a boundary row that exists is the only
# thing that can prove a bound is closed.
DAY = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
STAMPS = [DAY + timedelta(hours=index) for index in range(5)]


def _uid(index: int) -> str:
    return f"nota:janeta{index:02d}:a1b2c3d4:0123456789abcdef"


def _title(index: int) -> str:
    return f"Nota {index:02d}"


async def _seed(repo: Any) -> None:
    """Write the five rows, each with its vector.

    Idempotent by key: the fixture runs it for every test and the store answers
    `unchanged` after the first, so the rows keep the stamps they were born with
    and a later test cannot see a row another test moved.
    """
    from src.services.embeddings import local_embedding

    for index, stamp in enumerate(STAMPS):
        artifact = Artifact(
            uid=_uid(index),
            kind=ArtifactKind.NOTA,
            title=_title(index),
            body=f"texto da {_title(index)} para a janela de datas",
            quarter=QUARTER,
            status="ativo",
            created_at=stamp,
            updated_at=stamp,
        )
        await repo.upsert(
            WriteRequest(
                artifact=artifact,
                expected_revision=None,
                idempotency_key=f"search-dates-{index}",
                client_id="laptop",
            ),
            embedding=local_embedding(_title(index)),
        )


@pytest.fixture
async def store_repo(store_dsn: str) -> Any:
    """A repository over the five dated rows, with the pool closed after."""
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient(store_dsn)
    try:
        repo = ArtifactRepository(client)
        await _seed(repo)
        yield repo
    finally:
        await client.close()


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


def _stamps(result: Any) -> list[datetime]:
    return [artifact.updated_at for artifact in result.artifacts]


@requires_store
async def test_the_rows_are_the_store_the_assertions_read(store_repo: Any) -> None:
    """The fixture's own guard: five rows, each stamped as written.

    Falsification: change the seeding and every assertion below reads a
    different corpus; this fails first and says so.
    """
    result = await store_repo.search(SearchQuery())
    assert len(result.artifacts) == len(STAMPS)
    assert sorted(_stamps(result)) == STAMPS, "the store re-stamped the rows"


@requires_store
async def test_an_artifact_stamped_exactly_on_a_bound_is_inside(store_repo: Any) -> None:
    """CLOSED on both ends, proved by rows that sit on the bounds.

    Falsification: turn either comparison strict (`>` or `<`) and the boundary
    rows vanish — this fails with two artifacts missing, not with a syntax error.
    """
    since, until = STAMPS[1], STAMPS[3]

    result = await store_repo.search(SearchQuery(since=since, until=until))

    assert _stamps(result) == [STAMPS[3], STAMPS[2], STAMPS[1]], (
        "the window is not the closed interval it documents"
    )


@requires_store
async def test_each_bound_bounds_the_side_it_names(store_repo: Any) -> None:
    """One bound is not the other, and an absent bound is not a zero.

    Falsification: default `since`/`until` to an epoch instead of None and the
    `until`-only page loses the older rows it still asks for.
    """
    newer = await store_repo.search(SearchQuery(since=STAMPS[2]))
    older = await store_repo.search(SearchQuery(until=STAMPS[2]))

    assert _stamps(newer) == [STAMPS[4], STAMPS[3], STAMPS[2]]
    assert _stamps(older) == [STAMPS[2], STAMPS[1], STAMPS[0]]
    assert {_uid(i) for i in (0, 1, 2)} == {a.uid for a in older.artifacts}


@requires_store
async def test_the_window_and_the_cursor_page_the_same_rows(store_repo: Any) -> None:
    """The window does not break pagination, and pagination does not leak it.

    Four rows are in the window and the page holds two: the second page has to
    carry the window with it, and it has to END there — the fifth row exists,
    it is simply outside. Falsification: drop `since` from the second query
    (or let the cursor outrun the window) and this sees a row the window hides,
    or a third page that should not exist.
    """
    page_one = await store_repo.search(SearchQuery(since=STAMPS[1], limit=2))
    assert _stamps(page_one) == [STAMPS[4], STAMPS[3]]
    assert page_one.next_cursor, "four rows in the window, a page of two, no cursor"

    page_two = await store_repo.search(
        SearchQuery(since=STAMPS[1], limit=2, cursor=page_one.next_cursor)
    )
    assert _stamps(page_two) == [STAMPS[2], STAMPS[1]]
    assert page_two.next_cursor is None, "the window ended the result but not the pagination"

    # The same cursor WITHOUT the window keeps going: the row the window hides is
    # the one that would otherwise look like the end of the store.
    open_page = await store_repo.search(SearchQuery(limit=2, cursor=page_one.next_cursor))
    assert _stamps(open_page) == [STAMPS[2], STAMPS[1]]
    assert open_page.next_cursor is not None


@requires_store
async def test_the_semantic_search_is_windowed_too(store_repo: Any) -> None:
    """The vector half answers the same window as the index half.

    The clause lives in a second function, and a filter that reaches only one
    of them is a search that means two things. Falsification: delete the clause
    from `_search_semantic` and this returns five artifacts instead of three —
    with the same vector, so nothing else about the answer changes.
    """
    from src.services.embeddings import local_embedding

    text = _title(2)
    embedding = local_embedding(text)

    everything = await store_repo.search(SearchQuery(text=text, semantic=True), embedding=embedding)
    windowed = await store_repo.search(
        SearchQuery(text=text, semantic=True, since=STAMPS[2]),
        embedding=embedding,
    )

    assert len(everything.artifacts) == len(STAMPS), "the vector search found nothing at all"
    assert {a.uid for a in windowed.artifacts} == {_uid(2), _uid(3), _uid(4)}


@requires_store
async def test_an_instant_window_answers_the_row_stamped_on_it(store_repo: Any) -> None:
    """`since == until` is one instant, and the closed interval answers it.

    Falsification: treat an equal pair as empty, or make either bound strict,
    and the answer is zero rows for a request that names a row that exists.
    """
    instant = STAMPS[2]

    result = await store_repo.search(SearchQuery(since=instant, until=instant))

    assert [artifact.uid for artifact in result.artifacts] == [_uid(2)]
