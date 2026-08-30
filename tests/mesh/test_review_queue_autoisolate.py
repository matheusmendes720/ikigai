"""Verify the autouse conftest fixture isolates src.mesh.queue.QUEUE_DIR.

These tests would FAIL if the conftest's _isolate_review_queue fixture
were removed (writes would go to data/review_queue/ on the real machine).
The point of the test is to FAIL LOUDLY when isolation regresses.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# src/ is added to sys.path by tests/mesh/conftest.py — no inline block needed.
from src.contracts.task_change import TaskAction, TaskChange
from src.mesh import queue as queue_mod
from src.mesh.queue import enqueue


def _sample_event(
    ueid: str = "tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
) -> TaskChange:
    from datetime import datetime, timezone

    return TaskChange(
        event_id="evt_autoisolate",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": "AutoIsolate"},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 30, 14, 30, tzinfo=timezone.utc),
    )


def test_autouse_routes_queue_writes_to_tmp(tmp_path: Path) -> None:
    """QUEUE_DIR set by autouse is NOT the real data/review_queue path.

    The autouse fixture overrides QUEUE_DIR to a tmp_path_factory.mktemp()
    value. The real data/review_queue lives under PROJECT_ROOT/data/, so
    asserting `not QUEUE_DIR.is_relative_to(PROJECT_ROOT / "data")` is the
    strongest check that isolation is in effect.

    NOTE: must read `queue_mod.QUEUE_DIR` (the live module attribute) rather
    than a local `from src.mesh.queue import QUEUE_DIR` binding — that local
    binding captures the original value at import time and would NOT reflect
    the monkeypatch.
    """
    # Project root (parent of src/) — the real QUEUE_DIR would land under
    # PROJECT_ROOT/data/review_queue. The autouse should send writes elsewhere.
    project_root = queue_mod.PROJECT_ROOT
    actual_qdir = queue_mod.QUEUE_DIR
    assert str(actual_qdir) != str(project_root / "data" / "review_queue")
    assert not str(actual_qdir).startswith(str(project_root / "data")), (
        f"Autouse isolation regressed — QUEUE_DIR points at {actual_qdir!s} "
        f"which is under the real project data dir."
    )


def test_autouse_enqueues_without_touching_real_dir(tmp_path: Path) -> None:
    """enqueue() under autouse lands in tmp, not in real data/review_queue."""
    project_root = queue_mod.PROJECT_ROOT
    real_queue = project_root / "data" / "review_queue"

    # Snapshot real queue contents BEFORE the test runs — should be untouched.
    before = sorted(real_queue.glob("*.json")) if real_queue.exists() else []

    event = _sample_event()
    enqueue(event)

    # The autouse dir has the new file.
    assert any(queue_mod.QUEUE_DIR.glob("*.json"))
    # The real dir was NOT touched.
    after = sorted(real_queue.glob("*.json")) if real_queue.exists() else []
    assert before == after, (
        f"Real data/review_queue was modified! Before={before} After={after}"
    )


def test_explicit_queue_dir_fixture_still_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests that explicitly set QUEUE_DIR via monkeypatch still override autouse."""
    explicit_qdir = tmp_path / "explicit_review_queue"
    monkeypatch.setattr(queue_mod, "QUEUE_DIR", explicit_qdir)

    event = _sample_event(ueid="tsk:test:11111111-1111-1111-1111-111111111111:1111111111111111")
    enqueue(event)

    # Explicit dir has the new file.
    files = sorted(explicit_qdir.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text())
    assert payload["ueid"].endswith(":1111111111111111")
