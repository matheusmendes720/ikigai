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

M163: schema v2 migration. Adds 6 new columns to the `tasks` table:
  - tags           (TEXT NOT NULL DEFAULT '[]')      — JSON array of strings
  - deps           (TEXT NOT NULL DEFAULT '[]')      — JSON array of UEID strings
  - audit_log      (TEXT NOT NULL DEFAULT '[]')      — JSON array of audit objects
  - started_at     (TEXT)                            — ISO8601, nullable
  - completed_at   (TEXT)                            — ISO8601, nullable
  - priority_label (TEXT NOT NULL DEFAULT 'P2')      — P0/P1/P2/P3 textual

Lazy migration: ``_migrate_add_columns`` runs ``PRAGMA table_info`` and
only ALTERs columns that don't yet exist. Idempotent — safe on every
read/write. One-shot migration script: ``scripts/migrate_taskdog_schema_v2.py``.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contracts.common import UEID
from contracts.task_change import PropagationEvent

# M163: schema version constant. v1 = original 8 columns; v2 adds 6 new
# columns (tags, deps, audit_log, started_at, completed_at, priority_label).
# Migration: scripts/migrate_taskdog_schema_v2.py.
SCHEMA_VERSION = 2

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
    # M163 schema v2 additions:
    "tags",
    "deps",
    "audit_log",
    "started_at",
    "completed_at",
    "priority_label",
}

# SQLite column set (must match the table definition below).
# Schema v2 = original 8 columns + 6 M163 columns = 14.
_SQLITE_COLUMNS = (
    "ueid", "name", "status", "priority",
    "planned_start", "planned_end", "deadline", "created_at",
    "tags", "deps", "audit_log",
    "started_at", "completed_at", "priority_label",
)


def _safe_json_list(value: Any, default: list | None = None) -> list:
    """Parse a JSON-array string into a list. Returns default on parse error.

    Used for the M163 `tags`, `deps`, and `audit_log` columns — SQLite
    stores them as TEXT but the adapter reads them back as Python lists.
    """
    if default is None:
        default = []
    if value is None:
        return list(default)
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else list(default)
        except (json.JSONDecodeError, TypeError):
            return list(default)
    return list(default)


# ----------------------------------------------------------------------
# M164: tag subsystem — module-level helpers used by td tag add/remove/list/clear
# ----------------------------------------------------------------------
# `tags` is a JSON array of strings stored in the same row as the task.
# Each helper accepts an optional db_path override (used by tests that
# monkeypatch TASKDOG_DB). All mutators write an entry to the in-row
# audit_log JSON column AND best-effort append to `.tag_audit.log`.

# Tag validation regex: 1-32 chars, alphanumeric + hyphen + underscore.
# Keep this in lockstep with the validator used by the td tag subcommands.
_TAG_REGEX = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_MAX_TAG_LEN = 32


def _is_valid_tag(s: Any) -> bool:
    """True iff `s` is a valid tag per the M164 contract."""
    return isinstance(s, str) and bool(_TAG_REGEX.match(s))


def _read_tags_for(conn: sqlite3.Connection, ueid: str) -> list[str]:
    """Read the tags JSON array for a single row. Empty list on miss/null."""
    cur = conn.execute("SELECT tags FROM tasks WHERE ueid=?", (ueid,))
    row = cur.fetchone()
    if row is None or row[0] is None or row[0] == "":
        return []
    try:
        parsed = json.loads(row[0])
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _read_audit_log_for(conn: sqlite3.Connection, ueid: str) -> list[dict]:
    """Read the audit_log JSON array for a single row."""
    cur = conn.execute("SELECT audit_log FROM tasks WHERE ueid=?", (ueid,))
    row = cur.fetchone()
    if row is None or row[0] is None or row[0] == "":
        return []
    try:
        parsed = json.loads(row[0])
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _write_tags_with_audit(
    conn: sqlite3.Connection, ueid: str, new_tags: list[str], entry: dict
) -> None:
    """Persist new_tags + append entry to audit_log atomically (one UPDATE)."""
    audit = _read_audit_log_for(conn, ueid)
    audit.append(entry)
    conn.execute(
        "UPDATE tasks SET tags=?, audit_log=? WHERE ueid=?",
        (json.dumps(new_tags), json.dumps(audit), ueid),
    )


