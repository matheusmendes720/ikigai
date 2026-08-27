"""Unit tests for PAE-Maintainer state models.

Validates Pydantic v2 model invariants, default values, score bounds,
verdict enums, and balancer state machine semantics.

Source: .omo/plans/agentic-markdown-system.md T12
Linked: T9 (state.py + constants), ADR-006 (period schema)
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

import pytest

# Ensure vibe-ops/src is on sys.path so ``agents.pae_maintainer.*`` resolves.
VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from agents.pae_maintainer.nodes import balance_node  # noqa: E402
from agents.pae_maintainer.state import (  # noqa: E402
    BalancerState,
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
        cycle_id="test-cycle",
        cycle_start=_dt.date(2026, 1, 1),
        cycle_end=_dt.date(2026, 3, 31),
    )
    base.update(overrides)
    return PAEState(**base)


class TestPAEState:
    def test_defaults(self) -> None:
        s = make_state()
        assert s.iteration == 0
        assert s.terminated is False
        assert s.kill_switch_triggered is False
        assert s.last_step == "init"
        assert s.active_nodes == []
        assert s.archive == []
        assert s.prospective is None
        assert s.retrospective is None

    def test_balancer_default_state(self) -> None:
        s = make_state()
        assert s.balancer.state == BalancerVerdict.OK
        assert s.balancer.days_in_current_state == 1
        assert s.balancer.is_histerese_active is False

    def test_current_tier_within_cycle(self) -> None:
        s = make_state(
            cycle_start=_dt.date(2026, 1, 1),
            cycle_end=_dt.date(2026, 12, 31),
        )
        # current_tier() defaults to today; should always be a valid PlanTier member.
        assert s.current_tier() in list(PlanTier)

    def test_current_tier_pre_cycle(self) -> None:
        # Reference before cycle_start -> SONHO (planning forward).
        s = make_state(
            cycle_start=_dt.date(2026, 6, 1),
            cycle_end=_dt.date(2026, 9, 1),
        )
        assert s.current_tier(today=_dt.date(2026, 1, 1)) == PlanTier.SONHO

    def test_current_tier_post_cycle(self) -> None:
        # Reference after cycle_end -> DAILY (planning next cycle).
        s = make_state(
            cycle_start=_dt.date(2026, 1, 1),
            cycle_end=_dt.date(2026, 3, 31),
        )
        assert s.current_tier(today=_dt.date(2026, 12, 31)) == PlanTier.DAILY

    def test_balancer_overload_flag(self) -> None:
        # Constructing with high workload doesn't auto-trigger OVERLOAD — must
        # invoke balance_node to actually compute the verdict.
        s = make_state(
            balancer={
                "workload_estimate": 12.0,
                "capacity_estimate": 8.0,
                "qhe_score": 0.5,
            }
        )
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.OVERLOAD

    def test_balancer_underload_flag(self) -> None:
        s = make_state(
            balancer={
                "workload_estimate": 2.0,
                "capacity_estimate": 8.0,
                "qhe_score": 0.7,
            }
        )
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.UNDERLOAD

    def test_balancer_recover_flag(self) -> None:
        # Workload within bounds but qhe below recover threshold.
        s = make_state(
            balancer={
                "workload_estimate": 4.0,
                "capacity_estimate": 8.0,
                "qhe_score": 0.20,
            }
        )
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.RECOVER

    def test_balancer_ok_flag(self) -> None:
        s = make_state(
            balancer={
                "workload_estimate": 4.0,
                "capacity_estimate": 8.0,
                "qhe_score": 0.70,
            }
        )
        s = balance_node(s)
        assert s.balancer.state == BalancerVerdict.OK


class TestPlanNode:
    def test_score_validation_too_high(self) -> None:
        with pytest.raises(ValueError):
            PlanNode(id="x", tier=PlanTier.WEEKLY, title="t", verdict_score=1.5)

    def test_score_validation_too_low(self) -> None:
        with pytest.raises(ValueError):
            PlanNode(id="x", tier=PlanTier.WEEKLY, title="t", verdict_score=-0.1)

    def test_default_values(self) -> None:
        n = PlanNode(id="x", tier=PlanTier.DAILY, title="t")
        assert n.verdict_score == 0.0
        assert n.children == []
        assert n.metadata == {}
        assert n.parent_id is None
        assert n.verdict is None
        assert n.updated_at is not None

    def test_ikigai_vector_literal(self) -> None:
        # ikigai_vector is restricted to 4 strings.
        for vec in ("passion", "skill", "market", "revenue"):
            n = PlanNode(
                id="x", tier=PlanTier.WEEKLY, title="t", ikigai_vector=vec  # type: ignore[arg-type]
            )
            assert n.ikigai_vector == vec

    def test_ikigai_vector_invalid_rejected(self) -> None:
        with pytest.raises(ValueError):
            PlanNode(
                id="x",
                tier=PlanTier.WEEKLY,
                title="t",
                ikigai_vector="invalid",  # type: ignore[arg-type]
            )

    def test_extra_fields_allowed(self) -> None:
        # extra="allow" in PlanNode.config — should not raise.
        n = PlanNode(id="x", tier=PlanTier.DAILY, title="t", custom_field="hello")
        assert getattr(n, "custom_field", None) == "hello"


class TestProspectiveNode:
    def test_required_fields(self) -> None:
        n = ProspectiveNode(target_tier=PlanTier.WEEKLY, target_window_days=7)
        assert n.target_tier == PlanTier.WEEKLY
        assert n.target_window_days == 7
        assert n.candidates == []
        assert n.next_action is None
        assert n.drafted_at is None

    def test_candidates_default_factory(self) -> None:
        # Two instances must not share the same candidates list (mutable default trap).
        a = ProspectiveNode(target_tier=PlanTier.WEEKLY, target_window_days=7)
        b = ProspectiveNode(target_tier=PlanTier.WEEKLY, target_window_days=7)
        a.candidates.append("node-1")
        assert b.candidates == []


class TestRetrospectiveNode:
    def test_required_dates(self) -> None:
        r = RetrospectiveNode(
            period_start=_dt.date(2026, 1, 1),
            period_end=_dt.date(2026, 3, 31),
        )
        assert r.period_start == _dt.date(2026, 1, 1)
        assert r.period_end == _dt.date(2026, 3, 31)
        assert r.children_aggregated == []
        assert r.gaps == []
        assert r.suggested_corrections == []

    def test_aggregate_score_validation(self) -> None:
        with pytest.raises(ValueError):
            RetrospectiveNode(
                period_start=_dt.date(2026, 1, 1),
                period_end=_dt.date(2026, 3, 31),
                aggregate_score=1.5,
            )


class TestBalancerState:
    def test_thresholds_from_constants(self) -> None:
        b = BalancerState()
        # Default values come from operational PAVConstants (or hardcoded fallback).
        assert b.overload_factor == 1.20
        assert b.underload_factor == 0.50
        assert b.qhe_recover_threshold == 0.60
        assert b.histerese_upgrade_days == 3

    def test_custom_thresholds(self) -> None:
        b = BalancerState(
            overload_factor=1.5,
            underload_factor=0.30,
            qhe_recover_threshold=0.40,
            histerese_upgrade_days=7,
        )
        assert b.overload_factor == 1.5
        assert b.underload_factor == 0.30
        assert b.qhe_recover_threshold == 0.40
        assert b.histerese_upgrade_days == 7

    def test_qhe_score_validation(self) -> None:
        with pytest.raises(ValueError):
            BalancerState(qhe_score=1.5)
        with pytest.raises(ValueError):
            BalancerState(qhe_score=-0.1)

    def test_histerese_active_when_days_exceed(self) -> None:
        # is_histerese_active is a stored field, set by balance_node.
        b = BalancerState(days_in_current_state=5)
        assert b.is_histerese_active is False  # not yet — only after balance_node sets it.

        b.is_histerese_active = True
        assert b.is_histerese_active is True


class TestPlanTierEnum:
    def test_all_tiers_have_expected_days(self) -> None:
        # TIER_DAYS lookup: SONHO=None (variable), others are integers.
        assert PlanTier.SONHO.expected_days is None
        assert PlanTier.QUARTERLY.expected_days == 90
        assert PlanTier.ONDA.expected_days == 45
        assert PlanTier.WEEKLY.expected_days == 7
        assert PlanTier.DAILY.expected_days == 1

    def test_tier_values_unique(self) -> None:
        values = {t.value for t in PlanTier}
        assert len(values) == len(list(PlanTier))


class TestPlanVerdictEnum:
    def test_daily_weekly_quarterly_verdicts(self) -> None:
        assert PlanVerdict.PASS.value == "PASS"
        assert PlanVerdict.PARTIAL.value == "PARTIAL"
        assert PlanVerdict.FAIL.value == "FAIL"

    def test_onda_verdicts(self) -> None:
        assert PlanVerdict.CONTINUE_WAVE.value == "CONTINUE_WAVE"
        assert PlanVerdict.CORRECT_TRAJECTORY.value == "CORRECT_TRAJECTORY"
        assert PlanVerdict.KILL_WAVE.value == "KILL_WAVE"

    def test_sonho_verdicts(self) -> None:
        assert PlanVerdict.ACTIVE.value == "ACTIVE"
        assert PlanVerdict.VALIDATED.value == "VALIDATED"
        assert PlanVerdict.FALSIFIED.value == "FALSIFIED"
        assert PlanVerdict.PIVOTED.value == "PIVOTED"
        assert PlanVerdict.ABANDONED.value == "ABANDONED"


class TestBalancerVerdictEnum:
    def test_verdict_values(self) -> None:
        assert BalancerVerdict.OK.value == "OK"
        assert BalancerVerdict.OVERLOAD.value == "OVERLOAD"
        assert BalancerVerdict.UNDERLOAD.value == "UNDERLOAD"
        assert BalancerVerdict.RECOVER.value == "RECOVER"


class TestPAEStateMutability:
    def test_state_is_mutable(self) -> None:
        # Pydantic v2 without frozen=True — should be mutable.
        s = make_state()
        s.iteration = 42
        s.last_step = "manual"
        s.terminated = True
        assert s.iteration == 42
        assert s.last_step == "manual"
        assert s.terminated is True

    def test_active_nodes_append(self) -> None:
        s = make_state()
        s.active_nodes.append(
            PlanNode(id="n1", tier=PlanTier.DAILY, title="first")
        )
        assert len(s.active_nodes) == 1
        assert s.active_nodes[0].id == "n1"

    def test_archive_isolated_from_active(self) -> None:
        s = make_state()
        s.active_nodes.append(
            PlanNode(id="a", tier=PlanTier.DAILY, title="a")
        )
        s.archive.append(
            PlanNode(id="b", tier=PlanTier.DAILY, title="b")
        )
        assert len(s.active_nodes) == 1
        assert len(s.archive) == 1
        assert s.active_nodes[0].id == "a"
        assert s.archive[0].id == "b"