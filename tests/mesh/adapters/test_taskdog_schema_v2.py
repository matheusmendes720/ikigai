"""M163 schema v2 migration tests.

Covers:
  1. Schema v2 has all 6 new columns with correct defaults.
  2. Migration script is idempotent (running twice succeeds).
  3. Migration creates a `.backup-v1` file.
  4. Default values on freshly-migrated rows are correct.
  5. Pydantic TaskdogSlice model parses all 14 fields.

All tests use ``tmp_path`` + ``monkeypatch`` to isolate from the
real ``data/taskdog/tasks.db``.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
MIGRATION_SCRIPT = SCRIPTS_DIR / "migrate_taskdog_schema_v2.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def v1_db(tmp_path: Path, monkeypatch) -> Path:
    """Create a v1-schema taskdog DB (8 columns) in tmp.

    Mirrors the original schema exactly: id, ueid, name, status,
    priority, planned_start, planned_end, deadline, created_at.
    """
    db_path = tmp_path / "v1_tasks.db"
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
        CREATE UNIQUE INDEX idx_tasks_ueid ON tasks(ueid);
    """)
    conn.execute(
        "INSERT INTO tasks (ueid, name, status, priority, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            "tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
            "Pre-existing v1 row",
            "planned",
            2,
            "2026-09-01T12:00:00",
        ),
    )
    conn.commit()
    conn.close()

    # Patch the adapter so any TaskdogAdapter calls hit our tmp DB.
    from src.mesh.adapters import taskdog as taskdog_module
    monkeypatch.setattr(taskdog_module, "TASKDOG_DB", db_path)
    return db_path


# ---------------------------------------------------------------------------
# 1. Schema v2 has all 6 new columns
# ---------------------------------------------------------------------------

def test_schema_v2_has_all_six_columns(v1_db: Path) -> None:
    """After running the migration, all 6 new columns exist with
    the expected types, defaults, and nullability.
    """
    # Trigger lazy migration via the adapter.
    from src.mesh.adapters.taskdog import TaskdogAdapter

    adapter = TaskdogAdapter()
    # Force table creation + migration by calling list_all (no-op read).
    adapter.list_all()

    conn = sqlite3.connect(v1_db)
    cur = conn.execute("PRAGMA table_info(tasks)")
    cols = {row[1]: row for row in cur.fetchall()}
    conn.close()

    # Check all 6 new columns exist.
    expected = {
        "tags":           ("TEXT", 1, "'[]'"),
        "deps":           ("TEXT", 1, "'[]'"),
        "audit_log":      ("TEXT", 1, "'[]'"),
        "started_at":     ("TEXT", 0, None),
        "completed_at":   ("TEXT", 0, None),
        "priority_label": ("TEXT", 1, "'P2'"),
    }
    for col, (exp_type, exp_notnull, exp_default) in expected.items():
        assert col in cols, f"missing column: {col}"
        row = cols[col]
        assert row[2].upper() == exp_type, (
            f"{col}: expected type {exp_type}, got {row[2]}"
        )
        assert bool(row[3]) == bool(exp_notnull), (
            f"{col}: notnull mismatch (got {row[3]}, want {exp_notnull})"
        )
        # Default value comparison — strip quotes if present.
        actual_default = row[4]
        if exp_default:
            assert actual_default == exp_default, (
                f"{col}: default mismatch (got {actual_default!r}, "
                f"want {exp_default!r})"
            )


# ---------------------------------------------------------------------------
# 2. Migration script is idempotent
# ---------------------------------------------------------------------------

