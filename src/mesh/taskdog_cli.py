"""Read+write ops CLI for the TaskdogAdapter SQLite store.

The TaskdogAdapter is the only-connected MCP fork — it persists tasks
that flow through the mesh review queue. This CLI is the operator's
window into that store: list what we have, show details for a single
UEID. **Writes** go through the review queue (ADR-014): the CLI
enqueues a TaskChange; the worker validates + propagates to all
adapters.

Subcommands:
    list [--status STATUS] [--limit N] [--db-path PATH] [--human|--json]
        Show task slices (default: all, sorted by created_at DESC).
    status [--db-path PATH] [--human|--json]
        Show task counts by status + priority.
    show <ueid> [--db-path PATH] [--human|--json]
        Show the full slice for one task (or "not found").
    add --ueid UEID --title TITLE [--priority 1|2|3] [--due YYYY-MM-DD]
        Enqueue a CREATE TaskChange. Returns event_id.
    done <ueid>
        Enqueue a DONE TaskChange (idempotent).
    update <ueid> [--priority N] [--status X] [--due YYYY-MM-DD]
        Enqueue an UPDATE TaskChange with the provided fields.
    propagate
        Run the review queue worker once (consume → validate → propagate).

Output modes:
    Default (TTY): aligned ASCII table with column headers.
    Default (pipe/script): one JSON object per line.
    --human: force table output even when piped.
    --json: force JSON output even when on a TTY.

Usage:
    python -m src.mesh.taskdog_cli list
    python -m src.mesh.taskdog_cli list --status planned --limit 10
    python -m src.mesh.taskdog_cli show ikigai:task:abc:1:2
    python -m src.mesh.taskdog_cli add --ueid ikigai:task:abc:1:2 --title "Buy milk"
    python -m src.mesh.taskdog_cli done ikigai:task:abc:1:2
    python -m src.mesh.taskdog_cli update ikigai:task:abc:1:2 --priority 1
    python -m src.mesh.taskdog_cli propagate
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.contracts.task_change import TaskAction, TaskChange
from src.mesh import queue
from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.cli.td_advanced import (
    register_advanced_subparser,
    run_advanced_command,
)
from src.mesh.cli.td_gantt import (
    register_gantt_subparser,
    register_optimize_subparser,
    run_gantt_command,
    run_optimize_command,
)
from src.mesh.cli.td_tag import register_tag_subparser, run_tag_command


# --- Reflection hook ---------------------------------------------------------
# Every mutation appends a Decision to the reflection log so the agent can
# later review its own behaviour. Failures here MUST NOT block the mutation —
# the decision log is observational memory, not policy. We swallow exceptions
# and log to stderr to keep the CLI contract intact.
def _record_decision(action: str, ueid: str, context: dict | None = None) -> None:
    try:
        from src.agents.reflection.recursive import DecisionStore

        DecisionStore().append(action, ueid, context=context)
    except Exception as exc:  # noqa: BLE001 — observational, never block CLI
        print(
            f"warning: reflection log append failed: {exc}",
            file=sys.stderr,
        )


# Statuses we have seen in the taskdog store so far. Kept loose — the CLI
# surfaces whatever status the adapter returns, but argparse's --status
# choices need a closed list. New statuses can be added as the lifecycle
# expands; the CLI does not enforce a fixed enum on reads.
_KNOWN_STATUSES: tuple[str, ...] = ("planned", "in_progress", "done", "cancelled")

# Priority integers per the TaskdogAdapter.apply_change priority_map
# (high=1, medium=2, low=3). Listed descending so the table reads top-down.
_KNOWN_PRIORITIES: tuple[int, ...] = (1, 2, 3)

_MAX_NAME = 40
_MAX_UEID = 36  # one full 5-part UEID fits; truncate only if longer


def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _summarize(slice: dict) -> str:
    """One JSON line per task for `list` (JSON mode)."""
    return json.dumps(slice, default=str)


def _list_row(slice: dict) -> list[str]:
    """Compact cells for one task in human-readable table mode."""
    return [
        _truncate(str(slice.get("ueid") or ""), _MAX_UEID),
        _truncate(str(slice.get("name") or ""), _MAX_NAME),
        str(slice.get("status") or ""),
        str(slice.get("priority") or ""),
        str(slice.get("deadline") or ""),
    ]


def _render_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print headers + rows as an aligned ASCII table.

    Mirrors review_queue_cli._render_table (kept inline — CLI-to-CLI
    imports inside the same package are noisy).
    """
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


