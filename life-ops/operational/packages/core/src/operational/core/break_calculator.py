"""Break minutes calculator between TimeBlocks.

The time-blocks layer (per the user's architecture decision of
2026-06-07) captures **gross entry/exit times** for each block. This
module computes the **break minutes** between consecutive blocks,
which is the primary numerical signal for downstream metrics (rest,
energy, context switch).

**No pomodoro in this layer.** The break between two TimeBlocks is
the elapsed wall-clock time from the *end* of block N to the *start*
of block N+1. This is the **gross rest period** that the user actually
had, independent of any sub-block task tracking.

**Integrates with AjusteFino** (NL adjustments). The user can log
fine-grained adjustments between blocks (PAV §2 — ``ajusteFinos``)
that modify the net rest:

    adjusted_net_rest = net_rest + Σ(ajuste.minutos for the period)

Usage:

>>> from datetime import datetime, time
>>> from operational.entities.time_block import TimeBlock
>>> blocks = [
...     TimeBlock(id="tbl_1", label="morning", start=datetime(2026,6,7,3,30), end=datetime(2026,6,7,5,30), period=Period.MANHA, created_at=datetime(2026,6,7,3,30)),
...     TimeBlock(id="tbl_2", label="afternoon", start=datetime(2026,6,7,8,0), end=datetime(2026,6,7,12,0), period=Period.TARDE, created_at=datetime(2026,6,7,8,0)),
... ]
>>> compute_break_minutes(blocks[0], blocks[1])
150
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from operational.entities.ajuste_fino import AjusteFino
from operational.entities.time_block import TimeBlock

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from operational.enums import Period

__all__ = [
    "BreakInfo",
    "BreakStatistics",
    "adjusted_net_rest_minutes",
    "compute_break_minutes",
    "compute_break_statistics",
    "compute_breaks",
    "total_block_minutes",
    "total_break_minutes",
]


_BREAK_NEGATIVE_TOLERANCE_MIN: Final[float] = 0.5
"""Tolerance for detecting "negative breaks" (overlapping blocks).