def _append_tag_audit_file(ueid: str, action: str, details: dict) -> None:
    """Best-effort append to <data>/taskdog/.tag_audit.log.

    Pipe-separated lines: ISO8601|ueid|action|json_details. Mirrors the
    style used by the dep subsystem's audit log. Failures swallowed.
    """
    try:
        ts = datetime.now(timezone.utc).isoformat()
        line = f"{ts}|{ueid}|{action}|{json.dumps(details, sort_keys=True)}\n"
        TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)
        with (TASKDOG_DB.parent / ".tag_audit.log").open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass  # best-effort audit


def _ensure_tasks_table(conn: sqlite3.Connection) -> None:
    """Schema v2: tasks table with the M163 columns + lazy ALTER migration.

    Inlined rather than calling TaskdogAdapter._ensure_table so the tag
    helpers don't depend on a TaskdogAdapter instance. Same DDL.
    """
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
            created_at TEXT,
            tags TEXT NOT NULL DEFAULT '[]',
            deps TEXT NOT NULL DEFAULT '[]',
            audit_log TEXT NOT NULL DEFAULT '[]',
            started_at TEXT,
            completed_at TEXT,
            priority_label TEXT NOT NULL DEFAULT 'P2'
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_ueid ON tasks(ueid);
    """)
    # M163 lazy migration: ALTER any columns missing on legacy DBs.
    cur = conn.execute("PRAGMA table_info(tasks)")
    existing = {row[1] for row in cur.fetchall()}
    _ADD_SPECS: dict[str, str] = {
        "tags": "TEXT NOT NULL DEFAULT '[]'",
        "deps": "TEXT NOT NULL DEFAULT '[]'",
        "audit_log": "TEXT NOT NULL DEFAULT '[]'",
        "started_at": "TEXT",
        "completed_at": "TEXT",
        "priority_label": "TEXT NOT NULL DEFAULT 'P2'",
    }
    for col, ddl in _ADD_SPECS.items():
        if col in existing:
            continue
        try:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {ddl}")
        except sqlite3.OperationalError as exc:
            if "duplicate column" in str(exc).lower():
                continue
            raise


# Canonical 4-part UEID regex (mirrors src/contracts/common.py:UEID). Kept
# inline to avoid a circular import — contracts imports back through other
# paths and the tag helpers are used in tests that import the adapter
# directly.
_UEID_REGEX = re.compile(
    r"^(?:"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
    r"|"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{4,64}"
    r"|"
    r"[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
    r")$"
)


def _is_valid_ueid_str(s: Any) -> bool:
    """Lenient UEID check used by the tag helpers."""
    return isinstance(s, str) and bool(_UEID_REGEX.match(s))


# ----------------------------------------------------------------------
# Public module-level tag operations — used by td tag add/remove/list/clear
# ----------------------------------------------------------------------

def add_tags(
    ueid: str,
    tags: list[str],
    db_path: Path | None = None,
) -> list[str]:
    """Append tags to a task's tag set. Idempotent: returns unchanged set
    if every tag is already present.

    Returns the FULL post-mutation tag list (sorted, deduped).

    Raises:
        ValueError: invalid UEID or any invalid tag format.
        LookupError: ueid not found in taskdog.
    """
    if not _is_valid_ueid_str(ueid):
        raise ValueError(f"invalid UEID: {ueid!r}")
    cleaned: list[str] = []
    for t in tags:
        if not _is_valid_tag(t):
            raise ValueError(
                f"invalid tag: {t!r} (max {_MAX_TAG_LEN} chars, "
                "alphanumeric+hyphen+underscore)"
            )
        cleaned.append(t)
    if not cleaned:
        raise ValueError("add_tags requires at least one tag")

    db = db_path or TASKDOG_DB
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        _ensure_tasks_table(conn)
        cur = conn.execute("SELECT 1 FROM tasks WHERE ueid=?", (ueid,))
        if cur.fetchone() is None:
            raise LookupError(
                f"add_tags target ueid={ueid!r} not found in taskdog"
            )
        current = _read_tags_for(conn, ueid)
        added = [t for t in cleaned if t not in current]
        new_tags = sorted(list(current) + added)
        if not added:
            return new_tags  # idempotent: nothing changed
        _write_tags_with_audit(
            conn,
            ueid,
            new_tags,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "tag_add",
                "actor": "cli",
                "fields_diff": {
                    "added": added,
                    "before": current,
                    "after": new_tags,
                },
            },
        )
        conn.commit()
    finally:
        conn.close()
    _append_tag_audit_file(
        ueid, "tag_add", {"added": added, "before": current, "after": new_tags}
    )
    return new_tags


def remove_tags(
    ueid: str,
    tags: list[str],
    db_path: Path | None = None,
) -> list[str]:
    """Remove tags from a task's tag set. Missing tags are no-ops.

    Returns the FULL post-mutation tag list (sorted, deduped).

    Raises:
        ValueError: invalid UEID or any invalid tag format.
        LookupError: ueid not found in taskdog.
    """
    if not _is_valid_ueid_str(ueid):
        raise ValueError(f"invalid UEID: {ueid!r}")
    cleaned: list[str] = []
    for t in tags:
        if not _is_valid_tag(t):
            raise ValueError(
                f"invalid tag: {t!r} (max {_MAX_TAG_LEN} chars, "
                "alphanumeric+hyphen+underscore)"
            )
        cleaned.append(t)
    if not cleaned:
        raise ValueError("remove_tags requires at least one tag")

    db = db_path or TASKDOG_DB
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        _ensure_tasks_table(conn)
        cur = conn.execute("SELECT 1 FROM tasks WHERE ueid=?", (ueid,))
        if cur.fetchone() is None:
            raise LookupError(
                f"remove_tags target ueid={ueid!r} not found in taskdog"
            )
        current = _read_tags_for(conn, ueid)
        removed = [t for t in cleaned if t in current]
        new_tags = sorted(t for t in current if t not in cleaned)
        if not removed:
            return new_tags  # idempotent: nothing changed
        _write_tags_with_audit(
            conn,
            ueid,
            new_tags,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "tag_remove",
                "actor": "cli",
                "fields_diff": {
                    "removed": removed,
                    "before": current,
                    "after": new_tags,
                },
            },
        )
        conn.commit()
    finally:
        conn.close()
    _append_tag_audit_file(
        ueid,
        "tag_remove",
        {"removed": removed, "before": current, "after": new_tags},
    )
    return new_tags


def clear_tags(
    ueid: str,
    db_path: Path | None = None,
) -> list[str]:
    """Remove all tags from a task. Idempotent: returns [] if already empty.

    Raises:
        ValueError: invalid UEID.
        LookupError: ueid not found in taskdog.
    """
    if not _is_valid_ueid_str(ueid):
        raise ValueError(f"invalid UEID: {ueid!r}")
    db = db_path or TASKDOG_DB
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        _ensure_tasks_table(conn)
        cur = conn.execute("SELECT 1 FROM tasks WHERE ueid=?", (ueid,))
        if cur.fetchone() is None:
            raise LookupError(
                f"clear_tags target ueid={ueid!r} not found in taskdog"
            )
        current = _read_tags_for(conn, ueid)
        if not current:
            return current  # idempotent: already empty
        _write_tags_with_audit(
            conn,
            ueid,
            [],
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "tag_clear",
                "actor": "cli",
                "fields_diff": {"before": current, "after": []},
            },
        )
        conn.commit()
    finally:
        conn.close()
    _append_tag_audit_file(
        ueid, "tag_clear", {"before": current, "after": []}
    )
    return []


def get_tags(
    ueid: str,
    db_path: Path | None = None,
) -> list[str]:
    """Return the canonical tag list for a task (sorted, deduped).

    Returns [] if the row has no tags. Raises LookupError if the row is
    missing entirely; that distinguishes "tag-less task" from "no such task".

    Raises:
        ValueError: invalid UEID.
        LookupError: ueid not found in taskdog.
    """
    if not _is_valid_ueid_str(ueid):
        raise ValueError(f"invalid UEID: {ueid!r}")
    db = db_path or TASKDOG_DB
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        _ensure_tasks_table(conn)
        cur = conn.execute("SELECT 1 FROM tasks WHERE ueid=?", (ueid,))
        if cur.fetchone() is None:
            raise LookupError(
                f"get_tags target ueid={ueid!r} not found in taskdog"
            )
        return _read_tags_for(conn, ueid)
    finally:
        conn.close()


def _normalize_http_task(api_task: dict) -> dict:
    """Normalize one task object from the HTTP bridge into the slice shape
    the rest of the mesh expects. Defensive against key drift on the daemon.
    """
    # Adapter reads return dicts with these keys: ueid, name, status,
    # priority, planned_start, planned_end, deadline, created_at, plus
    # M163 v2 additions: tags, deps, audit_log, started_at,
    # completed_at, priority_label. Missing fields fall back to safe
    # defaults so downstream code can rely on the shape.
    return {
        "ueid": api_task.get("ueid") or api_task.get("id"),
        "name": api_task.get("name") or api_task.get("title"),
        "status": api_task.get("status"),
        "priority": api_task.get("priority"),
        "planned_start": api_task.get("planned_start"),
        "planned_end": api_task.get("planned_end"),
        "deadline": api_task.get("deadline") or api_task.get("due"),
        "created_at": api_task.get("created_at"),
        "tags": _safe_json_list(api_task.get("tags")),
        "deps": _safe_json_list(api_task.get("deps")),
        "audit_log": _safe_json_list(api_task.get("audit_log")),
        "started_at": api_task.get("started_at"),
        "completed_at": api_task.get("completed_at"),
        "priority_label": api_task.get("priority_label") or "P2",
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
                    created_at TEXT,
                    tags TEXT NOT NULL DEFAULT '[]',
                    deps TEXT NOT NULL DEFAULT '[]',
                    audit_log TEXT NOT NULL DEFAULT '[]',
                    started_at TEXT,
                    completed_at TEXT,
                    priority_label TEXT NOT NULL DEFAULT 'P2'
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_ueid ON tasks(ueid);
            """)
            self._migrate_add_columns(conn)
            cur = conn.execute(
                "SELECT ueid, name, status, priority, planned_start, "
                "planned_end, deadline, created_at, "
                "tags, deps, audit_log, "
                "started_at, completed_at, priority_label "
                "FROM tasks WHERE ueid=?",
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
                "tags": _safe_json_list(row[8]),
                "deps": _safe_json_list(row[9]),
                "audit_log": _safe_json_list(row[10]),
                "started_at": row[11],
                "completed_at": row[12],
                "priority_label": row[13] or "P2",
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
                    created_at TEXT,
                    tags TEXT NOT NULL DEFAULT '[]',
                    deps TEXT NOT NULL DEFAULT '[]',
                    audit_log TEXT NOT NULL DEFAULT '[]',
                    started_at TEXT,
                    completed_at TEXT,
                    priority_label TEXT NOT NULL DEFAULT 'P2'
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_ueid ON tasks(ueid);
            """)
            self._migrate_add_columns(conn)
            cur = conn.execute(
                "SELECT ueid, name, status, priority, planned_start, "
                "planned_end, deadline, created_at, "
                "tags, deps, audit_log, "
                "started_at, completed_at, priority_label "
                "FROM tasks"
            )
            out = []
            for r in cur.fetchall():
                out.append({
                    "ueid": r[0], "name": r[1], "status": r[2],
                    "priority": r[3], "planned_start": r[4],
                    "planned_end": r[5], "deadline": r[6],
                    "created_at": r[7],
                    "tags": _safe_json_list(r[8]),
                    "deps": _safe_json_list(r[9]),
                    "audit_log": _safe_json_list(r[10]),
                    "started_at": r[11],
                    "completed_at": r[12],
                    "priority_label": r[13] or "P2",
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

        - CREATE:   idempotent insert-or-replace on `ueid`
        - UPDATE:   partial update of whitelisted fields
        - DONE:     sets status='done' (idempotent)
        - DELETE:   removes the row
        - TAG_ADD:  append tags (idempotent on already-present)
        - TAG_REMOVE: remove tags (no-op on missing)
        - TAG_CLEAR: remove all tags

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
        elif action == "tag_add":
            self._apply_tag_add(event)
        elif action == "tag_remove":
            self._apply_tag_remove(event)
        elif action == "tag_clear":
            self._apply_tag_clear(event)
        # else: forward-compatible skip

    # ------------------------------------------------------------------
    # M164: tag action handlers (apply_change dispatch)
    # ------------------------------------------------------------------
    # These wrappers normalize the PropagationEvent into a module-level
    # tag helper call. They exist on the adapter (rather than directly
    # enqueuing the module helpers) so the canonical apply_change entry
    # point is the only way mesh events touch the SQLite write store.
    def _apply_tag_add(self, event: PropagationEvent) -> None:
        """TAG_ADD: append tags from event.fields['tags'] (list[str]).

        Raises ValueError on invalid tag strings (forwards to mesh worker).
        """
        tags = event.fields.get("tags") or []
        if not isinstance(tags, list):
            raise ValueError(
                f"TAG_ADD fields.tags must be list[str], got {type(tags).__name__}"
            )
        add_tags(str(event.ueid), tags)

    def _apply_tag_remove(self, event: PropagationEvent) -> None:
        """TAG_REMOVE: drop tags from event.fields['tags'] (list[str])."""
        tags = event.fields.get("tags") or []
        if not isinstance(tags, list):
            raise ValueError(
                f"TAG_REMOVE fields.tags must be list[str], got {type(tags).__name__}"
            )
        remove_tags(str(event.ueid), tags)

    def _apply_tag_clear(self, event: PropagationEvent) -> None:
        """TAG_CLEAR: wipe all tags on the row."""
        clear_tags(str(event.ueid))

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
                created_at TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                deps TEXT NOT NULL DEFAULT '[]',
                audit_log TEXT NOT NULL DEFAULT '[]',
                started_at TEXT,
                completed_at TEXT,
                priority_label TEXT NOT NULL DEFAULT 'P2'
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_ueid ON tasks(ueid);
        """)
        # M163: lazily ALTER missing columns on legacy DBs.
        self._migrate_add_columns(conn)

    @staticmethod
    def _migrate_add_columns(conn: sqlite3.Connection) -> None:
        """Idempotent ALTER TABLE for M163 columns on a v1 schema.

        Runs ``PRAGMA table_info`` and issues ALTER TABLE only for
        missing columns. SQLite raises on duplicate-column ADD; we
        swallow that specific case and re-raise anything else (real
        schema drift, locked DB, etc.). Safe to call on every read/write.

        IMPORTANT: each ALTER is committed immediately so the schema
        change survives ``conn.close()``. Without the explicit commit,
        the implicit transaction opened by sqlite3's default isolation
        level would be rolled back when the caller closes the
        connection, silently dropping the new columns.
        """
        cur = conn.execute("PRAGMA table_info(tasks)")
        existing = {row[1] for row in cur.fetchall()}

        _ADD_SPECS: dict[str, str] = {
            "tags": "TEXT NOT NULL DEFAULT '[]'",
            "deps": "TEXT NOT NULL DEFAULT '[]'",
            "audit_log": "TEXT NOT NULL DEFAULT '[]'",
            "started_at": "TEXT",
            "completed_at": "TEXT",
            "priority_label": "TEXT NOT NULL DEFAULT 'P2'",
        }
        for col, ddl in _ADD_SPECS.items():
            if col in existing:
                continue
            try:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {ddl}")
            except sqlite3.OperationalError as exc:
                if "duplicate column" in str(exc).lower():
                    continue
                raise
            # DDL implicitly commits, but DML (the backfill UPDATE below)
            # does NOT — sqlite3 default isolation_level opens an implicit
            # transaction. Commit after the ALTER so the column-add is
            # durable even if a later UPDATE in the same call fails.
            conn.commit()
            # Backfill: defensive — DEFAULT clause should already cover
            # NOT NULL constraints, but be explicit for visibility.
            if col in ("tags", "deps", "audit_log"):
                conn.execute(
                    f"UPDATE tasks SET {col}='[]' WHERE {col} IS NULL"
                )
                conn.commit()

    def _apply_create(self, event: PropagationEvent) -> None:
        """CREATE: idempotent insert-or-replace keyed by `ueid`.

        M163: also populates the 6 v2 columns with defaults, or with
        values from `event.fields` if provided. `tags`/`deps`/`audit_log`
        are JSON-serialized when supplied as Python lists.
        """
        TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            self._ensure_table(conn)
            priority = self._normalize_priority(event.fields.get("priority"))
            title = event.fields.get("title")
            due = event.fields.get("due")
            approved_at = event.approved_at.isoformat()

            # M163 v2 columns: pull from event.fields if present, else defaults.
            tags_raw = event.fields.get("tags")
            deps_raw = event.fields.get("deps")
            audit_raw = event.fields.get("audit_log")
            tags_json = (
                json.dumps(tags_raw) if isinstance(tags_raw, list)
                else (tags_raw if isinstance(tags_raw, str) else "[]")
            )
            deps_json = (
                json.dumps(deps_raw) if isinstance(deps_raw, list)
                else (deps_raw if isinstance(deps_raw, str) else "[]")
            )
            audit_json = (
                json.dumps(audit_raw) if isinstance(audit_raw, list)
                else (audit_raw if isinstance(audit_raw, str) else "[]")
            )
            priority_label = event.fields.get("priority_label") or "P2"
            started_at = event.fields.get("started_at")
            completed_at = event.fields.get("completed_at")

            conn.execute(
                """INSERT INTO tasks (
                       ueid, name, status, priority, deadline, created_at,
                       tags, deps, audit_log, priority_label,
                       started_at, completed_at
                   )
                   VALUES (?, ?, 'planned', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(ueid) DO UPDATE SET
                       name=excluded.name,
                       priority=excluded.priority,
                       deadline=excluded.deadline,
                       tags=excluded.tags,
                       deps=excluded.deps,
                       audit_log=excluded.audit_log,
                       priority_label=excluded.priority_label,
                       started_at=COALESCE(excluded.started_at, started_at),
                       completed_at=COALESCE(excluded.completed_at, completed_at)""",
                (
                    event.ueid, title, priority, due, approved_at,
                    tags_json, deps_json, audit_json, priority_label,
                    started_at, completed_at,
                ),
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
            elif k in ("tags", "deps", "audit_log"):
                # M163: JSON-serialize list fields. Pass strings through;
                # reject anything else (the column stores JSON text).
                if isinstance(v, list):
                    clean[k] = json.dumps(v)
                elif isinstance(v, str):
                    clean[k] = v
                else:
                    continue  # bad type → drop
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
