import json
import threading
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


def _sample_event(
    ueid: str = "tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
) -> PropagationEvent:
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
    unknown_ueid: UEID = (
        "tsk:other:00000000-0000-0000-0000-000000000000:0000000000000000"
    )
    assert adapter.read(unknown_ueid) is None


def test_cli_adapter_supports_field():
    """CliAdapter supports title, due, priority fields."""
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()
    assert adapter.supports_field("title") is True
    assert adapter.supports_field("due") is True
    assert adapter.supports_field("priority") is True
    assert adapter.supports_field("start_at") is False


# ──────────────────── R1.1 — 14-field unified schema ────────────────────


def test_cli_adapter_writes_all_14_fields(tasks_jsonl: Path):
    """R1.1: CliAdapter must persist all 14 fields defined by the unified schema.

    The split-brain _write_tasks_to_data (sys_ikigai/vault/task_io.py) writes
    id, source, description, horizon, project_id, estimated_minutes, done,
    done_at, vector in addition to the 6 fields CliAdapter currently emits.
    After R1.1 CliAdapter must own the unified schema.
    """
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()
    event = PropagationEvent(
        event_id="evt_001",
        ueid="tsk:full:00000000-0000-0000-0000-000000000000:0000000000000001",
        action=TaskAction.CREATE,
        fields={
            "id": "abc12345",
            "title": "Full task",
            "description": "A full task description",
            "horizon": "today",
            "priority": "high",
            "project_id": "p1",
            "estimated_minutes": 30,
            "done": False,
            "done_at": None,
            "ueid": "tsk:full:00000000-0000-0000-0000-000000000000:0000000000000001",
            "vector": [0.1, 0.2],
            "due": "2099-01-01",
        },
        approved_at=datetime(2026, 9, 21, tzinfo=timezone.utc),
        source_fork="deep_agent",
    )
    adapter.apply_change(event)

    rec = json.loads(tasks_jsonl.read_text().strip())
    # All 14 fields must be persisted
    assert rec["id"] == "abc12345"
    assert rec["title"] == "Full task"
    assert rec["description"] == "A full task description"
    assert rec["horizon"] == "today"
    assert rec["priority"] == "high"
    assert rec["project_id"] == "p1"
    assert rec["estimated_minutes"] == 30
    assert rec["done"] is False
    assert rec["done_at"] is None
    assert rec["ueid"] == event.ueid
    assert rec["vector"] == [0.1, 0.2]
    assert rec["due"] == "2099-01-01"
    assert rec["written_at"] is not None
    assert rec["source_fork"] == "deep_agent"


def test_cli_adapter_supported_fields_includes_all_14():
    """R1.1: SUPPORTED_FIELDS must include all 14 unified-schema fields."""
    from src.mesh.adapters.cli import CliAdapter, SUPPORTED_FIELDS

    expected = {
        "id",
        "title",
        "description",
        "horizon",
        "priority",
        "project_id",
        "estimated_minutes",
        "done",
        "done_at",
        "ueid",
        "vector",
        "due",
        "written_at",
        "source_fork",
    }
    assert SUPPORTED_FIELDS == expected

    adapter = CliAdapter()
    for field in expected:
        assert adapter.supports_field(field), f"missing support for {field!r}"


# ──────────────────── R1.2 — cross-platform file lock ────────────────────


def test_cli_adapter_serializes_concurrent_writers(tasks_jsonl: Path):
    """R1.2: Two threads calling apply_change concurrently must not lose writes.

    Without fcntl.flock (POSIX) / msvcrt.locking (Windows), the read-existing
    step can race the temp-rename step, silently dropping records.
    """
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()
    barrier = threading.Barrier(5)
    errors: list[BaseException] = []

    def writer(i: int) -> None:
        try:
            event = PropagationEvent(
                event_id=f"evt_{i}",
                ueid=f"tsk:r{i}:00000000-0000-0000-0000-000000000000:000000000000000{i}",
                action=TaskAction.CREATE,
                fields={"title": f"task {i}", "priority": "medium"},
                approved_at=datetime(2026, 9, 21, tzinfo=timezone.utc),
                source_fork="interfaces/cli",
            )
            barrier.wait()
            adapter.apply_change(event)
        except BaseException as exc:  # noqa: BLE001 — capture for assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=writer, args=(i,), name=f"writer-{i}") for i in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"writers raised: {errors!r}"

    lines = [ln for ln in tasks_jsonl.read_text().splitlines() if ln.strip()]
    assert len(lines) == 5, (
        f"expected 5 records, got {len(lines)} — write race lost data"
    )
    ueids = {json.loads(ln)["ueid"] for ln in lines}
    assert len(ueids) == 5, "duplicate ueids imply read-existing lost a record"


