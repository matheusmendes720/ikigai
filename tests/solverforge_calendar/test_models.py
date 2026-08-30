"""Tests for solverforge_calendar Pydantic models."""
from __future__ import annotations
from datetime import datetime
import pytest
from pydantic import ValidationError
from src.solverforge_calendar.models import SfScheduleInput, SfAvailabilityInput


def test_sf_schedule_input_minimal():
    inp = SfScheduleInput(
        ueid="sc:task:abc12345-1234-5678-9abc-def012345678:def4567890123456",
        title="BYD market research",
        start_at=datetime(2026, 9, 1, 9, 0, 0),
    )
    assert inp.title == "BYD market research"
    assert inp.blocked_by == []  # default
    assert inp.tags == []  # default
    assert inp.ikigai == {}  # default


def test_sf_schedule_input_frozen_rejects_mutation():
    inp = SfScheduleInput(
        ueid="sc:task:abc12345-1234-5678-9abc-def012345678:def4567890123456",
        title="Test",
        start_at=datetime(2026, 9, 1, 9, 0, 0),
    )
    with pytest.raises(ValidationError):
        inp.title = "Modified"


def test_sf_schedule_input_extra_field_rejected():
    with pytest.raises(ValidationError):
        SfScheduleInput(
            ueid="sc:task:abc12345-1234-5678-9abc-def012345678:def4567890123456",
            title="Test",
            start_at=datetime(2026, 9, 1, 9, 0, 0),
            unknown_field="extra",  # type: ignore[call-arg]
        )


def test_sf_availability_input_defaults():
    inp = SfAvailabilityInput(
        window_start=datetime(2026, 9, 1),
        window_end=datetime(2026, 9, 8),
    )
    assert inp.min_slot_minutes == 30  # default
    assert inp.exclude_ueids == []