If a block ends *after* the next block starts by more than this many
minutes, it is treated as an overlap (not a break). This guards
against user-input errors where two blocks have inconsistent times.
"""


@dataclass(frozen=True, slots=True)
class BreakInfo:
    """A single break between two consecutive TimeBlocks.

    Attributes:
        from_block_id: UEID of the block that ended.
        to_block_id: UEID of the block that started.
        break_minutes: Wall-clock rest between blocks (≥ 0).
        is_overlap: True if blocks overlap (negative break within tolerance).
        overlap_minutes: If overlap, how many minutes of overlap (positive value).
    """
    from_block_id: str
    to_block_id: str
    break_minutes: float
    is_overlap: bool
    overlap_minutes: float


def compute_break_minutes(prev: TimeBlock, next_: TimeBlock) -> float:
    """Compute break minutes between two consecutive TimeBlocks.

    Args:
        prev: The block that ended first.
        next_: The block that started after.

    Returns:
        Break in minutes (≥ 0). Returns 0 if blocks overlap (with a
        small tolerance).

    Raises:
        ValueError: If next_.start is before prev.end (overlap exceeds tolerance).
    """
    if next_.start < prev.end:
        overlap = (prev.end - next_.start).total_seconds() / 60.0
        if overlap > _BREAK_NEGATIVE_TOLERANCE_MIN:
            raise ValueError(
                "TimeBlocks overlap by %.1fmin "
                "(prev.end=%s, next.start=%s)" % (overlap, prev.end.isoformat(), next_.start.isoformat())
            )
        return 0.0
    return (next_.start - prev.end).total_seconds() / 60.0


def compute_breaks(blocks: Sequence[TimeBlock]) -> list[BreakInfo]:
    """Compute all breaks between a chronologically-sorted sequence of TimeBlocks.

    The input is sorted by start time if not already sorted.

    Args:
        blocks: A list of TimeBlocks. Can be in any order; will be sorted.

    Returns:
        A list of BreakInfo, one per consecutive pair. Length = len(blocks) - 1.
    """
    if len(blocks) <= 1:
        return []
    sorted_blocks = sorted(blocks, key=lambda b: b.start)
    breaks: list[BreakInfo] = []
    for prev, nxt in zip(sorted_blocks[:-1], sorted_blocks[1:], strict=True):
        try:
            break_min = compute_break_minutes(prev, nxt)
            breaks.append(BreakInfo(
                from_block_id=prev.id,
                to_block_id=nxt.id,
                break_minutes=break_min,
                is_overlap=False,
                overlap_minutes=0.0,
            ))
        except ValueError:
            # Compute overlap for reporting
            overlap = (prev.end - nxt.start).total_seconds() / 60.0
            breaks.append(BreakInfo(
                from_block_id=prev.id,
                to_block_id=nxt.id,
                break_minutes=0.0,
                is_overlap=True,
                overlap_minutes=overlap,
            ))
    return breaks


@dataclass(frozen=True, slots=True)
class BreakStatistics:
    """Aggregate break statistics over a day or week.

    Attributes:
        total_break_minutes: Sum of all break minutes.
        mean_break_minutes: Average break.
        max_break_minutes: Longest break.
        min_break_minutes: Shortest break (excluding overlaps).
        break_count: Number of breaks.
        overlap_count: Number of overlaps detected.
    """
    total_break_minutes: float
    mean_break_minutes: float
    max_break_minutes: float
    min_break_minutes: float
    break_count: int
    overlap_count: int


def compute_break_statistics(blocks: Sequence[TimeBlock]) -> BreakStatistics:
    """Compute aggregate break statistics.

    Args:
        blocks: List of TimeBlocks (any order; will be sorted).

    Returns:
        BreakStatistics with mean/min/max/total/overlap counts.
        Returns a zero-valued BreakStatistics if fewer than 2 blocks.
    """
    breaks = compute_breaks(blocks)
    if not breaks:
        return BreakStatistics(
            total_break_minutes=0.0,
            mean_break_minutes=0.0,
            max_break_minutes=0.0,
            min_break_minutes=0.0,
            break_count=0,
            overlap_count=0,
        )
    non_overlap_breaks = [b.break_minutes for b in breaks if not b.is_overlap]
    overlap_count = sum(1 for b in breaks if b.is_overlap)
    if not non_overlap_breaks:
        return BreakStatistics(
            total_break_minutes=0.0,
            mean_break_minutes=0.0,
            max_break_minutes=0.0,
            min_break_minutes=0.0,
            break_count=len(breaks),
            overlap_count=overlap_count,
        )
    return BreakStatistics(
        total_break_minutes=sum(non_overlap_breaks),
        mean_break_minutes=sum(non_overlap_breaks) / len(non_overlap_breaks),
        max_break_minutes=max(non_overlap_breaks),
        min_break_minutes=min(non_overlap_breaks),
        break_count=len(breaks),
        overlap_count=overlap_count,
    )


def total_break_minutes(blocks: Sequence[TimeBlock]) -> float:
    """Sum of all break minutes between consecutive blocks (excluding overlaps)."""
    return compute_break_statistics(blocks).total_break_minutes


def total_block_minutes(blocks: Sequence[TimeBlock]) -> float:
    """Sum of all block durations in minutes.

    Note: this is the **gross work time** (sum of all block durations),
    not the total elapsed time across the day.
    """
    return sum(b.duration_minutes for b in blocks)


def adjusted_net_rest_minutes(
    gross_break_minutes: float,
    from_period: Period,
    to_period: Period,
    ajustes_finos: Iterable[AjusteFino] | None = None,
    custom_overrides: dict[tuple[Period, Period], int] | None = None,
) -> float:
    """Compute **net rest** minus PAV context-switch overhead plus adjustments.

    Combines:
    1. Gross break between blocks (wall-clock)
    2. PAV context-switch overhead (from ``context_switch.context_switch_overhead_minutes``)
    3. Signed :class:`AjusteFino` adjustments in the source period

    Args:
        gross_break_minutes: Wall-clock break.
        from_period: Source period.
        to_period: Target period.
        ajustes_finos: Optional iterable of AjusteFino entries to add
            to the net rest. The function filters by ``from_period``
            and sums the signed ``minutos`` field.
        custom_overrides: Optional user-customized overrides for the
            PAV context-switch overhead matrix.

    Returns:
        Adjusted net rest in minutes (≥ 0).
    """
    from operational.core.context_switch import context_switch_overhead_minutes

    if gross_break_minutes < 0:
        raise ValueError("gross_break_minutes must be >= 0, got %s" % gross_break_minutes)
    overhead = context_switch_overhead_minutes(from_period, to_period, custom_overrides)
    net_after_overhead = max(0.0, gross_break_minutes - float(overhead))
    if ajustes_finos is None:
        return net_after_overhead
    ajuste_total = sum(a.minutos for a in ajustes_finos if a.period == from_period)
    return max(0.0, net_after_overhead + float(ajuste_total))