def _apply_db_override(db_path_str: str) -> None:
    """Mutate module-level TASKDOG_DB to honor --db-path (test + ops override).

    The adapter reads from the module-global TASKDOG_DB. The cleanest way
    to redirect it is to update the module attr before each call. This is
    process-local and intentional — production code defaults to the module
    constant; this helper only fires when --db-path differs from it.
    """
    if str(taskdog_mod.TASKDOG_DB) != db_path_str:
        taskdog_mod.TASKDOG_DB = Path(db_path_str)


def cmd_list(args: argparse.Namespace) -> int:
    _apply_db_override(args.db_path)
    adapter = TaskdogAdapter()
    tasks = adapter.list_all()

    if args.status is not None:
        tasks = [t for t in tasks if t.get("status") == args.status]

    # Newest first. created_at is an ISO date string — sorts lexicographically.
    tasks.sort(key=lambda t: t.get("created_at") or "", reverse=True)

    if args.limit is not None:
        tasks = tasks[: args.limit]

    if _wants_human(args):
        _render_table(
            ["ueid", "name", "status", "priority", "deadline"],
            [_list_row(t) for t in tasks],
        )
    else:
        for task in tasks:
            print(_summarize(task), flush=True)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _apply_db_override(args.db_path)
    adapter = TaskdogAdapter()
    tasks = adapter.list_all()

    # Initialize counts with zeros for all known statuses + priorities so
    # the table always renders the same shape even on empty/partial DBs.
    status_counts: dict[str, int] = {s: 0 for s in _KNOWN_STATUSES}
    priority_counts: dict[int, int] = {p: 0 for p in _KNOWN_PRIORITIES}
    for task in tasks:
        s = task.get("status")
        if s in status_counts:
            status_counts[s] += 1
        p = task.get("priority")
        if p in priority_counts:
            priority_counts[p] += 1

    if _wants_human(args):
        print(
            f"db_path: {taskdog_mod.TASKDOG_DB}    total: {len(tasks)}",
            flush=True,
        )
        _render_table(
            ["status", "count"], [[s, str(status_counts[s])] for s in _KNOWN_STATUSES]
        )
        _render_table(
            ["priority", "count"],
            [[str(p), str(priority_counts[p])] for p in _KNOWN_PRIORITIES],
        )
    else:
        print(f"db_path: {taskdog_mod.TASKDOG_DB}", flush=True)
        print(f"total: {len(tasks)}", flush=True)
        for status in _KNOWN_STATUSES:
            print(f"  {status}: {status_counts[status]}", flush=True)
        for priority in _KNOWN_PRIORITIES:
            print(f"  priority {priority}: {priority_counts[priority]}", flush=True)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    _apply_db_override(args.db_path)
    adapter = TaskdogAdapter()
    slice_ = adapter.read(args.ueid)
    if slice_ is None:
        print(f"ueid not found: {args.ueid}", file=sys.stderr)
        return 1

    if _wants_human(args):
        for key in (
            "ueid",
            "name",
            "status",
            "priority",
            "planned_start",
            "planned_end",
            "deadline",
            "created_at",
        ):
            print(f"{key + ':':15}{slice_.get(key) or ''}", flush=True)
    else:
        print(json.dumps(slice_, default=str, indent=2), flush=True)
    return 0


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
        help="force human-readable table output (default when on a TTY)",
    )


def _add_db_path(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--db-path",
        type=str,
        default=str(taskdog_mod.TASKDOG_DB),
        help=f"path to taskdog SQLite DB (default: {taskdog_mod.TASKDOG_DB})",
    )


