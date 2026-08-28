import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.contracts.task_change import TaskChange, TaskAction
from src.mesh.agent_consumer import ValidationResult, Decision


@pytest.fixture
def sample_event() -> TaskChange:
    return TaskChange(
        event_id="evt_001",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Test", "due": "2099-01-01"},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )


def test_propagate_calls_all_adapters(sample_event):
    """propagate() calls apply_change() on every registered adapter."""
    from src.mesh.agent_propagator import propagate
    from src.mesh.adapters.base import ForkAdapter

    adapter1 = MagicMock(spec=ForkAdapter)
    adapter1.name = "taskdog"
    adapter1.apply_change.return_value = MagicMock(success=True)

    adapter2 = MagicMock(spec=ForkAdapter)
    adapter2.name = "solverforge_calendar"
    adapter2.apply_change.return_value = MagicMock(success=True)

    result = propagate(
        sample_event,
        ValidationResult(Decision.APPROVE, approved_fields=sample_event.fields),
        adapters=[adapter1, adapter2],
    )

    assert len(result) == 2
    assert all(r.success for r in result)
    adapter1.apply_change.assert_called_once()
    adapter2.apply_change.assert_called_once()


def test_propagate_marks_partial_when_adapter_fails(sample_event):
    """propagate() marks partial_propagation if any adapter fails."""
    from src.mesh.agent_propagator import propagate
    from src.mesh.adapters.base import ForkAdapter

    adapter_ok = MagicMock(spec=ForkAdapter)
    adapter_ok.name = "taskdog"
    adapter_ok.apply_change.return_value = MagicMock(success=True)

    adapter_fail = MagicMock(spec=ForkAdapter)
    adapter_fail.name = "solverforge_calendar"
    adapter_fail.apply_change.side_effect = ConnectionError("solverforge down")

    result = propagate(
        sample_event,
        ValidationResult(Decision.APPROVE, approved_fields=sample_event.fields),
        adapters=[adapter_ok, adapter_fail],
    )

    assert len(result) == 2
    assert result[0].success is True
    assert result[1].success is False


def test_propagate_is_idempotent(sample_event):
    """Same event_id twice produces same UEID writes (no double-apply)."""
    from src.mesh.agent_propagator import propagate
    from src.mesh.agent_consumer import ValidationResult, Decision
    from src.mesh.adapters.base import ForkAdapter

    adapter = MagicMock(spec=ForkAdapter)
    adapter.name = "taskdog"
    adapter.apply_change.return_value = MagicMock(success=True)

    result1 = propagate(
        sample_event,
        ValidationResult(Decision.APPROVE, approved_fields=sample_event.fields),
        adapters=[adapter],
    )
    result2 = propagate(
        sample_event,
        ValidationResult(Decision.APPROVE, approved_fields=sample_event.fields),
        adapters=[adapter],
    )

    # Adapter called twice (each propagation is independent)
    assert adapter.apply_change.call_count == 2
    # Both results are success
    assert result1[0].success is True
    assert result2[0].success is True


def test_propagate_acks_partial_propagation_in_queue(sample_event, tmp_path, monkeypatch):
    """propagate() acks queue as 'partial_propagation' so consume_pending() skips it."""
    from src.mesh import queue
    from src.mesh.agent_propagator import propagate
    from src.mesh.adapters.base import ForkAdapter

    # Isolate queue dir
    qdir = tmp_path / "queue"
    qdir.mkdir()
    monkeypatch.setattr(queue, "QUEUE_DIR", qdir)

    # Enqueue the sample event
    queue.enqueue(sample_event)
    assert len(list(queue.consume_pending())) == 1  # sanity check

    adapter_ok = MagicMock(spec=ForkAdapter)
    adapter_ok.name = "taskdog"
    adapter_ok.apply_change.return_value = MagicMock(success=True)

    adapter_fail = MagicMock(spec=ForkAdapter)
    adapter_fail.name = "solverforge_calendar"
    adapter_fail.apply_change.side_effect = ConnectionError("solverforge down")

    result = propagate(
        sample_event,
        ValidationResult(Decision.APPROVE, approved_fields=sample_event.fields),
        adapters=[adapter_ok, adapter_fail],
    )

    # Partial propagation observed
    assert any(not r.success for r in result)

    # Queue event is acked as partial_propagation
    assert list(queue.consume_pending()) == []
    content = json.loads((qdir / f"{sample_event.event_id}.json").read_text())
    assert content["status"] == "partial_propagation"
