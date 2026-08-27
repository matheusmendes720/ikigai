"""Integration tests for Prospective + Retrospective channels.

Verifies channel isolation: each channel reads state but does NOT mutate
it (pure functions returning fresh snapshots). Also exercises the
decision rules (next_action thresholds, aggregate verdict buckets,
rollback signals).

Source: .omo/plans/agentic-markdown-system.md T12
Linked: T9 (channels.py), state.py
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[2] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from agents.pae_maintainer.channels import (  # noqa: E402
    ProspectiveChannel,
    RetrospectiveChannel,
)
from agents.pae_maintainer.state import (  # noqa: E402
    PAEState,
    PlanNode,
    PlanTier,
    PlanVerdict,
)


def make_state(**overrides) -> PAEState:
    """Factory for valid PAEState kwargs (cycle-only defaults)."""
    base: dict = dict(
        cycle_id="channel-test",
        cycle_start=_dt.date(2026, 1, 1),
        cycle_end=_dt.date(2026, 3, 31),
    )
    base.update(overrides)
    return PAEState(**base)


class TestProspectiveChannel:
    def test_evaluate_returns_prospective_node(self) -> None:
        ch = ProspectiveChannel(default_window_days=7)
        s = make_state()
        result = ch.evaluate(s)
        assert result.target_tier in list(PlanTier)
        assert result.target_window_days == 7
        assert result.next_action == "REVIEW"

    def test_evaluate_filters_by_current_tier(self) -> None:
        ch = ProspectiveChannel(default_window_days=7)
        s = make_state()
        s.active_nodes = [
            PlanNode(id="w1", tier=PlanTier.WEEKLY, title="w", verdict_score=0.85),
            PlanNode(id="d1", tier=PlanTier.DAILY, title="d", verdict_score=0.90),
        ]
        result = ch.evaluate(s)
        # Candidates must all match the inferred current tier.
        for c in result.candidates:
            assert c.tier == result.target_tier

    def test_default_window_days(self) -> None:
        ch = ProspectiveChannel(default_window_days=14)
        s = make_state()
        result = ch.evaluate(s)
        assert result.target_window_days == 14

    def test_evaluate_does_not_mutate_state(self) -> None:
        ch = ProspectiveChannel()
        s = make_state()
        before = s.model_copy(deep=True)
        ch.evaluate(s)
        # State must be byte-equal after evaluate.
        assert s.model_dump() == before.model_dump()
        assert s.prospective is None  # not assigned

    def test_next_action_high_score_promotes(self) -> None:
        ch = ProspectiveChannel()
        n = PlanNode(
            id="x", tier=PlanTier.WEEKLY, title="t", verdict_score=0.85
        )
        assert ch.next_action(n) == "PROMOTE_TO_PARENT"

    def test_next_action_at_threshold_promotes(self) -> None:
        # PROMOTE_THRESHOLD = 0.80, so >= 0.80 promotes.
        ch = ProspectiveChannel()
        n = PlanNode(
            id="x", tier=PlanTier.WEEKLY, title="t", verdict_score=0.80
        )
        assert ch.next_action(n) == "PROMOTE_TO_PARENT"

    def test_next_action_low_score_flags(self) -> None:
        ch = ProspectiveChannel()
        n = PlanNode(
            id="x", tier=PlanTier.WEEKLY, title="t", verdict_score=0.3
        )
        assert ch.next_action(n) == "FLAGGED_FOR_REFACTOR"

    def test_next_action_at_flag_threshold_flags(self) -> None:
        # FLAG_THRESHOLD = 0.50, so < 0.50 flags (i.e. exactly 0.50 is MAINTAIN).
        ch = ProspectiveChannel()
        n = PlanNode(
            id="x", tier=PlanTier.WEEKLY, title="t", verdict_score=0.49
        )
        assert ch.next_action(n) == "FLAGGED_FOR_REFACTOR"

    def test_next_action_mid_maintains(self) -> None:
        ch = ProspectiveChannel()
        n = PlanNode(
            id="x", tier=PlanTier.WEEKLY, title="t", verdict_score=0.6
        )
        assert ch.next_action(n) == "MAINTAIN"

    def test_next_action_at_boundary_50(self) -> None:
        # 0.50 is exactly FLAG_THRESHOLD -> MAINTAIN.
        ch = ProspectiveChannel()
        n = PlanNode(
            id="x", tier=PlanTier.WEEKLY, title="t", verdict_score=0.50
        )
        assert ch.next_action(n) == "MAINTAIN"


class TestRetrospectiveChannel:
    def test_aggregate_computes_avg(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        children = [
            PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.8),
            PlanNode(id="b", tier=PlanTier.WEEKLY, title="b", verdict_score=0.6),
        ]
        result = ch.aggregate(s, children)
        assert result.aggregate_score == pytest.approx(0.7)

    def test_aggregate_empty_returns_zero(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        result = ch.aggregate(s, [])
        assert result.aggregate_score == 0.0
        assert result.gaps == []

    def test_aggregate_pass_threshold(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        children = [
            PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.8)
        ]
        result = ch.aggregate(s, children)
        assert result.aggregate_verdict == PlanVerdict.PASS
        assert result.gaps == []

    def test_aggregate_at_pass_threshold(self) -> None:
        # PASS_THRESHOLD = 0.70, so >= 0.70 passes.
        ch = RetrospectiveChannel()
        s = make_state()
        children = [
            PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.70)
        ]
        result = ch.aggregate(s, children)
        assert result.aggregate_verdict == PlanVerdict.PASS

    def test_aggregate_partial_threshold(self) -> None:
        # 0.50 <= score < 0.70 -> PARTIAL.
        ch = RetrospectiveChannel()
        s = make_state()
        children = [
            PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.55)
        ]
        result = ch.aggregate(s, children)
        assert result.aggregate_verdict == PlanVerdict.PARTIAL

    def test_aggregate_fail_threshold(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        children = [
            PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.3)
        ]
        result = ch.aggregate(s, children)
        assert result.aggregate_verdict == PlanVerdict.FAIL
        assert len(result.gaps) == 1

    def test_aggregate_multiple_gaps(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        children = [
            PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.20),
            PlanNode(id="b", tier=PlanTier.WEEKLY, title="b", verdict_score=0.30),
        ]
        result = ch.aggregate(s, children)
        assert len(result.gaps) == 2

    def test_aggregate_does_not_mutate_state(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        before = s.model_copy(deep=True)
        children = [
            PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.5)
        ]
        ch.aggregate(s, children)
        # State must be byte-equal after aggregate.
        assert s.model_dump() == before.model_dump()
        assert s.retrospective is None

    def test_aggregate_period_dates_from_state(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state(
            cycle_start=_dt.date(2026, 4, 1),
            cycle_end=_dt.date(2026, 6, 30),
        )
        children = [
            PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.7)
        ]
        result = ch.aggregate(s, children)
        assert result.period_start == _dt.date(2026, 4, 1)
        assert result.period_end == _dt.date(2026, 6, 30)


class TestRetrospectiveChannelRollbackSignals:
    def test_critical_signal_on_fail(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        agg = ch.aggregate(
            s,
            [PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.2)],
        )
        signals = ch.rollback_signals(agg)
        assert any("CRITICAL" in sig for sig in signals)

    def test_warn_signal_on_partial(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        agg = ch.aggregate(
            s,
            [PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.55)],
        )
        signals = ch.rollback_signals(agg)
        assert any("WARN" in sig for sig in signals)

    def test_no_critical_on_pass(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        agg = ch.aggregate(
            s,
            [PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.85)],
        )
        signals = ch.rollback_signals(agg)
        assert not any("CRITICAL" in sig for sig in signals)
        assert not any("WARN" in sig for sig in signals)

    def test_gap_signals_emitted_per_gap(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        agg = ch.aggregate(
            s,
            [
                PlanNode(id="a", tier=PlanTier.WEEKLY, title="a", verdict_score=0.2),
                PlanNode(id="b", tier=PlanTier.WEEKLY, title="b", verdict_score=0.3),
            ],
        )
        signals = ch.rollback_signals(agg)
        gap_signals = [s for s in signals if "GAP" in s]
        assert len(gap_signals) == 2


class TestChannelIsolation:
    """Channels must not share state with each other (no global mutation)."""

    def test_prospective_does_not_set_retrospective(self) -> None:
        ch = ProspectiveChannel()
        s = make_state()
        ch.evaluate(s)
        assert s.retrospective is None
        assert s.prospective is None

    def test_retrospective_does_not_set_prospective(self) -> None:
        ch = RetrospectiveChannel()
        s = make_state()
        ch.aggregate(s, [])
        assert s.prospective is None
        assert s.retrospective is None

    def test_multiple_evaluations_are_independent(self) -> None:
        ch = ProspectiveChannel(default_window_days=7)
        s1 = make_state(cycle_id="s1")
        s2 = make_state(cycle_id="s2")
        r1 = ch.evaluate(s1)
        r2 = ch.evaluate(s2)
        assert r1 is not r2  # separate objects
        # Each result carries its own cycle metadata implicitly via target_tier.
        # (target_tier is shared since both states span Q1.)
        assert r1.target_window_days == 7
        assert r2.target_window_days == 7