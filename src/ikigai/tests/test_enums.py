"""Tests for ikigai.enums — all enum classes."""

from __future__ import annotations

import pytest
from ikigai.enums import (
    AlignmentLabel,
    ClusterType,
    EntityType,
    Phase,
    RegimeType,
    SourceType,
    StatusType,
    VectorType,
)


class TestEntityType:
    """Polymorphic plan entity types."""

    def test_all_plan_types_present(self) -> None:
        """All 6 plan hierarchy types must be present."""
        names = {e.value for e in EntityType}
        for expected in ["dream", "goal", "objective", "project", "task", "deliverable"]:
            assert expected in names

    def test_values_are_lowercase(self) -> None:
        """All enum values must be lowercase strings."""
        for et in EntityType:
            assert et.value == et.value.lower()


class TestVectorType:
    """IKIGAi vector types."""

    def test_all_5_canonical_present(self) -> None:
        """All 5 canonical vectors must be present."""
        names = {v.value for v in VectorType}
        for expected in ["passion", "skill", "market", "revenue", "course"]:
            assert expected in names

    def test_passion_not_external(self) -> None:
        assert VectorType.PASSION.is_external is False

    def test_skill_not_external(self) -> None:
        assert VectorType.SKILL.is_external is False

    def test_course_is_external(self) -> None:
        assert VectorType.COURSE.is_external is True

    def test_canonical_names_returns_5(self) -> None:
        names = VectorType.canonical_names()
        assert len(names) == 5


class TestRegimeType:
    """4-state policy FSM."""

    def test_all_4_states_present(self) -> None:
        names = {r.value for r in RegimeType}
        for expected in ["push", "maintain", "reduce", "recover"]:
            assert expected in names

    def test_hardwork_budget_push(self) -> None:
        assert RegimeType.PUSH.hardwork_budget_h == 4.0

    def test_hardwork_budget_recover(self) -> None:
        assert RegimeType.RECOVER.hardwork_budget_h == 0.5

    def test_pause_min_push(self) -> None:
        assert RegimeType.PUSH.pause_min == 10

    def test_pause_min_recover(self) -> None:
        assert RegimeType.RECOVER.pause_min == 30

    def test_sleep_target_push(self) -> None:
        assert RegimeType.PUSH.sleep_target_h == 7.5

    def test_sleep_target_recover(self) -> None:
        assert RegimeType.RECOVER.sleep_target_h == 9.0

    def test_qhe_target_push(self) -> None:
        assert RegimeType.PUSH.qhe_target == 0.85

    def test_qhe_target_recover(self) -> None:
        assert RegimeType.RECOVER.qhe_target == 0.25

    def test_c_comp_target_push(self) -> None:
        assert RegimeType.PUSH.c_comp_target == 0.90


class TestPhase:
    """5-phase IKIGAi cycle (PT-BR names)."""

    def test_all_5_phases_present(self) -> None:
        names = {p.value for p in Phase}
        for expected in ["fundacao", "busca", "hackathon", "recuperacao", "overclocking"]:
            assert expected in names

    def test_fundacao_weights(self) -> None:
        w = Phase.FUNDACAO.vector_weights
        assert w["passion"] == 0.15
        assert w["skill"] == 0.40
        assert w["market"] == 0.15
        assert w["revenue"] == 0.10
        assert w["course"] == 0.20

    def test_busca_weights(self) -> None:
        w = Phase.BUSCA.vector_weights
        assert w["passion"] == 0.10
        assert w["skill"] == 0.15
        assert w["market"] == 0.45

    def test_hackathon_weights(self) -> None:
        w = Phase.HACKATHON.vector_weights
        assert w["revenue"] == 0.40

    def test_overclocking_weights(self) -> None:
        w = Phase.OVERCLOCKING.vector_weights
        assert w["revenue"] == 0.50


class TestAlignmentLabel:
    """ALIGNED >= 75, CONVERGING >= 50, MISALIGNED >= 25, CRITICAL < 25."""

    def test_aligned_from_score(self) -> None:
        assert AlignmentLabel.from_score(80.0) == AlignmentLabel.ALIGNED
        assert AlignmentLabel.from_score(75.0) == AlignmentLabel.ALIGNED

    def test_converging_from_score(self) -> None:
        assert AlignmentLabel.from_score(60.0) == AlignmentLabel.CONVERGING
        assert AlignmentLabel.from_score(50.0) == AlignmentLabel.CONVERGING

    def test_misaligned_from_score(self) -> None:
        assert AlignmentLabel.from_score(35.0) == AlignmentLabel.MISALIGNED
        assert AlignmentLabel.from_score(25.0) == AlignmentLabel.MISALIGNED

    def test_critical_from_score(self) -> None:
        assert AlignmentLabel.from_score(20.0) == AlignmentLabel.CRITICAL
        assert AlignmentLabel.from_score(0.0) == AlignmentLabel.CRITICAL


class TestStatusType:
    """Generic status types."""

    def test_draft_and_active_present(self) -> None:
        values = {s.value for s in StatusType}
        assert "draft" in values
        assert "active" in values

    def test_done_present(self) -> None:
        assert "done" in {s.value for s in StatusType}


class TestClusterType:
    """Cluster taxonomy."""

    def test_plan_and_study_present(self) -> None:
        values = {c.value for c in ClusterType}
        assert "plan" in values
        assert "study" in values

    def test_ikigai_cluster_present(self) -> None:
        assert ClusterType.IKIGAI.value == "ikigai"


class TestSourceType:
    """Entity origin source."""

    def test_user_and_cli_present(self) -> None:
        values = {s.value for s in SourceType}
        assert "user" in values
        assert "cli" in values
