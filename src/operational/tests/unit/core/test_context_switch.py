"""Unit tests for :mod:`operational.core.context_switch`."""
from __future__ import annotations

import pytest

from operational.core.context_switch import (
    ContextSwitchEstimate,
    ContextSwitchSeverity,
    context_switch_overhead_minutes,
    estimate_context_switch,
    net_rest_minutes,
)
from operational.enums import Period


# ---------------------------------------------------------------------------
# context_switch_overhead_minutes
# ---------------------------------------------------------------------------


class TestContextSwitchOverheadMinutes:
    """Tests for the canonical overhead matrix."""

    def test_manha_to_tarde(self) -> None:
        assert context_switch_overhead_minutes(Period.MANHA, Period.TARDE) == 30

    def test_tarde_to_noite(self) -> None:
        assert context_switch_overhead_minutes(Period.TARDE, Period.NOITE) == 20

    def test_manha_to_noite_skip_tarde(self) -> None:
        assert context_switch_overhead_minutes(Period.MANHA, Period.NOITE) == 60

    def test_tarde_to_manha_backward(self) -> None:
        assert context_switch_overhead_minutes(Period.TARDE, Period.MANHA) == 45

    def test_noite_to_manha_severe(self) -> None:
        assert context_switch_overhead_minutes(Period.NOITE, Period.MANHA) == 45

    def test_noite_to_tarde(self) -> None:
        assert context_switch_overhead_minutes(Period.NOITE, Period.TARDE) == 30

    @pytest.mark.parametrize(
        "period",
        [Period.MANHA, Period.TARDE, Period.NOITE],
    )
    def test_within_period_is_5min(self, period: Period) -> None:
        assert context_switch_overhead_minutes(period, period) == 5

    def test_custom_override(self) -> None:
        overrides = {(Period.MANHA, Period.TARDE): 60}
        assert context_switch_overhead_minutes(Period.MANHA, Period.TARDE, overrides) == 60

    def test_custom_override_does_not_affect_other_pairs(self) -> None:
        overrides = {(Period.MANHA, Period.TARDE): 60}
        assert context_switch_overhead_minutes(Period.TARDE, Period.NOITE, overrides) == 20

    def test_negative_override_raises(self) -> None:
        overrides = {(Period.MANHA, Period.TARDE): -10}
        with pytest.raises(ValueError, match="override must be"):
            context_switch_overhead_minutes(Period.MANHA, Period.TARDE, overrides)


# ---------------------------------------------------------------------------
# estimate_context_switch
# ---------------------------------------------------------------------------


class TestEstimateContextSwitch:
    """Tests for the high-level estimate function."""

    def test_canonical_manha_to_tarde(self) -> None:
        est = estimate_context_switch(Period.MANHA, Period.TARDE)
        assert isinstance(est, ContextSwitchEstimate)
        assert est.from_period == Period.MANHA
        assert est.to_period == Period.TARDE
        assert est.overhead_minutes == 30
        assert est.severity == ContextSwitchSeverity.LOW
        assert est.is_canonical
        assert not est.is_reverse

    def test_canonical_tarde_to_noite(self) -> None:
        est = estimate_context_switch(Period.TARDE, Period.NOITE)
        assert est.overhead_minutes == 20
        assert est.severity == ContextSwitchSeverity.LOW
        assert est.is_canonical

    def test_within_period_minimal(self) -> None:
        est = estimate_context_switch(Period.MANHA, Period.MANHA)
        assert est.severity == ContextSwitchSeverity.MINIMAL
        assert not est.is_canonical
        assert not est.is_reverse

    def test_backward_tarde_to_manha(self) -> None:
        est = estimate_context_switch(Period.TARDE, Period.MANHA)
        assert est.severity == ContextSwitchSeverity.MEDIUM
        assert not est.is_canonical
        assert est.is_reverse

    def test_severe_noite_to_manha(self) -> None:
        est = estimate_context_switch(Period.NOITE, Period.MANHA)
        assert est.severity == ContextSwitchSeverity.SEVERE
        assert est.is_reverse

    def test_high_manha_to_noite(self) -> None:
        est = estimate_context_switch(Period.MANHA, Period.NOITE)
        assert est.severity == ContextSwitchSeverity.HIGH
        assert not est.is_canonical  # not forward canonical (skips TARDE)
        assert not est.is_reverse

    def test_estimate_is_frozen(self) -> None:
        est = estimate_context_switch(Period.MANHA, Period.TARDE)
        with pytest.raises((AttributeError, TypeError)):
            est.overhead_minutes = 999  # type: ignore[misc]

    def test_custom_override_flows_through(self) -> None:
        overrides = {(Period.MANHA, Period.TARDE): 15}
        est = estimate_context_switch(Period.MANHA, Period.TARDE, overrides)
        assert est.overhead_minutes == 15


# ---------------------------------------------------------------------------
# net_rest_minutes
# ---------------------------------------------------------------------------


class TestNetRestMinutes:
    """Tests for net rest computation."""

    def test_30min_gross_minus_30min_overhead(self) -> None:
        # Gross break 30min, MANHÃ → TARDE overhead 30min → net 0
        result = net_rest_minutes(30.0, Period.MANHA, Period.TARDE)
        assert result == 0.0

    def test_60min_gross_minus_30min_overhead(self) -> None:
        # Gross break 60min, MANHÃ → TARDE overhead 30min → net 30
        result = net_rest_minutes(60.0, Period.MANHA, Period.TARDE)
        assert result == 30.0

    def test_negative_net_clamped_to_zero(self) -> None:
        # Gross break 10min, MANHÃ → NOITE overhead 60min → net 0
        result = net_rest_minutes(10.0, Period.MANHA, Period.NOITE)
        assert result == 0.0

    def test_negative_gross_raises(self) -> None:
        with pytest.raises(ValueError, match="gross_break_minutes"):
            net_rest_minutes(-1.0, Period.MANHA, Period.TARDE)

    def test_within_period(self) -> None:
        # Within-period overhead 5min
        assert net_rest_minutes(15.0, Period.MANHA, Period.MANHA) == 10.0

    def test_within_period_zero_overhead(self) -> None:
        # 5min break, 5min overhead → 0 net
        assert net_rest_minutes(5.0, Period.MANHA, Period.MANHA) == 0.0

    def test_zero_gross_break(self) -> None:
        # No rest at all → 0 net
        assert net_rest_minutes(0.0, Period.MANHA, Period.TARDE) == 0.0
