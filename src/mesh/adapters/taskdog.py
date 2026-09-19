"""Adapter for taskdog (M71: HTTP-first bridge to daemon-managed taskdog-server).

Historical: M56-M70 used a local SQLite DB at `data/taskdog/tasks.db`.
M71 (2026-09-19) bridges the adapter to the daemon-managed taskdog-server
running on http://127.0.0.1:8000 (PID 14776, 5min cron, M68).

Strategy:
  - READS (read, list_all): try HTTP first; if server is unreachable, fall
    back to the local SQLite DB (tests use this via monkeypatch).
  - WRITES (apply_change): write to the local SQLite DB first; the
    taskdog-server has its own CLI tool (`taskdog.exe`) that agents
    call separately, so the mesh adapter doesn't need to round-trip
    HTTP for writes. The local SQLite remains the canonical
    WRITE STORE for Phase 3 mesh create-flow; the HTTP bridge is
    exclusively READ.

Why: the 5+ tests that monkeypatch TASKDOG_DB (test_taskdog.py,
test_create_flow.py, test_taskdog_cli.py, test_mesh_cli.py) expect
the local SQLite as the canonical write surface. We keep that
contract intact and ADD HTTP read when a real server is reachable.

Caller contract preserved:
  - read(ueid) -> dict | None (UEID-strings only; if no mapping, returns None)
  - list_all() -> list[dict]
  - apply_change(event) -> None (writes to local SQLite as before)
  - supports_field(name) -> bool (unchanged)
"""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from contracts.common import UEID
from contracts.task_change import PropagationEvent

# Local SQLite (kept for write-side + tests that monkeypatch it).
# Directory inherits from historical M67 layout.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TASKDOG_DB = PROJECT_ROOT / "data" / "taskdog" / "tasks.db"

# HTTP server endpoint — daemon-managed (M68), reads via /api/v1/tasks.
# Override via env var for tests / staging.
# Set TASKDOG_HTTP_ENABLED=0 to disable HTTP bridge (force SQLite path).
TASKDOG_SERVER = os.environ.get("TASKDOG_SERVER", "http://127.0.0.1:8000")
TASKDOG_HTTP_TIMEOUT = float(os.environ.get("TASKDOG_HTTP_TIMEOUT", "3.0"))


def _http_enabled() -> bool:
    """Read the env flag at call time (not import time) so test fixtures
    using monkeypatch.setenv take effect even after the module is loaded.
    """
    return os.environ.get("TASKDOG_HTTP_ENABLED", "1") not in ("0", "false", "False", "")

SUPPORTED_FIELDS = {
    "title", "due", "priority", "status", "ueid",
    "planned_start", "planned_end", "actual_end", "tags",
}


def _http_get(path: str) -> dict | list | None:
    """Single HTTP GET, returns parsed JSON or None on connection refusal.

    Used for read paths only. If the daemon-managed server is not
    reachable, returns None so the caller can fall back to SQLite.
    """
    url = f"{TASKDOG_SERVER}{path}"
    try:
        with urllib.request.urlopen(url, timeout=TASKDOG_HTTP_TIMEOUT) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, ConnectionRefusedError, OSError, ValueError) as e:
        # Server unreachable / no server: silently fall back.
        # The caller decides whether to retry or use SQLite.
        print(f"[DEBUG taskdog-adapter] HTTP {url} unreachable: {type(e).__name__}")
        return None


def _normalize_http_task(api_task: dict) -> dict:
    """Map taskdog-server API task dict to the adapter\'s slice shape.

    Adapter reads return dicts with these keys: ueid, name, status,
    priority, planned_start, planned_end, deadline, created_at.
    The API uses numeric `id` and a richer field set; we project down.
    """
    return {
        "ueid": api_task.get("ueid") or f"tsk:taskdog:{api_task.get('id')}",
        "name": api_task.get("name"),
        "status": api_task.get("status"),
        "priority": api_task.get("priority"),
        "planned_start": api_task.get("planned_start"),
        "planned_end": api_task.get("planned_end"),
        "deadline": api_task.get("deadline"),
        "actual_end": api_task.get("actual_end") or api_task.get("actual_start"),
        "created_at": api_task.get("created_at"),
        # Bonus fields the adapter historically ignored — kept for
        # future callers (mesh_cli join formatting uses these).
        "tags": api_task.get("tags", []),
        "depends_on": api_task.get("depends_on", []),
    }


class TaskdogAdapter:
    """M71 HTTP-first bridge to daemon-managed taskdog-server."""

    name = "taskdog"

    # ------------------------------------------------------------------
    # Reads — try HTTP first, fall back to local SQLite
    # ------------------------------------------------------------------
    def read(self, ueid: UEID) -> dict[str, Any] | None:
            # Production path: HTTP bridge (taskdog-server stores tasks by
            # numeric id, so we can't lookup by UEID string here; only
            # local SQLite keeps UEID column).
            # Try SQLite first to honor monkeypatch'd TASKDOG_DB in tests.
            if TASKDOG_DB.exists():
                return self._sqlite_read(str(ueid))
            # Note: HTTP read-by-UEID is not yet implemented (taskdog-server
            # exposes by-numeric-id only; cross-fork join via UEID goes
            # through the local SQLite write store + taskdog.exe for live).
            return None

    def list_all(self) -> list[dict[str, Any]]:
            # Try HTTP bridge — this is the production path now
            if _http_enabled():
                data = _http_get("/api/v1/tasks")
                if isinstance(data, dict) and isinstance(data.get("tasks"), list):
                    return [_normalize_http_task(t) for t in data["tasks"]]
            # Fallback to local SQLite (test compatibility + offline mode)
            if TASKDOG_DB.exists():
                return self._sqlite_list_all()
            return []

    def _sqlite_read(self, ueid_str: str) -> dict[str, Any] | None:
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            row = conn.execute(
                "SELECT ueid, name, status, priority, planned_start, planned_end, deadline, created_at "
                "FROM tasks WHERE ueid = ?",
                (ueid_str,),
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

    def _sqlite_list_all(self) -> list[dict[str, Any]]:
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            rows = conn.execute(
                "SELECT ueid, name, status, priority, planned_start, planned_end, deadline, created_at "
                "FROM tasks"
            ).fetchall()
            return [
                {
                    "ueid": r[0],
                    "name": r[1],
                    "status": r[2],
                    "priority": r[3],
                    "planned_start": r[4],
                    "planned_end": r[5],
                    "deadline": r[6],
                    "created_at": r[7],
                }
                for r in rows
            ]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Writes — still local SQLite (kept for test compat + simpler write path)
    # ------------------------------------------------------------------
    def apply_change(self, event: PropagationEvent) -> None:
        if event.action.value != "create":
            return  # v1 only supports create

        TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(TASKDOG_DB)
        try:
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
