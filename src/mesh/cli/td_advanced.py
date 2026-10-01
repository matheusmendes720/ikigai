"""M166 — advanced td subcommands (parity with upstream taskdog).

Seven subcommands target lifecycle + portability + reporting needs the
canonical ``taskdog_cli`` doesn't yet cover:

    rm <ueid>             — soft-delete (status='deleted', preserves audit_log)
    restore <ueid>        — undelete (status='deleted' → 'planned')
    audit [ueid]          — show audit_log (all tasks if no ueid)
    db backup [path]      — SQLite hot backup via sqlite3.Connection.backup()
    db restore <path>     — restore from backup (requires --yes)
    export <fmt>          — export tasks as json|csv|md (default = json)
    stats                 — completion rate, avg time, by-tag breakdown

Hard-deletion is NEVER performed. The canonical `tasks` row + `audit_log`
rows survive a `rm`; only the row's `status` flips to 'deleted'.

Output modes:
    Default (TTY): aligned ASCII tables for audit/export/stats; key:value for
    mutations.
    Default (pipe/script): JSON.
    --json: force JSON output even on a TTY.
    --human: force human-readable output even when piped.

Wire-in: imported by ``src/mesh/taskdog_cli.py`` and registered via
``register_advanced_subparser`` + ``run_advanced_command``.

Usage:
    python -m src.mesh.taskdog_cli rm ikigai:task:abc:1:2
    python -m src.mesh.taskdog_cli restore ikigai:task:abc:1:2
    python -m src.mesh.taskdog_cli audit
    python -m src.mesh.taskdog_cli audit ikigai:task:abc:1:2 --json
    python -m src.mesh.taskdog_cli db backup /tmp/tasks.bak.db
    python -m src.mesh.taskdog_cli db restore /tmp/tasks.bak.db --yes
    python -m src.mesh.taskdog_cli export json
    python -m src.mesh.taskdog_cli export csv --out /tmp/tasks.csv
    python -m src.mesh.taskdog_cli stats
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.mesh.adapters import taskdog as taskdog_mod


# ----------------------------------------------------------------------
# Inlined helpers — mirrors of small functions in taskdog_cli.py. Kept
# local to break what would otherwise be a circular import
# (taskdog_cli imports this module for its advanced subcommands).
# ----------------------------------------------------------------------

def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _render_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print headers + rows as an aligned ASCII table."""
    headers = [h.upper() for h in headers]
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def fmt_row(cells: list[str]) -> str:
        return "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells))

    print(fmt_row(headers), flush=True)
    if rows:
        print("  ".join("-" * w for w in widths), flush=True)
        for row in rows:
            print(fmt_row(row), flush=True)


def _wants_human(args: argparse.Namespace) -> bool:
    """Resolve output mode: --json wins, else --human wins, else TTY default."""
    if getattr(args, "json", False):
        return False
    if getattr(args, "human", False):
        return True
    return sys.stdout.isatty()


def _add_output_flags(p: argparse.ArgumentParser) -> None:
    """Attach --json / --human (mutually exclusive) to a subparser."""
    grp = p.add_mutually_exclusive_group()
    grp.add_argument(
        "--json",
        action="store_true",
        help="force JSON output (default when piped)",
    )
    grp.add_argument(
        "--human",
        action="store_true",
        help="force human-readable output (default when on a TTY)",
    )


def _add_db_path(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--db-path",
        type=str,
        default=str(taskdog_mod.TASKDOG_DB),
        help=f"path to taskdog SQLite DB (default: {taskdog_mod.TASKDOG_DB})",
    )


def _audit_db_path() -> Path:
    """Return the SQLite path used for both tasks and audit_log.

    Mirrors ``src.mesh.taskdog_cli._audit_db_path`` so the audit_log rows
    produced by ``rm`` / ``restore`` / ``note add`` share the same DB.
    Tests override TASKDOG_DB via monkeypatch (same pattern as note).
    """
    return taskdog_mod.TASKDOG_DB


