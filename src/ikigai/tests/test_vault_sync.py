"""Unit tests for vault-to-taskdog sync engine — Phase B6.3."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure repo root on sys.path for imports
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.ikigai.src.ikigai.vault.sync import (
    SyncAction,
    SyncActionKind,
    SyncState,
    SyncTaskEntry,
    TaskRecord,
    diff,
    load_state,
    parse_vault_tasks,
    push,
    run_sync,
    save_state,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create a minimal vault with task and non-task markdown files."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Task file — should be synced
    (vault / "task-foo.md").write_text(
        "---\n"
        "ueid: ikigai:task:foo:a1b2:c3d4\n"
        "title: Test task\n"
        'tags: [task]\n'
        "status: planned\n"
        "priority: high\n"
        "due: 2026-09-15\n"
        "---\n"
        "# Test task\n"
        "Body content.\n",
        encoding="utf-8",
    )

    # Non-task file — should be skipped
    (vault / "note-bar.md").write_text(
        "---\n"
        "ueid: ikigai:note:bar:e5f6\n"
        "title: Just a note\n"
        'tags: [note]\n'
        "status: active\n"
        "---\n"
        "# Note\n",
        encoding="utf-8",
    )

    # Task file using type: task discriminator
    (vault / "task-baz.md").write_text(
        "---\n"
        "ueid: ikigai:task:baz:g7h8\n"
        "title: Type-task test\n"
        "type: task\n"
        "status: in_progress\n"
        "---\n",
        encoding="utf-8",
    )

    # Task with no ueid — should be skipped
    (vault / "no-ueid.md").write_text(
        "---\n"
        "title: No UEID\n"
        'tags: [task]\n'
        "---\n",
        encoding="utf-8",
    )

    return vault


@pytest.fixture
def tmp_state_file(tmp_path: Path) -> Path:
    return tmp_path / "sync-state.json"


# ─────────────────────────────────────────────────────────────────────────────
# parse_vault_tasks
# ─────────────────────────────────────────────────────────────────────────────


def test_parse_vault_tasks_filters_non_tasks(tmp_vault: Path) -> None:
    """Only files with tags:[task] or type:task are returned."""
    tasks = parse_vault_tasks(tmp_vault)
    ueids = {t.ueid for t in tasks}
    assert "ikigai:note:bar:e5f6" not in ueids  # note is filtered
    assert "ikigai:task:foo:a1b2:c3d4" in ueids
    assert "ikigai:task:baz:g7h8" in ueids


def test_parse_vault_tasks_extracts_fields(tmp_vault: Path) -> None:
    """ueid, status, priority, due are all extracted correctly."""
    tasks = parse_vault_tasks(tmp_vault)
    by_ueid = {t.ueid: t for t in tasks}
    foo = by_ueid["ikigai:task:foo:a1b2:c3d4"]
    assert foo.title == "Test task"
    assert foo.status == "planned"
    assert foo.priority == "high"
    assert foo.due == "2026-09-15"


# ─────────────────────────────────────────────────────────────────────────────
# load_state / save_state
# ─────────────────────────────────────────────────────────────────────────────


def test_load_state_initializes_when_missing(tmp_path: Path) -> None:
    """Missing state file returns empty SyncState."""
    state = load_state(tmp_path / "nonexistent.json")
    assert state.version == 1
    assert state.tasks == {}
    assert state.last_sync_at is None


def test_save_state_atomic_rename(tmp_path: Path) -> None:
    """save_state writes .tmp then renames to final path."""
    state = SyncState(
        version=1,
        last_sync_at="2026-08-29T10:00:00Z",
        tasks={
            "ikigai:task:test:001": SyncTaskEntry(
                last_synced_at="2026-08-29T10:00:00Z",
                last_status="planned",
                vault_path="vault/test.md",
            )
        },
    )
    path = tmp_path / "state.json"
    save_state(path, state)

    assert path.exists()
    assert not path.with_suffix(".tmp").exists()

    loaded = load_state(path)
    assert loaded.version == 1
    assert "ikigai:task:test:001" in loaded.tasks


# ─────────────────────────────────────────────────────────────────────────────
# diff
# ─────────────────────────────────────────────────────────────────────────────


def test_diff_new_unchanged_changed() -> None:
    """NEW/UNCHANGED/CHANGED/CHANGED_TO_DONE are classified correctly."""
    record = TaskRecord(
        ueid="ikigai:task:foo:001",
        title="Foo",
        status="done",
        vault_path="vault/foo.md",
    )
    # NEW
    actions = diff([record], SyncState())
    assert len(actions) == 1
    assert actions[0].kind == SyncActionKind.NEW

    # UNCHANGED
    state = SyncState(
        tasks={
            "ikigai:task:foo:001": SyncTaskEntry(
                last_synced_at="2026-08-29T09:00:00Z",
                last_status="done",
                vault_path="vault/foo.md",
            )
        }
    )
    actions = diff([record], state)
    assert actions[0].kind == SyncActionKind.UNCHANGED

    # CHANGED_TO_DONE (was planned, now done)
    changed_record = TaskRecord(
        ueid="ikigai:task:foo:001",
        title="Foo",
        status="done",
        vault_path="vault/foo.md",
    )
    state_changed = SyncState(
        tasks={
            "ikigai:task:foo:001": SyncTaskEntry(
                last_synced_at="2026-08-29T09:00:00Z",
                last_status="planned",
                vault_path="vault/foo.md",
            )
        }
    )
    actions = diff([changed_record], state_changed)
    assert actions[0].kind == SyncActionKind.CHANGED_TO_DONE

    # CHANGED (status in_progress, not done)
    changed_inprog = TaskRecord(
        ueid="ikigai:task:foo:001",
        title="Foo",
        status="in_progress",
        vault_path="vault/foo.md",
    )
    actions = diff([changed_inprog], state_changed)
    assert actions[0].kind == SyncActionKind.CHANGED


# ─────────────────────────────────────────────────────────────────────────────
# push
# ─────────────────────────────────────────────────────────────────────────────


def test_push_per_task_isolation() -> None:
    """One task's failure does not abort the batch; errors are collected."""

    class _FailingAdapter:
        def call_tool(self, name: str, args: dict) -> dict:
            if "foo" in str(args.get("ueid", "")):
                raise RuntimeError("simulated MCP failure")
            return {"id": "td-99"}

    record_foo = TaskRecord(
        ueid="ikigai:task:foo:001",
        title="Foo",
        status="planned",
        vault_path="vault/foo.md",
    )
    record_bar = TaskRecord(
        ueid="ikigai:task:bar:002",
        title="Bar",
        status="planned",
        vault_path="vault/bar.md",
    )
    actions = [
        SyncAction(kind=SyncActionKind.NEW, record=record_foo),
        SyncAction(kind=SyncActionKind.NEW, record=record_bar),
    ]

    adapter = _FailingAdapter()
    updated, errors = push(actions, adapter)

    assert len(errors) == 1
    assert errors[0]["ueid"] == "ikigai:task:foo:001"
    assert "simulated MCP failure" in errors[0]["error"]
    # bar succeeded
    bar_action = next(a for a in updated if a.record.ueid == "ikigai:task:bar:002")
    assert bar_action.taskdog_id == "td-99"


# ─────────────────────────────────────────────────────────────────────────────
# run_sync (integration-level without real adapter)
# ─────────────────────────────────────────────────────────────────────────────


def test_run_sync_increments_state(tmp_vault: Path, tmp_state_file: Path) -> None:
    """run_sync updates state.json after successful push."""

    class _NoopAdapter:
        def call_tool(self, name: str, args: dict) -> dict:
            return {"id": f"td-{args['ueid'][-4:]}"}

    result = run_sync(
        vault_root=tmp_vault,
        state_path=tmp_state_file,
        adapter=_NoopAdapter(),
    )

    assert result.scanned == 2  # only task-tagged files
    assert result.added == 2
    assert result.skipped == 0
    assert result.errors == []

    state = load_state(tmp_state_file)
    assert len(state.tasks) == 2
    assert "ikigai:task:foo:a1b2:c3d4" in state.tasks
    assert "ikigai:task:baz:g7h8" in state.tasks
