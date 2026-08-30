"""Tests for the cross-fork mesh CLI (mesh_cli.show)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

# src/ is added to sys.path by tests/mesh/conftest.py — no inline block needed.
from src.contracts.task_change import PropagationEvent, TaskAction
from src.mesh.adapters import cli as cli_mod
from src.mesh.adapters import solverforge_calendar as calendar_mod
from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.adapters.cli import CliAdapter
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.mesh_cli import main


UEID_FULL = "tsk:build-wiremesh:11111111-1111-1111-1111-111111111111:1111111111111111"
UEID_CALENDAR_ONLY = (
    "tsk:calendar-only:22222222-2222-2222-2222-222222222222:2222222222222222"
)
UEID_MISSING = "tsk:nope:00000000-0000-0000-0000-000000000000:0000000000000000"


def _event(
    ueid: str,
    title: str,
    due: str,
    source_fork: str,
    priority: str = "medium",
) -> PropagationEvent:
    return PropagationEvent(
        event_id=f"evt_{ueid[:6]}",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": title, "due": due, "priority": priority},
        approved_at=datetime(2026, 8, 30, 14, 30, tzinfo=timezone.utc),
        source_fork=source_fork,
    )


# ──────────────────── Fixtures ────────────────────


@pytest.fixture
def cli_jsonl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Empty cli tasks.jsonl override."""
    tasks_file = tmp_path / "tasks.jsonl"
    tasks_file.write_text("")
    monkeypatch.setattr(cli_mod, "TASKS_JSONL", tasks_file)
    return tasks_file


@pytest.fixture
def taskdog_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Empty taskdog tasks.db override."""
    db_path = tmp_path / "taskdog.db"
    # Bootstrap empty schema so TaskdogAdapter.list_all() doesn't error.
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
            created_at TEXT
        );
    """)
    conn.commit()
    conn.close()
    monkeypatch.setattr(taskdog_mod, "TASKDOG_DB", db_path)
    return db_path


@pytest.fixture
def upi_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Empty UPI unified_planning.db override."""
    db_path = tmp_path / "upi.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE unified_planning_items (
            id TEXT PRIMARY KEY,
            ueid TEXT UNIQUE,
            status TEXT,
            start_at TEXT,
            end_at TEXT,
            blocked_by TEXT,
            tags TEXT,
            ikigai TEXT,
            provenance TEXT
        );
    """)
    conn.commit()
    conn.close()
    monkeypatch.setattr(calendar_mod, "UPI_DB", db_path)
    return db_path


@pytest.fixture
def all_three_present(
    cli_jsonl: Path,
    taskdog_db: Path,
    upi_db: Path,
) -> str:
    """Pre-populate every fork with the same UEID — exercises the join path."""
    ueid = UEID_FULL
    CliAdapter().apply_change(
        _event(ueid, "Build wiremesh", "2026-09-15", "interfaces/cli")
    )
    TaskdogAdapter().apply_change(
        _event(ueid, "Build wiremesh", "2026-09-15", "taskdog")
    )
    SolverforgeCalendarAdapter().apply_change(
        _event(ueid, "Build wiremesh", "2026-09-15", "solverforge_calendar")
    )
    return ueid


@pytest.fixture
def one_in_calendar_only(
    cli_jsonl: Path,
    taskdog_db: Path,
    upi_db: Path,
) -> str:
    """Only the calendar fork has this UEID — exercises partial-join path."""
    ueid = UEID_CALENDAR_ONLY
    SolverforgeCalendarAdapter().apply_change(
        _event(ueid, "Calendar-only task", "2026-12-01", "solverforge_calendar")
    )
    return ueid


# ──────────────────── show (JSON default) ────────────────────


def test_show_returns_joined_object_when_all_three_present(
    all_three_present: str,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["show", all_three_present])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ueid"] == all_three_present
    assert parsed["present_count"] == 3
    assert parsed["cli"] is not None
    assert parsed["cli"]["title"] == "Build wiremesh"
    assert parsed["taskdog"] is not None
    assert parsed["taskdog"]["name"] == "Build wiremesh"
    assert parsed["solverforge_calendar"] is not None
    assert parsed["solverforge_calendar"]["status"] == "planned"


def test_show_handles_partial_presence(
    one_in_calendar_only: str,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["show", one_in_calendar_only])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["present_count"] == 1
    assert parsed["cli"] is None
    assert parsed["taskdog"] is None
    assert parsed["solverforge_calendar"] is not None
    assert parsed["solverforge_calendar"]["ikigai"]["title"] == "Calendar-only task"


def test_show_returns_1_when_no_fork_has_ueid(
    cli_jsonl: Path,
    taskdog_db: Path,
    upi_db: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["show", UEID_MISSING])
    assert rc == 1
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["present_count"] == 0
    assert parsed["cli"] is None
    assert parsed["taskdog"] is None
    assert parsed["solverforge_calendar"] is None
    assert "not found in any fork" in captured.err


# ──────────────────── show --human ────────────────────


