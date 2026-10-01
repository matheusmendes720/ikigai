"""Tests for the M164 td dep subsystem (src/mesh/td_dep.py + adapter functions).

Covers:
- add / remove / list / blocked (operator surface)
- cycle detection (A → B → C → A rejected)
- self-loop (A → A rejected)
- blocked list correctly identifies tasks with unmet deps
- audit_log entries are written for add + remove

Run:
    pytest tests/mesh/test_td_dep.py -q
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import PropagationEvent, TaskAction
from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.dep_subsystem import (
    CycleDetected,
    SelfLoopError,
    add_dep,
    detect_cycle,
    get_deps,
    list_blocked,
    remove_dep,
)
from src.mesh.td_dep import main as dep_main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# Two parallel import paths exist (src.X vs X) due to sys.path setup in
# tests/conftest.py. Tests must patch BOTH identities to redirect the
# adapter's TASKDOG_DB. (See CLAUDE.md "dual-module identity bug class".)


@pytest.fixture
def taskdog_db(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Create a tmp taskdog SQLite schema and override the adapter's path.

    Mirrors the pattern in tests/mesh/test_taskdog_cli.py — patches both
    `src.mesh.adapters.taskdog` and `mesh.adapters.taskdog` so all code
    paths (adapter functions + td_dep main) hit the isolated DB.
    """
    db_path = tmp_path / "tasks.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ueid TEXT UNIQUE,
            name TEXT,
            status TEXT,
            priority INTEGER,
            planned_start TEXT,
            planned_end TEXT,
            deadline TEXT,
            created_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            tags TEXT,
            deps TEXT,
            audit_log TEXT,
            priority_label TEXT
        );
        CREATE UNIQUE INDEX idx_tasks_ueid ON tasks(ueid);
    """)
    conn.commit()
    conn.close()

    # Patch both module identities.
    original_src = taskdog_mod.TASKDOG_DB
    taskdog_mod.TASKDOG_DB = db_path

    try:
        from mesh.adapters import taskdog as taskdog_mod_for_main
        original_main = taskdog_mod_for_main.TASKDOG_DB
        taskdog_mod_for_main.TASKDOG_DB = db_path
    except ImportError:
        original_main = None

    def _restore() -> None:
        taskdog_mod.TASKDOG_DB = original_src
        if original_main is not None:
            from mesh.adapters import taskdog as taskdog_mod_for_main2
            taskdog_mod_for_main2.TASKDOG_DB = original_main

    request.addfinalizer(_restore)
    return db_path


def _make_event(
    ueid: str,
    title: str,
    status: str = "planned",
    due: str = "2099-01-01",
) -> PropagationEvent:
    return PropagationEvent(
        event_id=f"evt_{ueid[:6]}",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": title, "due": due, "status": status},
        approved_at=datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )


@pytest.fixture
def db_with_three_tasks(taskdog_db: Path) -> list[str]:
    """Pre-populated DB with 3 tasks (A, B, C) for dep-edge tests."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    ueids = [
        "tsk:task-a:11111111-1111-1111-1111-111111111111:1111111111111111",
        "tsk:task-b:22222222-2222-2222-2222-222222222222:2222222222222222",
        "tsk:task-c:33333333-3333-3333-3333-333333333333:3333333333333333",
    ]
    adapter = TaskdogAdapter()
    for ueid in ueids:
        adapter.apply_change(_make_event(ueid, f"Task {ueid[4:9]}"))
    return ueids


# ---------------------------------------------------------------------------
# Direct adapter-level tests (cycle detection + CRUD)
# ---------------------------------------------------------------------------


def test_add_dep_basic(taskdog_db: Path, db_with_three_tasks: list[str]) -> None:
    """add_dep writes the target UEID into the deps JSON array."""
    a, b, _c = db_with_three_tasks
    add_dep(a, b)
    result = get_deps(a)
    assert b in result["blocked_by"]


def test_add_dep_idempotent(taskdog_db: Path, db_with_three_tasks: list[str]) -> None:
    """Adding the same edge twice leaves the dep list with one copy."""
    a, b, _c = db_with_three_tasks
    add_dep(a, b)
    add_dep(a, b)  # idempotent
    result = get_deps(a)
    assert result["blocked_by"].count(b) == 1


def test_remove_dep_basic(taskdog_db: Path, db_with_three_tasks: list[str]) -> None:
    """remove_dep returns True and clears the edge."""
    a, b, _c = db_with_three_tasks
    add_dep(a, b)
    assert remove_dep(a, b) is True
    assert get_deps(a)["blocked_by"] == []


