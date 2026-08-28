import pytest
from datetime import datetime, timezone
from src.contracts.task_change import TaskChange, TaskAction


def test_task_change_accepts_valid_create_event():
    event = TaskChange(
        event_id="evt_001",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action="create",
        fields={"title": "Test task", "due": "2026-08-29"},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )
    assert event.action == TaskAction.CREATE
    assert event.fields["title"] == "Test task"
    assert event.status == "pending"  # default


def test_task_change_rejects_invalid_action():
    with pytest.raises(ValueError):
        TaskChange(
            event_id="evt_002",
            ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
            action="invalid_action",  # not in Literal
            fields={},
            source_fork="interfaces/cli",
            timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        )


def test_task_change_rejects_invalid_ueid():
    with pytest.raises(ValueError):
        TaskChange(
            event_id="evt_003",
            ueid="not-a-ueid",
            action="create",
            fields={},
            source_fork="interfaces/cli",
            timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        )


def test_task_change_is_frozen():
    event = TaskChange(
        event_id="evt_004",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action="create",
        fields={},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )
    with pytest.raises(Exception):  # ValidationError for frozen
        event.status = "approved"


def test_task_change_rejects_extra_fields():
    with pytest.raises(ValueError):
        TaskChange(
            event_id="evt_005",
            ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
            action="create",
            fields={},
            source_fork="interfaces/cli",
            timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
            unknown_field="bad",  # extra="forbid"
        )
