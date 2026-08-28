"""Adapter for solverforge-calendar unified_planning_items (UPI)."""
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
UPI_DB = PROJECT_ROOT / "data" / "solverforge_calendar" / "unified_planning.db"

SUPPORTED_FIELDS = {"title", "status", "start_at", "end_at", "rrule", "blocked_by", "tags", "ueid"}


class SolverforgeCalendarAdapter:
    """Read/write solverforge-calendar UPI (after v3 migration)."""
    name = "solverforge_calendar"

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        if not UPI_DB.exists():
            return None
        conn = sqlite3.connect(UPI_DB)
        try:
            row = conn.execute(
                "SELECT id, ueid, status, start_at, end_at, blocked_by, tags, ikigai "
                "FROM unified_planning_items WHERE ueid = ?",
                (ueid,),
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "ueid": row[1],
                "status": row[2],
                "start_at": row[3],
                "end_at": row[4],
                "blocked_by": json.loads(row[5]) if row[5] else [],
                "tags": json.loads(row[6]) if row[6] else [],
                "ikigai": json.loads(row[7]) if row[7] else {},
            }
        finally:
            conn.close()

    def apply_change(self, event: PropagationEvent) -> None:
        if event.action.value != "create":
            return  # v1 only supports create

        UPI_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(UPI_DB)
        try:
            # Idempotent bootstrap (assumes v3 migration already added ueid column)
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS unified_planning_items (
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
                CREATE INDEX IF NOT EXISTS idx_upi_ueid ON unified_planning_items(ueid);
            """)

            ikigai = {
                "title": event.fields.get("title"),
                "due": event.fields.get("due"),
                "source_fork": event.source_fork,
                "approved_at": event.approved_at.isoformat(),
            }
            new_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO unified_planning_items (id, ueid, status, blocked_by, tags, ikigai, provenance)
                   VALUES (?, ?, 'planned', '[]', '[]', ?, '{}')
                   ON CONFLICT(ueid) DO UPDATE SET
                     status=excluded.status,
                     ikigai=excluded.ikigai""",
                (new_id, event.ueid, json.dumps(ikigai)),
            )
            conn.commit()
        finally:
            conn.close()

    def supports_field(self, field_name: str) -> bool:
        return field_name in SUPPORTED_FIELDS
