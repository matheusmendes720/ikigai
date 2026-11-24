"""The date window of the search: `since` and `until` on the `updated_at` axis.

Three things have to hold, and only the middle one is obvious:

1. the window DEFAULTS TO OPEN. A filter wired with the wrong default silently
   narrows every search the client makes, and every one of them still answers;
2. a set bound reaches the SQL as a clause AND the parameter list, in the right
   order — a clause with no parameter, or a parameter in the wrong slot, is a
   query that runs and returns the wrong rows without an error anywhere;
3. the window is the SERVICE's policy, not the store's: an inverted interval is
   rejected before the data layer is asked, because a search that answers
   "nothing" for a request that meant "everything in June" is a silent bug.

Runs without Postgres, like every test beside it: a recording client captures
the SQL and the parameters, and the assertions are on that structure.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.contracts.dom import ArtifactKind, SearchQuery
from src.contracts.errors import InvalidPayloadError
from src.data.repository import ArtifactRepository
from src.services.artifacts import ArtifactService

START = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
END = datetime(2026, 6, 30, 23, 59, 59, tzinfo=UTC)

SINCE_CLAUSE = "updated_at >= %s::timestamptz"
UNTIL_CLAUSE = "updated_at <= %s::timestamptz"

_STRUCTURED = "order by updated_at desc, uid desc"
_SEMANTIC = "order by embedding"


def _summary_row(**overrides: object) -> dict[str, object]:
    """A row shaped like the search's projection."""
    row: dict[str, object] = {
        "uid": "kpi:taxa-conclusao:a1b2c3d4:0123456789abcdef",
        "kind": ArtifactKind.KPI,
        "title": "Taxa de conclusão",
        "body_hash": "0" * 64,
        "parent_uid": None,
        "quarter": "Q2-2026",
        "status": "on-track",
        "vault_path": "2_projeto/alfa/taxa.md",
        "revision": 1,
        "created_at": START,
        "updated_at": START,
        "deleted_at": None,
        "_semantic": 0.1,
    }
    row.update(overrides)
    return row


