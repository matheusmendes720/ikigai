"""Tests for tuiboard snapshot persistence (JSON files)."""
from __future__ import annotations

from pathlib import Path

import pytest
from src.tuiboard.snapshots import SnapshotStore


def test_save_and_load_round_trip(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    tasks = [{"ueid": "sc:task:a:0:0", "title": "A", "status": "scheduled"}]
    out = store.save(name="baseline", tasks=tasks)
    assert out["task_count"] == 1
    loaded = store.load(out["snapshot_id"])
    assert loaded["tasks"] == tasks


def test_save_is_idempotent_on_same_name(tmp_path: Path):
    """Per spec: idempotent on (name, filters) — same name returns same id."""
    store = SnapshotStore(tmp_path / "snapshots")
    tasks = [{"ueid": "sc:task:a:0:0", "title": "A"}]
    out1 = store.save(name="baseline", tasks=tasks)
    out2 = store.save(name="baseline", tasks=tasks)
    assert out1["snapshot_id"] == out2["snapshot_id"]


def test_list_snapshots(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    store.save(name="a", tasks=[])
    store.save(name="b", tasks=[])
    snapshots = store.list_all()
    assert {s["name"] for s in snapshots} == {"a", "b"}


def test_load_missing_raises(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    with pytest.raises(FileNotFoundError):
        store.load("nonexistent-id")
