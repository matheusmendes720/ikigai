"""SQLite manager wrapping the unified_planning_items (UPI) table.

Schema matches the existing cross-fork storage adapter at
src/mesh/adapters/solverforge_calendar.py. UPSERT on ueid.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import sqlite3


_SCHEMA = """
CREATE TABLE IF NOT EXISTS unified_planning_items (
    id TEXT PRIMARY KEY,
    ueid TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT,
    blocked_by TEXT DEFAULT '[]',
    tags TEXT DEFAULT '[]',
    ikigai TEXT DEFAULT '{}',
    status TEXT DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_upi_ueid ON unified_planning_items(ueid);
CREATE INDEX IF NOT EXISTS idx_upi_start ON unified_planning_items(start_at);
"""


class SolverforgeDB:
    """SQLite wrapper for the UPI table. SQLite UPSERT on ueid."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, isolation_level=None)

    def upsert(
        self,
        *,
        ueid: str,
        title: str,
        start_at: datetime,
        end_at: datetime | None,
        blocked_by: list[str] | None = None,
        tags: list[str] | None = None,
        ikigai: dict | None = None,
        status: str = "scheduled",
    ) -> dict:
        now = datetime.utcnow().isoformat()
        row_id = str(uuid.uuid4().hex)
        with self._conn() as c:
            # UPSERT: insert new with new uuid, or update existing row in place
            existing = c.execute(
                "SELECT id FROM unified_planning_items WHERE ueid = ?", (ueid,)
            ).fetchone()
            if existing:
                row_id = existing[0]
                c.execute(
                    """UPDATE unified_planning_items SET
                        title=?, start_at=?, end_at=?, blocked_by=?, tags=?, ikigai=?,
                        status=?, updated_at=?
                       WHERE ueid=?""",
                    (
                        title,
                        start_at.isoformat(),
                        end_at.isoformat() if end_at else None,
                        json.dumps(blocked_by or []),
                        json.dumps(tags or []),
                        json.dumps(ikigai or {}),
                        status,
                        now,
                        ueid,
                    ),
                )
            else:
                c.execute(
                    """INSERT INTO unified_planning_items
                        (id, ueid, title, start_at, end_at, blocked_by, tags, ikigai,
                         status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row_id,
                        ueid,
                        title,
                        start_at.isoformat(),
                        end_at.isoformat() if end_at else None,
                        json.dumps(blocked_by or []),
                        json.dumps(tags or []),
                        json.dumps(ikigai or {}),
                        status,
                        now,
                        now,
                    ),
                )
        return {"id": row_id, "ueid": ueid, "status": status}

    def read(self, ueid: str) -> dict | None:
        with self._conn() as c:
            row = c.execute(
                """SELECT id, ueid, title, start_at, end_at, blocked_by, tags,
                          ikigai, status
                   FROM unified_planning_items WHERE ueid = ?""",
                (ueid,),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "ueid": row[1],
                "title": row[2],
                "start_at": row[3],
                "end_at": row[4],
                "blocked_by": json.loads(row[5]),
                "tags": json.loads(row[6]),
                "ikigai": json.loads(row[7]),
                "status": row[8],
            }

    def list_busy_in_window(self, *, start: datetime, end: datetime) -> list[dict]:
        """Return rows whose [start_at, end_at) overlaps [start, end)."""
        with self._conn() as c:
            rows = c.execute(
                """SELECT ueid, title, start_at, end_at, status
                   FROM unified_planning_items
                   WHERE start_at < ? AND (end_at IS NULL OR end_at > ?)""",
                (end.isoformat(), start.isoformat()),
            ).fetchall()
            return [
                {
                    "ueid": r[0],
                    "title": r[1],
                    "start_at": r[2],
                    "end_at": r[3],
                    "status": r[4],
                }
                for r in rows
            ]
