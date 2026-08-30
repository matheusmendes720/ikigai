"""Read-only CLI for inspecting the SSE EventLog.

Companion to `client_cli` (live SSE stream) and `event_log.py` (the log
itself). Reads JSONL records from `data/sse_events.jsonl` and emits them
on stdout — useful for post-mortem, replay, and audit.

Usage:
    python -m ikigai.gateway.event_log_cli tail --n 20
    python -m ikigai.gateway.event_log_cli since --seconds-ago 60
    python -m ikigai.gateway.event_log_cli status
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ikigai.gateway.event_log import EventLog

DEFAULT_LOG_PATH = "data/sse_events.jsonl"


def _format_record(record: dict) -> str:
    """One JSON line per record. ts is rendered as ISO 8601 for humans."""
    out = {
        "ts_iso": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.get("ts", 0.0))
        ),
        "ts": record.get("ts"),
        "event": record.get("event"),
        "data": record.get("data"),
    }
    return json.dumps(out, default=str)


def cmd_tail(args: argparse.Namespace) -> int:
    log = EventLog(args.path)
    records = log.tail(args.n)
    for record in records:
        print(_format_record(record), flush=True)
    return 0


def cmd_since(args: argparse.Namespace) -> int:
    log = EventLog(args.path)
    if args.timestamp is not None:
        since_ts = args.timestamp
    elif args.seconds_ago is not None:
        since_ts = time.time() - args.seconds_ago
    else:
        since_ts = 0.0
    records = log.since(since_ts)
    for record in records:
        print(_format_record(record), flush=True)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    log = EventLog(args.path)
    path = Path(args.path)
    print(f"path: {path}", flush=True)
    print(f"max_bytes: {log.max_bytes}", flush=True)
    print(f"max_rotations: {log.max_rotations}", flush=True)
    for i, candidate in enumerate(log._candidate_files()):
        size = candidate.stat().st_size if candidate.exists() else 0
        label = "active" if i == len(log._candidate_files()) - 1 else f".{i}"
        print(f"  {label}: {candidate.name} ({size} bytes)", flush=True)
    total = sum(1 for _ in log)
    print(f"total_records: {total}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ikigai-event-log",
        description="Read-only inspector for the SSE EventLog JSONL store.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_path(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--path",
            default=DEFAULT_LOG_PATH,
            help=f"path to the EventLog JSONL file (default: {DEFAULT_LOG_PATH})",
        )

    tail_p = sub.add_parser("tail", help="print the last N events")
    tail_p.add_argument("--n", type=int, default=10, help="number of events (default 10)")
    _add_path(tail_p)

    since_p = sub.add_parser("since", help="print events since a timestamp")
    since_p.add_argument(
        "--timestamp",
        type=float,
        default=None,
        help="absolute Unix timestamp (lower bound, inclusive)",
    )
    since_p.add_argument(
        "--seconds-ago",
        type=float,
        default=None,
        help="relative offset from now (e.g. 60 = last minute)",
    )
    _add_path(since_p)

    status_p = sub.add_parser("status", help="show file sizes, rotation count, total records")
    _add_path(status_p)

    args = parser.parse_args(argv)
    if args.command == "tail":
        return cmd_tail(args)
    if args.command == "since":
        return cmd_since(args)
    if args.command == "status":
        return cmd_status(args)
    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
