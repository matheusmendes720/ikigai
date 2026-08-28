"""Tests for agent_consumer PAE validation."""
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.contracts.task_change import TaskChange, TaskAction


@pytest.fixture
def sample_create_event() -> TaskChange:
    return TaskChange(
        event_id="evt_001",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Review BYD case", "due": "2099-01-01"},  # far future = valid
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )


@pytest.fixture
def vault_context_empty(tmp_path: Path, monkeypatch) -> Path:
    """Create empty vault dir for context loading."""
    vault = tmp_path / "vault"
    (vault / "ikigai" / "closing-2026").mkdir(parents=True)
    monkeypatch.setenv("VAULT_PATH", str(vault))
    return vault


def test_validate_approves_clean_event(sample_create_event, vault_context_empty):
    """Validate returns approve for a clean event with valid fields."""
    from src.mesh.agent_consumer import validate, Decision

    result = validate(sample_create_event)
    assert result.decision == Decision.APPROVE


def test_validate_rejects_past_due_date(vault_context_empty):
    """Validate rejects event with due date in the past."""
    from src.mesh.agent_consumer import validate, Decision

    event = TaskChange(
        event_id="evt_002",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Past task", "due": "2020-01-01"},  # in the past
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )
    result = validate(event)
    assert result.decision == Decision.REJECT
    assert "past" in result.reason.lower()


def test_validate_clarifies_vague_title(vault_context_empty):
    """Validate asks clarification for vague title (<10 chars or generic)."""
    from src.mesh.agent_consumer import validate, Decision

    event = TaskChange(
        event_id="evt_003",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "todo"},  # too vague
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )
    result = validate(event)
    assert result.decision == Decision.CLARIFY
    assert "title" in result.reason.lower()


def test_validate_rejects_ueid_collision(vault_context_empty, sample_create_event):
    """Validate rejects if UEID already exists with different title."""
    from src.mesh.agent_consumer import validate, Decision

    # Mock the queue module - patch where it's imported (inside validate function)
    mock_queue = MagicMock()
    mock_existing = sample_create_event.model_copy(update={
        "status": "propagated",
    })
    mock_queue.replay_after_restart.return_value = [mock_existing]

    with patch("src.mesh.queue", mock_queue):
        # New event with same UEID but different title
        new_event = sample_create_event.model_copy(update={
            "event_id": "evt_004",
            "fields": {"title": "Different title", "due": "2099-01-01"},
        })
        result = validate(new_event)
        assert result.decision == Decision.REJECT
        assert "collision" in result.reason.lower() or "exists" in result.reason.lower()