# M151: UEID validation + helpers for the write path ---------------------------
# Mirrors the canonical regex in src/contracts/common.py so the CLI accepts the
# same UEID shapes as the rest of the project.
_UEID_REGEX = re.compile(
    r"^(?:"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
    r"|"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{4,64}"
    r"|"
    r"[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
    r")$"
)
_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_ueid(s: str) -> str:
    """argparse type= callback. Returns the UEID if valid, raises ArgumentTypeError."""
    if not _UEID_REGEX.match(s):
        raise argparse.ArgumentTypeError(
            f"invalid UEID format: {s!r} (expected <cluster>:<entity>:<id>:<id>:<id>)"
        )
    return s


def _validate_due(s: str) -> str:
    """argparse type= callback for YYYY-MM-DD."""
    if not _DATE_REGEX.match(s):
        raise argparse.ArgumentTypeError(
            f"invalid due date: {s!r} (expected YYYY-MM-DD)"
        )
    return s


def _validate_priority_str(s: str) -> int:
    """argparse type= callback. Returns int 1/2/3."""
    try:
        n = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"priority must be integer, got {s!r}")
    if n not in (1, 2, 3):
        raise argparse.ArgumentTypeError(f"priority must be 1/2/3, got {n}")
    return n


def _enqueue_change(ueid: str, action: TaskAction, fields: dict) -> str:
    """Build a TaskChange and enqueue it. Returns the event_id."""
    event = TaskChange(
        event_id=str(uuid.uuid4()),
        ueid=ueid,
        action=action,
        fields=fields,
        source_fork="cli",
        timestamp=datetime.now(timezone.utc),
        status="pending",
    )
    return queue.enqueue(event)


def cmd_add(args: argparse.Namespace) -> int:
    """CREATE via review queue."""
    # argparse has already validated --ueid / --priority / --due format.
    # We still check title emptiness here because that's a semantic check,
    # not a format check.
    if not args.title or not args.title.strip():
        print("--title is required and cannot be empty", file=sys.stderr)
        return 2
    fields: dict = {"title": args.title.strip()}
    if args.priority is not None:
        fields["priority"] = args.priority
    if args.due is not None:
        fields["due"] = args.due
    if args.description is not None:
        fields["description"] = args.description.strip()
    event_id = _enqueue_change(args.ueid, TaskAction.CREATE, fields)
    _record_decision("create", args.ueid, context={"title": fields.get("title", ""), "fields": fields})
    print(f"enqueued CREATE event {event_id} for ueid {args.ueid}", flush=True)
    print("Run `td propagate` to apply.", flush=True)
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    """DONE via review queue (idempotent — sets status='done')."""
    event_id = _enqueue_change(args.ueid, TaskAction.DONE, {})
    _record_decision("done", args.ueid, context={})
    print(f"enqueued DONE event {event_id} for ueid {args.ueid}", flush=True)
    print("Run `td propagate` to apply.", flush=True)
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """UPDATE via review queue (only the fields provided are changed)."""
    fields: dict = {}
    if args.priority is not None:
        fields["priority"] = args.priority
    if args.status is not None:
        if args.status not in _KNOWN_STATUSES:
            print(
                f"status must be one of {_KNOWN_STATUSES}, got {args.status!r}",
                file=sys.stderr,
            )
            return 2
        fields["status"] = args.status
    if args.due is not None:
        fields["due"] = args.due
    if args.title is not None:
        if not args.title.strip():
            print("--title cannot be empty", file=sys.stderr)
            return 2
        fields["title"] = args.title.strip()
    if not fields:
        print(
            "at least one of --priority/--status/--due/--title required",
            file=sys.stderr,
        )
        return 2
    event_id = _enqueue_change(args.ueid, TaskAction.UPDATE, fields)
    _record_decision("update", args.ueid, context={"fields": fields})
    print(f"enqueued UPDATE event {event_id} for ueid {args.ueid}", flush=True)
    print("Run `td propagate` to apply.", flush=True)
    return 0


