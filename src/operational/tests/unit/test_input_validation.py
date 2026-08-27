# tests/unit/test_input_validation.py
from datetime import time
import pytest
from operational.input_validation import validate_HHMM, parse_HHMM, validate_block_times


class TestParseHHMM:
    def test_parses_valid_hhmm(self):
        assert parse_HHMM("05:00") == (5, 0)
        assert parse_HHMM("23:59") == (23, 59)
        assert parse_HHMM("00:00") == (0, 0)
        assert parse_HHMM("12:30") == (12, 30)

    def test_rejects_invalid_format(self):
        with pytest.raises(Exception, match="HH:MM"):
            parse_HHMM("5:00")
        with pytest.raises(Exception, match="HH:MM"):
            parse_HHMM("5-00")

    def test_rejects_non_string(self):
        with pytest.raises(TypeError):
            parse_HHMM(500)  # type: ignore


class TestValidateHHMM:
    def test_parses_valid_hhmm(self):
        assert validate_HHMM("05:00") == time(5, 0)
        assert validate_HHMM("23:59") == time(23, 59)
        assert validate_HHMM("00:00") == time(0, 0)

    def test_rejects_invalid_format(self):
        with pytest.raises(ValueError, match="HH:MM"):
            validate_HHMM("5:00")
        with pytest.raises(ValueError, match="HH:MM"):
            validate_HHMM("5-00")

    def test_rejects_non_string(self):
        with pytest.raises(TypeError):
            validate_HHMM(500)  # type: ignore

    def test_rejects_out_of_range(self):
        with pytest.raises(ValueError, match="out of range"):
            validate_HHMM("25:00")
        with pytest.raises(ValueError, match="out of range"):
            validate_HHMM("12:60")


class TestValidateBlockTimes:
    def test_valid_block_ascending(self):
        start, end, dur = validate_block_times(time(5, 0), time(8, 30))
        assert start == time(5, 0)
        assert end == time(8, 30)
        assert dur == 210  # 3h30m

    def test_valid_block_exact_hour(self):
        start, end, dur = validate_block_times(time(9, 0), time(10, 0))
        assert dur == 60

    def test_rejects_end_before_start(self):
        with pytest.raises(ValueError, match="must be after"):
            validate_block_times(time(8, 30), time(5, 0))

    def test_rejects_equal_times(self):
        with pytest.raises(ValueError, match="must be after"):
            validate_block_times(time(5, 0), time(5, 0))