def test_migration_script_is_idempotent(v1_db: Path) -> None:
    """Running the migration script twice in a row succeeds."""
    # First run — adds 6 columns.
    result1 = subprocess.run(
        [sys.executable, str(MIGRATION_SCRIPT), "--db", str(v1_db)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result1.returncode == 0, (
        f"first run failed:\nSTDOUT: {result1.stdout}\n"
        f"STDERR: {result1.stderr}"
    )

    # Second run — should succeed (idempotent — no-op on already-migrated DB).
    result2 = subprocess.run(
        [sys.executable, str(MIGRATION_SCRIPT), "--db", str(v1_db)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result2.returncode == 0, (
        f"second run failed:\nSTDOUT: {result2.stdout}\n"
        f"STDERR: {result2.stderr}"
    )

    # Verify all 14 columns exist after both runs.
    conn = sqlite3.connect(v1_db)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    conn.close()

    expected_cols = {
        "id", "ueid", "name", "status", "priority",
        "planned_start", "planned_end", "deadline", "created_at",
        "tags", "deps", "audit_log",
        "started_at", "completed_at", "priority_label",
    }
    missing = expected_cols - set(cols)
    assert not missing, f"missing columns after migration: {missing}"


# ---------------------------------------------------------------------------
# 3. Migration creates backup file
# ---------------------------------------------------------------------------

def test_migration_creates_backup(v1_db: Path) -> None:
    """After running the migration, `<db>.backup-v1` exists on disk."""
    backup_path = Path(str(v1_db) + ".backup-v1")

    assert not backup_path.exists(), (
        f"backup should not exist before migration: {backup_path}"
    )

    result = subprocess.run(
        [sys.executable, str(MIGRATION_SCRIPT), "--db", str(v1_db)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"migration failed:\nSTDOUT: {result.stdout}\n"
        f"STDERR: {result.stderr}"
    )

    assert backup_path.exists(), (
        f"backup file not created at {backup_path}"
    )
    assert backup_path.stat().st_size > 0, "backup file is empty"


# ---------------------------------------------------------------------------
# 4. Default values are correct on freshly-migrated rows
# ---------------------------------------------------------------------------

def test_default_values_correct(v1_db: Path) -> None:
    """After migration, INSERT a row without specifying the 6 new columns
    and verify the defaults are applied.
    """
    # Run migration first.
    subprocess.run(
        [sys.executable, str(MIGRATION_SCRIPT), "--db", str(v1_db)],
        capture_output=True, text=True, timeout=30, check=True,
    )

    # Insert a new row without specifying the new columns.
    new_ueid = "tsk:new:00000000-0000-0000-0000-000000000000:0000000000000000"
    conn = sqlite3.connect(v1_db)
    conn.execute(
        "INSERT INTO tasks (ueid, name, status, priority, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (new_ueid, "Brand new task", "planned", 2, "2026-10-01T00:00:00"),
    )
    conn.commit()

    # Fetch the new row.
    row = conn.execute(
        "SELECT tags, deps, audit_log, started_at, completed_at, "
        "priority_label FROM tasks WHERE ueid=?",
        (new_ueid,),
    ).fetchone()
    conn.close()

    assert row is not None, "row not found"
    tags, deps, audit_log, started_at, completed_at, priority_label = row

    # Defaults per M163 spec.
    assert tags == "[]", f"tags default: {tags!r}"
    assert deps == "[]", f"deps default: {deps!r}"
    assert audit_log == "[]", f"audit_log default: {audit_log!r}"
    assert started_at is None, f"started_at default: {started_at!r}"
    assert completed_at is None, f"completed_at default: {completed_at!r}"
    assert priority_label == "P2", (
        f"priority_label default: {priority_label!r}"
    )


# ---------------------------------------------------------------------------
# 5. Pydantic TaskdogSlice parses all 14 fields
# ---------------------------------------------------------------------------

def test_taskdog_slice_parses_new_fields() -> None:
    """TaskdogSlice Pydantic model handles all 14 fields, including
    coercion from SQLite-shaped dicts where list fields arrive as JSON
    strings.
    """
    try:
        from src.mesh.taskdog_models import (
            TaskdogAuditEntry,
            TaskdogSlice,
        )
    except ImportError:
        pytest.skip(
            "TaskdogSlice model not yet available "
            "(src/mesh/taskdog_models.py)"
        )

    # 5a. Bare minimum: just ueid, all v2 fields get defaults.
    s = TaskdogSlice(
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
    )
    assert s.tags == []
    assert s.deps == []
    assert s.audit_log == []
    assert s.started_at is None
    assert s.completed_at is None
    assert s.priority_label == "P2"

    # 5b. Full slice with audit log entry.
    s2 = TaskdogSlice(
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        name="Buy groceries",
        status="planned",
        priority=2,
        tags=["urgent", "home"],
        deps=[
            "tsk:dep:00000000-0000-0000-0000-000000000000:0000000000000000",
        ],
        audit_log=[
            {
                "timestamp": "2026-10-01T12:00:00",
                "action": "create",
                "actor": "cli",
                "fields_diff": {},
            },
        ],
        priority_label="P1",
        started_at="2026-10-01T13:00:00",
        completed_at=None,
    )
    assert s2.tags == ["urgent", "home"]
    assert s2.deps == [
        "tsk:dep:00000000-0000-0000-0000-000000000000:0000000000000000",
    ]
    assert s2.priority_label == "P1"
    assert s2.started_at == "2026-10-01T13:00:00"
    assert len(s2.audit_log) == 1
    assert isinstance(s2.audit_log[0], TaskdogAuditEntry)
    assert s2.audit_log[0].action == "create"
    assert s2.audit_log[0].actor == "cli"

    # 5c. Coercion from SQLite-shaped dict (list fields arrive as JSON strings).
    sqlite_row = {
        "ueid": "tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        "name": "From SQLite",
        "status": "planned",
        "priority": 2,
        "tags": json.dumps(["a", "b"]),
        "deps": json.dumps([]),
        "audit_log": json.dumps([]),
        "priority_label": "P3",
        "started_at": None,
        "completed_at": None,
        "created_at": "2026-10-01T00:00:00",
    }
    s3 = TaskdogSlice(**sqlite_row)
    assert s3.tags == ["a", "b"], f"tags coercion: {s3.tags!r}"
    assert s3.deps == []
    assert s3.audit_log == []
    assert s3.priority_label == "P3"

    # 5d. extra="forbid" — extra fields are rejected.
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        TaskdogSlice(
            ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
            bogus_field="nope",
        )

    # 5e. frozen=True — mutation is rejected.
    with pytest.raises((AttributeError, pydantic.ValidationError, TypeError)):
        s.ueid = "tsk:other:00000000-0000-0000-0000-000000000000:0000000000000000"

    # 5f. invalid priority_label is rejected by the Literal type.
    with pytest.raises(pydantic.ValidationError):
        TaskdogSlice(
            ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
            priority_label="INVALID",
        )
