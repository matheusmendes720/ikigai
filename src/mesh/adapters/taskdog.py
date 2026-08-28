"""Adapter for taskdog SQLite (simplified schema for v1; full SQLAlchemy in v2)."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TASKDOG_DB = PROJECT_ROOT / "data" / "taskdog" / "tasks.db"

SUPPORTED_FIELDS = {
    "title",
    "due",
    "priority",
    "status",
    "ueid",
    "planned_start",
    "planned_end",
    "actual_end",
    "tags",
}


class TaskdogAdapter:
    """Read/write the taskdog tasks table (simplified for v1)."""

    name = "taskdog"

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        if not TASKDOG_DB.exists():
            return None
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            row = conn.execute(
                "SELECT ueid, name, status, priority, planned_start, planned_end, deadline, created_at "
                "FROM tasks WHERE ueid = ?",
                (ueid,),
            ).fetchone()
            if row is None:
                return None
            return {
                "ueid": row[0],
                "name": row[1],
                "status": row[2],
                "priority": row[3],
                "planned_start": row[4],
                "planned_end": row[5],
                "deadline": row[6],
                "created_at": row[7],
            }
        finally:
            conn.close()

    def apply_change(self, event: PropagationEvent) -> None:
        if event.action.value != "create":
            return  # v1 only supports create

        TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            # Check if table exists (create if not — idempotent bootstrap)
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
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
                CREATE INDEX IF NOT EXISTS idx_tasks_ueid ON tasks(ueid);
            """)

            # Native SQLite UPSERT: single INSERT with ON CONFLICT
            priority = event.fields.get("priority")
            if isinstance(priority, str):
                priority_map = {"high": 1, "medium": 2, "low": 3}
                priority = priority_map.get(priority.lower(), 2)

            title = event.fields.get("title")
            due = event.fields.get("due")
            approved_at = event.approved_at.isoformat()

            conn.execute(
                """INSERT INTO tasks (ueid, name, status, priority, deadline, created_at)
                   VALUES (?, ?, 'planned', ?, ?, ?)
                   ON CONFLICT(ueid) DO UPDATE SET
                       name=excluded.name,
                       priority=excluded.priority,
                       deadline=excluded.deadline""",
                (event.ueid, title, priority, due, approved_at),
            )
            conn.commit()
        finally:
            conn.close()

    def supports_field(self, field_name: str) -> bool:
        return field_name in SUPPORTED_FIELDS