def _ensure_audit_log_table(conn: "sqlite3.Connection") -> None:
    """Create the audit_log table on first use.

    Schema mirrors ``src.mesh.taskdog_cli._ensure_audit_log_table`` so
    notes / rm / restore / audit_log all share one schema. Idempotent.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ueid TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL DEFAULT 'note',
            actor TEXT NOT NULL DEFAULT 'cli',
            text TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_audit_log_ueid ON audit_log(ueid);
        CREATE INDEX IF NOT EXISTS idx_audit_log_ueid_action
            ON audit_log(ueid, action);
        """
    )


# ----------------------------------------------------------------------
# Output-mode helpers
# ----------------------------------------------------------------------

# Soft-delete flips status to this value (rows stay queryable for restore).
DELETED_STATUS = "deleted"

# Known non-deleted statuses for stats; mirrors taskdog_cli._KNOWN_STATUSES
# but excludes the 'deleted' state so completion-rate math ignores soft-deletes.
_LIVE_STATUSES = ("planned", "in_progress", "done", "cancelled")


def _apply_db_override(db_path_str: str) -> None:
    """Mutate module-level TASKDOG_DB to honor --db-path override."""
    if str(taskdog_mod.TASKDOG_DB) != db_path_str:
        taskdog_mod.TASKDOG_DB = Path(db_path_str)


def _emit(args: argparse.Namespace, payload: dict, *, human_text: str | None = None) -> None:
    """Render payload as JSON or one-line human text."""
    if _wants_human(args):
        if human_text is not None:
            print(human_text, flush=True)
        else:
            print(json.dumps(payload, default=str, sort_keys=True), flush=True)
        return
    print(json.dumps(payload, default=str, sort_keys=True), flush=True)


# ----------------------------------------------------------------------
# Audit log helpers (M166: 'soft_delete' / 'restore' actions live here)
# ----------------------------------------------------------------------

def _append_audit_row(
    conn: sqlite3.Connection,
    ueid: str,
    action: str,
    text: str = "",
    actor: str = "cli",
) -> int:
    """Insert one audit_log row. Caller commits."""
    ts = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO audit_log (ueid, timestamp, action, actor, text) "
        "VALUES (?, ?, ?, ?, ?)",
        (ueid, ts, action, actor, text),
    )
    return int(cur.lastrowid)


