"""Reusable validation utilities for entity fields."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from operational.types import UEID_PATTERN

if TYPE_CHECKING:
    from datetime import datetime

__all__ = [
    "validate_datetime_ordered",
    "validate_period_bounds",
    "validate_ueid_format",
]


def validate_ueid_format(value: Any) -> str:
    """Validate and return a UEID string.

    Args:
        value: The candidate UEID.

    Returns:
        The validated string.

    Raises:
        TypeError: If the value is not a string.
        ValueError: If the value does not match the UEID pattern.
    """
    if not isinstance(value, str):
        msg = f"UEID must be a string, got {type(value).__name__}: {value!r}"
        raise TypeError(msg)
    if not UEID_PATTERN.match(value):
        msg = f"Invalid UEID format: {value!r}"
        raise ValueError(msg)
    return value


def validate_datetime_ordered(
    start: datetime,
    end: datetime,
    *,
    name: str = "interval",
) -> None:
    """Verify ``end`` is strictly after ``start``.

    Args:
        start: Start datetime.
        end: End datetime.
        name: Human-readable name for error messages.

    Raises:
        ValueError: If ``end <= start``.
    """
    if end <= start:
        msg = (
            f"{name}: end ({end.isoformat()}) must be strictly after "
            f"start ({start.isoformat()})"
        )
        raise ValueError(msg)


def validate_period_bounds(
    hour: int,
    lo: int,
    hi: int,
    *,
    label: str = "hour",
) -> int:
    """Validate an hour falls within ``[lo, hi)``.

    Args:
        hour: The hour to validate (0-23).
        lo: Inclusive lower bound.
        hi: Exclusive upper bound.
        label: Label for error messages.

    Returns:
        The validated hour.

    Raises:
        ValueError: If the hour is out of bounds.
    """
    if not lo <= hour < hi:
        msg = f"{label} ({hour}) out of expected range [{lo}, {hi})"
        raise ValueError(
            msg
        )
    return hour