def test_show_human_renders_three_fork_sections(
    all_three_present: str,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["show", all_three_present, "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ueid:" in out
    assert "[fork: cli]" in out
    assert "[fork: taskdog]" in out
    assert "[fork: solverforge_calendar]" in out
    assert "present: yes" in out


def test_show_human_renders_not_present_for_missing_forks(
    one_in_calendar_only: str,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["show", one_in_calendar_only, "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[fork: cli]" in out
    assert "[fork: taskdog]" in out
    assert "[fork: solverforge_calendar]" in out
    # cli + taskdog sections show `present: no`
    assert out.count("present: no") == 2
    assert out.count("present: yes") == 1


def test_show_human_renders_empty_marker_for_blank_fields(
    cli_jsonl: Path,
    taskdog_db: Path,
    upi_db: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """Empty containers / None values render as `<empty>` so the operator
    can distinguish 'field present but blank' from 'field missing'."""
    # calendar fork has blocked_by=[] (empty list) and tags=[] (empty list)
    SolverforgeCalendarAdapter().apply_change(
        _event(UEID_FULL, "x", "2026-09-15", "solverforge_calendar")
    )
    rc = main(["show", UEID_FULL, "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "<empty>" in out


# ──────────────────── --json / --human flag override ────────────────────


def test_show_json_flag_in_pipe_friendly_format(
    all_three_present: str,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["show", all_three_present, "--json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ueid"] == all_three_present
    assert parsed["present_count"] == 3


def test_mutually_exclusive_json_and_human() -> None:
    """argparse rejects --json + --human together."""
    with pytest.raises(SystemExit):
        main(["show", UEID_FULL, "--json", "--human"])


def test_main_without_command_exits_nonzero() -> None:
    with pytest.raises(SystemExit):
        main([])


# ──────────────────── Per-fork --path / --db overrides ────────────────────


def test_show_cli_path_override(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """--cli-path must point at the operator's tasks.jsonl."""
    other = tmp_path / "other.jsonl"
    other.write_text(
        '{"ueid": "' + UEID_FULL + '", "title": "Other", '
        '"priority": "high", "due": "2026-12-31", '
        '"written_at": "2026-08-30T14:30:00+00:00", "source_fork": "interfaces/cli"}\n'
    )

    rc = main(["show", "--cli-path", str(other), UEID_FULL])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["cli"] is not None
    assert parsed["cli"]["title"] == "Other"
    # Other two adapters still use defaults (no data → None).
    assert parsed["taskdog"] is None
    assert parsed["solverforge_calendar"] is None


def test_show_taskdog_db_override(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """--taskdog-db must point at the operator's taskdog SQLite."""
    db_path = tmp_path / "taskdog.db"
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
            created_at TEXT
        );
    """)
    conn.execute(
        "INSERT INTO tasks (ueid, name, status, priority, deadline, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (UEID_FULL, "Overridden", "planned", 1, "2026-12-31", "2026-08-30T14:30:00"),
    )
    conn.commit()
    conn.close()

    rc = main(["show", "--taskdog-db", str(db_path), UEID_FULL])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["taskdog"] is not None
    assert parsed["taskdog"]["name"] == "Overridden"


def test_show_upi_db_override(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """--upi-db must point at the operator's solverforge_calendar UPI DB."""
    db_path = tmp_path / "upi.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE unified_planning_items (
            id TEXT PRIMARY KEY,
            ueid TEXT UNIQUE,
            status TEXT,
            start_at TEXT,
            end_at TEXT,
            blocked_by TEXT,
            tags TEXT,
            ikigai TEXT,
            provenance TEXT
        );
    """)
    import uuid as uuid_lib

    conn.execute(
        "INSERT INTO unified_planning_items (id, ueid, status, blocked_by, tags, ikigai) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            str(uuid_lib.uuid4()),
            UEID_FULL,
            "planned",
            "[]",
            "[]",
            json.dumps({"title": "Calendar overridden"}),
        ),
    )
    conn.commit()
    conn.close()

    rc = main(["show", "--upi-db", str(db_path), UEID_FULL])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["solverforge_calendar"] is not None
    assert parsed["solverforge_calendar"]["ikigai"]["title"] == "Calendar overridden"


# ──────────────────── Helper-level coverage ────────────────────


def test_wants_human_resolves_flag_conflicts() -> None:
    """Direct check of the output-mode resolver."""
    from src.mesh.mesh_cli import _wants_human
    import argparse

    base = argparse.Namespace(json=False, human=False)

    # --json wins
    args = argparse.Namespace(**{**vars(base), "json": True, "human": True})
    assert _wants_human(args) is False

    # --human wins when --json absent
    args = argparse.Namespace(**{**vars(base), "json": False, "human": True})
    assert _wants_human(args) is True

    # Neither → TTY default (capsys is non-TTY in pytest → False)
    args = argparse.Namespace(**{**vars(base), "json": False, "human": False})
    assert _wants_human(args) is False


def test_collect_slices_returns_none_for_missing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When every adapter's DB is missing, the join is all-None — no raises."""
    monkeypatch.setattr(cli_mod, "TASKS_JSONL", tmp_path / "absent.jsonl")
    monkeypatch.setattr(taskdog_mod, "TASKDOG_DB", tmp_path / "absent_taskdog.db")
    monkeypatch.setattr(calendar_mod, "UPI_DB", tmp_path / "absent_upi.db")

    from src.mesh.mesh_cli import _collect_slices

    slices = _collect_slices(UEID_MISSING)
    assert slices == {"cli": None, "taskdog": None, "solverforge_calendar": None}


def test_apply_overrides_no_op_when_path_unchanged() -> None:
    """Module-globals are mutated only when the override string differs."""
    from src.mesh.mesh_cli import (
        _apply_calendar_override,
        _apply_cli_override,
        _apply_taskdog_override,
    )

    cli_before = cli_mod.TASKS_JSONL
    taskdog_before = taskdog_mod.TASKDOG_DB
    calendar_before = calendar_mod.UPI_DB

    _apply_cli_override(str(cli_before))
    _apply_taskdog_override(str(taskdog_before))
    _apply_calendar_override(str(calendar_before))

    assert cli_mod.TASKS_JSONL is cli_before
    assert taskdog_mod.TASKDOG_DB is taskdog_before
    assert calendar_mod.UPI_DB is calendar_before
