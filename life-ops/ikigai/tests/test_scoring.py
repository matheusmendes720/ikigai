"""Tests for ikigai.core.scoring — vector scores, meta-vetor, Q_HE, RICE."""

from __future__ import annotations

import pytest
from ikigai.core.scoring.vector_scores import score_passion, score_skill, score_market, score_revenue, score_course
from ikigai.core.scoring.meta_vector import meta_vector, compute_alignment_label
from ikigai.core.scoring.qhe import compute_qhe, h_from_streak
from ikigai.core.scoring.rice import compute_rice_score, W_IKIGAI_BY_VECTOR
from ikigai.enums import AlignmentLabel, VectorType
from ikigai.types import ScoreValue


class TestScorePassion:
    """H(t) = 1 - e^(-λ * streak_days)."""

    def test_zero_streak(self) -> None:
        result = score_passion(0.0)
        assert result.value == 0.0

    def test_medium_streak(self) -> None:
        result = score_passion(25.0)
        assert 0 < result.value < 100

    def test_very_long_streak_saturates(self) -> None:
        result = score_passion(1000.0)
        assert result.value < 100.0

    def test_unit_is_percent(self) -> None:
        assert score_passion(10.0).unit == "percent"


class TestScoreSkill:
    """skill_score = weighted sum of (level×demand)/N * 0.5 + momentum*0.3 + completion*0.2."""

    def test_empty_skills(self) -> None:
        result = score_skill([], [], 0.0, 0.0)
        assert result.value == 0.0

    def test_single_skill(self) -> None:
        result = score_skill([50.0], [50.0], 0.0, 0.0)
        assert result.value > 0

    def test_high_momentum_boosts(self) -> None:
        low = score_skill([50.0], [50.0], 0.0, 0.0)
        high = score_skill([50.0], [50.0], 80.0, 0.0)
        assert high.value > low.value

    def test_unit_is_percent(self) -> None:
        assert score_skill([50.0], [50.0], 0.0, 0.0).unit == "percent"


class TestScoreMarket:
    """Market = fit*0.4 + demand*0.4 + pipeline*0.2."""

    def test_all_zero(self) -> None:
        result = score_market(0.0, 0.0, 0.0)
        assert result.value == 0.0

    def test_all_100(self) -> None:
        result = score_market(100.0, 100.0, 100.0)
        assert result.value == 100.0

    def test_unit_is_percent(self) -> None:
        assert score_market(50.0, 50.0, 50.0).unit == "percent"


class TestScoreRevenue:
    """Revenue = (actual/target)*70 + pipeline*0.3."""

    def test_zero_actual(self) -> None:
        result = score_revenue(0.0, 1000.0, 0.0)
        assert result.value == 0.0

    def test_half_target(self) -> None:
        result = score_revenue(500.0, 1000.0, 0.0)
        assert 30 < result.value < 40

    def test_exceeding_target(self) -> None:
        result = score_revenue(1500.0, 1000.0, 0.0)
        assert result.value <= 100.0

    def test_unit_is_percent(self) -> None:
        assert score_revenue(500.0, 1000.0, 50.0).unit == "percent"


class TestScoreCourse:
    """Course = attendance*0.5 + assignments*0.3 + exams*0.2."""

    def test_all_zero(self) -> None:
        result = score_course(0.0, 0.0, 0.0)
        assert result.value == 0.0

    def test_all_100(self) -> None:
        result = score_course(100.0, 100.0, 100.0)
        assert result.value == 100.0

    def test_attendance_heaviest(self) -> None:
        att = score_course(100.0, 0.0, 0.0)
        assign = score_course(0.0, 100.0, 0.0)
        assert att.value > assign.value

    def test_unit_is_percent(self) -> None:
        assert score_course(50.0, 50.0, 50.0).unit == "percent"


class TestHFromStreak:
    """H(t) = 1 - e^(-λ * streak)."""

    def test_zero_streak(self) -> None:
        assert h_from_streak(0.0) == 0.0

    def test_positive_streak(self) -> None:
        result = h_from_streak(30.0)
        assert 0 < result < 1

    def test_streak_approaches_one(self) -> None:
        result = h_from_streak(10000.0)
        assert result < 1.0


class TestComputeQHE:
    """Q_HE = sono*0.35 + med*0.20 + workout*0.25 + lunch*0.10 + streak*0.15."""

    def test_zero_inputs(self) -> None:
        result = compute_qhe(0.0, 0.0, 0.0, 0.0, 0.0)
        assert result == 0.0

    def test_perfect_inputs(self) -> None:
        result = compute_qhe(1.0, 1.0, 1.0, 1.0, 1.0)
        assert result == 1.0

    def test_mixed_inputs(self) -> None:
        result = compute_qhe(1.0, 0.0, 0.0, 0.0, 0.0)
        assert abs(result - 0.35) < 1e-9

    def test_returns_float(self) -> None:
        result = compute_qhe(0.8, 0.8, 0.8, 0.8, 0.8)
        assert isinstance(result, float)


