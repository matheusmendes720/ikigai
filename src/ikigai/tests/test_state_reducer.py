"""Tests for StateReducer — IKIGAiStateDict → IKIGAiRecord.

Task 10 of data-model-unification: collapses the in-memory LangGraph
state into the canonical IKIGAiRecord polymorphic root.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from ikigai.adapters.state_reducer import StateReducer
from ikigai.entities.ikigai_record import IKIGAiRecord, EntityType


@pytest.fixture
def state_dict() -> dict:
    return {
        "cycle_id": "ikigai:cycle:2026-08-26:00000000:00000001",
        "cycle_start": "2026-08-26",
        "cycle_end": "2026-09-02",
        "iteration": 2,
        "last_step": "commit",
        "regime_state": "PUSH",
        "q_he_score": 0.82,
        "days_in_regime": 5,
        "is_hysteresis_active": False,
        "phase": "BUSCA",
        "phase_iteration": 1,
        "phase_converged": False,
        "phase_weights": {"passion": 0.30, "skill": 0.25, "market": 0.20},
        "vector_scores": {
            "passion": 0.9, "skill": 0.8, "market": 0.7, "revenue": 0.6, "course": 0.5,
        },
        "meta_vector_score": 0.71,
        "active_dream_ueid": "ikigai:dream:2026-q3:00000000:00000001",
        "active_goal_ueids": [],
        "active_objective_ueids": [],
        "active_project_ueids": [],
        "active_task_ueids": [],
        "workload_estimate": 5.5,
        "capacity_estimate": 8.0,
        "balancer_verdict": "OK",
        "prospective_buffer": ["observe q_he trend"],
        "retrospective_log": ["regime stayed PUSH"],
        "corrections": [],
        "kill_switch_triggered": False,
        "terminated": False,
        "messages": [{"role": "user", "content": "score"}],
    }


def test_reduce_emits_cycle_entity(state_dict: dict) -> None:
    rec = StateReducer.reduce(state_dict, source_md_path=Path("data/matheus/ikigai_state/cycle-2026-08-26.md"))
    assert isinstance(rec, IKIGAiRecord)
    assert rec.entity_type == EntityType.CYCLE
    # CYCLE is a derived log entry per SPEC D7
    assert rec.is_placeholder is True


def test_reduce_maps_regime_into_fractal_regime(state_dict: dict) -> None:
    rec = StateReducer.reduce(state_dict, source_md_path=Path("data/matheus/ikigai_state/cycle-2026-08-26.md"))
    assert rec.regime is not None
    levels = [lvl.level for lvl in rec.regime.levels]
    assert levels == ["global", "cluster", "vector", "sub_vector"]


def test_reduce_maps_vector_scores(state_dict: dict) -> None:
    rec = StateReducer.reduce(state_dict, source_md_path=Path("data/matheus/ikigai_state/cycle-2026-08-26.md"))
    assert rec.vector_scores is not None
    # each vector score became a ScoreValue with unit="percent"
    for key, sv in rec.vector_scores.items():
        assert sv.unit == "percent"
        assert 0.0 <= sv.value <= 100.0


def test_reduce_preserves_corrections_buffer_and_retrospective(state_dict: dict) -> None:
    rec = StateReducer.reduce(state_dict, source_md_path=Path("data/matheus/ikigai_state/cycle-2026-08-26.md"))
    assert rec.corrections == []
    assert rec.prospective_buffer == ["observe q_he trend"]
    assert rec.retrospective_log == ["regime stayed PUSH"]


def test_reduce_sets_ueid_from_cycle_id(state_dict: dict) -> None:
    rec = StateReducer.reduce(state_dict, source_md_path=Path("data/matheus/ikigai_state/cycle-2026-08-26.md"))
    # ueid is preserved as-is from the cycle_id in state_dict
    assert rec.ueid == state_dict["cycle_id"]


def test_reduce_sets_source_md_path(state_dict: dict) -> None:
    p = Path("data/matheus/ikigai_state/cycle-2026-08-26.md")
    rec = StateReducer.reduce(state_dict, source_md_path=p)
    assert rec.source_md_path == p


def test_reduce_initialises_timestamps(state_dict: dict) -> None:
    rec = StateReducer.reduce(state_dict, source_md_path=Path("data/matheus/ikigai_state/cycle-2026-08-26.md"))
    assert isinstance(rec.created_at, datetime)
    assert isinstance(rec.updated_at, datetime)
    assert rec.created_at.tzinfo is not None


def test_reduce_maps_balancer_verdict(state_dict: dict) -> None:
    rec = StateReducer.reduce(state_dict, source_md_path=Path("data/matheus/ikigai_state/cycle-2026-08-26.md"))
    assert rec.balancer_verdict is not None
    # balancer_verdict is a Literal on IKIGAiRecord; pass-through string
    assert rec.balancer_verdict == "OK"