def _read_audit_rows(
    conn: sqlite3.Connection,
    ueid: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Read audit_log rows. ueid=None → all rows (global audit view)."""
    if ueid is None:
        cur = conn.execute(
            "SELECT id, ueid, timestamp, action, actor, text "
            "FROM audit_log ORDER BY id DESC"
        )
    else:
        cur = conn.execute(
            "SELECT id, ueid, timestamp, action, actor, text "
            "FROM audit_log WHERE ueid=? ORDER BY id DESC",
            (ueid,),
        )
    rows = [
        {
            "id": r[0],
            "ueid": r[1],
            "timestamp": r[2],
            "action": r[3],
            "actor": r[4],
            "text": r[5],
        }
        for r in cur.fetchall()
    ]
    if limit is not None:
        rows = rows[:limit]
    return rows


# ----------------------------------------------------------------------
# Soft-delete + restore (NEVER hard delete)
# ----------------------------------------------------------------------

def cmd_rm(args: argparse.Namespace) -> int:
    """`td rm <ueid>` — soft-delete. Sets status='deleted', writes audit."""
    _apply_db_override(args.db_path)
    db_path = _audit_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        taskdog_mod._ensure_tasks_table(conn)
        _ensure_audit_log_table(conn)
        cur = conn.execute("SELECT status FROM tasks WHERE ueid=?", (args.ueid,))
        row = cur.fetchone()
        if row is None:
            payload = {"error": "ueid_not_found", "ueid": args.ueid}
            print(json.dumps(payload), file=sys.stderr, flush=True)
            return 1
        prev_status = row[0] or "planned"
        if prev_status == DELETED_STATUS:
            # Idempotent: already deleted — no audit entry, no status flip.
            payload = {
                "ok": True,
                "action": "rm",
                "ueid": args.ueid,
                "status": DELETED_STATUS,
                "idempotent": True,
            }
            if _wants_human(args):
                print(
                    f"rm: {args.ueid} already {DELETED_STATUS} (no-op)",
                    flush=True,
                )
            else:
                print(json.dumps(payload), flush=True)
            return 0
        # Flip status, write audit row, commit.
        conn.execute(
            "UPDATE tasks SET status=? WHERE ueid=?",
            (DELETED_STATUS, args.ueid),
        )
        audit_id = _append_audit_row(
            conn, args.ueid, "soft_delete",
            text=f"status: {prev_status} -> {DELETED_STATUS}",
        )
        conn.commit()
    finally:
        conn.close()
    payload = {
        "ok": True,
        "action": "rm",
        "ueid": args.ueid,
        "previous_status": prev_status,
        "status": DELETED_STATUS,
        "audit_id": audit_id,
    }
    if _wants_human(args):
        print(
            f"rm: {args.ueid} {prev_status} -> {DELETED_STATUS} "
            f"(audit_id={audit_id})",
            flush=True,
        )
    else:
        print(json.dumps(payload), flush=True)
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    """`td restore <ueid>` — undelete. Sets status='deleted' → 'planned'."""
    _apply_db_override(args.db_path)
    db_path = _audit_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        taskdog_mod._ensure_tasks_table(conn)
        _ensure_audit_log_table(conn)
        cur = conn.execute("SELECT status FROM tasks WHERE ueid=?", (args.ueid,))
        row = cur.fetchone()
        if row is None:
            payload = {"error": "ueid_not_found", "ueid": args.ueid}
            print(json.dumps(payload), file=sys.stderr, flush=True)
            return 1
        prev_status = row[0]
        if prev_status != DELETED_STATUS:
            payload = {
                "ok": True,
                "action": "restore",
                "ueid": args.ueid,
                "status": prev_status,
                "idempotent": True,
                "note": "row was not soft-deleted; no-op",
            }
            if _wants_human(args):
                print(
                    f"restore: {args.ueid} status={prev_status} "
                    "(no-op, not deleted)",
                    flush=True,
                )
            else:
                print(json.dumps(payload), flush=True)
            return 0
        # Restore → 'planned'. Writes an audit row so the roundtrip is
        # fully traceable.
        conn.execute(
            "UPDATE tasks SET status='planned' WHERE ueid=?",
            (args.ueid,),
        )
        audit_id = _append_audit_row(
            conn, args.ueid, "restore",
            text=f"status: {DELETED_STATUS} -> planned",
        )
        conn.commit()
    finally:
        conn.close()
    payload = {
        "ok": True,
        "action": "restore",
        "ueid": args.ueid,
        "previous_status": DELETED_STATUS,
        "status": "planned",
        "audit_id": audit_id,
    }
    if _wants_human(args):
        print(
            f"restore: {args.ueid} {DELETED_STATUS} -> planned "
            f"(audit_id={audit_id})",
            flush=True,
        )
    else:
        print(json.dumps(payload), flush=True)
    return 0


# ----------------------------------------------------------------------
# Audit log viewer
# ----------------------------------------------------------------------

def cmd_audit(args: argparse.Namespace) -> int:
    """`td audit [ueid]` — list audit_log entries (most-recent first)."""
    _apply_db_override(args.db_path)
    db_path = _audit_db_path()
    if not db_path.exists():
        if _wants_human(args):
            print("(no audit log — database does not exist yet)", flush=True)
        else:
            print(json.dumps({"audit": [], "count": 0}), flush=True)
        return 0
    conn = sqlite3.connect(db_path)
    try:
        _ensure_audit_log_table(conn)
        rows = _read_audit_rows(conn, ueid=args.ueid)
    finally:
        conn.close()
    payload = {
        "ueid": args.ueid,
        "audit": rows,
        "count": len(rows),
    }
    if _wants_human(args):
        if not rows:
            scope = f" for ueid {args.ueid}" if args.ueid else ""
            print(f"(no audit rows{scope})", flush=True)
            return 0
        print(
            f"audit: {len(rows)} row(s)"
            + (f" for ueid={args.ueid}" if args.ueid else ""),
            flush=True,
        )
        print("-" * 80, flush=True)
        _render_table(
            ["id", "timestamp", "ueid", "action", "actor", "text"],
            [
                [
                    str(r["id"]),
                    str(r["timestamp"]),
                    _truncate(str(r["ueid"] or ""), 36),
                    str(r["action"] or ""),
                    str(r["actor"] or ""),
                    _truncate(str(r["text"] or ""), 40),
                ]
                for r in rows
            ],
        )
    else:
        print(json.dumps(payload), flush=True)
    return 0


# ----------------------------------------------------------------------
# SQLite hot backup + restore
# ----------------------------------------------------------------------

def _default_backup_path() -> Path:
    """<data>/taskdog/.backup-YYYYMMDD-HHMMSS.db (UTC)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return taskdog_mod.TASKDOG_DB.parent / f".backup-{ts}.db"


def cmd_db_backup(args: argparse.Namespace) -> int:
    """`td db backup [path]` — SQLite hot backup via Connection.backup().

    Uses sqlite3.Connection.backup() so the snapshot is consistent even
    while the live DB is being written. Default path:
    <data>/taskdog/.backup-YYYYMMDD-HHMMSS.db (UTC).
    """
    _apply_db_override(args.db_path)
    src_path = _audit_db_path()
    if not src_path.exists():
        payload = {"error": "db_not_found", "path": str(src_path)}
        print(json.dumps(payload), file=sys.stderr, flush=True)
        return 1
    out_path = Path(args.path) if args.path else _default_backup_path()
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    src_conn = sqlite3.connect(src_path)
    dst_conn = sqlite3.connect(out_path)
    try:
        # Connection.backup(target) is the canonical atomic snapshot API
        # in sqlite3 — safer than copying the file while live writers are
        # active.
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()
    size_bytes = out_path.stat().st_size if out_path.exists() else 0
    payload = {
        "ok": True,
        "action": "db_backup",
        "source": str(src_path),
        "destination": str(out_path),
        "size_bytes": size_bytes,
    }
    if _wants_human(args):
        print(
            f"db backup: {src_path} -> {out_path} "
            f"({size_bytes} bytes)",
            flush=True,
        )
    else:
        print(json.dumps(payload), flush=True)
    return 0


def cmd_db_restore(args: argparse.Namespace) -> int:
    """`td db restore <path> --yes` — destructive restore from a backup file.

    Requires --yes (positive confirmation). The live DB at TASKDOG_DB is
    REPLACED atomically: write backup -> <data>/taskdog/.restore-tmp.db,
    swap paths via os.replace() (atomic on POSIX + Windows). The previous
    live DB is preserved as <data>/taskdog/.pre-restore-<db>.bak so a
    failed restore can be rolled back manually.
    """
    if not args.yes:
        payload = {
            "error": "confirmation_required",
            "detail": "db restore is destructive; pass --yes to confirm",
        }
        print(json.dumps(payload), file=sys.stderr, flush=True)
        return 2

    src_path = Path(args.path).resolve()
    if not src_path.exists():
        payload = {"error": "backup_not_found", "path": str(src_path)}
        print(json.dumps(payload), file=sys.stderr, flush=True)
        return 1

    _apply_db_override(args.db_path)
    live_path = _audit_db_path()
    live_dir = live_path.parent
    live_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: write the backup to a tmp path inside the live DB directory
    # (same filesystem → os.replace is atomic).
    tmp_path = live_dir / ".restore-tmp.db"
    pre_restore = live_dir / ".pre-restore.db.bak"

    src_conn = sqlite3.connect(src_path)
    try:
        dst_conn = sqlite3.connect(tmp_path)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()

    # Stage 2: move the existing live DB aside (if it exists) so we can
    # restore on failure.
    import os
    pre_restore_existed = live_path.exists()
    if pre_restore_existed:
        # Remove an old pre-restore backup from a previous run so os.replace
        # doesn't fail on Windows.
        if pre_restore.exists():
            pre_restore.unlink()
        os.replace(live_path, pre_restore)
    os.replace(tmp_path, live_path)

    payload = {
        "ok": True,
        "action": "db_restore",
        "source": str(src_path),
        "destination": str(live_path),
        "previous_db_backup": str(pre_restore) if pre_restore_existed else None,
    }
    if _wants_human(args):
        print(
            f"db restore: {src_path} -> {live_path} "
            + (
                f"(previous preserved at {pre_restore})"
                if pre_restore_existed
                else "(no previous db)"
            ),
            flush=True,
        )
    else:
        print(json.dumps(payload), flush=True)
    return 0


# ----------------------------------------------------------------------
# Export (json|csv|md)
# ----------------------------------------------------------------------

# Map task fields we emit on export. Mirrors the columns the
# TaskdogAdapter normalizes for reads.
_EXPORT_FIELDS = (
    "ueid", "name", "status", "priority", "planned_start",
    "planned_end", "deadline", "created_at", "started_at",
    "completed_at", "priority_label", "tags", "deps",
)


def _fetch_all_tasks() -> list[dict[str, Any]]:
    """Read all task rows via the adapter (HTTP-bridge + SQLite fallback)."""
    adapter = taskdog_mod.TaskdogAdapter()
    return adapter.list_all()


def _export_json(tasks: list[dict]) -> str:
    return json.dumps(
        {"tasks": tasks, "count": len(tasks)},
        default=str, indent=2, sort_keys=True,
    )


def _export_csv(tasks: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_EXPORT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for t in tasks:
        row = dict(t)
        # tags + deps come back as lists; serialise to a JSON string so the
        # CSV cell stays one row (CSV with embedded newlines is hostile).
        for key in ("tags", "deps"):
            if isinstance(row.get(key), list):
                row[key] = json.dumps(row[key], sort_keys=True)
        writer.writerow(row)
    return buf.getvalue()


def _export_markdown(tasks: list[dict]) -> str:
    """Render a Markdown table; one row per task."""
    headers = ["ueid", "name", "status", "priority", "deadline", "tags"]
    lines: list[str] = []
    lines.append("# taskdog export")
    lines.append("")
    lines.append(f"Total tasks: **{len(tasks)}**")
    lines.append("")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for t in tasks:
        tags = t.get("tags") or []
        if isinstance(tags, list):
            tags_s = ", ".join(str(x) for x in tags)
        else:
            tags_s = ""
        lines.append(
            "| "
            + " | ".join(
                [
                    str(t.get("ueid") or ""),
                    str(t.get("name") or "").replace("|", "\\|"),
                    str(t.get("status") or ""),
                    str(t.get("priority") or ""),
                    str(t.get("deadline") or ""),
                    tags_s.replace("|", "\\|"),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def cmd_export(args: argparse.Namespace) -> int:
    """`td export <fmt>` — emit all tasks as json|csv|md."""
    fmt = args.fmt.lower()
    if fmt not in ("json", "csv", "md"):
        payload = {
            "error": "invalid_format",
            "format": args.fmt,
            "supported": ["json", "csv", "md"],
        }
        print(json.dumps(payload), file=sys.stderr, flush=True)
        return 2
    _apply_db_override(args.db_path)
    tasks = _fetch_all_tasks()
    if fmt == "json":
        body = _export_json(tasks)
    elif fmt == "csv":
        body = _export_csv(tasks)
    else:
        body = _export_markdown(tasks)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body, encoding="utf-8")
        payload = {
            "ok": True,
            "action": "export",
            "format": fmt,
            "count": len(tasks),
            "path": str(out_path),
        }
        if _wants_human(args):
            print(
                f"export: {len(tasks)} task(s) -> {out_path} ({fmt})",
                flush=True,
            )
        else:
            print(json.dumps(payload), flush=True)
        return 0
    # stdout
    sys.stdout.write(body)
    sys.stdout.flush()
    return 0


# ----------------------------------------------------------------------
# Stats (read-only)
# ----------------------------------------------------------------------

def _compute_stats(tasks: list[dict]) -> dict:
    """Aggregate counts + completion metrics + per-tag breakdown.

    Performance: single pass over the task list. For 10k tasks this stays
    well under 100ms on commodity hardware (Python dict updates only).
    """
    total = len(tasks)
    # status counts (live + deleted bucket, separately)
    status_counts: dict[str, int] = {s: 0 for s in _LIVE_STATUSES}
    status_counts[DELETED_STATUS] = 0
    priority_counts: dict[int, int] = {1: 0, 2: 0, 3: 0}
    tag_counts: dict[str, int] = {}
    durations: list[float] = []  # hours, completed only

    for t in tasks:
        s = t.get("status") or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
        p = t.get("priority")
        if p in priority_counts:
            priority_counts[p] += 1
        tags = t.get("tags") or []
        if isinstance(tags, list):
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        # duration: completed_at - started_at when both present
        started = t.get("started_at")
        completed = t.get("completed_at")
        if started and completed:
            try:
                t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(completed.replace("Z", "+00:00"))
                delta = (t1 - t0).total_seconds() / 3600.0
                if delta >= 0:
                    durations.append(delta)
            except (ValueError, TypeError):
                # Malformed timestamps are silently ignored — stats is
                # best-effort, not a contract enforcer.
                pass

    live_total = sum(status_counts.get(s, 0) for s in _LIVE_STATUSES)
    done_count = status_counts.get("done", 0)
    completion_rate = (
        (done_count / live_total) if live_total > 0 else 0.0
    )
    avg_duration_h = (
        sum(durations) / len(durations) if durations else None
    )

    return {
        "total": total,
        "live_total": live_total,
        "deleted_total": status_counts.get(DELETED_STATUS, 0),
        "by_status": status_counts,
        "by_priority": priority_counts,
        "by_tag": dict(sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "completion_rate": round(completion_rate, 4),
        "completed_with_duration": len(durations),
        "avg_duration_hours": (
            round(avg_duration_h, 2) if avg_duration_h is not None else None
        ),
    }


def cmd_stats(args: argparse.Namespace) -> int:
    """`td stats` — completion rate, avg time, by-tag breakdown."""
    _apply_db_override(args.db_path)
    tasks = _fetch_all_tasks()
    stats = _compute_stats(tasks)
    if _wants_human(args):
        print(f"db_path: {taskdog_mod.TASKDOG_DB}", flush=True)
        print(
            f"total: {stats['total']}   live: {stats['live_total']}   "
            f"deleted: {stats['deleted_total']}",
            flush=True,
        )
        print(f"completion_rate: {stats['completion_rate']:.2%}", flush=True)
        if stats["avg_duration_hours"] is not None:
            print(
                f"avg_duration: {stats['avg_duration_hours']} h "
                f"(over {stats['completed_with_duration']} completed)",
                flush=True,
            )
        else:
            print("avg_duration: n/a", flush=True)
        _render_table(
            ["status", "count"],
            [[s, str(stats["by_status"].get(s, 0))] for s in _LIVE_STATUSES],
        )
        _render_table(
            ["priority", "count"],
            [[str(p), str(stats["by_priority"].get(p, 0))]
             for p in (1, 2, 3)],
        )
        if stats["by_tag"]:
            print("--- by_tag ---", flush=True)
            _render_table(
                ["tag", "count"],
                [[tag, str(c)] for tag, c in stats["by_tag"].items()],
            )
        else:
            print("(no tags)", flush=True)
    else:
        print(json.dumps(stats), flush=True)
    return 0


# ----------------------------------------------------------------------
# Parser wiring — called from taskdog_cli.main()
# ----------------------------------------------------------------------

def register_advanced_subparser(
    sub: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    """Attach 7 subparsers (rm / restore / audit / db / export / stats) and
    return the parents so the caller can chain additional subcommands."""
    # rm / restore / audit share the same DB path override
    rm_p = sub.add_parser(
        "rm",
        help="soft-delete (status='deleted', audit_log entry preserved)",
    )
    rm_p.add_argument("ueid", help="UEID to soft-delete")
    _add_db_path(rm_p)
    _add_output_flags(rm_p)

    restore_p = sub.add_parser(
        "restore",
        help="undelete: status='deleted' -> 'planned'",
    )
    restore_p.add_argument("ueid", help="UEID to restore")
    _add_db_path(restore_p)
    _add_output_flags(restore_p)

    audit_p = sub.add_parser(
        "audit",
        help="list audit_log entries (most-recent first)",
    )
    audit_p.add_argument(
        "ueid",
        nargs="?",
        default=None,
        help="filter to one UEID (default: all rows)",
    )
    audit_p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="cap rows shown (default: unlimited)",
    )
    _add_db_path(audit_p)
    _add_output_flags(audit_p)

    # db sub-app: backup / restore
    db_p = sub.add_parser(
        "db",
        help="SQLite hot backup + restore (M166)",
    )
    db_sub = db_p.add_subparsers(dest="db_command", required=True)
    db_backup_p = db_sub.add_parser(
        "backup",
        help="atomic snapshot via sqlite3.Connection.backup()",
    )
    db_backup_p.add_argument(
        "path",
        nargs="?",
        default=None,
        help="destination path (default: <data>/taskdog/.backup-<ts>.db)",
    )
    _add_db_path(db_backup_p)
    _add_output_flags(db_backup_p)

    db_restore_p = db_sub.add_parser(
        "restore",
        help="restore from backup file (REQUIRES --yes)",
    )
    db_restore_p.add_argument(
        "path",
        help="source backup path to restore from",
    )
    db_restore_p.add_argument(
        "--yes",
        action="store_true",
        help="confirm destructive restore (required)",
    )
    _add_db_path(db_restore_p)
    _add_output_flags(db_restore_p)

    # export <fmt>
    export_p = sub.add_parser(
        "export",
        help="export tasks as json|csv|md (default: json)",
    )
    export_p.add_argument(
        "fmt",
        nargs="?",
        default="json",
        choices=["json", "csv", "md"],
        help="output format (default: json)",
    )
    export_p.add_argument(
        "--out",
        type=str,
        default=None,
        help="write to file path instead of stdout",
    )
    _add_db_path(export_p)

    # stats (read-only)
    stats_p = sub.add_parser(
        "stats",
        help="completion rate, avg duration, by-tag breakdown (read-only)",
    )
    _add_db_path(stats_p)
    _add_output_flags(stats_p)

    return sub  # caller only needs the action; the parsers are attached


def run_advanced_command(args: argparse.Namespace) -> int:
    """Dispatch a parsed `td {rm,restore,audit,db,export,stats}` command."""
    if args.command == "rm":
        return cmd_rm(args)
    if args.command == "restore":
        return cmd_restore(args)
    if args.command == "audit":
        return cmd_audit(args)
    if args.command == "db":
        if args.db_command == "backup":
            return cmd_db_backup(args)
        if args.db_command == "restore":
            return cmd_db_restore(args)
        print(f"unknown db command: {args.db_command}", file=sys.stderr)
        return 2
    if args.command == "export":
        return cmd_export(args)
    if args.command == "stats":
        return cmd_stats(args)
    print(f"unknown advanced command: {args.command}", file=sys.stderr)
    return 2


# Allow direct `python -m src.mesh.cli.td_advanced ...` invocation.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ikigai-td-advanced",
        description=(
            "Advanced td subcommands (M166): rm / restore / audit / "
            "db / export / stats."
        ),
    )
    register_advanced_subparser(parser.add_subparsers(dest="command", required=True))
    args = parser.parse_args(argv)
    return run_advanced_command(args)


if __name__ == "__main__":
    raise SystemExit(main())