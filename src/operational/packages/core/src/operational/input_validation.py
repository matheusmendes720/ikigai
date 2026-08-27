"""Time input validation helpers — shared between CLI (questionary) and TUI."""

from __future__ import annotations

from datetime import time

__all__ = ["parse_HHMM", "validate_HHMM", "validate_block_times"]


class HHMMValidationError(ValueError):
    """Raised when a HH:MM string is malformed or out of range."""


def parse_HHMM(value: str) -> tuple[int, int]:
    """Parse a 'HH:MM' string into (hour, minute) integers.

    Does NOT validate range. Raises HHMMValidationError on parse failure.

    Returns:
        (hour, minute) as ints.
    """
    if not isinstance(value, str):
        msg = f"expected string, got {type(value).__name__}"
        raise TypeError(msg)
    parts = value.split(":")
    if len(parts) != 2:
        msg = f"must be HH:MM, got {value!r}"
        raise HHMMValidationError(msg)
    if len(parts[0]) != 2 or len(parts[1]) != 2:
        msg = f"must be HH:MM, got {value!r}"
        raise HHMMValidationError(msg)
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        msg = f"must be HH:MM (numbers only), got {value!r}"
        raise HHMMValidationError(msg) from exc
    return hour, minute


def validate_HHMM(value: str) -> time:
    """Parse and validate a 'HH:MM' time string.

    Args:
        value: A string of the form 'HH:MM' (24-hour, zero-padded).

    Returns:
        datetime.time

    Raises:
        HHMMValidationError: If the string is not 'HH:MM' or hour/minute
            are out of range (hour 0-23, minute 0-59).
        TypeError: If value is not a string.
    """
    hour, minute = parse_HHMM(value)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        msg = f"HH:MM out of range: {value!r} (hour 0-23, minute 0-59)"
        raise HHMMValidationError(msg)
    return time(hour, minute)


def validate_block_times(start: time, end: time) -> tuple[time, time, int]:
    """Validate a time block's start < end and compute duration in minutes.

    Args:
        start: Block start time.
        end: Block end time.

    Returns:
        (start, end, duration_minutes).

    Raises:
        ValueError: If end is at or before start.
    """
    if end <= start:
        msg = "end must be after start"
        raise ValueError(msg)
    # Compute minutes difference (crossing midnight not allowed here)
    start_min = start.hour * 60 + start.minute
    end_min = end.hour * 60 + end.minute
    duration = end_min - start_min
    return start, end, duration
