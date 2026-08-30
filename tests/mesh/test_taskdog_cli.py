"""Tests for the Taskdog adapter read-only CLI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

# src/ is added to sys.path by tests/mesh/conftest.py — no inline block needed.
from src.contracts.task_change import PropagationEvent, TaskAction
from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.taskdog_cli import main


@pytest.fixture
def taskdog_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a tmp taskdog SQLite schema and override the adapter's path."""
    db_path = tmp_path / "tasks.db"
    conn = __import__("sqlite3").connect(db_path)
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
        CREATE UNIQUE INDEX idx_tasks_ueid ON tasks(ueid);
    """)
    conn.commit()
    conn.close()
    monkeypatch.setattr(taskdog_mod, "TASKDOG_DB", db_path)
    return db_path


def _sample_event(
    ueid: str,
    title: str,
    due: str,
    priority: int = 2,
) -> PropagationEvent:
    return PropagationEvent(
        event_id=f"evt_{ueid[:6]}",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": title, "due": due, "priority": priority},
        approved_at=datetime(2026, 8, 30, 14, 30, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )


@pytest.fixture
def db_with_three_tasks(taskdog_db: Path) -> list[PropagationEvent]:
    """Pre-populated DB with 3 tasks spanning distinct statuses + deadlines."""
    events = [
        _sample_event(
            "tsk:build-wiremesh:11111111-1111-1111-1111-111111111111:1111111111111111",
            "Build wiremesh",
            "2026-09-15",
            priority=1,
        ),
        _sample_event(
            "tsk:review-papers:22222222-2222-2222-2222-222222222222:2222222222222222",
            "Review papers",
            "2026-09-20",
            priority=2,
        ),
        _sample_event(
            "tsk:run-standup:33333333-3333-3333-3333-333333333333:3333333333333333",
            "Run standup",
            "2026-09-10",
            priority=3,
        ),
    ]
    adapter = TaskdogAdapter()
    for ev in events:
        adapter.apply_change(ev)
    # Bump two rows to different statuses so the status filter has bite.
    import sqlite3

    conn = sqlite3.connect(taskdog_db)
    conn.execute(
        "UPDATE tasks SET status='in_progress' WHERE ueid=?",
        ("tsk:review-papers:22222222-2222-2222-2222-222222222222:2222222222222222",),
    )
    conn.execute(
        "UPDATE tasks SET status='done' WHERE ueid=?",
        ("tsk:run-standup:33333333-3333-3333-3333-333333333333:3333333333333333",),
    )
    conn.commit()
    conn.close()
    return events


# ──────────────────── list (JSON mode, capsys default) ────────────────────


def test_list_prints_all_newest_first(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list"])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(lines) == 3
    parsed = [json.loads(ln) for ln in lines]
    # created_at is identical (same fixture timestamp), but sort is stable —
    # verify the full set is present.
    ueids = {p["ueid"] for p in parsed}
    assert ueids == {ev.ueid for ev in db_with_three_tasks}


def test_list_filters_by_status(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--status", "done"])
    assert rc == 0
    parsed = [
        json.loads(ln)
        for ln in capsys.readouterr().out.strip().splitlines()
        if ln.strip()
    ]
    assert len(parsed) == 1
    assert parsed[0]["ueid"].startswith("tsk:run-standup:")
    assert parsed[0]["status"] == "done"


def test_list_respects_limit(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--limit", "2"])
    assert rc == 0
    parsed = [
        json.loads(ln)
        for ln in capsys.readouterr().out.strip().splitlines()
        if ln.strip()
    ]
    assert len(parsed) == 2


def test_list_with_empty_db_prints_nothing(
    taskdog_db: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main(["list"])
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_list_status_no_match_prints_nothing(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--status", "cancelled"])
    assert rc == 0
    assert capsys.readouterr().out == ""


# ──────────────────── show (JSON mode) ────────────────────


def test_show_returns_full_slice(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    target = "tsk:build-wiremesh:11111111-1111-1111-1111-111111111111:1111111111111111"
    rc = main(["show", target])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ueid"] == target
    assert parsed["name"] == "Build wiremesh"
    assert parsed["deadline"] == "2026-09-15"
    assert parsed["priority"] == 1


def test_show_returns_one_for_missing_ueid(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(
        ["show", "tsk:nope:00000000-0000-0000-0000-000000000000:0000000000000000"]
    )
    assert rc == 1
    assert "ueid not found" in capsys.readouterr().err


def test_show_on_missing_db_returns_one(
    taskdog_db: Path, capsys: pytest.CaptureFixture
) -> None:
    """If TASKDOG_DB has been deleted (or never created), `show` exits 1."""
    taskdog_db.unlink()
    rc = main(["show", "tsk:any:00000000-0000-0000-0000-000000000000:0000000000000000"])
    assert rc == 1


# ──────────────────── Human-readable mode ────────────────────


def test_human_flag_prints_table_not_json(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    # Header row
    assert "UEID" in lines[0]
    assert "NAME" in lines[0]
    assert "STATUS" in lines[0]
    assert "PRIORITY" in lines[0]
    assert "DEADLINE" in lines[0]
    # Body rows are NOT JSON
    for ln in lines[2:]:
        assert not ln.lstrip().startswith("{")


def test_json_flag_in_pipe_friendly_format(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--json"])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        parsed = json.loads(ln)
        assert "ueid" in parsed
        assert "name" in parsed


def test_default_mode_with_capsys_is_json(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    """Without --json/--human, capsys is non-TTY → JSON mode preserved."""
    rc = main(["list"])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    parsed = [json.loads(ln) for ln in lines]
    assert len(parsed) == 3


def test_human_list_shows_aligned_columns(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    # Separator line under the header
    lines = out.splitlines()
    assert any(set(ln) <= {"-", " "} and "-" in ln for ln in lines)


def test_human_list_with_empty_db_prints_header_only(
    taskdog_db: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main(["list", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    # Header row but no separator (empty rows -> headers only)
    assert len(lines) == 1
    assert "UEID" in lines[0]


def test_human_show_prints_key_value_summary(
    db_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    target = "tsk:build-wiremesh:11111111-1111-1111-1111-111111111111:1111111111111111"
    rc = main(["show", target, "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ueid:" in out
    assert "name:" in out
    assert "status:" in out
    assert "priority:" in out
    assert "deadline:" in out
    # Values present
    assert "Build wiremesh" in out
    assert "2026-09-15" in out


def test_mutually_exclusive_json_and_human() -> None:
    """argparse rejects --json + --human together (mutually_exclusive_group)."""
    with pytest.raises(SystemExit):
        main(["list", "--json", "--human"])


def test_main_without_command_exits_nonzero() -> None:
    """argparse must reject missing subcommand (required=True)."""
    with pytest.raises(SystemExit):
        main([])


# ──────────────────── --db-path override ────────────────────


def test_db_path_override_is_honored(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """--db-path should point at a different DB than the module default."""
    # Build a tiny DB with one row
    other = tmp_path / "other.db"
    conn = __import__("sqlite3").connect(other)
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
        "VALUES (?, ?, 'planned', 1, '2026-12-31', '2026-08-30T14:30:00+00:00')",
        (
            "tsk:other:00000000-0000-0000-0000-000000000000:0000000000000000",
            "Other task",
        ),
    )
    conn.commit()
    conn.close()

    rc = main(["list", "--db-path", str(other)])
    assert rc == 0
    parsed = [
        json.loads(ln)
        for ln in capsys.readouterr().out.strip().splitlines()
        if ln.strip()
    ]
    assert len(parsed) == 1
    assert parsed[0]["name"] == "Other task"


def test_show_with_db_path_override(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`show --db-path` should also honor the override."""
    other = tmp_path / "other.db"
    conn = __import__("sqlite3").connect(other)
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
        "VALUES (?, ?, 'planned', 1, '2026-12-31', '2026-08-30T14:30:00+00:00')",
        (
            "tsk:lookup:00000000-0000-0000-0000-000000000000:0000000000000000",
            "Lookup me",
        ),
    )
    conn.commit()
    conn.close()

    rc = main(
        [
            "show",
            "--db-path",
            str(other),
            "tsk:lookup:00000000-0000-0000-0000-000000000000:0000000000000000",
        ]
    )
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["name"] == "Lookup me"
