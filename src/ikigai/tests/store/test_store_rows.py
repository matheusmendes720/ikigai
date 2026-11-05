"""A row must become a mapping, whatever the driver hands back.

psycopg's default row factory returns plain TUPLES. `dict(row)` reads a tuple
as a sequence of pairs and fails with "cannot convert dictionary update
sequence element #0 to a sequence" — and the repository does exactly that on
every read, so every path that reads a row back was broken.

The bug only shows against a real driver, which is why this test fakes one:
the columns are in the cursor's description, and the conversion is spelled
out rather than guessed. A row is a MAPPING here, because every caller reads
it by name.
"""

from __future__ import annotations

from typing import Any

from src.data.client import rows_as_dicts


class _Column:
    def __init__(self, name: str) -> None:
        self.name = name


class _Cursor:
    def __init__(self, columns: list[str]) -> None:
        self.description = [_Column(name) for name in columns]
        self._rows: list[tuple[Any, ...]] = []

    async def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows


async def test_a_tuple_row_becomes_a_mapping() -> None:
    cursor = _Cursor(["uid", "revision"])
    rows = [("kpi:meta:aaaaaaaa:0123456789abcdef", 1)]

    assert rows_as_dicts(cursor, rows) == [
        {"uid": "kpi:meta:aaaaaaaa:0123456789abcdef", "revision": 1}
    ]


async def test_a_row_is_readable_by_name() -> None:
    """The repository reads every row by name — that is the contract."""
    cursor = _Cursor(["uid", "kind", "title"])
    rows = [("kpi:meta:aaaaaaaa:0123456789abcdef", "kpi", "Sono")]

    (row,) = rows_as_dicts(cursor, rows)

    assert row["kind"] == "kpi"
    assert row["title"] == "Sono"


async def test_no_rows_is_no_mappings() -> None:
    cursor = _Cursor(["uid"])

    assert rows_as_dicts(cursor, []) == []
