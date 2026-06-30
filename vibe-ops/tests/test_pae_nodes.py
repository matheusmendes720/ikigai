"""Unit tests for the 5 PAE-Maintainer nodes.

Covers:
  - observe_node: iteration counter + last_step tagging.
  - plan_node: prospective channel decision rule (REDUCE_LOAD / EXPAND / MAINTAIN).
  - reflect_node: retrospective aggregation, verdict bucket, gap detection.
  - balance_node: workload/capacity proportionality + Q_HE histerese.
  - commit_node: kill switch propagation on OVERLOAD.

Each node is tested with mocked inputs (state-only, no DB / no I/O).

Source: .omo/plans/agentic-markdown-system.md T12
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from agents.pae_maintainer.nodes import (  # noqa: E402
    balance_node,
    commit_node,
    observe_node,
    plan_node,
    reflect_node,
)
from agents.pae_maintainer.state import (  # noqa: E402
    BalancerVerdict,
    PAEState,
    PlanNode,
    PlanTier,
    PlanVerdict,
    ProspectiveNode,
    RetrospectiveNode,
)


def make_state(**overrides) -> PAEState:
    """Factory for valid PAEState kwargs (cycle-only defaults)."""
    base: dict = dict(
        cycle_id="test",
        cycle_start=_dt.date(2026, 7, 1),
        cycle_end=_dt.date(2026, 9, 30),
    )
    base.update(overrides)
    return PAEState(**base)


class TestObserveNode:
    def test_increments_iteration(self) -> None:
        s = make_state()
        assert s.iteration == 0
        s = observe_node(s)
        assert s.iteration == 1

    def test_sets_last_step(self) -> None:
        s = make_state()
        s = observe_node(s)
        assert s.last_step == "observe"

    def test_double_observe_increments_twice(self) -> None:
        s = make_state()
        s = observe_node(s)
        s = observe_node(s)
        assert s.iteration == 2


class TestPlanNode:
    def test_no_prospective_is_noop(self) -> None:
        s = make_state()
        s = plan_node(s)
        # last_step still updated even with no prospective channel set.
        assert s.last_step == "plan"

    def test_prospective_empty_candidates(self) -> None:
        s = make_state()
        s.prospective = ProspectiveNode(
            target_tier=PlanTier.WEEKLY,
            target_window_days=7,
        )
        s = plan_node(s)
        # Empty candidates -> avg defaults to 0.5 -> MAINTAIN.
        assert s.prospective.next_action == "MAINTAIN"
        assert s.prospective.drafted_at is not None

    def test_high_score_triggers_expand(self) -> None:
        # Avg > 0.80 -> EXPAND.
        s = make_state()
        s.prospective = ProspectiveNode(
            target_tier=PlanTier.WEEKLY,
            target_window_days=7,
            candidates=[
                PlanNode(id="t1", tier=PlanTier.WEEKLY, title="t", verdict_score=0.85)
            ],
        )
        s = plan_node(s)
        assert s.prospective.next_action == "EXPAND"

    def test_low_score_triggers_reduce(self) -> None:
        # Avg < 0.50 -> REDUCE_LOAD.
        s = make_state()
        s.prospective = ProspectiveNode(
            target_tier=PlanTier.WEEKLY,
            target_window_days=7,
            candidates=[
                PlanNode(id="t1", tier=PlanTier.WEEKLY, title="t", verdict_score=0.30)
            ],
        )
        s = plan_node(s)
        assert s.prospective.next_action == "REDUCE_LOAD"

    def test_mid_score_keeps_maintain(self) -> None:
        # 0.50 <= avg <= 0.80 -> MAINTAIN.
        s = make_state()
        s.prospective = ProspectiveNode(
            target_tier=PlanTier.WEEKLY,
            target_window_days=7,
            candidates=[
                PlanNode(id="t1", tier=PlanTier.WEEKLY, title="t", verdict_score=0.65)
            ],
        )
        s = plan_node(s)
        assert s.prospective.next_action == "MAINTAIN"

    def test_avg_across_multiple_candidates(self) -> None:
        # Avg of (0.85, 0.40) = 0.625 -> MAINTAIN (0.50 <= 0.625 <= 0.80).
        s = make_state()
        s.prospective = ProspectiveNode(
            target_tier=PlanTier.WEEKLY,
            target_window_days=7,
            candidates=[
                PlanNode(id="t1", tier=PlanTier.WEEKLY, title="t", verdict_score=0.85),
                PlanNode(id="t2", tier=PlanTier.WEEKLY, title="t", verdict_score=0.40),
            ],
        )
        s = plan_node(s)
        assert s.prospective.next_action == "MAINTAIN"


class TestReflectNode:
    def test_no_retrospective_is_noop(self) -> None:
        s = make_state()
        s = reflect_node(s)
        assert s.last_step == "reflect"

    def test_aggregate_score_computes_mean(self) -> None:
        s = make_state()
        s.retrospective = RetrospectiveNode(
            period_start=s.cycle_start,
            period_end=s.cycle_end,
            children_aggregated=[
                PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.8),
                PlanNode(id="b", tier=PlanTier.WEEKLY, title="b", verdict_score=0.6),
            ],
        )
        s = reflect_node(s)
        assert s.retrospective.aggregate_score == pytest.approx(0.7)
        assert s.retrospective.gaps == []  # both > 0.50

    def test_aggregate_verdict_pass(self) -> None:
        s = make_state()
        s.retrospective = RetrospectiveNode(
            period_start=s.cycle_start,
            period_end=s.cycle_end,
            children_aggregated=[
                PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.85),
            ],
        )
        s = reflect_node(s)
        assert s.retrospective.aggregate_verdict == PlanVerdict.PASS

    def test_aggregate_verdict_partial(self) -> None:
        s = make_state()
        s.retrospective = RetrospectiveNode(
            period_start=s.cycle_start,
            period_end=s.cycle_end,
            children_aggregated=[
                PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.55),
            ],
        )
        s = reflect_node(s)
        assert s.retrospective.aggregate_verdict == PlanVerdict.PARTIAL

    def test_aggregate_verdict_fail(self) -> None:
        s = make_state()
        s.retrospective = RetrospectiveNode(
            period_start=s.cycle_start,
            period_end=s.cycle_end,
            children_aggregated=[
                PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.30),
            ],
        )
        s = reflect_node(s)
        assert s.retrospective.aggregate_verdict == PlanVerdict.FAIL

    def test_gap_detection(self) -> None:
        s = make_state()
        s.retrospective = RetrospectiveNode(
            period_start=s.cycle_start,
            period_end=s.cycle_end,
            children_aggregated=[
                PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.30),
            ],
        )
        s = reflect_node(s)
        assert len(s.retrospective.gaps) == 1
        assert "a" in s.retrospective.gaps[0]

    def test_empty_children_no_crash(self) -> None:
        s = make_state()
        s.retrospective = RetrospectiveNode(
            period_start=s.cycle_start,
            period_end=s.cycle_end,
        )
        s = reflect_node(s)
        # No children -> aggregate_score stays 0.0 -> FAIL.
        assert s.retrospective.aggregate_verdict == PlanVerdict.FAIL


class TestBalanceNode:
    def test_overload_when_workload_exceeds_120pct_capacity(self) -> None:
        s = make_state(balancer={"workload_estimate": 12.0, "capacity_estimate": 8.0})
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.OVERLOAD
        assert "overload" in s.balancer.reason.lower() or "workload" in s.balancer.reason.lower()

    def test_underload_when_workload_below_50pct_capacity(self) -> None:
        s = make_state(balancer={"workload_estimate": 2.0, "capacity_estimate": 8.0})
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.UNDERLOAD

    def test_recover_when_qhe_below_threshold(self) -> None:
        # Workload within bounds, qhe below 0.60 -> RECOVER.
        s = make_state(
            balancer={
                "workload_estimate": 4.0,
                "capacity_estimate": 8.0,
                "qhe_score": 0.20,
            }
        )
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.RECOVER

    def test_ok_when_in_bounds(self) -> None:
        s = make_state(
            balancer={"workload_estimate": 4.0, "capacity_estimate": 8.0}
        )
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.OK

    def test_histerese_counter_increments_on_ok(self) -> None:
        s = make_state(
            balancer={"workload_estimate": 4.0, "capacity_estimate": 8.0}
        )
        # Default days_in_current_state=1.
        s = balance_node(s)
        assert s.balancer.days_in_current_state == 2
        s = balance_node(s)
        assert s.balancer.days_in_current_state == 3
        assert s.balancer.is_histerese_active is True

    def test_histerese_counter_resets_on_non_ok(self) -> None:
        s = make_state(
            balancer={"workload_estimate": 12.0, "capacity_estimate": 8.0}
        )
        # First balance -> OVERLOAD -> days_in_current_state resets to 1.
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.OVERLOAD
        assert s.balancer.days_in_current_state == 1
        assert s.balancer.is_histerese_active is False

    def test_overload_takes_precedence_over_recover(self) -> None:
        # Even with low qhe, if workload is over capacity -> OVERLOAD wins.
        s = make_state(
            balancer={
                "workload_estimate": 15.0,
                "capacity_estimate": 8.0,
                "qhe_score": 0.20,
            }
        )
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.OVERLOAD

    def test_underload_takes_precedence_over_recover(self) -> None:
        s = make_state(
            balancer={
                "workload_estimate": 1.0,
                "capacity_estimate": 8.0,
                "qhe_score": 0.20,
            }
        )
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.UNDERLOAD


class TestCommitNode:
    def test_skips_on_overload(self) -> None:
        s = make_state(balancer={"workload_estimate": 12.0, "capacity_estimate": 8.0})
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.OVERLOAD
        s = commit_node(s)
        assert s.kill_switch_triggered is True
        assert s.terminated is True

    def test_proceeds_on_ok(self) -> None:
        s = make_state(balancer={"workload_estimate": 4.0, "capacity_estimate": 8.0})
        s = balance_node(s)
        s = commit_node(s)
        assert s.kill_switch_triggered is False
        assert s.terminated is False
        assert s.last_step == "commit"

    def test_proceeds_on_underload(self) -> None:
        s = make_state(balancer={"workload_estimate": 1.0, "capacity_estimate": 8.0})
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.UNDERLOAD
        s = commit_node(s)
        # UNDERLOAD is allowed through the commit edge.
        assert s.kill_switch_triggered is False
        assert s.terminated is False

    def test_proceeds_on_recover(self) -> None:
        # commit_node itself doesn't reject RECOVER — only OVERLOAD triggers
        # the kill switch. The graph's should_commit guard rejects RECOVER.
        s = make_state(
            balancer={
                "workload_estimate": 4.0,
                "capacity_estimate": 8.0,
                "qhe_score": 0.20,
            }
        )
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.RECOVER
        s = commit_node(s)
        assert s.kill_switch_triggered is False
        assert s.terminated is False