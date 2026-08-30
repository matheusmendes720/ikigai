"""Tests for tuiboard aggregator — multi-fork task read with dedup."""

from __future__ import annotations
from pathlib import Path

from src.tuiboard.aggregator import TaskAggregator


def test_aggregator_empty_when_no_forks(tmp_path: Path):
    """No tasks.jsonl -> empty list."""
    agg = TaskAggregator(data_dir=tmp_path)
    tasks = agg.aggregate()
    assert tasks == []


def test_aggregator_reads_cli_adapter(tmp_path: Path):
    """Write a tasks.jsonl entry -> aggregator returns it with source='cli'."""
    data_dir = tmp_path
    (data_dir / "data").mkdir(parents=True, exist_ok=True)
    # UEID matches regex: prefix=sc, slug=task, hex=a, hex=0 — both single chars
    (data_dir / "data" / "tasks.jsonl").write_text(
        '{"ueid": "sc:task:a:0:0", "title": "A", "status": "planned"}\n',
        encoding="utf-8",
    )
    agg = TaskAggregator(data_dir=data_dir)
    tasks = agg.aggregate()
    assert len(tasks) == 1
    assert tasks[0].ueid == "sc:task:a:0:0"
    assert tasks[0].title == "A"
    assert tasks[0].status == "planned"
    assert tasks[0].source == "cli"


def test_aggregator_reads_taskdog_adapter(tmp_path: Path, monkeypatch):
    """TaskdogAdapter rows → AggregatedTask with source='taskdog'.

    Monkeypatches TASKDOG_DB (module-level path) to a tmp SQLite file the
    aggregator can read. Then writes 1 row directly via sqlite3 to verify
    the end-to-end path: adapter.list_all() → AggregatedTask.
    """
    import sqlite3
    from src.mesh.adapters import taskdog as td_module

    # Override the module-level DB path BEFORE the adapter is constructed
    test_db = tmp_path / "tasks.db"
    monkeypatch.setattr(td_module, "TASKDOG_DB", test_db)

    # Seed a minimal taskdog row directly via SQL
    conn = sqlite3.connect(test_db)
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
        conn.execute(
            "INSERT INTO tasks (ueid, name, status, priority, deadline, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("td:task:11111111-1111-1111-1111-111111111111:aaa", "Taskdog Task",
             "planned", 2, "2026-09-15", "2026-09-01T00:00:00"),
        )
        conn.commit()
    finally:
        conn.close()

    # Aggregator uses real project root for data_dir, but in this test
    # only taskdog matters — cli reader will see no tasks.jsonl.
    agg = TaskAggregator(data_dir=tmp_path)
    tasks = agg.aggregate()

    # Only the taskdog row should be present
    taskdog_tasks = [t for t in tasks if t.source == "taskdog"]
    assert len(taskdog_tasks) == 1
    assert taskdog_tasks[0].ueid == "td:task:11111111-1111-1111-1111-111111111111:aaa"
    assert taskdog_tasks[0].title == "Taskdog Task"
    assert taskdog_tasks[0].status == "planned"
    assert taskdog_tasks[0].due == "2026-09-15"  # deadline date-only


def test_aggregator_3fork_precedence_taskdog_over_cli(tmp_path: Path, monkeypatch):
    """When the same ueid is in BOTH cli and taskdog, taskdog wins (higher precedence).

    Sets up cli fork with 1 row and taskdog fork with the same ueid + different title.
    Aggregator should return the taskdog slice.
    """
    import sqlite3
    from src.mesh.adapters import taskdog as td_module

    # Seed CLI adapter (jsonl)
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "tasks.jsonl").write_text(
        '{"ueid": "sc:task:11111111-1111-1111-1111-111111111111:bbb", '
        '"title": "CLI Version", "status": "planned"}\n',
        encoding="utf-8",
    )

    # Seed taskdog with same ueid, different title
    test_db = tmp_path / "tasks.db"
    monkeypatch.setattr(td_module, "TASKDOG_DB", test_db)
    conn = sqlite3.connect(test_db)
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
        conn.execute(
            "INSERT INTO tasks (ueid, name, status, priority, deadline, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("sc:task:11111111-1111-1111-1111-111111111111:bbb", "Taskdog Version",
             "in_progress", 1, "2026-09-20", "2026-09-01T00:00:00"),
        )
        conn.commit()
    finally:
        conn.close()

    agg = TaskAggregator(data_dir=tmp_path)
    tasks = agg.aggregate()

    # Exactly one row for that ueid, and it MUST be the taskdog slice
    matching = [t for t in tasks if t.ueid == "sc:task:11111111-1111-1111-1111-111111111111:bbb"]
    assert len(matching) == 1
    assert matching[0].source == "taskdog"  # higher precedence wins
    assert matching[0].title == "Taskdog Version"
    assert matching[0].status == "in_progress"
