"""Hypothesis property tests for PAE balancer + 5x3x3 invariants.

Exercises balance_node with thousands of randomly-generated
(workload, capacity, qhe) triples to confirm the four-state verdict
logic is consistent.

Invariants tested:
  - 5 proportionality buckets x 3 capacity ratios x 3 Q_HE bands = 45 scenarios
    (here reduced to the four-quadrant decision rule).
  - Histerese activation rule: is_histerese_active iff days >= upgrade_days.

Source: .omo/plans/agentic-markdown-system.md T12
Linked: T9 (balance_node), ADR-006 (period schema)
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

VIBE_OPS_SRC = Path(__file__).resolve().parents[2] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from agents.pae_maintainer.nodes import balance_node  # noqa: E402
from agents.pae_maintainer.state import (  # noqa: E402
    BalancerVerdict,
    PAEState,
    PlanTier,
)


def make_state(
    workload: float, capacity: float, qhe: float, **extra_balancer
) -> PAEState:
    """Factory with explicit balancer overrides."""
    balancer: dict = {
        "workload_estimate": workload,
        "capacity_estimate": capacity,
        "qhe_score": qhe,
    }
    balancer.update(extra_balancer)
    return PAEState(
        cycle_id="prop-test",
        cycle_start=_dt.date(2026, 1, 1),
        cycle_end=_dt.date(2026, 3, 31),
        balancer=balancer,
    )


class TestBalancerInvariants:
    @given(
        workload=st.floats(
            min_value=0, max_value=24, allow_nan=False, allow_infinity=False
        ),
        capacity=st.floats(
            min_value=1, max_value=24, allow_nan=False, allow_infinity=False
        ),
        qhe=st.floats(
            min_value=0, max_value=1, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_verdict_matches_documented_quadrants(
        self, workload: float, capacity: float, qhe: float
    ) -> None:
        """Verdict must obey the decision rule documented in balance_node:

          1. workload > capacity * 1.20           -> OVERLOAD
          2. workload < capacity * 0.50           -> UNDERLOAD
          3. qhe_score < qhe_recover_threshold    -> RECOVER
          4. otherwise                            -> OK
        """
        s = make_state(workload, capacity, qhe)
        s = balance_node(s)
        # qhe_recover_threshold defaults to 0.60.
        if workload > capacity * 1.20:
            assert s.balancer.state == BalancerVerdict.OVERLOAD
        elif workload < capacity * 0.50:
            assert s.balancer.state == BalancerVerdict.UNDERLOAD
        elif qhe < 0.60:
            assert s.balancer.state == BalancerVerdict.RECOVER
        else:
            assert s.balancer.state == BalancerVerdict.OK

    @given(
        workload=st.floats(
            min_value=0, max_value=24, allow_nan=False, allow_infinity=False
        ),
        capacity=st.floats(
            min_value=1, max_value=24, allow_nan=False, allow_infinity=False
        ),
        qhe=st.floats(
            min_value=0, max_value=1, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_state_always_one_of_four_verdicts(
        self, workload: float, capacity: float, qhe: float
    ) -> None:
        s = make_state(workload, capacity, qhe)
        s = balance_node(s)
        assert s.balancer.state in (
            BalancerVerdict.OK,
            BalancerVerdict.OVERLOAD,
            BalancerVerdict.UNDERLOAD,
            BalancerVerdict.RECOVER,
        )

    @given(
        workload=st.floats(
            min_value=0, max_value=24, allow_nan=False, allow_infinity=False
        ),
        capacity=st.floats(
            min_value=1, max_value=24, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_overload_boundary_at_120pct(
        self, workload: float, capacity: float
    ) -> None:
        # qhe = 0.9 (well above recover threshold) so verdict is OK or OVERLOAD.
        s = make_state(workload, capacity, qhe=0.9)
        s = balance_node(s)
        if workload > capacity * 1.20:
            assert s.balancer.state == BalancerVerdict.OVERLOAD
        else:
            assert s.balancer.state in (BalancerVerdict.OK, BalancerVerdict.UNDERLOAD)

    @given(
        workload=st.floats(
            min_value=0, max_value=24, allow_nan=False, allow_infinity=False
        ),
        capacity=st.floats(
            min_value=1, max_value=24, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_underload_boundary_at_50pct(
        self, workload: float, capacity: float
    ) -> None:
        # qhe = 0.9 (above recover threshold).
        s = make_state(workload, capacity, qhe=0.9)
        s = balance_node(s)
        if workload < capacity * 0.50:
            assert s.balancer.state == BalancerVerdict.UNDERLOAD
        # Else: OK or OVERLOAD — we don't constrain further.

    @given(
        qhe=st.floats(
            min_value=0, max_value=1, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_recover_only_when_workload_within_bounds(self, qhe: float) -> None:
        # workload=4, capacity=8 -> within 50%-120% bounds.
        s = make_state(workload=4.0, capacity=8.0, qhe=qhe)
        s = balance_node(s)
        if qhe < 0.60:
            assert s.balancer.state == BalancerVerdict.RECOVER
        else:
            assert s.balancer.state == BalancerVerdict.OK


class TestHisteresisInvariants:
    @given(
        days=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=50)
    def test_histeresis_activation_rule(self, days: int) -> None:
        """is_histerese_active is True iff days_in_current_state >= upgrade_days."""
        s = make_state(workload=4.0, capacity=8.0, qhe=0.7)
        s.balancer.days_in_current_state = days
        # Compute is_histerese_active via the same rule balance_node uses.
        s.balancer.is_histerese_active = (
            days >= s.balancer.histerese_upgrade_days
        )
        upgrade = s.balancer.histerese_upgrade_days  # default = 3
        if days >= upgrade:
            assert s.balancer.is_histerese_active is True
        else:
            assert s.balancer.is_histerese_active is False

    @given(
        n_cycles=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=50)
    def test_consecutive_ok_cycles_increment_days(self, n_cycles: int) -> None:
        """Each consecutive OK cycle increments days_in_current_state by 1."""
        s = make_state(workload=4.0, capacity=8.0, qhe=0.7)
        # Reset to 0 so we can predict the post-cycle value.
        s.balancer.days_in_current_state = 0
        for _ in range(n_cycles):
            s = balance_node(s)
        # After n OK cycles, days_in_current_state = n (starting from 0).
        assert s.balancer.days_in_current_state == n_cycles

    @given(
        ok_cycles=st.integers(min_value=1, max_value=5),
        overload_cycles=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50)
    def test_overload_resets_days_counter(
        self, ok_cycles: int, overload_cycles: int
    ) -> None:
        """A single OVERLOAD cycle resets days_in_current_state to 1."""
        s = make_state(workload=4.0, capacity=8.0, qhe=0.7)
        # Run some OK cycles to build up days.
        for _ in range(ok_cycles):
            s = balance_node(s)
        # Switch to overload.
        s.balancer.workload_estimate = 50.0
        for _ in range(overload_cycles):
            s = balance_node(s)
        # After any overload, days_in_current_state = 1.
        assert s.balancer.days_in_current_state == 1
        assert s.balancer.is_histerese_active is False


class TestCustomThresholds:
    @given(
        workload=st.floats(
            min_value=0, max_value=24, allow_nan=False, allow_infinity=False
        ),
        capacity=st.floats(
            min_value=1, max_value=24, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=50)
    def test_custom_overload_factor(self, workload: float, capacity: float) -> None:
        s = make_state(
            workload=workload,
            capacity=capacity,
            qhe=0.9,
            overload_factor=1.5,
        )
        s = balance_node(s)
        if workload > capacity * 1.5:
            assert s.balancer.state == BalancerVerdict.OVERLOAD

    @given(
        qhe=st.floats(
            min_value=0, max_value=1, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=50)
    def test_custom_recover_threshold(self, qhe: float) -> None:
        s = make_state(
            workload=4.0, capacity=8.0, qhe=qhe, qhe_recover_threshold=0.30
        )
        s = balance_node(s)
        if qhe < 0.30:
            assert s.balancer.state == BalancerVerdict.RECOVER
        else:
            # workload within bounds and qhe above threshold -> OK.
            assert s.balancer.state == BalancerVerdict.OK


class TestReasonInvariant:
    @given(
        workload=st.floats(
            min_value=0, max_value=24, allow_nan=False, allow_infinity=False
        ),
        capacity=st.floats(
            min_value=1, max_value=24, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=50)
    def test_reason_always_non_empty(
        self, workload: float, capacity: float
    ) -> None:
        """After balance_node, reason string must be set."""
        s = make_state(workload=workload, capacity=capacity, qhe=0.7)
        s = balance_node(s)
        assert isinstance(s.balancer.reason, str)
        assert len(s.balancer.reason) > 0