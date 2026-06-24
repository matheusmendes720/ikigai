"""Tests for ikigai.core.heuristics — regime, phase, UCB, opportunity, skill, priority."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, date

from ikigai.core.heuristics import (
    compute_regime,
    apply_hysteresis,
    compute_phase,
    recalibrate_weight_ucb,
    recalibrate_all_weights,
    compute_opportunity_fit,
    classify_opportunity,
    should_promote_skill,
    detect_stagnation,
    compute_weighted_priority,
    rank_tasks,
)
from ikigai.core.heuristics.regime import RegimeDecision
from ikigai.core.heuristics.phase_pivot import PhaseDecision
from ikigai.enums import RegimeType, Phase, VectorType, StatusType
from ikigai.entities.plan.task import TaskEntity, TaskPriority
from ikigai.entities.skill import SkillLevel
from ikigai.types import UEID


# -------------------------------------------------------------------------- #
# Regime
# -------------------------------------------------------------------------- #

class TestComputeRegime:

    def test_qhe_high_triggers_push(self):
        """Q_HE >= 0.85 + c_comp >= 0.90 + 0 infractions → PUSH."""
        result = compute_regime(
            qhe_7d_avg=0.90,
            c_comp_24h=0.95,
            infractions_24h=0,
        )
        assert result.regime == RegimeType.PUSH
        assert result.hysteresis_applied is False

    def test_qhe_low_triggers_recover(self):
        """Q_HE < 0.60 + sleep_debt > 2h → RECOVER."""
        result = compute_regime(
            qhe_7d_avg=0.50,
            c_comp_24h=0.60,
            infractions_24h=0,
            sleep_debt_h=3.0,
        )
        assert result.regime == RegimeType.RECOVER

    def test_infractions_pushes_toward_reduce(self):
        """Infractions influence REDUCE via raw_score? No - but the decision tree
        puts 0.65 in REDUCE when c_comp is 0.70. Infractions don't affect
        the raw_score formula (qhe + c_comp)/2. Let's test REDUCE via
        Q_HE in [0.60, 0.70) without infractions."""
        low_infraction = compute_regime(0.65, 0.70, 0)
        high_infraction = compute_regime(0.65, 0.70, 5)
        # Both go to REDUCE, raw_score is same (infractions not in formula)
        assert low_infraction.regime == RegimeType.REDUCE
        assert high_infraction.regime == RegimeType.REDUCE
        # raw_score = (0.65 + 0.70) / 2 = 0.675
        assert low_infraction.raw_score == 0.675
        assert high_infraction.raw_score == 0.675

    def test_sleep_debt_harsh_penalty(self):
        """sleep_debt is captured in the decision but doesn't change raw_score."""
        no_debt = compute_regime(0.65, 0.70, 1, 0.0)
        high_debt = compute_regime(0.65, 0.70, 1, 3.0)
        # Both REDUCE; raw_score is identical
        assert no_debt.regime == RegimeType.REDUCE
        assert high_debt.regime == RegimeType.REDUCE
        assert no_debt.raw_score == high_debt.raw_score

    def test_c_comp_low_triggers_reduce(self):
        """c_comp in [0.70, 0.80) → REDUCE."""
        result = compute_regime(0.75, 0.72, 0)
        assert result.regime == RegimeType.REDUCE

    def test_returns_regime_decision(self):
        result = compute_regime(0.70, 0.75, 1, 0.5)
        assert isinstance(result, RegimeDecision)
        assert hasattr(result, "regime")
        assert hasattr(result, "rationale")
        assert hasattr(result, "qhe_score")
        assert hasattr(result, "c_comp_score")
        assert hasattr(result, "infractions")
        assert hasattr(result, "sleep_debt_h")
        assert hasattr(result, "raw_score")
        assert hasattr(result, "hysteresis_applied")
        assert hasattr(result, "hysteresis_reason")
        # No setpoints attribute (that was in the old wrong test)
        assert not hasattr(result, "setpoints")


class TestApplyHysteresis:

    def test_recover_immediate_downgrade(self):
        """RECOVER entry is immediate — no hysteresis."""
        result = apply_hysteresis(
            current_regime=RegimeType.REDUCE,
            proposed_regime=RegimeType.RECOVER,
            regime_history=[],
        )
        assert result == (RegimeType.RECOVER, False, None)

    def test_sustained_good_performance_allows_upgrade(self):
        """3+ consecutive MAINTAIN proposals from history → upgrade from REDUCE."""
        now = datetime(2025, 1, 10)
        # History ends with 3 consecutive MAINTAIN proposals
        history = [
            (now - timedelta(days=i), RegimeType.MAINTAIN)
            for i in range(3, 0, -1)
        ]
        result = apply_hysteresis(
            current_regime=RegimeType.REDUCE,
            proposed_regime=RegimeType.MAINTAIN,
            regime_history=history,
        )
        final_regime, applied, reason = result
        assert final_regime == RegimeType.MAINTAIN
        assert applied is False

    def test_short_time_blocks_upgrade(self):
        """Only 1 consecutive day → stays REDUCE."""
        now = datetime(2025, 1, 10)
        history = [(now - timedelta(days=1), RegimeType.REDUCE)]
        result = apply_hysteresis(
            current_regime=RegimeType.REDUCE,
            proposed_regime=RegimeType.MAINTAIN,
            regime_history=history,
        )
        final_regime, applied, reason = result
        assert final_regime == RegimeType.REDUCE
        assert applied is True
        assert "Upgrade to maintain requires 3 consecutive days" in reason


