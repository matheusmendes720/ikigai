"""Tests for PhaseSnapshot — SPEC I7 phase weights live separately, not on IKIGAiRecord."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ikigai.entities.phase_snapshot import PhaseSnapshot


def test_round_trip() -> None:
    s = PhaseSnapshot(
        ueid="ikigai:phase_snapshot:2026-08-26:00000000:abcdef12",
        cycle_ueid="ikigai:cycle:2026-08-26:00000000:abcdef12",
        phase="fundacao",
        iteration=0,
        weights={"passion": 0.20, "skill": 0.20, "market": 0.20, "revenue": 0.20, "course": 0.20},
        created_at="2026-08-26T00:00:00Z",
    )
    assert s.phase == "fundacao"
    assert s.iteration == 0
    assert s.weight_sum() == pytest.approx(1.0)


def test_iteration_bounds() -> None:
    common = dict(
        ueid="ikigai:phase_snapshot:2026-08-26:00000000:abcdef12",
        cycle_ueid="ikigai:cycle:2026-08-26:00000000:abcdef12",
        phase="p",
        weights={"a": 1.0},
        created_at="2026-08-26T00:00:00Z",
    )
    with pytest.raises(ValidationError):
        PhaseSnapshot(iteration=6, **common)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        PhaseSnapshot(iteration=-1, **common)  # type: ignore[arg-type]


def test_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        PhaseSnapshot(
            ueid="ikigai:phase_snapshot:2026-08-26:0:abc12345",
            cycle_ueid="ikigai:cycle:2026-08-26:0000:0000",
            phase="p", iteration=0,
            weights={"a": 1.0},
            created_at="2026-08-26T00:00:00Z",
            extra_field="forbidden",
        )


def test_frozen() -> None:
    s = PhaseSnapshot(
        ueid="ikigai:phase_snapshot:2026-08-26:00000000:abcdef12",
        cycle_ueid="ikigai:cycle:2026-08-26:00000000:abcdef12",
        phase="p", iteration=0,
        weights={"a": 1.0},
        created_at="2026-08-26T00:00:00Z",
    )
    with pytest.raises(ValidationError):
        s.iteration = 3  # type: ignore[misc]


def test_weights_isolated_from_ikigai_record() -> None:
    """SPEC I7 — phase_weights MUST NOT live on IKIGAiRecord."""
    from ikigai.entities.ikigai_record import IKIGAiRecord
    assert "phase_weights" not in IKIGAiRecord.model_fields