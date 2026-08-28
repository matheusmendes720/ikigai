"""End-to-end: task-add → data/tasks.jsonl + data/review_queue/<event_id>.json

This is the smoke test for Phase A foundation.
Verifies that:
  1. task_add() writes a row to CliAdapter slice (data/tasks.jsonl)
  2. task_add() enqueues a TaskChange event (data/review_queue/<id>.json)
  3. Both files are well-formed JSON
  4. Event has pending status (awaiting agent review)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from interfaces.cli.read_tasks import do_task_add
from src.contracts.common import UEID
from src.contracts.task_change import TaskAction, TaskChange


def _parse_iso(ts: str) -> datetime:
    """Parse ISO timestamp from JSON, handling Z suffix and offset."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@pytest.fixture
def clean_console(monkeypatch):
    """Silence Rich console output during tests."""
    import os
    from rich.console import Console

    monkeypatch.setattr(
        "interfaces.cli.read_tasks.console",
        Console(file=open(os.devnull, "w"), quiet=True),
    )


def test_task_add_writes_to_cli_slice(tmp_data_dir, clean_console) -> None:
    """CliAdapter writes to data/tasks.jsonl atomically."""
    do_task_add(title="E2E: write slice", due=None, priority="high")

    tasks_path: Path = tmp_data_dir / "tasks.jsonl"
    assert tasks_path.exists(), "CliAdapter should have created tasks.jsonl"

    lines = tasks_path.read_text().strip().splitlines()
    assert len(lines) == 1, f"expected 1 task, got {len(lines)}"

    record = json.loads(lines[0])
    assert record["title"] == "E2E: write slice"
    assert record["priority"] == "high"
    assert record["due"] is None
    assert record["source_fork"] == "interfaces/cli"
    UEID(record["ueid"])  # validates 5-part format


def test_task_add_enqueues_mesh_event(tmp_data_dir, clean_console) -> None:
    """task_add enqueues a TaskChange to data/review_queue/."""
    do_task_add(title="E2E: enqueue event", due=None, priority="medium")

    queue_dir: Path = tmp_data_dir / "review_queue"
    files = list(queue_dir.glob("*.json"))
    assert len(files) == 1, f"expected 1 event file, got {len(files)}"

    event = TaskChange.model_validate_json(files[0].read_text())
    assert event.action == TaskAction.CREATE
    assert event.source_fork == "interfaces/cli"
    assert event.status == "pending"
    assert event.fields["title"] == "E2E: enqueue event"
    assert event.fields["priority"] == "medium"
    # event_id format: evt_<12 hex>
    assert event.event_id.startswith("evt_")
    assert len(event.event_id) == 4 + 12


def test_task_add_sanitizes_slug_in_ueid(tmp_data_dir, clean_console) -> None:
    """Title with special chars produces a valid UEID slug."""
    do_task_add(title="Fix bug #1234 (urgent)!", due=None, priority="high")

    # tasks.jsonl
    record = json.loads((tmp_data_dir / "tasks.jsonl").read_text().strip())
    ueid = UEID(record["ueid"])
    parts = str(ueid).split(":")
    slug = parts[1]
    # No +, no #, no parens — sanitized to hyphens
    assert "+" not in slug
    assert "#" not in slug
    assert "(" not in slug
    assert ")" not in slug
    assert "!" not in slug


def test_task_add_idempotent_per_title(tmp_data_dir, clean_console) -> None:
    """Two task_add calls with same title create two distinct UEIDs (uuid4 disambiguates)."""
    do_task_add(title="Same title", due=None, priority="low")
    do_task_add(title="Same title", due=None, priority="low")

    tasks_path: Path = tmp_data_dir / "tasks.jsonl"
    lines = tasks_path.read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["ueid"] != second["ueid"], "two tasks with same title must have distinct UEIDs"


def test_task_add_preserves_existing_tasks(tmp_data_dir, clean_console) -> None:
    """Atomic temp+rename pattern preserves previously-written tasks."""
    do_task_add(title="Task #1", due=None, priority="low")
    do_task_add(title="Task #2", due=None, priority="medium")
    do_task_add(title="Task #3", due=None, priority="high")

    lines = (tmp_data_dir / "tasks.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3
    titles = [json.loads(line)["title"] for line in lines]
    assert titles == ["Task #1", "Task #2", "Task #3"]