def cmd_propagate(args: argparse.Namespace) -> int:
    """Run the review queue worker once.

    M151: this is a thin wrapper over review_queue_worker.run_once().
    Returns the RunResult summary so the operator can see counts.
    """
    # Lazy import to keep startup fast for read-only commands.
    from src.mesh.review_queue_worker import run_once
    from src.mesh.adapters.cli import CliAdapter
    from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

    result = run_once(
        adapters=[
            TaskdogAdapter(),
            CliAdapter(),
            SolverforgeCalendarAdapter(),
        ]
    )
    print(
        f"consumed={result.consumed} approved={result.approved} "
        f"partial={result.partial} rejected={result.rejected} "
        f"clarified={result.clarified}",
        flush=True,
    )
    return 0


# M164: td note subsystem --------------------------------------------
# Notes are immutable annotations attached to a task's audit trail. They
# are persisted as rows in the `audit_log` table (sharing the same SQLite
# DB as the canonical tasks table) so notes stay co-located with their
# task and benefit from the same atomic-write guarantees. The `action`
# column discriminates row types; for M164 the only emitted action is
# 'note', but the schema is open to future audit-event kinds (status
# change, propagation event, etc.) without breaking the read path.
#
# Constraints:
#   - text ≤ 1024 chars after sanitization (control chars stripped,
#     newlines kept)
#   - notes are append-only; there is no update/delete subcommand
#   - reads filter action='note' so other audit rows stay invisible to
#     `td note show`
#
# Output mode honours the global --json / --human flags; default is
# auto-detected from TTY (see _wants_human).
_MAX_NOTE_LEN = 1024