class RecordingClient:
    """Captures the SQL and the parameters, and answers with one canned row."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, sql: str, params: tuple[object, ...] = ()) -> list[dict]:
        self.calls.append((sql, tuple(params)))
        return [row for row in (_summary_row(),) if "from ikig.artifacts" in sql]

    async def fetch_one(self, sql: str, params: tuple[object, ...] = ()) -> dict | None:
        self.calls.append((sql, tuple(params)))
        return _summary_row()


def _repo() -> tuple[ArtifactRepository, RecordingClient]:
    client = RecordingClient()
    return ArtifactRepository(client), client  # type: ignore[arg-type]


def _search(client: RecordingClient, marker: str) -> tuple[str, tuple[object, ...]]:
    """The recorded call that IS the search.

    The semantic path fetches the query vector first, so the search is not
    necessarily the first call — the order clause is what identifies it.
    """
    calls = [call for call in client.calls if marker in call[0]]
    assert len(calls) == 1, f"expected one search statement with {marker!r}"
    return calls[0]


# ---------------------------------------------------------------------------
# 1. The contract: the fields exist, default open, and keep the model strict.
# ---------------------------------------------------------------------------


def test_the_window_defaults_to_open() -> None:
    query = SearchQuery()
    assert query.since is None
    assert query.until is None


def test_the_window_accepts_timestamps() -> None:
    query = SearchQuery(since=START, until=END)
    assert query.since == START
    assert query.until == END


def test_the_model_is_still_frozen_and_still_closed() -> None:
    """`since`/`until` did not buy the query a way to mutate or to smuggle."""
    query = SearchQuery(since=START)
    with pytest.raises(ValidationError):
        query.until = END  # type: ignore[misc]
    with pytest.raises(ValidationError):
        SearchQuery(after=START)  # type: ignore[call-arg]


def test_the_window_is_documented_in_the_schema() -> None:
    """The MCP schema is generated from the model: an absent field is unsendable."""
    properties = SearchQuery.model_json_schema()["properties"]
    assert "since" in properties
    assert "until" in properties


# ---------------------------------------------------------------------------
# 2. The repository: the clause and the parameter, in both halves.
# ---------------------------------------------------------------------------


async def test_since_reaches_the_structured_sql_as_a_lower_bound() -> None:
    repo, client = _repo()

    await repo.search(SearchQuery(since=START))

    sql, params = _search(client, _STRUCTURED)
    assert SINCE_CLAUSE in sql
    assert UNTIL_CLAUSE not in sql
    assert START in params


async def test_until_reaches_the_structured_sql_as_an_upper_bound() -> None:
    repo, client = _repo()

    await repo.search(SearchQuery(until=END))

    sql, params = _search(client, _STRUCTURED)
    assert UNTIL_CLAUSE in sql
    assert SINCE_CLAUSE not in sql
    assert END in params


async def test_both_bounds_are_joined_and_ordered() -> None:
    repo, client = _repo()

    await repo.search(SearchQuery(since=START, until=END, quarter="Q2-2026"))

    sql, params = _search(client, _STRUCTURED)
    assert f"{SINCE_CLAUSE} and {UNTIL_CLAUSE}" in sql, (
        "the bounds are not joined into the same WHERE"
    )
    # The filter parameters keep the order of the clauses, and both land before
    # the limit — the pair that would silently narrow the page instead.
    assert [p for p in params if isinstance(p, datetime)] == [START, END]
    assert params[-1] == SearchQuery().limit + 1, "the page asks for one row more than it returns"


async def test_an_open_window_changes_nothing_at_all() -> None:
    """The default: no bound, no clause, and the page the store always served."""
    repo, client = _repo()

    await repo.search(SearchQuery(kinds=(ArtifactKind.KPI,)))

    sql, params = _search(client, _STRUCTURED)
    assert SINCE_CLAUSE not in sql
    assert UNTIL_CLAUSE not in sql
    assert not any(isinstance(p, datetime) for p in params)
    assert _STRUCTURED in sql, "the ordering the cursor paginates on moved"


async def test_the_window_does_not_disturb_the_cursor() -> None:
    """A page and a window share one axis, so they must not fight over it."""
    repo, client = _repo()
    cursor = '["2026-06-15T12:00:00+00:00", "kpi:x:a1b2c3d4:0123456789abcdef"]'

    await repo.search(SearchQuery(since=START, cursor=cursor))

    sql, params = _search(client, _STRUCTURED)
    assert "(updated_at, uid) < (%s::timestamptz, %s)" in sql
    assert SINCE_CLAUSE in sql
    assert "2026-06-15T12:00:00+00:00" in params, "the cursor no longer bounds the page"
    assert sql.count("%s") == len(params), "placeholders and parameters disagree"


async def test_the_semantic_path_is_filtered_too() -> None:
    """The vector half needs the window as much as the index half does.

    It is the half that would otherwise be missed: the clause lives in a second
    function, and a filter added to one of them silently disagrees with the
    client that reads the other.
    """
    repo, client = _repo()

    await repo.search(
        SearchQuery(text="taxa", semantic=True, since=START, until=END),
        embedding=[0.0, 1.0],
    )

    sql, params = _search(client, _SEMANTIC)
    assert SINCE_CLAUSE in sql
    assert UNTIL_CLAUSE in sql
    assert "embedding" in sql
    assert START in params
    assert END in params
    assert params[-1] == SearchQuery().limit, "the limit is no longer the last parameter"


async def test_the_semantic_path_without_a_window_adds_no_clause() -> None:
    repo, client = _repo()

    await repo.search(SearchQuery(text="taxa", semantic=True), embedding=[0.0, 1.0])

    sql, params = _search(client, _SEMANTIC)
    assert "timestamptz" not in sql
    assert not any(isinstance(p, datetime) for p in params)


# ---------------------------------------------------------------------------
# 3. The service: the policy lives here, before the store is asked.
# ---------------------------------------------------------------------------


async def test_an_inverted_window_is_rejected_before_the_store_is_asked() -> None:
    repo, client = _repo()
    service = ArtifactService(repo)

    with pytest.raises(InvalidPayloadError, match="since must not be after until"):
        await service.search(SearchQuery(since=END, until=START))

    assert client.calls == [], "the store was asked with a window that matches nothing"


async def test_an_instant_window_is_a_window_and_not_a_reversal() -> None:
    """since == until is one instant on the axis, and it is inclusive."""
    repo, client = _repo()
    service = ArtifactService(repo)

    await service.search(SearchQuery(since=START, until=START))

    sql, _ = _search(client, _STRUCTURED)
    assert SINCE_CLAUSE in sql
    assert UNTIL_CLAUSE in sql


async def test_a_window_with_no_zone_on_one_side_is_rejected() -> None:
    """One stamp carries an offset and the other does not.

    Comparing them has no answer, and asking the store would not be better: it
    would read the naive one in its own session zone and return wrong rows.
    """
    repo, client = _repo()
    service = ArtifactService(repo)

    with pytest.raises(InvalidPayloadError, match="timezone offset"):
        await service.search(SearchQuery(since=datetime(2026, 6, 1), until=END))

    assert client.calls == []


async def test_the_service_passes_a_valid_window_to_the_repository() -> None:
    repo, client = _repo()
    service = ArtifactService(repo)

    await service.search(SearchQuery(since=START, until=END))

    sql, params = _search(client, _STRUCTURED)
    assert SINCE_CLAUSE in sql
    assert UNTIL_CLAUSE in sql
    assert [p for p in params if isinstance(p, datetime)] == [START, END]
