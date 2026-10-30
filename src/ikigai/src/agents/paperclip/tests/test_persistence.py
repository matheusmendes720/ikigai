"""Paperclip — RunRecord / persistence unit tests (M183-paperclip-state-persistence).

Five focused tests covering the structured-state-persistence contract:

* ``test_persist_run_creates_file`` — :func:`persist_run` writes the
  record to ``runs_dir`` and the file exists with valid JSON.
* ``test_persist_run_filename_format`` — filename follows the
  ``<ISO-TS>_<task_id>.json`` convention so lexical sort matches
  chronological order.
* ``test_persist_run_gc_when_over_limit`` — when ``runs_dir`` exceeds
  ``max_runs``, oldest entries are deleted.
* ``test_list_recent_runs_newest_first`` — :func:`list_recent_runs`
  returns paths in reverse-chronological order.
* ``test_load_run_roundtrip`` — :func:`load_run` reproduces every field
  of the original :class:`RunRecord`.

All tests use ``tmp_path`` so the real ``data/paperclip/runs/`` tree is
never touched.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.ikigai.src.agents.paperclip.persistence import (
    RunRecord,
    list_recent_runs,
    load_run,
    persist_run,
)


def _make_record(task_id: str = "test-task") -> RunRecord:
    """Helper — build a minimal valid RunRecord."""
    return RunRecord(
        task_id=task_id,
        started_at="2026-10-12T01:42:17Z",
        finished_at="2026-10-12T01:42:42Z",
        duration_s=25.0,
        adapter="pi",
        status="ok",
        gates_consulted=[
            {"gate": "CostGate", "allowed": True, "reason": "ok"},
            {"gate": "RiskGate", "allowed": True, "reason": "ok"},
        ],
        steps=[
            {"node": "read_spec", "ts": "2026-10-12T01:42:18Z", "keys": ["spec_text"]},
            {"node": "implement", "ts": "2026-10-12T01:42:25Z", "keys": ["tests_ok"]},
        ],
        final_state={"commit_sha": "abc123", "tests_ok": True},
    )


def test_persist_run_creates_file(tmp_path: Path) -> None:
    """``persist_run(record)`` writes a JSON file to ``runs_dir``.

    Asserts:
    * the file exists,
    * it parses as valid JSON,
    * the ``run_id`` matches the record's ``run_id``.
    """
    record = _make_record(task_id="m183-create")
    runs_dir = tmp_path / "runs"

    path = persist_run(record, runs_dir=runs_dir)

    assert path.exists(), f"persisted file missing at {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["run_id"] == record.run_id
    assert payload["task_id"] == "m183-create"
    assert payload["status"] == "ok"


def test_persist_run_filename_format(tmp_path: Path) -> None:
    """Filename matches ``<ISO-TS>_<task_id>.json`` (lexically sortable)."""
    record = _make_record(task_id="m183-filename")
    runs_dir = tmp_path / "runs"

    path = persist_run(record, runs_dir=runs_dir, now=datetime(2026, 10, 12, 1, 42, 17, tzinfo=UTC))

    name = path.name
    # ISO 8601 timestamp YYYY-MM-DDTHH-MM-SSZ + _ <task_id> + .json
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z_m183-filename\.json$"
    assert re.match(pattern, name), f"unexpected filename: {name}"


def test_persist_run_gc_when_over_limit(tmp_path: Path) -> None:
    """Writing more than ``max_runs`` records removes the oldest ones.

    Uses ``max_runs=5`` so the test runs fast. Writes 10 records spaced 1
    second apart, then asserts exactly 5 remain and the OLDEST 5 are gone.
    """
    runs_dir = tmp_path / "runs"
    base_ts = datetime(2026, 10, 12, 2, 0, 0, tzinfo=UTC)

    for i in range(10):
        rec = RunRecord(
            task_id=f"gc-{i:02d}",
            started_at=(base_ts + timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            status="ok",
            adapter="dry-run",
        )
        persist_run(rec, runs_dir=runs_dir, max_runs=5, now=base_ts + timedelta(seconds=i))

    remaining = sorted(runs_dir.glob("*.json"))
    assert len(remaining) == 5, f"expected 5 after GC, got {len(remaining)}"

    # Oldest 5 should be gone (gc-00 .. gc-04); newest 5 should remain (gc-05 .. gc-09)
    remaining_task_ids = {p.stem.split("_", 1)[1] for p in remaining}
    for i in range(5):
        assert f"gc-{i:02d}" not in remaining_task_ids, f"oldest gc-{i:02d} should be GC'd"
    for i in range(5, 10):
        assert f"gc-{i:02d}" in remaining_task_ids, f"newest gc-{i:02d} should remain"


def test_list_recent_runs_newest_first(tmp_path: Path) -> None:
    """``list_recent_runs`` returns paths in reverse-chronological order."""
    runs_dir = tmp_path / "runs"
    base_ts = datetime(2026, 10, 12, 3, 0, 0, tzinfo=UTC)

    for i in range(3):
        rec = RunRecord(
            task_id=f"order-{i}",
            started_at=(base_ts + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            status="ok",
            adapter="dry-run",
        )
        persist_run(rec, runs_dir=runs_dir, now=base_ts + timedelta(minutes=i))

    paths = list_recent_runs(runs_dir=runs_dir, limit=10)

    assert len(paths) == 3
    # Newest first: order-2, order-1, order-0
    assert "order-2" in paths[0].name
    assert "order-1" in paths[1].name
    assert "order-0" in paths[2].name


def test_load_run_roundtrip(tmp_path: Path) -> None:
    """Persist a record, then :func:`load_run` reproduces every field."""
    original = _make_record(task_id="m183-roundtrip")
    runs_dir = tmp_path / "runs"

    path = persist_run(original, runs_dir=runs_dir)
    loaded = load_run(path)

    assert loaded["run_id"] == original.run_id
    assert loaded["task_id"] == original.task_id
    assert loaded["started_at"] == original.started_at
    assert loaded["finished_at"] == original.finished_at
    assert loaded["duration_s"] == original.duration_s
    assert loaded["adapter"] == original.adapter
    assert loaded["status"] == original.status
    assert loaded["gates_consulted"] == original.gates_consulted
    assert loaded["steps"] == original.steps
    assert loaded["final_state"] == original.final_state
    assert loaded["error"] == original.error
