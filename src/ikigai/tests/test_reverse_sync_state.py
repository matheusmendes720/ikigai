"""ReverseSyncState — taskdog-side snapshot store."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure repo root on sys.path for imports
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.ikigai.src.ikigai.vault.sync import (
    ReverseSyncState,
    ReverseSyncTaskEntry,
    load_reverse_state,
    save_reverse_state,
)


def test_load_reverse_state_empty_when_missing(tmp_path: Path) -> None:
    """Missing state file → empty ReverseSyncState."""
    state = load_reverse_state(tmp_path / "state.json")
    assert state.version == 1
    assert state.tasks == {}
    assert state.last_sync_at is None


def test_load_reverse_state_roundtrip(tmp_path: Path) -> None:
    """Save then load → identical content."""
    path = tmp_path / "state.json"
    state = ReverseSyncState(
        version=1,
        last_sync_at="2026-08-29T12:00:00+00:00",
        tasks={
            "ikigai:task:a:1": ReverseSyncTaskEntry(
                last_seen_status="planned",
                last_seen_title="Task A",
                taskdog_id=42,
                vault_path="plans/q3/a.md",
            ),
        },
    )
    save_reverse_state(path, state)
    loaded = load_reverse_state(path)
    assert loaded.last_sync_at == state.last_sync_at
    assert "ikigai:task:a:1" in loaded.tasks
    entry = loaded.tasks["ikigai:task:a:1"]
    assert entry.last_seen_status == "planned"
    assert entry.last_seen_title == "Task A"
    assert entry.taskdog_id == 42
    assert entry.vault_path == "plans/q3/a.md"


def test_save_reverse_state_atomic(tmp_path: Path) -> None:
    """Save uses .tmp + os.replace (no leftover .tmp on success)."""
    path = tmp_path / "state.json"
    save_reverse_state(path, ReverseSyncState(version=1))
    assert path.exists()
    assert not (tmp_path / "state.tmp").exists()


def test_save_reverse_state_overwrites_existing(tmp_path: Path) -> None:
    """Second save replaces first (Windows-safe)."""
    path = tmp_path / "state.json"
    save_reverse_state(path, ReverseSyncState(version=1, last_sync_at="first"))
    save_reverse_state(path, ReverseSyncState(version=1, last_sync_at="second"))
    loaded = load_reverse_state(path)
    assert loaded.last_sync_at == "second"


def test_reverse_sync_task_entry_frozen() -> None:
    """ReverseSyncTaskEntry is frozen — attribute assignment raises."""
    entry = ReverseSyncTaskEntry(
        last_seen_status="planned", last_seen_title="T", taskdog_id=1, vault_path="x.md"
    )
    with pytest.raises(Exception):  # ValidationError or AttributeError
        entry.last_seen_status = "done"  # type: ignore[misc]
