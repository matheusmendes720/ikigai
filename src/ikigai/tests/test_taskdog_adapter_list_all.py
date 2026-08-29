"""TaskdogAdapter.list_all() — enumerate all taskdog rows."""
import sqlite3
from pathlib import Path

import pytest

from src.mesh.adapters.taskdog import TaskdogAdapter


@pytest.fixture
def taskdog_db(tmp_path: Path) -> Path:
    """Create a minimal taskdog SQLite with 3 tasks."""
    db_path = tmp_path / "tasks.db"
    conn = sqlite3.connect(db_path)
    try:
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
        for ueid, name, status, prio in [
            ("ikigai:task:a:1", "Task A", "planned", 1),
            ("ikigai:task:b:2", "Task B", "in_progress", 2),
            ("ikigai:task:c:3", "Task C", "done", 3),
        ]:
            conn.execute(
                "INSERT INTO tasks (ueid, name, status, priority, created_at) VALUES (?, ?, ?, ?, ?)",
                (ueid, name, status, prio, "2026-08-29T00:00:00"),
            )
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_list_all_returns_three_tasks(taskdog_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """list_all() should return one dict per row, 3 total."""
    monkeypatch.setattr("src.mesh.adapters.taskdog.TASKDOG_DB", taskdog_db)
    rows = TaskdogAdapter().list_all()
    assert len(rows) == 3
    assert all("ueid" in r for r in rows)
    assert all("status" in r for r in rows)


def test_list_all_returns_empty_when_db_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """list_all() on missing DB returns [] (not None, not exception)."""
    monkeypatch.setattr("src.mesh.adapters.taskdog.TASKDOG_DB", tmp_path / "nope.db")
    assert TaskdogAdapter().list_all() == []


def test_list_all_includes_ueid_status_title(taskdog_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each row must include ueid, status, name (title), priority."""
    monkeypatch.setattr("src.mesh.adapters.taskdog.TASKDOG_DB", taskdog_db)
    rows = TaskdogAdapter().list_all()
    by_ueid = {r["ueid"]: r for r in rows}
    assert by_ueid["ikigai:task:b:2"]["status"] == "in_progress"
    assert by_ueid["ikigai:task:b:2"]["name"] == "Task B"
    assert by_ueid["ikigai:task:c:3"]["status"] == "done"
