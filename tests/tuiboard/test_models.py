"""Tests for tuiboard Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.tuiboard.models import (
    TuiboardRenderInput,
    TuiboardSnapshotInput,
    TuiboardDiffInput,
)


def test_render_input_minimal():
    inp = TuiboardRenderInput(layout="kanban")
    assert inp.ueids == []
    assert inp.filters is None


def test_render_input_validates_layout():
    with pytest.raises(ValidationError):
        TuiboardRenderInput(layout="invalid")  # type: ignore[arg-type]


def test_render_input_frozen_rejects_mutation():
    inp = TuiboardRenderInput(layout="list")
    with pytest.raises(ValidationError):
        inp.layout = "kanban"  # type: ignore[misc]


def test_snapshot_input_validates_name_length():
    with pytest.raises(ValidationError):
        TuiboardSnapshotInput(name="x" * 65, layout="kanban")


def test_diff_input_validates_required_ids():
    with pytest.raises(ValidationError):
        TuiboardDiffInput(from_snapshot_id="", to_snapshot_id="abc")