class TestComputeRiceScore:
    """RICE = (R × I × C) / E. Returns raw float."""

    def test_zero_effort_guard(self) -> None:
        result = compute_rice_score(5.0, 1.0, 0.8, 0.0)
        assert result == (5.0 * 1.0 * 0.8) / 0.5

    def test_standard_inputs(self) -> None:
        result = compute_rice_score(10.0, 1.0, 0.8, 4.0)
        expected = (10.0 * 1.0 * 0.8) / 4.0
        assert result == expected

    def test_returns_raw_float(self) -> None:
        result = compute_rice_score(10.0, 1.0, 0.8, 4.0)
        assert isinstance(result, float)


class TestMetaVector:
    """Hybrid meta-vetor: geo + harmonic blend, returns ScoreValue."""

    def _scores(self, **kwargs: float) -> dict[VectorType, ScoreValue]:
        defaults = {"passion": 60.0, "skill": 70.0, "market": 55.0, "revenue": 50.0, "course": 65.0}
        defaults.update(kwargs)
        return {
            VectorType.PASSION: ScoreValue(defaults["passion"], "percent"),
            VectorType.SKILL: ScoreValue(defaults["skill"], "percent"),
            VectorType.MARKET: ScoreValue(defaults["market"], "percent"),
            VectorType.REVENUE: ScoreValue(defaults["revenue"], "percent"),
            VectorType.COURSE: ScoreValue(defaults["course"], "percent"),
        }

    def _weights(self) -> dict[VectorType, float]:
        return {
            VectorType.PASSION: 0.15,
            VectorType.SKILL: 0.40,
            VectorType.MARKET: 0.15,
            VectorType.REVENUE: 0.10,
            VectorType.COURSE: 0.20,
        }

    def test_all_zero_scores(self) -> None:
        scores = {v: ScoreValue(0.0, "percent") for v in VectorType}
        result = meta_vector(scores, self._weights())
        assert result.value == 0.0

    def test_all_100_scores(self) -> None:
        scores = {v: ScoreValue(100.0, "percent") for v in VectorType}
        result = meta_vector(scores, self._weights())
        assert result.value == 100.0

    def test_skill_heavier_than_passion(self) -> None:
        base = self._scores()
        boosted_skill = self._scores(skill=90.0)
        base_meta = meta_vector(base, self._weights())
        boosted_meta = meta_vector(boosted_skill, self._weights())
        assert boosted_meta.value > base_meta.value

    def test_hybrid_geo_and_harmonic(self) -> None:
        scores = self._scores()
        result = meta_vector(scores, self._weights())
        assert 0 < result.value < 100

    def test_unit_is_percent(self) -> None:
        result = meta_vector(self._scores(), self._weights())
        assert result.unit == "percent"


class TestComputeAlignmentLabel:
    """ALIGNED>=75, CONVERGING>=50, MISALIGNED>=25, CRITICAL<25."""

    def test_aligned(self) -> None:
        label = compute_alignment_label(80.0)
        assert label == AlignmentLabel.ALIGNED

    def test_converging(self) -> None:
        label = compute_alignment_label(60.0)
        assert label == AlignmentLabel.CONVERGING

    def test_misaligned(self) -> None:
        label = compute_alignment_label(35.0)
        assert label == AlignmentLabel.MISALIGNED

    def test_critical(self) -> None:
        label = compute_alignment_label(15.0)
        assert label == AlignmentLabel.CRITICAL

    def test_score_value_input(self) -> None:
        label = compute_alignment_label(ScoreValue(80.0, "percent"))
        assert label == AlignmentLabel.ALIGNED


class TestW_IKIGAI_BY_VECTOR:
    """W_IKIGAI_BY_VECTOR has string keys (not VectorType)."""

    def test_has_string_keys(self) -> None:
        for k in W_IKIGAI_BY_VECTOR:
            assert isinstance(k, str)

    def test_skill_highest(self) -> None:
        assert W_IKIGAI_BY_VECTOR["skill"] == 1.2

    def test_market_and_revenue_high(self) -> None:
        assert W_IKIGAI_BY_VECTOR["market"] == 1.5
        assert W_IKIGAI_BY_VECTOR["revenue"] == 1.5

    def test_course_lowest(self) -> None:
        assert W_IKIGAI_BY_VECTOR["course"] == 0.8
