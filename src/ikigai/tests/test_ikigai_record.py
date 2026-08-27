"""Tests for IKIGAiRecord — SPEC §1 root class.

Covers the load-bearing invariants from §3.6 (PD/FR/SA/OV/PH) that touch
the root itself rather than its child entities.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from ikigai.entities.correction_signal import CorrectionSignal
from ikigai.entities.fractal_regime import FractalRegime, FractalRegimeState
from ikigai.entities.ikigai_record import (
    EntityType, IKIGAiRecord, ScoreUnit, ScoreValue, StatusType,
)


def _sample_ueid() -> str:
    return "ikigai:dream:vaga_remota_2026:1a2b3c4d:9f8e7d6c"


def _regime() -> FractalRegime:
    return FractalRegime(levels=[
        FractalRegimeState(level=l, regime="push", days_in_regime=10,
                           is_hysteresis_active=False, hysteresis_days=14)
        for l in ("global", "cluster", "vector", "sub_vector")
    ])


def _q_he() -> ScoreValue:
    return ScoreValue(value=0.85, unit=ScoreUnit.RATIO)


def _minimal_record(**overrides: Any) -> IKIGAiRecord:
    kwargs = dict(
        ueid=_sample_ueid(),
        entity_type=EntityType.DREAM,
        slug="vaga-remota-2026",
        title="Vaga remota 2026",
        created_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
        updated_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
        source_md_path=Path("data/matheus/dreams/vaga-remota-2026.md"),
        regime=_regime(),
        q_he_score=_q_he(),
    )
    kwargs.update(overrides)
    return IKIGAiRecord(**kwargs)


class TestIKIGAiRecordIdentity:
    def test_minimal_construction(self) -> None:
        r = _minimal_record()
        assert r.entity_type is EntityType.DREAM
        assert r.status is StatusType.DRAFT  # default
        assert r.drift_state.value == "in_sync"  # default
        assert r.is_placeholder is False  # default

    def test_invalid_ueid_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _minimal_record(ueid="not-a-ueid")


class TestIKIGAiRecordDiscriminator:
    """SPEC D6 — `entity_type` is the polymorphic discriminator."""

    def test_each_entity_type_loads(self) -> None:
        for et in (
            EntityType.DREAM, EntityType.GOAL, EntityType.OBJECTIVE,
            EntityType.PROJECT, EntityType.TASK, EntityType.DELIVERABLE,
            EntityType.ROUTINE, EntityType.HABIT, EntityType.VECTOR,
            EntityType.CYCLE,
        ):
            r = _minimal_record(entity_type=et)
            assert r.entity_type is et

    def test_cycle_variant_marked_placeholder_per_d7(self) -> None:
        """Per SPEC D7 + §3.2 — cycle logs are derived → is_placeholder=True."""
        r = _minimal_record(
            entity_type=EntityType.CYCLE,
            is_placeholder=True,
            placeholder_owner="agent",
        )
        assert r.is_placeholder is True
        assert r.placeholder_owner == "agent"


class TestIKIGAiRecordInvariants:
    def test_phase_iteration_bounds_i11(self) -> None:
        with pytest.raises(ValidationError):
            _minimal_record(phase_iteration=6)  # > 5
        with pytest.raises(ValidationError):
            _minimal_record(phase_iteration=-1)  # < 0
        r = _minimal_record(phase_iteration=3)
        assert r.phase_iteration == 3

    def test_recommendation_score_bounds(self) -> None:
        with pytest.raises(ValidationError):
            _minimal_record(recommendation_score=1.5)
        r = _minimal_record(recommendation_score=0.5)
        assert r.recommendation_score == 0.5

    def test_source_md_path_required_d8(self) -> None:
        """SPEC D8/I9 — markdown is canonical, source_md_path REQUIRED."""
        with pytest.raises(ValidationError):
            _minimal_record(source_md_path=None)  # type: ignore[arg-type]

    def test_phase_weights_field_removed_i7(self) -> None:
        """SPEC I7 — phase weights live on separate PhaseSnapshot, NOT here."""
        r = _minimal_record()
        assert "phase_weights" not in IKIGAiRecord.model_fields
        assert "phase_weights" not in r.model_dump()

    def test_extra_field_allowed_per_d6(self) -> None:
        """SPEC D6 — `extra="allow"` so entity-specific fields pass through."""
        r = _minimal_record(custom={"motivation": "freedom + income + learning"})
        assert r.custom["motivation"] == "freedom + income + learning"


class TestIKIGAiRecordAggregates:
    def test_corrections_typed_list(self) -> None:
        r = _minimal_record(corrections=[
            CorrectionSignal(
                heuristic="qhe_trend", signal_type="drift",
                description="Q_HE down 3d", target_ueid=None,
                urgency="high", metadata={},
                created_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
            ),
        ])
        assert len(r.corrections) == 1
        assert r.corrections[0].signal_type == "drift"

    def test_fractal_regime_round_trip(self) -> None:
        r = _minimal_record()
        assert r.regime is not None
        assert len(r.regime.levels) == 4

    def test_vector_scores_with_fractal_keys(self) -> None:
        r = _minimal_record(vector_scores={
            "skill": ScoreValue(value=70, unit=ScoreUnit.PERCENT),
            "skill.python": ScoreValue(value=85, unit=ScoreUnit.PERCENT),
        })
        assert "skill.python" in r.vector_scores  # SPEC D3 — fractal keys

    def test_active_ueid_lists_round_trip(self) -> None:
        r = _minimal_record(
            active_project_ueids=[
                "ikigai:project:byd_deep_dive:1a2b3c4d:9f8e7d6c",
                "ikigai:project:salvador_data:2b3c4d5e:0a1b2c3d",
            ],
        )
        assert len(r.active_project_ueids) == 2