def test_remove_dep_absent(taskdog_db: Path, db_with_three_tasks: list[str]) -> None:
    """remove_dep returns False when the edge doesn't exist."""
    a, b, _c = db_with_three_tasks
    assert remove_dep(a, b) is False


def test_self_loop_rejected(taskdog_db: Path, db_with_three_tasks: list[str]) -> None:
    """A blocked-by A raises SelfLoopError."""
    a, _b, _c = db_with_three_tasks
    with pytest.raises(SelfLoopError):
        add_dep(a, a)


def test_cycle_a_b_c_a_rejected(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """Cycle A → B → C → A is rejected."""
    a, b, c = db_with_three_tasks
    add_dep(a, b)
    add_dep(b, c)
    with pytest.raises(CycleDetected) as excinfo:
        add_dep(c, a)
    # Path must include the cycle nodes in order.
    path = excinfo.value.path
    assert path[0] == path[-1] == a
    assert b in path
    assert c in path


def test_cycle_detection_via_direct_call(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """detect_cycle returns the cycle path list (without raising)."""
    a, b, c = db_with_three_tasks
    add_dep(a, b)
    add_dep(b, c)
    cycle = detect_cycle(c, a)
    assert cycle is not None
    assert cycle[0] == a
    assert cycle[-1] == a
    assert c in cycle


def test_detect_cycle_no_cycle_returns_none(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """detect_cycle returns None when no cycle would be created."""
    a, b, c = db_with_three_tasks
    add_dep(a, b)
    cycle = detect_cycle(c, b)
    assert cycle is None


def test_detect_cycle_self_loop_returns_cycle(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """detect_cycle on (X, X) returns [X, X] before any DB lookup."""
    a, _b, _c = db_with_three_tasks
    cycle = detect_cycle(a, a)
    assert cycle == [a, a]


def test_add_dep_invalid_ueid_rejected(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """add_dep with a malformed UEID raises ValueError."""
    a, _b, _c = db_with_three_tasks
    with pytest.raises(ValueError):
        add_dep(a, "not-a-ueid")


def test_get_deps_blocks_field(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """get_deps returns both directions: blocked_by + blocks."""
    a, b, c = db_with_three_tasks
    add_dep(a, b)  # a blocked-by b -> a's blocked_by=[b]
    add_dep(b, c)  # b blocked-by c -> b's blocked_by=[c]
    # From B's perspective: blocked_by = [c], blocks = [a].
    result_b = get_deps(b)
    assert c in result_b["blocked_by"]
    assert a in result_b["blocks"]


# ---------------------------------------------------------------------------
# blocked-list tests
# ---------------------------------------------------------------------------


def test_blocked_detects_unmet_dep(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """list_blocked returns tasks whose deps are not done/cancelled."""
    a, b, _c = db_with_three_tasks
    add_dep(a, b)
    blocked = list_blocked()
    ueids = [r["ueid"] for r in blocked]
    assert a in ueids
    # B has no deps so it should not be in the blocked list.
    assert b not in ueids


def test_blocked_excludes_done_dep(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """A task whose only dep is `done` is no longer blocked."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    a, b, _c = db_with_three_tasks
    add_dep(a, b)
    # Mark B as done.
    done_event = PropagationEvent(
        event_id="evt_done",
        ueid=b,
        action=TaskAction.DONE,
        fields={},
        approved_at=datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )
    TaskdogAdapter().apply_change(done_event)
    blocked = list_blocked()
    ueids = [r["ueid"] for r in blocked]
    assert a not in ueids


def test_blocked_excludes_done_task(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """A task in `done` status is never reported as blocked."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    a, b, _c = db_with_three_tasks
    add_dep(a, b)
    # Mark A as done.
    done_event = PropagationEvent(
        event_id="evt_done_a",
        ueid=a,
        action=TaskAction.DONE,
        fields={},
        approved_at=datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )
    TaskdogAdapter().apply_change(done_event)
    blocked = list_blocked()
    ueids = [r["ueid"] for r in blocked]
    assert a not in ueids


def test_blocked_includes_unmet_deps_list(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """blocked rows carry `unmet_deps` so the operator knows what's blocking."""
    a, b, c = db_with_three_tasks
    add_dep(a, b)
    add_dep(a, c)
    blocked = list_blocked()
    a_row = next(r for r in blocked if r["ueid"] == a)
    assert b in a_row["unmet_deps"]
    assert c in a_row["unmet_deps"]


# ---------------------------------------------------------------------------
# Audit log tests
# ---------------------------------------------------------------------------


def test_audit_log_written_on_add(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """add_dep appends one entry to .dep_audit.log."""
    a, b, _c = db_with_three_tasks
    add_dep(a, b)
    log_path = taskdog_db.parent / ".dep_audit.log"
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    last = lines[-1]
    # Format: ISO8601|ueid|action|json_details
    parts = last.split("|", 3)
    assert len(parts) == 4
    assert parts[1] == a
    assert parts[2] == "add_dep"
    detail = json.loads(parts[3])
    assert detail["target"] == b


def test_audit_log_written_on_remove(
    taskdog_db: Path, db_with_three_tasks: list[str]
) -> None:
    """remove_dep appends one entry to .dep_audit.log."""
    a, b, _c = db_with_three_tasks
    add_dep(a, b)
    remove_dep(a, b)
    log_path = taskdog_db.parent / ".dep_audit.log"
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    # 2 entries: add + remove
    assert len(lines) == 2
    last = lines[-1]
    parts = last.split("|", 3)
    assert parts[2] == "remove_dep"


# ---------------------------------------------------------------------------
# CLI surface tests (td dep main)
# ---------------------------------------------------------------------------


def test_cli_add_bumps_json(
    taskdog_db: Path, db_with_three_tasks: list[str], capsys
) -> None:
    """td dep add emits a JSON `ok` line and exits 0."""
    a, b, _c = db_with_three_tasks
    rc = dep_main(["add", a, b, "--json"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["action"] == "add_dep"
    assert payload["ueid"] == a
    assert payload["target"] == b


def test_cli_add_cycle_rejected(
    taskdog_db: Path, db_with_three_tasks: list[str], capsys
) -> None:
    """td dep add emits cycle_detected JSON and exits non-zero."""
    a, b, c = db_with_three_tasks
    dep_main(["add", a, b, "--json"])
    capsys.readouterr()  # discard
    dep_main(["add", b, c, "--json"])
    capsys.readouterr()  # discard
    rc = dep_main(["add", c, a, "--json"])
    assert rc == 2
    err = capsys.readouterr().err.strip()
    payload = json.loads(err)
    assert payload["error"] == "cycle_detected"
    assert a in payload["path"]
    assert b in payload["path"]
    assert c in payload["path"]


def test_cli_remove_idempotent(
    taskdog_db: Path, db_with_three_tasks: list[str], capsys
) -> None:
    """td dep remove of an absent edge returns removed=False."""
    a, b, _c = db_with_three_tasks
    rc = dep_main(["remove", a, b, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["removed"] is False


def test_cli_list_blocked_by_and_blocks(
    taskdog_db: Path, db_with_three_tasks: list[str], capsys
) -> None:
    """td dep list emits both blocked_by and blocks as JSON arrays."""
    a, b, c = db_with_three_tasks
    dep_main(["add", a, b, "--json"])
    capsys.readouterr()  # discard
    dep_main(["add", b, c, "--json"])
    capsys.readouterr()  # discard
    rc = dep_main(["list", b, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ueid"] == b
    assert c in payload["blocked_by"]
    assert a in payload["blocks"]


def test_cli_blocked_emits_count_and_rows(
    taskdog_db: Path, db_with_three_tasks: list[str], capsys
) -> None:
    """td dep blocked emits a JSON object with `count` and `blocked` array."""
    a, b, _c = db_with_three_tasks
    dep_main(["add", a, b, "--json"])
    capsys.readouterr()  # discard
    rc = dep_main(["blocked", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert "blocked" in payload
    assert "count" in payload
    assert payload["count"] == len(payload["blocked"])
    ueids = [r["ueid"] for r in payload["blocked"]]
    assert a in ueids


def test_cli_self_loop_rejected(
    taskdog_db: Path, db_with_three_tasks: list[str], capsys
) -> None:
    """td dep add <same> <same> exits 2 with self_loop error JSON."""
    a, _b, _c = db_with_three_tasks
    rc = dep_main(["add", a, a, "--json"])
    assert rc == 2
    err = capsys.readouterr().err.strip()
    payload = json.loads(err)
    assert payload["error"] == "self_loop"


def test_cli_invalid_ueid_rejected(
    taskdog_db: Path, db_with_three_tasks: list[str], capsys
) -> None:
    """td dep add with malformed UEID exits 2 via argparse ArgumentTypeError."""
    a, _b, _c = db_with_three_tasks
    with pytest.raises(SystemExit) as excinfo:
        dep_main(["add", a, "not-a-ueid", "--json"])
    assert excinfo.value.code == 2


def test_cli_human_output_for_list(
    taskdog_db: Path, db_with_three_tasks: list[str], capsys
) -> None:
    """td dep list --human prints key:value lines."""
    a, b, _c = db_with_three_tasks
    dep_main(["add", a, b, "--json"])
    rc = dep_main(["list", a, "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert f"ueid: {a}" in out
    assert "blocked_by:" in out
    assert b in out