def _ensure_audit_log_table(conn: "sqlite3.Connection") -> None:
    """Create the audit_log table on first use.

    Schema:
        id         — autoincrement row id
        ueid       — task UEID (no FK so notes survive task deletes,
                     matches append-only semantics)
        timestamp  — ISO8601 UTC, naive datetime (matches _utc_now convention
                     in contracts/common.py)
        action     — discriminator; for M164 always 'note'
        actor      — emitter; for M164 always 'cli'
        text       — note body (sanitized, ≤ _MAX_NOTE_LEN)

    Idempotent: CREATE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.
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


def _sanitize_note_text(raw: str) -> str:
    """Strip control chars except newline, cap length.

    Strips ALL C0 control chars (0x00-0x1F) except \\n (0x0A) and \\t (0x09).
    """
    # Keep \n (0x0A) and \t (0x09); strip everything else in 0x00-0x1F + 0x7F.
    cleaned = "".join(
        ch for ch in raw
        if ch in ("\n", "\t") or (ord(ch) >= 0x20 and ord(ch) != 0x7F)
    )
    if len(cleaned) > _MAX_NOTE_LEN:
        raise ValueError(
            f"note text too long: {len(cleaned)} chars "
            f"(max {_MAX_NOTE_LEN} after sanitization)"
        )
    return cleaned


def _audit_db_path() -> Path:
    """Resolve the SQLite path used for both tasks and audit_log.

    The canonical DB is owned by ``src.mesh.adapters.taskdog.TASKDOG_DB``.
    We reuse it so notes and tasks share a single connection-friendly
    location; per-task isolation for tests comes from monkeypatching
    TASKDOG_DB before the CLI runs (same pattern as the rest of the
    subcommands).
    """
    return taskdog_mod.TASKDOG_DB


def cmd_note_add(args: argparse.Namespace) -> int:
    """Append a note row to audit_log for the given UEID.

    Validation:
        - UEID format checked by argparse (type=_validate_ueid)
        - text stripped of control chars, must be non-empty after stripping
        - text length ≤ _MAX_NOTE_LEN

    Output:
        human:  note added: id=N ueid=X chars=K
        json:   {"id": N, "ueid": "X", "action": "note", "chars": K}
    """
    text = _sanitize_note_text(args.text)
    if not text.strip():
        print("note text is empty after sanitization", file=sys.stderr)
        return 2

    db_path = _audit_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        _ensure_audit_log_table(conn)
        ts = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO audit_log (ueid, timestamp, action, actor, text) "
            "VALUES (?, ?, 'note', 'cli', ?)",
            (args.ueid, ts, text),
        )
        note_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()

    if _wants_human(args):
        print(
            f"note added: id={note_id} ueid={args.ueid} chars={len(text)}",
            flush=True,
        )
    else:
        print(
            json.dumps(
                {
                    "id": note_id,
                    "ueid": args.ueid,
                    "action": "note",
                    "chars": len(text),
                }
            ),
            flush=True,
        )
    return 0


def _list_audit_notes(ueid: str) -> list[dict]:
    """Read all `note` rows for a UEID from audit_log, ordered by id ASC.

    The `id ASC` ordering gives a stable chronological read even when two
    notes land in the same ISO-second (SQLite timestamp resolution).
    Returns a list of dicts with keys: id, timestamp, text.
    """
    db_path = _audit_db_path()
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    try:
        _ensure_audit_log_table(conn)
        cur = conn.execute(
            "SELECT id, timestamp, text FROM audit_log "
            "WHERE ueid=? AND action='note' ORDER BY id ASC",
            (ueid,),
        )
        return [
            {"id": row[0], "timestamp": row[1], "text": row[2]}
            for row in cur.fetchall()
        ]
    finally:
        conn.close()


def cmd_note_show(args: argparse.Namespace) -> int:
    """List notes attached to a task (audit_log filtered to action='note').

    Output:
        human:  aligned table of id / timestamp / text
        json:   one JSON object per line: {"id", "timestamp", "text"}
        empty:  "(no notes)" (TTY) / nothing (pipe)
    """
    notes = _list_audit_notes(args.ueid)

    if _wants_human(args):
        if not notes:
            print(f"(no notes for ueid {args.ueid})", flush=True)
            return 0
        rows = [
            [
                str(n["id"]),
                str(n["timestamp"]),
                _truncate(n["text"].replace("\n", " ⏎ "), 60),
            ]
            for n in notes
        ]
        _render_table(["id", "timestamp", "text"], rows)
    else:
        for n in notes:
            print(json.dumps(n), flush=True)
    return 0


# M153: Timeline + TUI dashboard --------------------------------------------
def _timeline_events(tasks: list[dict]) -> list[tuple[str, str, dict]]:
    """Build a sorted list of (timestamp, event_label, task) for timeline view.

    Each task contributes events for: created_at, deadline (if set),
    and completed_at (if status == 'done'). Sorted ascending by timestamp.
    Strings without an actual timestamp are filtered out.
    """
    events: list[tuple[str, str, dict]] = []
    for t in tasks:
        ueid = str(t.get("ueid") or "?")
        name = str(t.get("name") or "(no name)")
        created = t.get("created_at")
        if created:
            events.append((str(created), f"created   {ueid}  {name}", t))
        deadline = t.get("deadline")
        if deadline:
            events.append((str(deadline), f"DUE       {ueid}  {name}", t))
        if t.get("status") == "done":
            # We don't store completed_at separately; fall back to created_at
            # so the event still appears, marked clearly.
            events.append(
                (
                    str(created) if created else "9999",
                    f"completed {ueid}  {name}",
                    t,
                )
            )
    events.sort(key=lambda ev: ev[0])
    return events


def cmd_timeline(args: argparse.Namespace) -> int:
    """Print a chronological timeline of all task events.

    Each row is one event: created, deadline, or completed. Sorted ascending
    by timestamp. Tasks without any timestamp field are listed at the
    bottom with the sentinel "unknown" so they're not silently dropped.
    """
    _apply_db_override(args.db_path)
    adapter = TaskdogAdapter()
    tasks = adapter.list_all()
    events = _timeline_events(tasks)

    # Also surface tasks with NO timestamp at all, sorted last.
    missing_ts: list[tuple[str, str, dict]] = []
    for t in tasks:
        has_any = t.get("created_at") or t.get("deadline") or t.get("status") == "done"
        if not has_any:
            ueid = str(t.get("ueid") or "?")
            name = str(t.get("name") or "(no name)")
            missing_ts.append(("9999", f"no-ts     {ueid}  {name}", t))

    events.extend(missing_ts)

    if _wants_human(args):
        if not events:
            print("(no timeline events — store is empty)", flush=True)
            return 0
        print(f"timeline ({len(events)} events across {len(tasks)} tasks):", flush=True)
        print("-" * 60, flush=True)
        for ts, label, _t in events:
            print(f"{ts}  {label}", flush=True)
    else:
        for ts, label, t in events:
            print(
                json.dumps(
                    {"timestamp": ts, "event": label, "ueid": t.get("ueid")},
                    default=str,
                ),
                flush=True,
            )
    return 0


def cmd_tui(args: argparse.Namespace) -> int:
    """Live TUI dashboard using Rich (if available) or plain text fallback.

    Renders a one-shot view (no refresh loop yet — that's a follow-up).
    Layout:
        - Header: status counts (planned/in_progress/done/cancelled)
        - Priority table: tasks sorted by priority (high first), then deadline
        - Timeline summary: next 5 upcoming deadlines

    If Rich is installed, uses rich.layout.Layout with panels.
    Otherwise falls back to plain text sections.
    """
    _apply_db_override(args.db_path)
    adapter = TaskdogAdapter()
    tasks = adapter.list_all()

    # Counts by status
    counts = {s: 0 for s in _KNOWN_STATUSES}
    for t in tasks:
        s = t.get("status")
        if s in counts:
            counts[s] += 1

    # Sort tasks: priority asc (1 = high), then deadline asc, then created
    def sort_key(t: dict) -> tuple:
        pri = t.get("priority") or 99
        deadline = t.get("deadline") or "9999"
        created = t.get("created_at") or ""
        return (pri, deadline, created)

    sorted_tasks = sorted(tasks, key=sort_key)

    try:
        from rich.console import Console
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.table import Table
        from rich.live import Live

        console = Console()

        def render() -> Layout:
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
            )
            layout["body"].split_row(
                Layout(name="left"),
                Layout(name="right"),
            )
            header = (
                f"[bold]life-oss taskdog dashboard[/bold]  |  "
                f"total={len(tasks)}  |  "
                f"planned={counts['planned']}  "
                f"in_progress={counts['in_progress']}  "
                f"done={counts['done']}  "
                f"cancelled={counts['cancelled']}"
            )
            layout["header"].update(Panel(header, border_style="cyan"))

            table = Table(
                title="tasks by priority",
                show_lines=False,
                title_style="bold cyan",
            )
            table.add_column("ueid", style="dim", no_wrap=True)
            table.add_column("name")
            table.add_column("status")
            table.add_column("pri", justify="right")
            table.add_column("deadline")
            for t in sorted_tasks[:20]:
                pri = t.get("priority")
                pri_s = f"{pri}" if pri is not None else "-"
                table.add_row(
                    str(t.get("ueid") or ""),
                    _truncate(str(t.get("name") or ""), 30),
                    str(t.get("status") or ""),
                    pri_s,
                    str(t.get("deadline") or ""),
                )
            layout["left"].update(Panel(table, border_style="green"))

            # Upcoming deadlines
            upcoming = [
                t
                for t in sorted_tasks
                if t.get("deadline") and t.get("status") != "done"
            ][:5]
            upcoming_lines = []
            for t in upcoming:
                ueid = t.get("ueid") or "?"
                name = _truncate(str(t.get("name") or ""), 30)
                deadline = t.get("deadline") or ""
                upcoming_lines.append(f"{deadline}  {ueid}  {name}")
            upcoming_text = (
                "\n".join(upcoming_lines)
                if upcoming_lines
                else "(no upcoming deadlines)"
            )
            layout["right"].update(
                Panel(
                    "[bold]upcoming deadlines[/bold]\n\n" + upcoming_text,
                    border_style="yellow",
                )
            )
            return layout

        # One-shot render. Live(refresh_per_second=...) is the follow-up
        # when we add auto-refresh.
        console.print(render())
        return 0
    except ImportError:
        # Plain-text fallback.
        print("=" * 60, flush=True)
        print(f"life-oss taskdog dashboard  |  total={len(tasks)}", flush=True)
        print(
            f"planned={counts['planned']}  in_progress={counts['in_progress']}  "
            f"done={counts['done']}  cancelled={counts['cancelled']}",
            flush=True,
        )
        print("=" * 60, flush=True)
        print("tasks by priority:", flush=True)
        for t in sorted_tasks[:20]:
            print(
                f"  {t.get('ueid')}  {str(t.get('status'))}  "
                f"pri={t.get('priority')}  dl={t.get('deadline')}  "
                f"{_truncate(str(t.get('name') or ''), 30)}",
                flush=True,
            )
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ikigai-taskdog",
        description="Read-only ops CLI for the TaskdogAdapter SQLite store.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="list task slices")
    list_p.add_argument(
        "--status",
        type=str,
        choices=list(_KNOWN_STATUSES),
        default=None,
        help="filter by status (default: all)",
    )
    list_p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="max number of tasks to print (default: unlimited)",
    )
    _add_db_path(list_p)
    _add_output_flags(list_p)

    status_p = sub.add_parser("status", help="show task counts by status + priority")
    _add_db_path(status_p)
    _add_output_flags(status_p)

    show_p = sub.add_parser("show", help="show full slice for one ueid")
    show_p.add_argument("ueid", help="UEID to inspect (5-part format)")
    _add_db_path(show_p)
    _add_output_flags(show_p)

    timeline_p = sub.add_parser(
        "timeline",
        help="print chronological timeline of task events (created/deadline/done)",
    )
    _add_db_path(timeline_p)
    _add_output_flags(timeline_p)

    tui_p = sub.add_parser(
        "tui",
        help="render live TUI dashboard (Rich if installed, else plain text)",
    )
    _add_db_path(tui_p)
    tui_p.add_argument(
        "--refresh",
        type=float,
        default=0.0,
        help="auto-refresh interval in seconds (default: one-shot, no refresh)",
    )

    # M158: chat REPL (deep agent)
    chat_p = sub.add_parser(
        "chat",
        help="REPL interface for the v2 deep agent graph (context-aware, no auto-exec)",
    )
    chat_p.add_argument(
        "--thread-id",
        default=None,
        help="thread ID for the conversation (default: auto-generated)",
    )
    chat_p.add_argument(
        "--model",
        default="minimax-m3",
        help="model name (cosmetic; v2 graph uses env vars)",
    )
    chat_p.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI colors in output",
    )

    # M151: write path via review queue
    add_p = sub.add_parser("add", help="enqueue CREATE TaskChange")
    add_p.add_argument("--ueid", required=True, type=_validate_ueid, help="5-part UEID")
    add_p.add_argument("--title", required=True, help="task title (≥1 char)")
    add_p.add_argument("--priority", type=_validate_priority_str, default=None, help="1=high, 2=medium, 3=low")
    add_p.add_argument("--due", type=_validate_due, default=None, help="deadline YYYY-MM-DD")
    add_p.add_argument("--description", default=None, help="optional description")

    done_p = sub.add_parser("done", help="enqueue DONE TaskChange (idempotent)")
    done_p.add_argument("ueid", type=_validate_ueid, help="UEID to mark done")

    update_p = sub.add_parser("update", help="enqueue UPDATE TaskChange (partial fields)")
    update_p.add_argument("ueid", type=_validate_ueid, help="UEID to update")
    update_p.add_argument("--priority", type=_validate_priority_str, default=None, help="1/2/3")
    update_p.add_argument("--status", default=None, help="planned/in_progress/done/cancelled")
    update_p.add_argument("--due", type=_validate_due, default=None, help="YYYY-MM-DD")
    update_p.add_argument("--title", default=None, help="new title")

    sub.add_parser("propagate", help="run review queue worker once (consume → propagate)")

    # M164: dep subsystem — delegates to src/mesh/td_dep.py for the 4 verbs
    # (add / remove / list / blocked). The verbs are registered here so the
    # parent help text shows them; parsing + cycle detection + audit happen
    # in td_dep.main() which receives the inner argv.
    dep_p = sub.add_parser(
        "dep",
        help="manage task dependencies (M164): add/remove/list/blocked",
    )
    dep_sub = dep_p.add_subparsers(dest="dep_command", required=True)
    dep_sub.add_parser("add", help="add dependency: <ueid> blocked-by <other_ueid>")
    dep_sub.add_parser("remove", help="remove dependency edge")
    dep_sub.add_parser("list", help="list deps for a task (both directions)")
    dep_sub.add_parser("blocked", help="list tasks with one or more unmet deps")

    # M164: tag subsystem — delegates to src/mesh/cli/td_tag.py for the 4
    # verbs (add / remove / list / clear). The argparse sub-subparsers are
    # wired by register_tag_subparser; dispatch to cmd_* happens via
    # run_tag_command based on args.tag_command.
    register_tag_subparser(sub)

    # M167: gantt / optimize — delegates to src/mesh/cli/td_gantt.py.
    # Two top-level subcommands; each registered as a flat sub-parser
    # (no nested verbs). Dispatch goes through run_*_command.
    register_gantt_subparser(sub)
    register_optimize_subparser(sub)

    # M166: advanced subsystem — delegates to src/mesh/cli/td_advanced.py
    # for 6 verbs (rm / restore / audit / db / export / stats). The
    # argparse subparsers are wired by register_advanced_subparser;
    # dispatch happens via run_advanced_command based on args.command.
    register_advanced_subparser(sub)

    # M164: td note subsystem (nested sub-app: note add / note show)
    note_p = sub.add_parser(
        "note",
        help="append or list notes attached to a task (audit_log table)",
    )
    note_sub = note_p.add_subparsers(dest="note_command", required=True)

    note_add_p = note_sub.add_parser(
        "add",
        help="append a note to a task's audit_log",
    )
    note_add_p.add_argument("ueid", type=_validate_ueid, help="UEID to attach the note to")
    note_add_p.add_argument(
        "text",
        help=(
            "note body (sanitized: control chars stripped, newlines kept; "
            f"max {_MAX_NOTE_LEN} chars)"
        ),
    )
    _add_output_flags(note_add_p)

    note_show_p = note_sub.add_parser(
        "show",
        help="list notes for a task (filtered action='note')",
    )
    note_show_p.add_argument("ueid", type=_validate_ueid, help="UEID to list notes for")
    _add_output_flags(note_show_p)

    args = parser.parse_args(argv)

    if args.command == "list":
        return cmd_list(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "show":
        return cmd_show(args)
    if args.command == "timeline":
        return cmd_timeline(args)
    if args.command == "tui":
        return cmd_tui(args)
    if args.command == "chat":
        # Lazy import to keep --help fast
        from src.mesh.taskdog_chat import main as chat_main

        return chat_main(
            [
                *(["--thread-id", args.thread_id] if args.thread_id else []),
                *(["--model", args.model] if args.model != "minimax-m3" else []),
                *(["--no-color"] if args.no_color else []),
            ]
        )
    if args.command == "add":
        return cmd_add(args)
    if args.command == "done":
        return cmd_done(args)
    if args.command == "update":
        return cmd_update(args)
    if args.command == "propagate":
        return cmd_propagate(args)
    if args.command == "dep":
        # Re-dispatch to td_dep.main() with the inner argv. argparse at the
        # parent has already consumed `dep`; we hand over everything after it.
        from src.mesh.td_dep import main as dep_main

        try:
            dep_idx = sys.argv.index("dep")
        except ValueError:
            dep_idx = -1
        if dep_idx == -1:
            inner = [args.dep_command]
        else:
            inner = sys.argv[dep_idx + 1:]
        return dep_main(inner)
    if args.command == "note":
        if args.note_command == "add":
            return cmd_note_add(args)
        if args.note_command == "show":
            return cmd_note_show(args)
        parser.error(f"unknown note subcommand: {args.note_command}")
        return 2  # unreachable
    if args.command == "tag":
        return run_tag_command(args)
    if args.command == "gantt":
        return run_gantt_command(args)
    if args.command == "optimize":
        return run_optimize_command(args)
    if args.command in ("rm", "restore", "audit", "db", "export", "stats"):
        return run_advanced_command(args)
    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
