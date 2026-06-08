"""Tests for :mod:`operational.cli.formatters`."""
from __future__ import annotations

from operational.cli.formatters import format_as_json, format_as_table


class TestFormatAsJson:
    def test_dict(self) -> None:
        out = format_as_json({"a": 1, "b": 2})
        assert '"a": 1' in out

    def test_list(self) -> None:
        out = format_as_json([1, 2, 3])
        assert "1" in out
        assert "2" in out
        assert "3" in out


class TestFormatAsTable:
    def test_simple_table(self) -> None:
        out = format_as_table(["ID", "Name"], [["1", "Foo"], ["2", "Bar"]])
        assert "ID" in out
        assert "Foo" in out
        assert "Bar" in out
        lines = out.split("\n")
        assert len(lines) >= 3

    def test_empty_rows(self) -> None:
        out = format_as_table(["ID"], [])
        assert "ID" in out
