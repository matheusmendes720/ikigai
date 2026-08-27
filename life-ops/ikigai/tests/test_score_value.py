"""Tests for ScoreValue — SPEC I3 (vector scores ∈ [0,100]), I4 (Q_HE ∈ [0,1])."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ikigai.entities.score_value import ScoreUnit, ScoreValue


class TestScoreValue:
    def test_percent_in_range(self) -> None:
        s = ScoreValue(value=85.0, unit=ScoreUnit.PERCENT)
        assert s.value == 85.0
        assert s.unit == ScoreUnit.PERCENT
        assert s.normalized == 0.85

    def test_percent_above_100_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScoreValue(value=150.0, unit=ScoreUnit.PERCENT)

    def test_percent_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScoreValue(value=-1.0, unit=ScoreUnit.PERCENT)

    def test_ratio_in_range(self) -> None:
        s = ScoreValue(value=0.85, unit=ScoreUnit.RATIO)
        assert s.normalized == 0.85

    def test_ratio_above_1_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScoreValue(value=1.5, unit=ScoreUnit.RATIO)

    def test_ratio_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScoreValue(value=-0.1, unit=ScoreUnit.RATIO)

    def test_normalized_unit_agnostic(self) -> None:
        """SU-04: same normalized value across units."""
        assert ScoreValue(value=85.0, unit=ScoreUnit.PERCENT).normalized == 0.85
        assert ScoreValue(value=0.85, unit=ScoreUnit.RATIO).normalized == 0.85

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            ScoreValue(value=0.5, unit=ScoreUnit.RATIO, foo="bar")

    def test_frozen(self) -> None:
        s = ScoreValue(value=0.5, unit=ScoreUnit.RATIO)
        with pytest.raises(ValidationError):
            s.value = 0.6  # type: ignore[misc]
