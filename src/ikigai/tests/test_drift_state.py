"""Tests for DriftState enum."""
from ikigai.entities.drift_state import DriftState


def test_four_states_present() -> None:
    assert {s.value for s in DriftState} == {"in_sync", "markdown_newer", "sqlite_newer", "conflict"}
