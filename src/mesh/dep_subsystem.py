"""M164 dep subsystem — cycle detection + dep CRUD + audit log.

Kept in its own module (rather than nested inside adapters/taskdog.py)
to avoid drift-net reverts when the canonical adapter is touched. The
adapter exposes the table; this module owns the dep-graph semantics.

Public surface:
    add_dep(start_ueid, target_ueid) -> None
    remove_dep(start_ueid, target_ueid) -> bool
    get_deps(ueid) -> {"blocked_by": [...], "blocks": [...]}
    list_blocked() -> [{"ueid": ..., "name": ..., "status": ..., "unmet_deps": [...]}]
    detect_cycle(start_ueid, target_ueid) -> list[str] | None

Errors:
    CycleDetected(path) — adding the edge would form a cycle.
    SelfLoopError(ueid) — start == target.
    ValueError — malformed UEID per the 4-part ADR-014 regex.
    LookupError — start_ueid row not in the taskdog table.

Cycle detection algorithm:
    Iterative DFS with a color map (white/gray/black). Hits a gray node
    = back-edge = cycle. Path is reconstructed from the parent map so the
    caller can show the operator which edges form the loop.
    Complexity: O(V + E) over the dep graph (no recursive descent).
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Canonical taskdog DB. Lazy-imported to dodge the dual-module identity
# problem (src.X vs X). The local ``_resolve_db`` helper reads TASKDOG_DB
# from the live adapter module so monkeypatch in tests is honored.
def _resolve_db() -> Path:
    from src.mesh.adapters import taskdog as taskdog_mod
    return taskdog_mod.TASKDOG_DB


# UEID regex (4-part per ADR-014). Mirrors the canonical regex in
# src/contracts/common.py.
_UEID_REGEX = re.compile(
    r"^(?:"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
    r"|"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{4,64}"
    r"|"
    r"[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
    r")$"
)


def _is_valid_ueid(s: str) -> bool:
    return bool(_UEID_REGEX.match(s))


class CycleDetected(ValueError):
    """Raised when adding a dep edge would create a cycle.

    Attributes:
        path: List of UEIDs forming the cycle, e.g. [A, B, C, A].
    """

    def __init__(self, path: list[str]) -> None:
        self.path = path
        super().__init__(
            f"cycle detected: {' -> '.join(path)}"
        )


class SelfLoopError(ValueError):
    """Raised when trying to add a self-loop (A blocked-by A)."""

    def __init__(self, ueid: str) -> None:
        self.ueid = ueid
        super().__init__(
            f"self-loop rejected: {ueid} cannot depend on itself"
        )


# Canonical schema DDL with the M163/M164 columns. Kept module-level so
# all dep code paths use the same definition.
_SCHEMA_DDL = """
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
        started_at TEXT,
        completed_at TEXT,
        tags TEXT,
        deps TEXT,
        audit_log TEXT,
        priority_label TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_tasks_ueid ON tasks(ueid);
"""


def _migrate_add_deps_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add `deps TEXT` column to tasks if absent."""
    cur = conn.execute("PRAGMA table_info(tasks)")
    existing = {row[1] for row in cur.fetchall()}
    if "deps" in existing:
        return
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN deps TEXT")
        conn.commit()
    except sqlite3.OperationalError as exc:
        if "duplicate column" in str(exc).lower():
            return
        raise


def _safe_json_list(value: Any, default: list | None = None) -> list:
    """Parse a JSON-array string into a list. Returns default on parse error."""
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


def _read_deps_for(conn: sqlite3.Connection, ueid: str) -> list[str]:
    """Read the deps JSON array for a single row. Empty list if missing/null."""
    cur = conn.execute("SELECT deps FROM tasks WHERE ueid=?", (ueid,))
    row = cur.fetchone()
    if row is None or row[0] is None or row[0] == "":
        return []
    return _safe_json_list(row[0])