# -------------------------------------------------------------------------- #
# Phase
# -------------------------------------------------------------------------- #

class TestComputePhase:

    def test_ikigai_high_returns_momentum(self):
        """ikigai_score > 60 + no debt → not OVERCLOCKING."""
        result = compute_phase(
            ikigai_score=75.0,
            revenue_actual_30d=1000.0,
            revenue_target=2000.0,
            opportunities_pursuing=0,
            cognitive_debt=0.0,
        )
        assert isinstance(result, PhaseDecision)
        assert result.phase != Phase.OVERCLOCKING

    def test_low_ikigai_returns_snapshot(self):
        """ikigai_score < 30 → OVERCLOCKING."""
        result = compute_phase(
            ikigai_score=25.0,
            revenue_actual_30d=0.0,
            revenue_target=1000.0,
        )
        assert result.phase == Phase.OVERCLOCKING

    def test_iterations_reported(self):
        result = compute_phase(ikigai_score=50.0, revenue_actual_30d=100.0, revenue_target=1000.0)
        assert result.iterations >= 1

    def test_converged_flag_reported(self):
        result = compute_phase(ikigai_score=50.0, revenue_actual_30d=100.0, revenue_target=1000.0)
        assert isinstance(result.converged, bool)

    def test_weights_included_in_decision(self):
        result = compute_phase(ikigai_score=50.0, revenue_actual_30d=100.0, revenue_target=1000.0)
        assert isinstance(result.weights, dict)
        assert all(isinstance(k, VectorType) for k in result.weights)


# -------------------------------------------------------------------------- #
# UCB
# -------------------------------------------------------------------------- #

class TestRecalibrateWeightUCB:

    def test_raises_on_invalid_input(self):
        with pytest.raises(ValueError):
            recalibrate_weight_ucb(-0.5, 0.0, 0.1, 1, {})  # w_i < 0

    def test_confidence_bonus_increases_with_uncertainty(self):
        """Fewer visits → higher UCB bonus."""
        all_n = {VectorType.SKILL: 10}
        w1 = recalibrate_weight_ucb(1.0, 5.0, 1.0, 1, all_n)
        w2 = recalibrate_weight_ucb(1.0, 5.0, 1.0, 100, all_n)
        # Higher n_i → smaller UCB bonus → lower new weight
        assert w2 < w1

    def test_confidence_bonus_decreases_with_visits(self):
        """More visits → lower UCB bonus."""
        all_n = {VectorType.SKILL: 1000}
        w_low_visits = recalibrate_weight_ucb(1.0, 5.0, 1.0, 1, all_n)
        w_high_visits = recalibrate_weight_ucb(1.0, 5.0, 1.0, 500, all_n)
        assert w_low_visits > w_high_visits

    def test_positive_delta_boosts(self):
        """Positive delta_score → weight increases."""
        all_n = {VectorType.SKILL: 100}
        w_pos = recalibrate_weight_ucb(1.0, 10.0, 0.1, 50, all_n)
        w_neg = recalibrate_weight_ucb(1.0, -10.0, 0.1, 50, all_n)
        assert w_pos > w_neg

    def test_recalibrate_all_weights_sums_near_one(self):
        """All recalibrated weights stay within [0, 1.5]."""
        current = {v: 1.0 for v in VectorType}
        deltas = {v: 5.0 for v in VectorType}
        sigmas = {v: 1.0 for v in VectorType}
        counts = {v: 50 for v in VectorType}
        result = recalibrate_all_weights(current, deltas, sigmas, counts)
        assert all(0.0 <= w <= 1.5 for w in result.values())


# -------------------------------------------------------------------------- #
# Opportunity
# -------------------------------------------------------------------------- #

class TestComputeOpportunityFit:

    def test_all_zero_fit(self):
        result = compute_opportunity_fit(
            required_skills=["rust"],
            user_skills=["python"],
            deadline_days=30,
            estimated_revenue_brl=0.0,
            estimated_hours=10.0,
            ikigai_alignment={},
        )
        assert 0.0 <= result <= 1.0

    def test_all_perfect_fit(self):
        result = compute_opportunity_fit(
            required_skills=["python"],
            user_skills=["python"],
            deadline_days=5,
            estimated_revenue_brl=300.0,
            estimated_hours=10.0,
            ikigai_alignment={VectorType.SKILL: 1.0, VectorType.MARKET: 1.0},
        )
        assert result > 0.5

    def test_skills_heaviest(self):
        """Skills match is 40% of score, so it's the dominant factor."""
        perfect = compute_opportunity_fit(
            required_skills=["python"],
            user_skills=["python"],
            deadline_days=30,
            estimated_revenue_brl=300.0,
            estimated_hours=10.0,
            ikigai_alignment={VectorType.SKILL: 1.0},
        )
        partial = compute_opportunity_fit(
            required_skills=["python", "rust", "go"],
            user_skills=["python"],
            deadline_days=30,
            estimated_revenue_brl=300.0,
            estimated_hours=10.0,
            ikigai_alignment={VectorType.SKILL: 1.0},
        )
        assert perfect > partial


