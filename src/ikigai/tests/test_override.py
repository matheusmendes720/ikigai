"""Tests for OverrideRecord — SPEC D12 typed audit trail."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ikigai.entities.override import OverrideRecord


class TestOverrideRecord:
    def test_round_trip(self) -> None:
        o = OverrideRecord(
            at=datetime(2026, 8, 26, tzinfo=timezone.utc),
            by="human:matheus",
            field_path="regime.levels[0].regime",
            previous_value="maintain",
            new_value="push",
            reason="Q_HE recovered above 0.85",
        )
        assert o.by == "human:matheus"
        assert o.field_path == "regime.levels[0].regime"

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            OverrideRecord(
                at=datetime(2026, 8, 26, tzinfo=timezone.utc),
                by="agent", field_path="x", previous_value=1, new_value=2,
                reason="r", extra_field="forbidden",
            )
