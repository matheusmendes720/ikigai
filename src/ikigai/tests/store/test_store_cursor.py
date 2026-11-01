"""The pagination cursor of the structured search.

The cursor is the difference between stable pagination and a query that skips
or repeats rows while another client writes. It is part of the contract
(`SearchQuery.cursor`), so the contract test lives with the contract.

These tests need no database: a fake client captures the SQL the repository
builds, which is where a cursor can be silently dropped.
"""

from __future__ import annotations

import json

import pytest

from src.contracts.dom import ArtifactKind, SearchQuery
from src.contracts.errors import InvalidPayloadError
from src.data.repository import ArtifactRepository, _decode_cursor


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


async def test_a_search_without_a_cursor_sends_no_cursor_clause() -> None:
    repo, client = _repo()
    await repo.search(SearchQuery(kinds=(ArtifactKind.KPI,), quarter="Q4-2026"))
    sql, params = client.calls[0]
    assert "updated_at, uid) <" not in sql
    assert params == ("kpi", "Q4-2026", 21)


async def test_the_cursor_reaches_the_sql() -> None:
    repo, client = _repo()
    cursor = json.dumps(["2026-11-01T12:00:00+00:00", "kpi:taxa:a1b2c3d4:0123456789abcdef"])
    await repo.search(SearchQuery(text="taxa", cursor=cursor))
    sql, params = client.calls[0]
    assert "(updated_at, uid) < (%s::timestamptz, %s)" in sql
    assert "2026-11-01T12:00:00+00:00" in params
    assert "kpi:taxa:a1b2c3d4:0123456789abcdef" in params


async def test_the_cursor_is_ordered_by_the_same_key_it_compares() -> None:
    repo, client = _repo()
    cursor = json.dumps(["2026-11-01", "kpi:x:a1b2c3d4:0123456789abcdef"])
    await repo.search(SearchQuery(cursor=cursor))
    sql, _ = client.calls[0]
    assert "order by updated_at desc, uid desc" in sql


def test_a_malformed_cursor_is_rejected() -> None:
    with pytest.raises(InvalidPayloadError):
        _decode_cursor("not json")
    with pytest.raises(InvalidPayloadError):
        _decode_cursor(json.dumps(["only-one-element"]))
    with pytest.raises(InvalidPayloadError):
        _decode_cursor(json.dumps({"updated_at": "x", "uid": "y"}))


def test_the_cursor_round_trips() -> None:
    cursor = json.dumps(["2026-11-01T12:00:00+00:00", "kpi:taxa:a1b2c3d4:0123456789abcdef"])
    updated_at, uid = _decode_cursor(cursor)
    assert updated_at == "2026-11-01T12:00:00+00:00"
    assert uid == "kpi:taxa:a1b2c3d4:0123456789abcdef"
