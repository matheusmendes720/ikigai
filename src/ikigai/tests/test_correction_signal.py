"""Tests for CorrectionSignal — typed IKIGAi cycle output."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ikigai.entities.correction_signal import CorrectionSignal


class TestCorrectionSignal:
    def test_drift_signal(self) -> None:
        c = CorrectionSignal(
            heuristic="qhe_trend",
            signal_type="drift",
            description="Q_HE trending down 3 days",
            target_ueid=None,
            urgency="high",
            metadata={"window_days": 3},
            created_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
        )
        assert c.signal_type == "drift"

    def test_invalid_signal_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CorrectionSignal(
                heuristic="x", signal_type="bogus",  # type: ignore[arg-type]
                description="d", target_ueid=None, urgency="low",
                metadata={}, created_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
            )
