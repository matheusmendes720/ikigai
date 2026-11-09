"""The zone filter: one bucket, and nothing else.

The knowledge tree is a set of buckets, and a client that cannot ask for one
bucket gets all of them — which is the difference between "what do I know
about the project" and "here are nineteen hundred notes, some of them about
it".

The filter is a bucket, not a column: the zone is the first segment of
`vault_path`, so the store answers it with a prefix match and the client never
has to know how the path is spelled.

These tests need no database: a fake client captures the SQL the repository
builds, which is where a filter can be silently dropped — or, worse, where a
pattern that matches more than it was asked for survives unnoticed.
"""

from __future__ import annotations

from src.contracts.dom import ArtifactKind, SearchQuery
from src.data.repository import ArtifactRepository, _zone_pattern


class RecordingClient:
    """Captures the SQL the repository would send."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, sql: str, params: tuple[object, ...] = ()) -> list[dict]:
        self.calls.append((sql, tuple(params)))
        return []

    async def fetch_one(self, sql: str, params: tuple[object, ...] = ()) -> dict | None:
        self.calls.append((sql, tuple(params)))
        return None


def _repo() -> tuple[ArtifactRepository, RecordingClient]:
    client = RecordingClient()
    return ArtifactRepository(client), client  # type: ignore[arg-type]


def test_the_underscore_of_a_zone_is_escaped() -> None:
    """`_` is a wildcard in LIKE, and every zone name has one in it.

    `2_projeto` unescaped also matches `2Xprojeto` — a bucket that does not
    exist. A search that answers for a zone nobody asked for is a search that
    lies.
    """
    assert _zone_pattern("2_projeto") == "2\\_projeto/%"


def test_the_percent_of_a_zone_is_escaped() -> None:
    assert _zone_pattern("a%b") == "a\\%b/%"


def test_the_backslash_of_a_zone_is_escaped() -> None:
    assert _zone_pattern("a\\b") == "a\\\\b/%"


def test_a_trailing_slash_does_not_double() -> None:
    assert _zone_pattern("2_projeto/") == "2\\_projeto/%"


async def test_the_zone_filter_reaches_the_sql() -> None:
    repo, client = _repo()

    await repo.search(SearchQuery(zone="2_projeto"))

    sql, params = client.calls[0]
    assert "vault_path like" in sql
    assert "2\\_projeto/%" in params


async def test_the_clause_names_the_escape_character() -> None:
    """Without it, the escaped backslash is a literal backslash."""
    repo, client = _repo()

    await repo.search(SearchQuery(zone="2_projeto"))

    sql, _ = client.calls[0]
    assert "escape" in sql


async def test_a_search_without_a_zone_sends_no_zone_clause() -> None:
    repo, client = _repo()

    await repo.search(SearchQuery(kinds=(ArtifactKind.NOTA,)))

    sql, params = client.calls[0]
    assert "vault_path like" not in sql
    assert not any(isinstance(param, str) and param.endswith("/%") for param in params)


async def test_the_semantic_path_filters_by_zone_too() -> None:
    """A vector search that ignored the zone would answer with the whole tree."""
    repo, client = _repo()

    await repo.search(
        SearchQuery(text="negócio", zone="2_projeto", semantic=True),
        embedding=[0.0] * 4,
    )

    sql, params = client.calls[0]
    assert "vault_path like" in sql
    assert "2\\_projeto/%" in params
