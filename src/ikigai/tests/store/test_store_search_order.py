"""The ORDER BY of the semantic search, and what a tie-break would cost.

The semantic search orders by distance and by NOTHING ELSE. That reads like a
defect — an ORDER BY with no tie-break is not a total order, and two rows at
the same distance can come back in either order. It was measured before it was
changed, and the measurement said the tie-break is more expensive than the
defect.

MEASURED on the live store (2026-11-09, 1954 artefacts, `EXPLAIN ANALYZE`):

    order by embedding <=> v            Index Scan using ix_artifacts_embedding_hnsw
                                        48 ms · 534 buffers
    order by embedding <=> v, uid       Seq Scan on artifacts + Sort (top-N heapsort)
                                        144 ms · 7060 buffers

A second sort key takes the ANN index away. PostgreSQL cannot serve
`ORDER BY distance, uid` from an index that only knows `distance`, so it falls
back to an exact scan of every row and sorts them: three times the time,
thirteen times the pages, and a cost that grows with the vault.

And the tie it would break does not exist. The top 200 distances of the live
vault hold ZERO groups with the same distance, and the search already repeats
itself — three consecutive runs returned the same twenty uids in the same
order (gate G5) — because the index scan returns the rows already ordered by
distance.

So the tie-break is NOT added. This test is here so that the next session
does not "fix" the determinism and lose the index.
"""

from __future__ import annotations

from src.contracts.dom import SearchQuery
from src.data.repository import ArtifactRepository


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


async def test_the_semantic_search_orders_by_the_distance_alone() -> None:
    """No tie-break — and the reason is a measurement, not an oversight."""
    repo, client = _repo()

    await repo.search(SearchQuery(text="taxa", semantic=True), embedding=[0.0, 1.0])

    sql, _ = client.calls[0]
    assert "order by embedding <=> %s::vector limit %s" in sql
    assert "order by embedding <=> %s::vector, uid" not in sql, (
        "a tie-break in the semantic ORDER BY costs the HNSW index — see this file's header"
    )


async def test_the_vector_and_the_limit_reach_the_sql_in_that_order() -> None:
    """The parameter order is the contract.

    A swapped pair would not fail loudly: the query would still run, and the
    limit would be compared against a vector — returning rows nobody asked
    for, with no error anywhere.
    """
    repo, client = _repo()

    await repo.search(SearchQuery(text="taxa", semantic=True, limit=7), embedding=[0.0, 1.0])

    sql, params = client.calls[0]
    assert params[-1] == 7, "the limit is not the last parameter"
    assert str(params[-2]).startswith("["), "the vector is not the parameter before the limit"
    assert sql.rstrip().endswith("limit %s")


async def test_the_structured_search_is_a_total_order() -> None:
    """The other half of the rule: this one DOES break its ties.

    Every ORDER BY in the store is total — the structured path ends with
    `uid desc`, and `uid` is unique. The semantic path cannot, and this file
    says why.
    """
    repo, client = _repo()

    await repo.search(SearchQuery(text="taxa"))

    sql, _ = client.calls[0]
    assert "order by updated_at desc, uid desc" in sql