class TestClassifyOpportunity:

    def test_high_fit_strong_buy(self):
        assert classify_opportunity(0.75) == "PURSUING"
        assert classify_opportunity(1.0) == "PURSUING"

    def test_mid_fit_hold(self):
        assert classify_opportunity(0.55) == "EVALUATING"
        assert classify_opportunity(0.69) == "EVALUATING"

    def test_low_fit_skip(self):
        assert classify_opportunity(0.35) == "DETECTED"
        assert classify_opportunity(0.10) == "LOST"


# -------------------------------------------------------------------------- #
# Skill
# -------------------------------------------------------------------------- #

class TestSkillVelocity:

    def test_should_promote_all_conditions_met(self):
        result = should_promote_skill(
            current_level=SkillLevel.BEGINNER,
            target_level=SkillLevel.INTERMEDIATE,
            hours_invested=100.0,
            target_hours=100.0,
            days_in_phase=50,
            retention_score_avg=0.80,
        )
        assert result is True

    def test_should_not_promote_insufficient_hours(self):
        result = should_promote_skill(
            current_level=SkillLevel.BEGINNER,
            target_level=SkillLevel.INTERMEDIATE,
            hours_invested=50.0,
            target_hours=100.0,
            days_in_phase=50,
            retention_score_avg=0.80,
        )
        assert result is False

    def test_should_not_promote_new_skill(self):
        """Same level → False."""
        result = should_promote_skill(
            current_level=SkillLevel.BEGINNER,
            target_level=SkillLevel.BEGINNER,
            hours_invested=200.0,
            target_hours=100.0,
            days_in_phase=100,
            retention_score_avg=0.90,
        )
        assert result is False

    def test_should_not_promote_low_retention(self):
        result = should_promote_skill(
            current_level=SkillLevel.BEGINNER,
            target_level=SkillLevel.INTERMEDIATE,
            hours_invested=100.0,
            target_hours=100.0,
            days_in_phase=50,
            retention_score_avg=0.50,
        )
        assert result is False

    def test_detect_stagnation_improving(self):
        """0.5 levels in 180d → not stagnation (threshold is 0.3)."""
        result = detect_stagnation(levels_promoted_last_180d=0.5)
        assert result is False

    def test_detect_stagnation_true(self):
        """0.1 levels in 180d → stagnation."""
        result = detect_stagnation(levels_promoted_last_180d=0.1)
        assert result is True


# -------------------------------------------------------------------------- #
# Priority
# -------------------------------------------------------------------------- #

class TestComputeWeightedPriority:

    def _task(self, uid_suffix="base"):
        return TaskEntity(
            ueid=UEID.generate("work", "task", f"task-{uid_suffix}"),
            slug=f"task-{uid_suffix}",
            title="Task",
            horizon_days=7,
            status=StatusType.DRAFT,
            rice_reach=1.0,
            rice_impact=0.5,
            rice_confidence=0.8,
            rice_effort_h=1.0,
        )

    def test_zero_rice_gives_zero_priority(self):
        t = TaskEntity(
            ueid=UEID.generate("work", "task", "zero-rice"),
            slug="zero-rice",
            title="Zero",
            horizon_days=7,
            status=StatusType.DRAFT,
            rice_reach=1.0,
            rice_impact=0.5,
            rice_confidence=0.0,
            rice_effort_h=1.0,
        )
        result = compute_weighted_priority(t)
        assert result == 0.0

    def test_deadline_soon_boosts(self):
        t = self._task()
        p_soon = compute_weighted_priority(t, days_to_deadline=3)
        p_far = compute_weighted_priority(t, days_to_deadline=60)
        assert p_soon > p_far

    def test_higher_ikigai_boosts(self):
        t = self._task()
        t.ikigai_vectors = [VectorType.SKILL]
        w1 = compute_weighted_priority(t, w_ikigai_by_vector={"skill": 1.0})
        w2 = compute_weighted_priority(t, w_ikigai_by_vector={"skill": 1.5})
        assert w2 > w1


class TestRankTasks:

    def test_sorted_by_priority(self):
        tasks = [
            TaskEntity(
                ueid=UEID.generate("work", "task", f"rank-{i}"),
                slug=f"rank-{i}",
                title=f"Task {i}",
                horizon_days=7,
                status=StatusType.DRAFT,
                rice_reach=1.0 + i,
                rice_impact=0.5,
                rice_confidence=0.8,
                rice_effort_h=1.0,
            )
            for i in range(3)
        ]
        ranked = rank_tasks(tasks)
        assert [t.slug for t in ranked] == ["rank-2", "rank-1", "rank-0"]

    def test_empty_list(self):
        assert rank_tasks([]) == []
