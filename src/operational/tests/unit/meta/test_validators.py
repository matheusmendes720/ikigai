"""Tests for :mod:`operational.meta.validators`."""
from __future__ import annotations

from datetime import datetime

import pytest

from operational.meta.validators import (
    validate_datetime_ordered,
    validate_period_bounds,
    validate_ueid_format,
)


class TestValidateUEID:
    def test_valid(self) -> None:
        assert validate_ueid_format("hab_morning_water") == "hab_morning_water"

    def test_non_string(self) -> None:
        with pytest.raises(TypeError):
            validate_ueid_format(123)

    def test_invalid_pattern_no_prefix(self) -> None:
        with pytest.raises(ValueError, match="Invalid UEID"):
            validate_ueid_format("bad")

    def test_invalid_pattern_uppercase(self) -> None:
        with pytest.raises(ValueError, match="Invalid UEID"):
            validate_ueid_format("HAB_water")


class TestValidateDatetimeOrdered:
    def test_valid(self) -> None:
        validate_datetime_ordered(
            datetime(2026, 6, 7, 4, 0),
            datetime(2026, 6, 7, 5, 0),
        )

    def test_equal_raises(self) -> None:
        dt = datetime(2026, 6, 7, 4, 0)
        with pytest.raises(ValueError, match="must be strictly after"):
            validate_datetime_ordered(dt, dt)

    def test_reversed_raises(self) -> None:
        with pytest.raises(ValueError, match="must be strictly after"):
            validate_datetime_ordered(
                datetime(2026, 6, 7, 5, 0),
                datetime(2026, 6, 7, 4, 0),
            )


class TestValidatePeriodBounds:
    def test_valid(self) -> None:
        assert validate_period_bounds(4, 3, 5) == 4

    def test_below_lo(self) -> None:
        with pytest.raises(ValueError, match="out of expected range"):
            validate_period_bounds(2, 3, 5)

    def test_at_or_above_hi(self) -> None:
        with pytest.raises(ValueError, match="out of expected range"):
            validate_period_bounds(5, 3, 5)
