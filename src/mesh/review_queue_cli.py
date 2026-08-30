"""Read-only CLI for inspecting the review queue.

Companion to mesh.queue — reads TaskChange JSON files from the queue dir
and prints them on stdout for inspection, debugging, and audit.

Subcommands:
    list [--status STATUS] [--limit N]
        Show TaskChange summaries (default: all statuses, sorted newest-first).
    status
        Show counts grouped by status + total.
    show <event_id>
        Show full TaskChange JSON for one event.

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
    """One-line summary for `list` output."""
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

    for event in events:
        print(_summarize(event), flush=True)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    queue_dir: Path = args.queue_dir
    print(f"queue_dir: {queue_dir}", flush=True)

    if not queue_dir.exists():
        print("total: 0", flush=True)
        for status in VALID_STATUSES:
            print(f"  {status}: 0", flush=True)
        return 0

    events = _read_events(queue_dir)
    counts: dict[str, int] = {s: 0 for s in VALID_STATUSES}
    for event in events:
        counts[event.status] = counts.get(event.status, 0) + 1

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

    print(event.model_dump_json(indent=2), flush=True)
    return 0


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

    status_cmd = list_p.add_parser("status", help="show queue counts by status")
    _add_qd(status_cmd)

    show_cmd = list_p.add_parser("show", help="show full JSON for one event")
    show_cmd.add_argument("event_id", help="event_id to inspect")
    _add_qd(show_cmd)

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