def test_cli_adapter_serializes_with_existing_records(tasks_jsonl: Path):
    """R1.2: A concurrent writer that targets an existing ueid must noop safely
    while another writer appends a new record. Verifies the lock covers both
    the dedup-read and the temp-write windows.
    """
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()

    # Seed an existing record
    seed_ueid = "tsk:seed:00000000-0000-0000-0000-000000000000:00000000a1d00000"
    existing = PropagationEvent(
        event_id="evt_seed",
        ueid=seed_ueid,
        action=TaskAction.CREATE,
        fields={"title": "seed", "priority": "low"},
        approved_at=datetime(2026, 9, 21, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )
    adapter.apply_change(existing)
    assert len(tasks_jsonl.read_text().splitlines()) == 1

    barrier = threading.Barrier(3)
    errors: list[BaseException] = []

    def writer(i: int, ueid: str) -> None:
        try:
            event = PropagationEvent(
                event_id=f"evt_{i}",
                ueid=ueid,
                action=TaskAction.CREATE,
                fields={"title": f"task {i}", "priority": "medium"},
                approved_at=datetime(2026, 9, 21, tzinfo=timezone.utc),
                source_fork="interfaces/cli",
            )
            barrier.wait()
            adapter.apply_change(event)
        except BaseException as exc:  # noqa: BLE001 — capture for assertion
            errors.append(exc)

    threads = [
        threading.Thread(
            target=writer,
            args=(1, seed_ueid),
            name="dedup-writer",
        ),
        threading.Thread(
            target=writer,
            args=(
                2,
                "tsk:new2:00000000-0000-0000-0000-000000000000:00000000e2c00000",
            ),
            name="new-writer-2",
        ),
        threading.Thread(
            target=writer,
            args=(
                3,
                "tsk:new3:00000000-0000-0000-0000-000000000000:00000000d3f00000",
            ),
            name="new-writer-3",
        ),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"writers raised: {errors!r}"

    lines = [ln for ln in tasks_jsonl.read_text().splitlines() if ln.strip()]
    # Seed + 2 new (dedup-writer skipped because ueid matches seed)
    assert len(lines) == 3, f"expected 3 records (1 seed + 2 new), got {len(lines)}"


# ──────────────────── R1.1 delegation — _write_tasks_to_data ────────────────


def test_write_tasks_to_data_delegates_to_cli_adapter(
    tasks_jsonl: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R1.1: sys_ikigai.vault.task_io._write_tasks_to_data writes via CliAdapter.

    After the unification, the legacy open("a") writer is gone; every Deep
    Agent task must reach disk through the adapter so the unified 14-field
    schema and the cross-platform lock are exercised.
    """
    # Route the adapter at the tmp tasks file
    from src.mesh.adapters import cli as cli_mod

    monkeypatch.setattr(cli_mod, "TASKS_JSONL", tasks_jsonl)

    # Point _write_tasks_to_data at the same tmp path. The function uses
    # Path(__file__).parent.parent.parent.parent.parent to compute the path,
    # so we monkeypatch _tasks_path() instead.
    from sys_ikigai.vault import task_io

    monkeypatch.setattr(task_io, "_tasks_path", lambda: tasks_jsonl)

    result_str = task_io._write_tasks_to_data(
        [
            {
                "title": "Wiremesh",
                "description": "Build wiremesh",
                "horizon": "this_week",
                "priority": "high",
                "project_id": "p1",
                "estimated_minutes": 60,
                "ueid": "tsk:wiremesh:00000000-0000-0000-0000-000000000000:00000000a11ce000",
                "vector": [0.5, 0.5],
                "due": "2026-09-30",
            }
        ]
    )
    result = json.loads(result_str)
    assert result["ok"] is True
    assert result["written"] == 1

    lines = [ln for ln in tasks_jsonl.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])

    # Unified 14-field schema (subset that came from the caller)
    assert rec["title"] == "Wiremesh"
    assert rec["description"] == "Build wiremesh"
    assert rec["horizon"] == "this_week"
    assert rec["priority"] == "high"
    assert rec["project_id"] == "p1"
    assert rec["estimated_minutes"] == 60
    assert (
        rec["ueid"]
        == "tsk:wiremesh:00000000-0000-0000-0000-000000000000:00000000a11ce000"
    )
    assert rec["vector"] == [0.5, 0.5]
    assert rec["due"] == "2026-09-30"

    # Adapter-managed fields
    assert rec["source_fork"] == "deep_agent"
    assert rec["written_at"] is not None
    assert rec["done"] is False
    assert rec["done_at"] is None


def test_write_tasks_to_data_is_idempotent(
    tasks_jsonl: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R1.1: Calling _write_tasks_to_data twice with the same ueid must write once.

    CliAdapter's dedup logic kicks in via the unified path — same record
    reaches the same adapter.
    """
    from src.mesh.adapters import cli as cli_mod
    from sys_ikigai.vault import task_io

    monkeypatch.setattr(cli_mod, "TASKS_JSONL", tasks_jsonl)
    monkeypatch.setattr(task_io, "_tasks_path", lambda: tasks_jsonl)

    payload = {
        "title": "Same",
        "ueid": "tsk:same:00000000-0000-0000-0000-000000000000:00000000a11ce001",
    }
    task_io._write_tasks_to_data([payload])
    task_io._write_tasks_to_data([payload])

    lines = [ln for ln in tasks_jsonl.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected idempotent dedup (1 record), got {len(lines)}"
