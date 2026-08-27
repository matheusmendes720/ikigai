"""Unit tests for :mod:`operational.parsers.time_block_parser`."""
from __future__ import annotations

from datetime import datetime

import pytest

from operational.parsers.time_block_parser import (
    parse_time_block_dict,
    parse_time_block_line,
    serialize_time_block_line,
)
from operational.enums import Period


# ---------------------------------------------------------------------------
# parse_time_block_dict
# ---------------------------------------------------------------------------


class TestParseTimeBlockDict:
    def test_minimal_dict(self) -> None:
        data = {
            "id": "blk_manha_01",
            "start": "2026-06-07T04:00:00",
            "end": "2026-06-07T05:00:00",
            "period": "MANHA",
        }
        block = parse_time_block_dict(data)
        assert block.id == "blk_manha_01"
        assert block.label == ""
        assert block.period == Period.MANHA
        assert block.start == datetime(2026, 6, 7, 4, 0)

    def test_full_dict(self) -> None:
        data = {
            "id": "blk_tarde_focus",
            "label": "Deep work session",
            "start": "2026-06-07T14:00:00",
            "end": "2026-06-07T15:50:00",
            "period": "TARDE",
            "routine_id": "rou_hardwork_s2",
            "energia_nivel": 8,
            "foco_nivel": 9,
            "notes": "Good flow",
        }
        block = parse_time_block_dict(data)
        assert block.label == "Deep work session"
        assert block.period == Period.TARDE
        assert block.routine_id == "rou_hardwork_s2"
        assert block.energia_nivel == 8

    def test_portuguese_keys(self) -> None:
        data = {
            "id": "blk_pt",
            "inicio": "2026-06-07T06:00:00",
            "fim": "2026-06-07T07:00:00",
            "periodo": "manha",
            "rotulo": "Running",
        }
        block = parse_time_block_dict(data)
        assert block.label == "Running"
        assert block.period == Period.MANHA

    def test_missing_id_raises(self) -> None:
        with pytest.raises(ValueError, match="'id' field"):
            parse_time_block_dict({"start": "2026-06-07T04:00", "end": "2026-06-07T05:00"})

    def test_missing_start_raises(self) -> None:
        with pytest.raises(ValueError, match="missing 'start'"):
            parse_time_block_dict({"id": "blk_x", "end": "2026-06-07T05:00"})

    def test_missing_end_raises(self) -> None:
        with pytest.raises(ValueError, match="missing 'end'"):
            parse_time_block_dict({"id": "blk_x", "start": "2026-06-07T05:00"})


# ---------------------------------------------------------------------------
# parse_time_block_line
# ---------------------------------------------------------------------------


class TestParseTimeBlockLine:
    def test_minimal_csv(self) -> None:
        line = "blk_1,Morning,2026-06-07T04:00:00,2026-06-07T05:00:00,MANHA"
        block = parse_time_block_line(line)
        assert block.id == "blk_1"
        assert block.label == "Morning"
        assert block.period == Period.MANHA

    def test_csv_with_routine_id(self) -> None:
        line = "blk_2,Focus,2026-06-07T14:00:00,2026-06-07T15:50:00,TARDE,rou_dev"
        block = parse_time_block_line(line)
        assert block.id == "blk_2"
        assert block.routine_id == "rou_dev"

    def test_csv_with_metrics(self) -> None:
        line = "blk_3,Code,2026-06-07T14:00:00,2026-06-07T15:50:00,TARDE,rou_dev,8,9"
        block = parse_time_block_line(line)
        assert block.energia_nivel == 8
        assert block.foco_nivel == 9

    def test_too_few_fields_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 5"):
            parse_time_block_line("a,b,c")

    def test_empty_line(self) -> None:
        with pytest.raises(ValueError):
            parse_time_block_line("")


# ---------------------------------------------------------------------------
# serialize_time_block_line
# ---------------------------------------------------------------------------


class TestSerializeTimeBlockLine:
    def test_roundtrip(self) -> None:
        line = "blk_rt,Test,2026-06-07T10:00:00,2026-06-07T11:00:00,MANHA"
        block = parse_time_block_line(line)
        out = serialize_time_block_line(block)
        assert out.startswith("blk_rt,Test,2026-06-07T10:00:00")

    def test_roundtrip_with_optional_fields(self) -> None:
        line = "blk_rt2,Test2,2026-06-07T10:00:00,2026-06-07T11:00:00,MANHA,rou_x,7,8"
        block = parse_time_block_line(line)
        out = serialize_time_block_line(block)
        parts = out.split(",")
        assert parts[5] == "rou_x"
        assert parts[6] == "7"
        assert parts[7] == "8"
