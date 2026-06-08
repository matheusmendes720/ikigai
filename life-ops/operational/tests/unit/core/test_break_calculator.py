"""Unit tests for :mod:`operational.core.break_calculator`."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from operational.core.break_calculator import (
    BreakInfo,
    BreakStatistics,
    compute_break_minutes,
    compute_break_statistics,
    compute_breaks,
    total_block_minutes,
    total_break_minutes,
)
from operational.entities.time_block import TimeBlock
from operational.enums import Period


def _make_block(
    block_id: str,
    start: datetime,
    end: datetime,
    period: Period = Period.MANHA,
) -> TimeBlock:
    return TimeBlock(
        id=block_id,
        label=f"block-{block_id}",
        start=start,
        end=end,
        period=period,
        created_at=start,
    )


# ---------------------------------------------------------------------------
# compute_break_minutes
# ---------------------------------------------------------------------------


class TestComputeBreakMinutes:
    """Tests for compute_break_minutes()."""

    def test_15min_break(self) -> None:
        prev = _make_block("tbl_1", datetime(2026, 6, 7, 4, 0), datetime(2026, 6, 7, 5, 0))
        nxt = _make_block("tbl_2", datetime(2026, 6, 7, 5, 15), datetime(2026, 6, 7, 6, 0))
        assert compute_break_minutes(prev, nxt) == pytest.approx(15.0)

    def test_zero_break(self) -> None:
        prev = _make_block("tbl_1", datetime(2026, 6, 7, 4, 0), datetime(2026, 6, 7, 5, 0))
        nxt = _make_block("tbl_2", datetime(2026, 6, 7, 5, 0), datetime(2026, 6, 7, 6, 0))
        assert compute_break_minutes(prev, nxt) == pytest.approx(0.0)

    def test_long_break_2h30m(self) -> None:
        prev = _make_block("tbl_1", datetime(2026, 6, 7, 5, 0), datetime(2026, 6, 7, 5, 30))
        nxt = _make_block("tbl_2", datetime(2026, 6, 7, 8, 0), datetime(2026, 6, 7, 12, 0))
        assert compute_break_minutes(prev, nxt) == pytest.approx(150.0)

    def test_cross_day_break(self) -> None:
        # End at 23:00 of day N, start at 03:00 of day N+1
        prev = _make_block("tbl_1", datetime(2026, 6, 7, 22, 0), datetime(2026, 6, 7, 23, 0))
        nxt = _make_block("tbl_2", datetime(2026, 6, 8, 3, 0), datetime(2026, 6, 8, 6, 0))
        assert compute_break_minutes(prev, nxt) == pytest.approx(240.0)  # 4 hours

    def test_tiny_break_seconds_resolution(self) -> None:
        prev = _make_block("tbl_1", datetime(2026, 6, 7, 5, 0, 0), datetime(2026, 6, 7, 5, 30, 0))
        nxt = _make_block("tbl_2", datetime(2026, 6, 7, 5, 30, 30), datetime(2026, 6, 7, 6, 0, 0))
        assert compute_break_minutes(prev, nxt) == pytest.approx(0.5)

    def test_overlap_within_tolerance_returns_zero(self) -> None:
        # Overlap of 0.1 minutes = 6 seconds, within tolerance
        prev = _make_block("tbl_1", datetime(2026, 6, 7, 5, 0), datetime(2026, 6, 7, 5, 30, 6))
        nxt = _make_block("tbl_2", datetime(2026, 6, 7, 5, 30), datetime(2026, 6, 7, 6, 0))
        assert compute_break_minutes(prev, nxt) == 0.0

    def test_overlap_exceeds_tolerance_raises(self) -> None:
        prev = _make_block("tbl_1", datetime(2026, 6, 7, 5, 0), datetime(2026, 6, 7, 5, 35))
        nxt = _make_block("tbl_2", datetime(2026, 6, 7, 5, 30), datetime(2026, 6, 7, 6, 0))
        with pytest.raises(ValueError, match="overlap"):
            compute_break_minutes(prev, nxt)


# ---------------------------------------------------------------------------
# compute_breaks
# ---------------------------------------------------------------------------


class TestComputeBreaks:
    """Tests for compute_breaks()."""

    def test_empty_list(self) -> None:
        assert compute_breaks([]) == []

    def test_single_block(self) -> None:
        blocks = [_make_block("tbl_1", datetime(2026, 6, 7, 4, 0), datetime(2026, 6, 7, 5, 0))]
        assert compute_breaks(blocks) == []

    def test_two_blocks(self) -> None:
        blocks = [
            _make_block("tbl_1", datetime(2026, 6, 7, 4, 0), datetime(2026, 6, 7, 5, 0)),
            _make_block("tbl_2", datetime(2026, 6, 7, 5, 15), datetime(2026, 6, 7, 6, 0)),
        ]
        result = compute_breaks(blocks)
        assert len(result) == 1
        assert result[0].from_block_id == "tbl_1"
        assert result[0].to_block_id == "tbl_2"
        assert result[0].break_minutes == pytest.approx(15.0)
        assert not result[0].is_overlap

    def test_three_blocks(self) -> None:
        blocks = [
            _make_block("tbl_1", datetime(2026, 6, 7, 3, 0), datetime(2026, 6, 7, 5, 0)),
            _make_block("tbl_2", datetime(2026, 6, 7, 8, 0), datetime(2026, 6, 7, 12, 0)),
            _make_block("tbl_3", datetime(2026, 6, 7, 14, 0), datetime(2026, 6, 7, 17, 0)),
        ]
        result = compute_breaks(blocks)
        assert len(result) == 2
        assert result[0].break_minutes == pytest.approx(180.0)  # 3h
        assert result[1].break_minutes == pytest.approx(120.0)  # 2h

    def test_unsorted_input_is_sorted(self) -> None:
        blocks = [
            _make_block("tbl_3", datetime(2026, 6, 7, 14, 0), datetime(2026, 6, 7, 17, 0)),
            _make_block("tbl_1", datetime(2026, 6, 7, 3, 0), datetime(2026, 6, 7, 5, 0)),
            _make_block("tbl_2", datetime(2026, 6, 7, 8, 0), datetime(2026, 6, 7, 12, 0)),
        ]
        result = compute_breaks(blocks)
        assert [b.from_block_id for b in result] == ["tbl_1", "tbl_2"]
        assert [b.to_block_id for b in result] == ["tbl_2", "tbl_3"]

    def test_overlap_marked_in_breaks(self) -> None:
        blocks = [
            _make_block("tbl_1", datetime(2026, 6, 7, 5, 0), datetime(2026, 6, 7, 5, 35)),
            _make_block("tbl_2", datetime(2026, 6, 7, 5, 30), datetime(2026, 6, 7, 6, 0)),
        ]
        result = compute_breaks(blocks)
        assert len(result) == 1
        assert result[0].is_overlap
        assert result[0].overlap_minutes == pytest.approx(5.0)
        assert result[0].break_minutes == 0.0

    def test_break_info_is_frozen(self) -> None:
        blocks = [
            _make_block("tbl_1", datetime(2026, 6, 7, 5, 0), datetime(2026, 6, 7, 5, 30)),
            _make_block("tbl_2", datetime(2026, 6, 7, 5, 45), datetime(2026, 6, 7, 6, 0)),
        ]
        bi = compute_breaks(blocks)[0]
        with pytest.raises((AttributeError, TypeError)):  # frozen dataclass
            bi.break_minutes = 999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# compute_break_statistics
# ---------------------------------------------------------------------------


class TestComputeBreakStatistics:
    """Tests for compute_break_statistics()."""

    def test_empty(self) -> None:
        stats = compute_break_statistics([])
        assert stats.total_break_minutes == 0.0
        assert stats.break_count == 0
        assert stats.overlap_count == 0

    def test_single_block(self) -> None:
        blocks = [_make_block("tbl_1", datetime(2026, 6, 7, 5, 0), datetime(2026, 6, 7, 5, 30))]
        stats = compute_break_statistics(blocks)
        assert stats.break_count == 0

    def test_three_breaks(self) -> None:
        blocks = [
            _make_block("tbl_1", datetime(2026, 6, 7, 3, 0), datetime(2026, 6, 7, 5, 0)),
            _make_block("tbl_2", datetime(2026, 6, 7, 5, 30), datetime(2026, 6, 7, 8, 0)),
            _make_block("tbl_3", datetime(2026, 6, 7, 10, 0), datetime(2026, 6, 7, 12, 0)),
            _make_block("tbl_4", datetime(2026, 6, 7, 14, 0), datetime(2026, 6, 7, 17, 0)),
        ]
        stats = compute_break_statistics(blocks)
        assert stats.break_count == 3
        assert stats.total_break_minutes == pytest.approx(30 + 120 + 120)  # 30min, 2h, 2h
        assert stats.mean_break_minutes == pytest.approx(90.0)
        assert stats.min_break_minutes == pytest.approx(30.0)
        assert stats.max_break_minutes == pytest.approx(120.0)
        assert stats.overlap_count == 0

    def test_overlap_counted(self) -> None:
        blocks = [
            _make_block("tbl_1", datetime(2026, 6, 7, 5, 0), datetime(2026, 6, 7, 5, 35)),
            _make_block("tbl_2", datetime(2026, 6, 7, 5, 30), datetime(2026, 6, 7, 6, 0)),
        ]
        stats = compute_break_statistics(blocks)
        assert stats.overlap_count == 1
        assert stats.break_count == 1

    def test_all_overlaps(self) -> None:
        blocks = [
            _make_block("tbl_1", datetime(2026, 6, 7, 5, 0), datetime(2026, 6, 7, 5, 30)),
            _make_block("tbl_2", datetime(2026, 6, 7, 5, 0), datetime(2026, 6, 7, 5, 30)),
        ]
        stats = compute_break_statistics(blocks)
        # One pair, one overlap
        assert stats.break_count == 1
        assert stats.overlap_count == 1
        # No non-overlap breaks → all zeros
        assert stats.total_break_minutes == 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    """Tests for total_break_minutes and total_block_minutes."""

    def test_total_break_minutes(self) -> None:
        blocks = [
            _make_block("tbl_1", datetime(2026, 6, 7, 3, 0), datetime(2026, 6, 7, 5, 0)),
            _make_block("tbl_2", datetime(2026, 6, 7, 5, 30), datetime(2026, 6, 7, 8, 0)),
        ]
        assert total_break_minutes(blocks) == pytest.approx(30.0)

    def test_total_block_minutes(self) -> None:
        blocks = [
            _make_block("tbl_1", datetime(2026, 6, 7, 3, 0), datetime(2026, 6, 7, 5, 0)),  # 120min
            _make_block("tbl_2", datetime(2026, 6, 7, 8, 0), datetime(2026, 6, 7, 12, 0)),  # 240min
        ]
        assert total_block_minutes(blocks) == pytest.approx(360.0)

    def test_total_block_minutes_with_three(self) -> None:
        blocks = [
            _make_block("tbl_1", datetime(2026, 6, 7, 3, 0), datetime(2026, 6, 7, 5, 0)),
            _make_block("tbl_2", datetime(2026, 6, 7, 8, 0), datetime(2026, 6, 7, 12, 0)),
            _make_block("tbl_3", datetime(2026, 6, 7, 14, 0), datetime(2026, 6, 7, 17, 0)),
        ]
        assert total_block_minutes(blocks) == pytest.approx(120 + 240 + 180)

    def test_empty_helpers(self) -> None:
        assert total_break_minutes([]) == 0.0
        assert total_block_minutes([]) == 0.0
