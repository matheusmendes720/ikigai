"""Read-only CLI for inspecting the review queue.

Companion to mesh.queue — reads TaskChange JSON files from the queue dir
and prints them on stdout for inspection, debugging, and audit.

Subcommands:
    list [--status STATUS] [--limit N] [--human|--json]
        Show TaskChange summaries (default: all statuses, sorted newest-first).
    status [--human|--json]
        Show counts grouped by status + total.
    show <event_id> [--human|--json]
        Show full TaskChange JSON for one event.

Output modes:
    Default (TTY): aligned ASCII table with column headers, multi-line.
    Default (pipe/script): one JSON object per line (stable, scriptable).
    --human: force table output even when piped.
    --json: force JSON output even when on a TTY.

Usage:
    python -m src.mesh.review_queue_cli list
    python -m src.mesh.review_queue_cli list --status pending --limit 5
    python -m src.mesh.review_queue_cli status
    python -m src.mesh.review_queue_cli show evt_001
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from src.contracts.task_change import TaskChange, TaskStatus
from src.mesh import queue as queue_mod

VALID_STATUSES: tuple[TaskStatus, ...] = (
    "pending",
    "approved",
    "rejected",
    "propagated",
    "partial_propagation",
    "clarified",
)


def _read_events(queue_dir: Path) -> list[TaskChange]:
    """Load all TaskChange JSON files from queue_dir, skipping malformed."""
    events: list[TaskChange] = []
    for path in sorted(queue_dir.glob("*.json")):
        try:
            events.append(TaskChange.model_validate_json(path.read_text()))
        except (ValueError, json.JSONDecodeError):
            continue
    return events


def _summarize(event: TaskChange) -> str:
    """One-line summary for `list` output (JSON mode)."""
    ts = event.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(event.timestamp, datetime) else str(event.timestamp)
    return json.dumps(
        {
            "event_id": event.event_id,
            "ueid": event.ueid,
            "action": event.action.value,
            "status": event.status,
            "source_fork": event.source_fork,
            "timestamp": ts,
        },
        default=str,
    )


def _event_row(event: TaskChange) -> list[str]:
    """Compact cells for one event in human-readable table mode."""
    ts = (
        event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(event.timestamp, datetime)
        else str(event.timestamp)
    )
    return [
        event.status,
        event.event_id,
        event.action.value,
        event.source_fork,
        ts,
    ]


def _render_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print headers + rows as an aligned ASCII table.

    Headers are uppercased. Empty rows -> just headers (no separator) so the
    operator sees an empty table, not nothing at all.
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


def cmd_list(args: argparse.Namespace) -> int:
    queue_dir: Path = args.queue_dir
    if not queue_dir.exists():
        print(f"queue dir not found: {queue_dir}", file=sys.stderr)
        return 0  # empty result is not an error

    events = _read_events(queue_dir)
    if args.status is not None:
        events = [e for e in events if e.status == args.status]

    # Newest first
    events.sort(key=lambda e: e.timestamp, reverse=True)

    if args.limit is not None:
        events = events[: args.limit]

    if _wants_human(args):
        _render_table(
            ["status", "event_id", "action", "source_fork", "timestamp"],
            [_event_row(e) for e in events],
        )
    else:
        for event in events:
            print(_summarize(event), flush=True)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    queue_dir: Path = args.queue_dir

    if not queue_dir.exists():
        if _wants_human(args):
            print(f"queue_dir: {queue_dir}", flush=True)
            _render_table(["status", "count"], [[s, "0"] for s in VALID_STATUSES])
        else:
            print(f"queue_dir: {queue_dir}", flush=True)
            print("total: 0", flush=True)
            for status in VALID_STATUSES:
                print(f"  {status}: 0", flush=True)
        return 0

    events = _read_events(queue_dir)
    counts: dict[str, int] = {s: 0 for s in VALID_STATUSES}
    for event in events:
        counts[event.status] = counts.get(event.status, 0) + 1

    if _wants_human(args):
        print(f"queue_dir: {queue_dir}    total: {len(events)}", flush=True)
        _render_table(["status", "count"], [[s, str(counts[s])] for s in VALID_STATUSES])
    else:
        print(f"queue_dir: {queue_dir}", flush=True)
        print(f"total: {len(events)}", flush=True)
        for status in VALID_STATUSES:
            print(f"  {status}: {counts[status]}", flush=True)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    queue_dir: Path = args.queue_dir
    event_id: str = args.event_id
    target = queue_dir / f"{event_id}.json"

    if not target.exists():
        print(f"event not found: {event_id}", file=sys.stderr)
        return 1

    try:
        event = TaskChange.model_validate_json(target.read_text())
    except (ValueError, json.JSONDecodeError) as e:
        print(f"malformed event file {target}: {e}", file=sys.stderr)
        return 1

    # JSON mode is already pretty-printed by .model_dump_json(indent=2).
    # Human mode adds a small key=value summary above the JSON for quick scan.
    if _wants_human(args):
        ts = (
            event.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
            if isinstance(event.timestamp, datetime)
            else str(event.timestamp)
        )
        print(f"event_id:   {event.event_id}", flush=True)
        print(f"ueid:       {event.ueid}", flush=True)
        print(f"action:     {event.action.value}", flush=True)
        print(f"status:     {event.status}", flush=True)
        print(f"source_fork:{event.source_fork}", flush=True)
        print(f"timestamp:  {ts}", flush=True)
        print("fields:", flush=True)
        print(json.dumps(event.fields, indent=2, default=str), flush=True)
    else:
        print(event.model_dump_json(indent=2), flush=True)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ikigai-review-queue",
        description="Read-only inspector for the mesh review queue (TaskChange JSON files).",
    )

    def _add_qd(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--queue-dir",
            type=Path,
            default=queue_mod.QUEUE_DIR,
            help=f"path to the review queue dir (default: {queue_mod.QUEUE_DIR})",
        )

    list_p = parser.add_subparsers(dest="command", required=True)

    list_cmd = list_p.add_parser("list", help="list TaskChange summaries")
    list_cmd.add_argument(
        "--status",
        type=str,
        choices=list(VALID_STATUSES),
        default=None,
        help="filter by status (default: all)",
    )
    list_cmd.add_argument(
        "--limit",
        type=int,
        default=None,
        help="max number of events to print (default: unlimited)",
    )
    _add_qd(list_cmd)
    _add_output_flags(list_cmd)

    status_cmd = list_p.add_parser("status", help="show queue counts by status")
    _add_qd(status_cmd)
    _add_output_flags(status_cmd)

    show_cmd = list_p.add_parser("show", help="show full JSON for one event")
    show_cmd.add_argument("event_id", help="event_id to inspect")
    _add_qd(show_cmd)
    _add_output_flags(show_cmd)

    args = parser.parse_args(argv)

    if args.command == "list":
        return cmd_list(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "show":
        return cmd_show(args)
    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())