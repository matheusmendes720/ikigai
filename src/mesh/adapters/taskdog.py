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

M148: apply_change expanded to support UPDATE/DONE/DELETE actions.
CREATE remains idempotent insert-or-replace; UPDATE/DONE/DELETE
mutate existing rows in the local SQLite canonical write store.
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
    return os.environ.get("TASKDOG_HTTP_ENABLED", "1") not in (
        "0",
        "false",
        "",
    )


def _http_get(path: str) -> dict | list | None:
    """GET from TASKDOG_SERVER + path. Returns parsed JSON or None on failure."""
    url = f"{TASKDOG_SERVER}{path}"
    try:
        with urllib.request.urlopen(url, timeout=TASKDOG_HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        # Caller checks None and falls back to SQLite — silent by design
        # (reads are best-effort with SQLite as the canonical fallback).
        return None


# Whitelist of fields the adapter accepts on UPDATE/INSERT. Matches the
# SQLite column set so we don't try to bind to non-existent columns.
SUPPORTED_FIELDS = {
    "title",
    "due",
    "priority",
    "status",
    "ueid",
    "planned_start",
    "planned_end",
}

# SQLite column set (must match the table definition below).
_SQLITE_COLUMNS = (
    "ueid", "name", "status", "priority",
    "planned_start", "planned_end", "deadline", "created_at",
)


def _normalize_http_task(api_task: dict) -> dict:
    """Normalize one task object from the HTTP bridge into the slice shape
    the rest of the mesh expects. Defensive against key drift on the daemon.
    """
    # Adapter reads return dicts with these keys: ueid, name, status,
    # priority, planned_start, planned_end, deadline, created_at.
    return {
        "ueid": api_task.get("ueid") or api_task.get("id"),
        "name": api_task.get("name") or api_task.get("title"),
        "status": api_task.get("status"),
        "priority": api_task.get("priority"),
        "planned_start": api_task.get("planned_start"),
        "planned_end": api_task.get("planned_end"),
        "deadline": api_task.get("deadline") or api_task.get("due"),
        "created_at": api_task.get("created_at"),
    }


class TaskdogAdapter:
    """Adapter that joins the MCP mesh against taskdog (HTTP or SQLite)."""

    # Canonical fork name used by agent_propagator.PropagationResult.
    # Matches the forks defined in src/mesh/adapters/__init__.py:
    # ('cli', 'taskdog', 'solverforge_calendar').
    name: str = "taskdog"

    # ------------------------------------------------------------------
    # Reads — HTTP-first with SQLite fallback
    # ------------------------------------------------------------------
    def read(self, ueid: UEID) -> dict[str, Any] | None:
        if _http_enabled():
            payload = _http_get(f"/api/v1/tasks/{ueid}")
            if payload and isinstance(payload, dict):
                return _normalize_http_task(payload)
            if payload is not None:
                # Server reachable but returned something unexpected —
                # try SQLite fallback to avoid losing data.
                pass
            else:
                # Server unreachable — fall through to SQLite.
                return self._sqlite_read(str(ueid))
        else:
            return self._sqlite_read(str(ueid))

    def list_all(self) -> list[dict[str, Any]]:
        if _http_enabled():
            payload = _http_get("/api/v1/tasks")
            if isinstance(payload, list):
                return [_normalize_http_task(t) for t in payload
                        if isinstance(t, dict)]
            # Server unreachable or bad payload — fall through to SQLite.
        return self._sqlite_list_all()

    def _sqlite_read(self, ueid_str: str) -> dict[str, Any] | None:
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
            cur = conn.execute(
                "SELECT ueid, name, status, priority, planned_start, "
                "planned_end, deadline, created_at FROM tasks WHERE ueid=?",
                (ueid_str,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return {
                "ueid": row[0], "name": row[1], "status": row[2],
                "priority": row[3], "planned_start": row[4],
                "planned_end": row[5], "deadline": row[6],
                "created_at": row[7],
            }
        finally:
            conn.close()

    def _sqlite_list_all(self) -> list[dict[str, Any]]:
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
            cur = conn.execute(
                "SELECT ueid, name, status, priority, planned_start, "
                "planned_end, deadline, created_at FROM tasks"
            )
            out = []
            for r in cur.fetchall():
                out.append({
                    "ueid": r[0], "name": r[1], "status": r[2],
                    "priority": r[3], "planned_start": r[4],
                    "planned_end": r[5], "deadline": r[6],
                    "created_at": r[7],
                })
            return out
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Writes — still local SQLite (kept for test compat + simpler write path)
    # ------------------------------------------------------------------
    # M148: apply_change expanded for UPDATE/DONE/DELETE actions.
    _WRITE_STATUSES: tuple[str, ...] = (
        "planned", "in_progress", "done", "cancelled",
    )
    _WRITE_PRIORITIES: tuple[int, ...] = (1, 2, 3)

    def apply_change(self, event: PropagationEvent) -> None:
        """Dispatch to the per-action branch.

        - CREATE: idempotent insert-or-replace on `ueid`
        - UPDATE: partial update of whitelisted fields
        - DONE:   sets status='done' (idempotent)
        - DELETE: removes the row

        Unknown actions are no-ops (forward compatibility).
        """
        action = event.action.value
        if action == "create":
            self._apply_create(event)
        elif action == "update":
            self._apply_update(event)
        elif action == "done":
            self._apply_done(event)
        elif action == "delete":
            self._apply_delete(event)
        # else: forward-compatible skip

    def _ensure_table(self, conn: sqlite3.Connection) -> None:
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

    def _apply_create(self, event: PropagationEvent) -> None:
        """CREATE: idempotent insert-or-replace keyed by `ueid`."""
        TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            self._ensure_table(conn)
            priority = self._normalize_priority(event.fields.get("priority"))
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

    def _apply_update(self, event: PropagationEvent) -> None:
        """UPDATE: partial update of whitelisted fields on existing row."""
        if "ueid" in event.fields:
            raise ValueError(
                f"UPDATE cannot change ueid (got ueid={event.fields.get('ueid')!r}); "
                "use CREATE + DELETE instead"
            )
        clean = self._filter_update_fields(event.fields)
        TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            self._ensure_table(conn)
            cur = conn.execute("SELECT 1 FROM tasks WHERE ueid=?", (event.ueid,))
            if cur.fetchone() is None:
                raise LookupError(
                    f"UPDATE target ueid={event.ueid!r} not found in taskdog"
                )
            if not clean:
                return  # all fields filtered out → no-op
            set_clauses = ", ".join(f"{k}=?" for k in clean.keys())
            params = list(clean.values()) + [event.ueid]
            conn.execute(
                f"UPDATE tasks SET {set_clauses} WHERE ueid=?",
                params,
            )
            conn.commit()
        finally:
            conn.close()

    def _apply_done(self, event: PropagationEvent) -> None:
        """DONE: marks task with status='done' (idempotent)."""
        TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            self._ensure_table(conn)
            cur = conn.execute(
                "SELECT status FROM tasks WHERE ueid=?", (event.ueid,)
            )
            row = cur.fetchone()
            if row is None:
                raise LookupError(
                    f"DONE target ueid={event.ueid!r} not found in taskdog"
                )
            if row[0] == "done":
                return  # idempotent: already done
            conn.execute(
                "UPDATE tasks SET status='done' WHERE ueid=?",
                (event.ueid,),
            )
            conn.commit()
        finally:
            conn.close()

    def _apply_delete(self, event: PropagationEvent) -> None:
        """DELETE: removes row. Refuses if row missing."""
        TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            self._ensure_table(conn)
            cur = conn.execute("SELECT 1 FROM tasks WHERE ueid=?", (event.ueid,))
            if cur.fetchone() is None:
                raise LookupError(
                    f"DELETE target ueid={event.ueid!r} not found in taskdog"
                )
            conn.execute("DELETE FROM tasks WHERE ueid=?", (event.ueid,))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Field validators
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_priority(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value if value in TaskdogAdapter._WRITE_PRIORITIES else None
        if isinstance(value, str):
            m = {"high": 1, "medium": 2, "low": 3}
            return m.get(value.lower())
        return None

    @classmethod
    def _filter_update_fields(cls, fields: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for k, v in fields.items():
            if k not in SUPPORTED_FIELDS:
                continue
            if k == "priority":
                clean[k] = cls._normalize_priority(v)
            elif k == "status" and isinstance(v, str) and v in cls._WRITE_STATUSES:
                clean[k] = v
            elif k == "status":
                continue  # bad status string → drop
            else:
                clean[k] = v
        # M148: column rename `title` → `name` (matches CREATE INSERT).
        # The portable key in the Pydantic contract is `title`; SQLite
        # stores it as `name`. Map here so UPDATE works on title.
        if "title" in clean:
            clean["name"] = clean.pop("title")
        return clean

    def supports_field(self, field_name: str) -> bool:
        return field_name in SUPPORTED_FIELDS
