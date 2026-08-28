import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import PropagationEvent, TaskAction


@pytest.fixture
def tasks_jsonl(tmp_path: Path, monkeypatch) -> Path:
    """Create empty tasks.jsonl in tmp dir, point CLI adapter at it."""
    tasks_file = tmp_path / "tasks.jsonl"
    tasks_file.write_text("")  # empty

    from src.mesh.adapters import cli
    monkeypatch.setattr(cli, "TASKS_JSONL", tasks_file)
    return tasks_file


def _sample_event(ueid: str = "tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000") -> PropagationEvent:
    return PropagationEvent(
        event_id="evt_001",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": "Test task", "due": "2099-01-01"},
        approved_at=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )


def test_cli_adapter_apply_change_appends_task(tasks_jsonl: Path):
    """apply_change appends new task to tasks.jsonl."""
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    lines = tasks_jsonl.read_text().strip().split("\n")
    assert len(lines) == 1
    task = json.loads(lines[0])
    assert task["ueid"] == event.ueid
    assert task["title"] == "Test task"


def test_cli_adapter_read_returns_slice(tasks_jsonl: Path):
    """read() returns slice for given UEID."""
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    slice = adapter.read(event.ueid)
    assert slice is not None
    assert slice["ueid"] == event.ueid


def test_cli_adapter_read_returns_none_for_unknown(tasks_jsonl: Path):
    """read() returns None when UEID not in tasks.jsonl."""
    from src.mesh.adapters.cli import CliAdapter
    from src.contracts.common import UEID

    adapter = CliAdapter()
    unknown_ueid: UEID = "tsk:other:00000000-0000-0000-0000-000000000000:0000000000000000"
    assert adapter.read(unknown_ueid) is None


def test_cli_adapter_supports_field():
    """CliAdapter supports title, due, priority fields."""
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()
    assert adapter.supports_field("title") is True
    assert adapter.supports_field("due") is True
    assert adapter.supports_field("priority") is True
    assert adapter.supports_field("start_at") is False
