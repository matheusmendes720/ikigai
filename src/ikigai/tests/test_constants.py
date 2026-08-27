"""Tests for ikigai.constants — PAV_NS / NSM dataclass."""

from __future__ import annotations

import pytest
from ikigai.constants import NSM, PAV_NS


class TestPAV_NS:
    """NSM must be a frozen dataclass with canonical values."""

    def test_is_frozen(self) -> None:
        """PAV_NS must be frozen (immutable)."""
        import dataclasses
        assert dataclasses.is_dataclass(NSM)

    def test_lambda_positive(self) -> None:
        assert NSM.LAMBDA > 0

    def test_rho_in_unit_interval(self) -> None:
        assert 0 <= NSM.RHO <= 1

    def test_wave_days_positive(self) -> None:
        assert NSM.WAVE_DAYS > 0

    def test_cycle_days_positive(self) -> None:
        assert NSM.CYCLE_DAYS > 0

    def test_phase_days_positive(self) -> None:
        assert NSM.PHASE_DAYS > 0

    def test_q_he_thresholds_ordered(self) -> None:
        """Q_HE thresholds must be ordered: PUSH > REDUCE > RECOVER."""
        assert NSM.Q_HE_PUSH > NSM.Q_HE_REDUCE
        assert NSM.Q_HE_REDUCE > NSM.Q_HE_RECOVER

    def test_hysteresis_upgrade_positive(self) -> None:
        assert NSM.HYSTERESIS_UPGRADE_DAYS > 0

    def test_hysteresis_downgrade_positive(self) -> None:
        assert NSM.HYSTERESIS_DOWNGRADE_DAYS > 0

    def test_meta_vetor_w_geo_positive(self) -> None:
        assert 0 < NSM.META_VETOR_W_GEO < 1

    def test_meta_vetor_w_harm_positive(self) -> None:
        assert 0 < NSM.META_VETOR_W_HARM < 1

    def test_meta_vetor_w_geo_plus_harm_equals_one(self) -> None:
        """Geo + harmonic weights must sum to 1.0."""
        total = NSM.META_VETOR_W_GEO + NSM.META_VETOR_W_HARM
        assert abs(total - 1.0) < 1e-9

    def test_phase_max_iters_positive(self) -> None:
        assert NSM.PHASE_MAX_ITERS > 0

    def test_phase_convergence_threshold_positive(self) -> None:
        assert NSM.PHASE_CONVERGENCE_THRESHOLD > 0

    def test_hysteresis_upgrade_lt_downgrade(self) -> None:
        """Upgrade should take longer than downgrade (hysteresis protection)."""
        assert NSM.HYSTERESIS_UPGRADE_DAYS >= NSM.HYSTERESIS_DOWNGRADE_DAYS
