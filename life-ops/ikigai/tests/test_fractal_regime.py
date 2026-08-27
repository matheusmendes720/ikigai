"""Tests for FractalRegime — SPEC D13 4-level fractal regime."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ikigai.entities.fractal_regime import FractalRegime, FractalRegimeState


class TestFractalRegime:
    def _state(self, level: str) -> FractalRegimeState:
        return FractalRegimeState(
            level=level,  # type: ignore[arg-type]
            regime="push",
            days_in_regime=10,
            is_hysteresis_active=False,
            hysteresis_days=14,
        )

    def test_four_levels_required(self) -> None:
        levels = [self._state(l) for l in ("global", "cluster", "vector", "sub_vector")]
        r = FractalRegime(levels=levels)
        assert len(r.levels) == 4

    def test_unknown_level_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FractalRegimeState(
                level="planetary",  # type: ignore[arg-type]
                regime="push", days_in_regime=10,
                is_hysteresis_active=False, hysteresis_days=14,
            )

    def test_negative_days_in_regime_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FractalRegimeState(
                level="global", regime="push", days_in_regime=-1,
                is_hysteresis_active=False, hysteresis_days=14,
            )

    def test_per_level_hysteresis_independent(self) -> None:
        levels = [
            self._state("global"),
            self._state("cluster"),
            self._state("vector"),
            self._state("sub_vector"),
        ]
        levels[2].hysteresis_days = 21
        r = FractalRegime(levels=levels)
        assert r.levels[0].hysteresis_days == 14
        assert r.levels[2].hysteresis_days == 21
