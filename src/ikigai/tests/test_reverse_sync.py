"""reverse_sync() — enumerate taskdog, diff vs snapshot, emit TaskChange."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Ensure repo root on sys.path for imports
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.ikigai.src.ikigai.vault.sync import (
    ReverseSyncState,
    ReverseSyncTaskEntry,
    reverse_sync,
)


class FakeAdapter:
    """Minimal TaskdogAdapter stub returning hardcoded list."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def list_all(self) -> list[dict[str, Any]]:
        return self.rows


@pytest.fixture
def tmp_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Override QUEUE_DIR to a tmp dir for isolated queue writes."""
    qdir = tmp_path / "review_queue"
    monkeypatch.setattr("src.mesh.queue.QUEUE_DIR", qdir)
    return qdir


def _read_queue_events(qdir: Path) -> list[dict[str, Any]]:
    """Read all .json files in queue dir as TaskChange dicts."""
    events: list[dict[str, Any]] = []
    for p in sorted(qdir.glob("*.json")):
        events.append(json.loads(p.read_text()))
    return events


def test_reverse_sync_emits_done_for_moved_to_done(tmp_path: Path, tmp_queue: Path) -> None:
    """UEID in state with status=planned, taskdog now says done -> emit DONE event."""
    state_path = tmp_path / "state.json"
    initial = ReverseSyncState(
        version=1,
        tasks={
            "task:a1b2:abcdef01:12345678": ReverseSyncTaskEntry(
                last_seen_status="planned",
                last_seen_title="A",
                taskdog_id=1,
                vault_path="plans/a.md",
            ),
        },
    )
    initial_state_path = state_path
    # Write initial state
    from src.ikigai.src.ikigai.vault.sync import save_reverse_state
    save_reverse_state(initial_state_path, initial)

    adapter = FakeAdapter(
        rows=[
            {
                "ueid": "task:a1b2:abcdef01:12345678",
                "name": "A",
                "status": "done",
                "priority": 1,
            }
        ]
    )
    result = reverse_sync(state_path=state_path, adapter=adapter, review_queue_dir=tmp_queue)
    assert result.scanned == 1
    assert result.emitted == 1
    events = _read_queue_events(tmp_queue)
    assert len(events) == 1
    assert events[0]["action"] == "done"
    assert events[0]["ueid"] == "task:a1b2:abcdef01:12345678"
    assert events[0]["source_fork"] == "taskdog"


def test_reverse_sync_emits_update_for_status_change(tmp_path: Path, tmp_queue: Path) -> None:
    """Status changed (not to done) -> emit UPDATE event."""
    state_path = tmp_path / "state.json"
    from src.ikigai.src.ikigai.vault.sync import save_reverse_state
    save_reverse_state(
        state_path,
        ReverseSyncState(
            version=1,
            tasks={
                "task:b2c3:bcdef01:23456789": ReverseSyncTaskEntry(
                    last_seen_status="planned", last_seen_title="B", vault_path="plans/b.md"
                )
            },
        ),
    )
    adapter = FakeAdapter(
        rows=[{"ueid": "task:b2c3:bcdef01:23456789", "name": "B", "status": "in_progress", "priority": 2}]
    )
    reverse_sync(state_path=state_path, adapter=adapter, review_queue_dir=tmp_queue)
    events = _read_queue_events(tmp_queue)
    assert len(events) == 1
    assert events[0]["action"] == "update"
    assert events[0]["fields"]["status"] == "in_progress"


def test_reverse_sync_skips_unchanged(tmp_path: Path, tmp_queue: Path) -> None:
    """Same status as before -> no event."""
    state_path = tmp_path / "state.json"
    from src.ikigai.src.ikigai.vault.sync import save_reverse_state
    save_reverse_state(
        state_path,
        ReverseSyncState(
            version=1,
            tasks={
                "task:c3d4:cdef0123:3456789a": ReverseSyncTaskEntry(
                    last_seen_status="planned", last_seen_title="C", vault_path="plans/c.md"
                )
            },
        ),
    )
    adapter = FakeAdapter(
        rows=[{"ueid": "task:c3d4:cdef0123:3456789a", "name": "C", "status": "planned", "priority": 3}]
    )
    result = reverse_sync(state_path=state_path, adapter=adapter, review_queue_dir=tmp_queue)
    assert result.scanned == 1
    assert result.emitted == 0
    assert _read_queue_events(tmp_queue) == []


def test_reverse_sync_emits_update_for_new_ueid_with_vault_match(
    tmp_path: Path, tmp_queue: Path
) -> None:
    """UEID in taskdog not in snapshot -> emit UPDATE only if vault_path known.

    For Task 3 we keep it simple: if UEID is new (not in snapshot), skip
    (orphan, vault_path unknown). v1.3 will do vault lookup.
    """
    state_path = tmp_path / "state.json"
    from src.ikigai.src.ikigai.vault.sync import save_reverse_state
    save_reverse_state(state_path, ReverseSyncState(version=1))

    adapter = FakeAdapter(
        rows=[{"ueid": "task:new5678:def01234:456789ab", "name": "New", "status": "planned", "priority": 2}]
    )
    result = reverse_sync(state_path=state_path, adapter=adapter, review_queue_dir=tmp_queue)
    assert result.scanned == 1
    assert result.emitted == 0  # orphan — skipped


def test_reverse_sync_is_idempotent(tmp_path: Path, tmp_queue: Path) -> None:
    """Re-run with same input -> 0 events emitted the second time."""
    state_path = tmp_path / "state.json"
    from src.ikigai.src.ikigai.vault.sync import save_reverse_state
    save_reverse_state(
        state_path,
        ReverseSyncState(
            version=1,
            tasks={
                "task:d4e5:ef012345:56789abc": ReverseSyncTaskEntry(
                    last_seen_status="done", last_seen_title="D", vault_path="plans/d.md"
                )
            },
        ),
    )
    adapter = FakeAdapter(
        rows=[{"ueid": "task:d4e5:ef012345:56789abc", "name": "D", "status": "done", "priority": 1}]
    )
    # First run already in sync — no events
    result1 = reverse_sync(state_path=state_path, adapter=adapter, review_queue_dir=tmp_queue)
    assert result1.emitted == 0
    # Second run also in sync — no events
    result2 = reverse_sync(state_path=state_path, adapter=adapter, review_queue_dir=tmp_queue)
    assert result2.emitted == 0


def test_reverse_sync_updates_snapshot(tmp_path: Path, tmp_queue: Path) -> None:
    """After reverse_sync, snapshot reflects current taskdog state."""
    state_path = tmp_path / "state.json"
    from src.ikigai.src.ikigai.vault.sync import (
        load_reverse_state,
        save_reverse_state,
    )
    save_reverse_state(
        state_path,
        ReverseSyncState(
            version=1,
            tasks={
                "task:e5f6:f0123456:6789abcd": ReverseSyncTaskEntry(
                    last_seen_status="planned", last_seen_title="E", vault_path="plans/e.md"
                )
            },
        ),
    )
    adapter = FakeAdapter(
        rows=[{"ueid": "task:e5f6:f0123456:6789abcd", "name": "E (renamed)", "status": "in_progress", "priority": 2}]
    )
    reverse_sync(state_path=state_path, adapter=adapter, review_queue_dir=tmp_queue)
    state = load_reverse_state(state_path)
    entry = state.tasks["task:e5f6:f0123456:6789abcd"]
    assert entry.last_seen_status == "in_progress"
    assert entry.last_seen_title == "E (renamed)"
    assert state.last_sync_at is not None


def test_reverse_sync_per_task_isolation(tmp_path: Path, tmp_queue: Path) -> None:
    """One task throwing doesn't crash the loop — error recorded, others processed."""
    state_path = tmp_path / "state.json"
    from src.ikigai.src.ikigai.vault.sync import save_reverse_state
    save_reverse_state(
        state_path,
        ReverseSyncState(
            version=1,
            tasks={
                "task:good1:01234567:89abcdef0": ReverseSyncTaskEntry(
                    last_seen_status="planned", last_seen_title="Good", vault_path="plans/g.md"
                ),
                "task:bad2:89abcdef:abcdef01": ReverseSyncTaskEntry(
                    last_seen_status="planned", last_seen_title="Bad", vault_path="plans/bad.md"
                ),
            },
        ),
    )

    class PartialFailAdapter:
        def list_all(self) -> list[dict[str, Any]]:
            return [
                {"ueid": "task:good1:01234567:89abcdef0", "name": "Good", "status": "done", "priority": 1},
                {"ueid": "task:bad2:89abcdef:abcdef01", "name": "Bad", "status": "done", "priority": 1},
            ]

    # Patch queue.enqueue to throw on the second event
    real_enqueue = __import__("src.mesh.queue", fromlist=["enqueue"]).enqueue
    call_count = {"n": 0}

    def selective_enqueue(event):  # type: ignore[no-untyped-def]
        call_count["n"] += 1
        if event.ueid == "task:bad2:89abcdef:abcdef01":
            raise OSError("simulated failure")
        return real_enqueue(event)

    import src.mesh.queue as qmod
    monkeypatch_orig = qmod.enqueue
    qmod.enqueue = selective_enqueue  # type: ignore[assignment]
    try:
        adapter = PartialFailAdapter()
        result = reverse_sync(state_path=state_path, adapter=adapter, review_queue_dir=tmp_queue)
    finally:
        qmod.enqueue = monkeypatch_orig  # type: ignore[assignment]

    assert result.scanned == 2
    assert result.emitted == 1
    assert len(result.errors) == 1
    assert result.errors[0]["ueid"] == "task:bad2:89abcdef:abcdef01"


def test_reverse_sync_source_fork_override(tmp_path: Path, tmp_queue: Path) -> None:
    """source_fork kwarg populates emitted events' source_fork field."""
    state_path = tmp_path / "state.json"
    from src.ikigai.src.ikigai.vault.sync import save_reverse_state
    save_reverse_state(
        state_path,
        ReverseSyncState(
            version=1,
            tasks={
                "task:f6g7:abcdef01:bcdef012": ReverseSyncTaskEntry(
                    last_seen_status="planned", last_seen_title="F", vault_path="plans/f.md"
                )
            },
        ),
    )
    adapter = FakeAdapter(
        rows=[{"ueid": "task:f6g7:abcdef01:bcdef012", "name": "F", "status": "done", "priority": 1}]
    )
    reverse_sync(
        state_path=state_path,
        adapter=adapter,
        review_queue_dir=tmp_queue,
        source_fork="cli",  # override for testing
    )
    events = _read_queue_events(tmp_queue)
    assert events[0]["source_fork"] == "cli"