def _read_all_deps(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Bulk read: returns a {ueid: [deps...]} map for every row in tasks."""
    cur = conn.execute("SELECT ueid, deps FROM tasks")
    out: dict[str, list[str]] = {}
    for ueid, deps_json in cur.fetchall():
        if not ueid:
            continue
        out[str(ueid)] = _safe_json_list(deps_json)
    return out


def detect_cycle(
    start_ueid: str,
    target_ueid: str,
    db_path: Path | None = None,
) -> list[str] | None:
    """Detect whether adding edge start->target creates a cycle.

    Convention: ``start_ueid`` is blocked-by ``target_ueid`` (i.e. start's
    deps list will gain ``target_ueid``). An edge creates a cycle iff there
    is already a path from ``target_ueid`` forward (along deps edges) to
    ``start_ueid`` — the candidate edge then closes the loop.

    Returns:
        None if no cycle (safe to add the edge).
        List of UEIDs forming the cycle, e.g. [start, ..., start],
        if the edge would create a cycle.

    Algorithm: iterative DFS from target_ueid along existing `deps` edges.
    We flag a cycle when the DFS reaches start_ueid. Path is reconstructed
    from the parent map.

    Complexity: O(V + E) over the dep graph (one DFS, no recursive descent).
    """
    if start_ueid == target_ueid:
        return [start_ueid, start_ueid]

    db = db_path or _resolve_db()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        conn.executescript(_SCHEMA_DDL)
        _migrate_add_deps_column(conn)
        graph = _read_all_deps(conn)
    finally:
        conn.close()

    # Iterative DFS from target_ueid. We don't need to inject the candidate
    # edge — the cycle exists iff target_ueid can reach start_ueid via the
    # EXISTING edges (the candidate edge would close the loop).
    visited: set[str] = set()
    parent: dict[str, str | None] = {target_ueid: None}
    stack: list[tuple[str, list[str]]] = [
        (target_ueid, list(graph.get(target_ueid, [])))
    ]
    visited.add(target_ueid)

    cycle: list[str] | None = None
    while stack:
        node, neighbours = stack[-1]
        if not neighbours:
            stack.pop()
            continue
        nxt = neighbours.pop()
        if nxt in visited:
            continue
        visited.add(nxt)
        parent[nxt] = node
        if nxt == start_ueid:
            # Reconstruct path from target_ueid (DFS root) to start_ueid
            # by walking back through the parent map. The cycle is the
            # existing target->...->start path closed by the candidate
            # start->target edge.
            cycle = []
            cur: str | None = nxt
            while cur is not None:
                cycle.append(cur)
                cur = parent.get(cur)
            # cycle is [start, ..., target]; reverse to [target, ..., start],
            # then close with target at the end to form the loop.
            cycle.reverse()
            # Close the loop: candidate edge goes start->target, so the
            # final cycle reads target -> ... -> start -> target.
            cycle.append(target_ueid)
            break
        stack.append((nxt, list(graph.get(nxt, []))))

    return cycle


def _append_audit_log(ueid: str, action: str, details: dict) -> None:
    """Append a single line to the dep audit log (append-only file).

    Path: ``<data>/taskdog/.dep_audit.log``. Lines are pipe-separated:
        ISO8601|ueid|action|json_details
    """
    try:
        ts = datetime.now(timezone.utc).isoformat()
        line = f"{ts}|{ueid}|{action}|{json.dumps(details, sort_keys=True)}\n"
        db = _resolve_db()
        db.parent.mkdir(parents=True, exist_ok=True)
        with (db.parent / ".dep_audit.log").open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass  # best-effort audit


def add_dep(
    start_ueid: str,
    target_ueid: str,
    db_path: Path | None = None,
) -> None:
    """Add edge start->target (start blocked-by target).

    Raises:
        ValueError: invalid UEID format.
        SelfLoopError: start == target.
        CycleDetected: edge would create a cycle.
        LookupError: start_ueid row not found.
    """
    if not _is_valid_ueid(start_ueid):
        raise ValueError(f"invalid UEID: {start_ueid!r}")
    if not _is_valid_ueid(target_ueid):
        raise ValueError(f"invalid UEID: {target_ueid!r}")
    if start_ueid == target_ueid:
        raise SelfLoopError(start_ueid)

    cycle = detect_cycle(start_ueid, target_ueid, db_path=db_path)
    if cycle is not None:
        raise CycleDetected(cycle)

    db = db_path or _resolve_db()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        conn.executescript(_SCHEMA_DDL)
        _migrate_add_deps_column(conn)
        cur = conn.execute("SELECT 1 FROM tasks WHERE ueid=?", (start_ueid,))
        if cur.fetchone() is None:
            raise LookupError(
                f"add_dep target ueid={start_ueid!r} not found in taskdog"
            )
        cur = conn.execute("SELECT 1 FROM tasks WHERE ueid=?", (target_ueid,))
        if cur.fetchone() is None:
            raise LookupError(
                f"add_dep dependency ueid={target_ueid!r} not found in taskdog"
            )
        current = _read_deps_for(conn, start_ueid)
        if target_ueid in current:
            return  # idempotent: already present
        new_deps = current + [target_ueid]
        conn.execute(
            "UPDATE tasks SET deps=? WHERE ueid=?",
            (json.dumps(new_deps), start_ueid),
        )
        conn.commit()
    finally:
        conn.close()
    _append_audit_log(
        start_ueid,
        "add_dep",
        {"target": target_ueid},
    )


def remove_dep(
    start_ueid: str,
    target_ueid: str,
    db_path: Path | None = None,
) -> bool:
    """Remove edge start->target. Returns True if removed, False if absent."""
    if not _is_valid_ueid(start_ueid):
        raise ValueError(f"invalid UEID: {start_ueid!r}")
    if not _is_valid_ueid(target_ueid):
        raise ValueError(f"invalid UEID: {target_ueid!r}")

    db = db_path or _resolve_db()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        conn.executescript(_SCHEMA_DDL)
        _migrate_add_deps_column(conn)
        current = _read_deps_for(conn, start_ueid)
        if target_ueid not in current:
            return False
        new_deps = [d for d in current if d != target_ueid]
        conn.execute(
            "UPDATE tasks SET deps=? WHERE ueid=?",
            (json.dumps(new_deps), start_ueid),
        )
        conn.commit()
    finally:
        conn.close()
    _append_audit_log(
        start_ueid,
        "remove_dep",
        {"target": target_ueid},
    )
    return True


def get_deps(
    ueid: str,
    db_path: Path | None = None,
) -> dict[str, list[str]]:
    """Return deps in both directions: {"blocked_by": [...], "blocks": [...]}.

    ``blocked_by`` = upstream tasks (deps column).
    ``blocks`` = downstream tasks (rows whose deps contain this ueid).
    """
    if not _is_valid_ueid(ueid):
        raise ValueError(f"invalid UEID: {ueid!r}")
    db = db_path or _resolve_db()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        conn.executescript(_SCHEMA_DDL)
        _migrate_add_deps_column(conn)
        blocked_by = _read_deps_for(conn, ueid)
        cur = conn.execute("SELECT ueid, deps FROM tasks")
        blocks: list[str] = []
        for other_ueid, deps_json in cur.fetchall():
            if not other_ueid or other_ueid == ueid:
                continue
            parsed = _safe_json_list(deps_json)
            if ueid in parsed:
                blocks.append(str(other_ueid))
        return {"blocked_by": blocked_by, "blocks": blocks}
    finally:
        conn.close()


def list_blocked(
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return all tasks with one or more unmet deps.

    A task is "blocked" if its status is not in (done, cancelled) AND it
    has at least one dep that is also not in (done, cancelled). The output
    rows include `ueid`, `name`, `status`, `unmet_deps` (list of UEIDs).
    """
    db = db_path or _resolve_db()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        conn.executescript(_SCHEMA_DDL)
        _migrate_add_deps_column(conn)
        cur = conn.execute("SELECT ueid, name, status, deps FROM tasks")
        blocked: list[dict[str, Any]] = []
        status_map: dict[str, str | None] = {}
        deps_map: dict[str, list[str]] = {}
        names_map: dict[str, str | None] = {}
        for ueid_, name_, status_, deps_json in cur.fetchall():
            if not ueid_:
                continue
            suid = str(ueid_)
            status_map[suid] = status_
            names_map[suid] = name_
            deps_map[suid] = _safe_json_list(deps_json)

        for ueid_, deps_ in deps_map.items():
            if not deps_:
                continue
            if status_map.get(ueid_) in ("done", "cancelled"):
                continue
            unmet = [
                d for d in deps_
                if status_map.get(d) not in ("done", "cancelled")
            ]
            if not unmet:
                continue
            blocked.append({
                "ueid": ueid_,
                "name": names_map.get(ueid_),
                "status": status_map.get(ueid_),
                "unmet_deps": unmet,
            })
        blocked.sort(key=lambda r: r["ueid"])
        return blocked
    finally:
        conn.close()