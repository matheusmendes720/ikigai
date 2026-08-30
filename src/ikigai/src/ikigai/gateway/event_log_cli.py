"""Read-only CLI for inspecting the SSE EventLog.

Companion to `client_cli` (live SSE stream) and `event_log.py` (the log
itself). Reads JSONL records from `data/sse_events.jsonl` and emits them
on stdout — useful for post-mortem, replay, and audit.

Output modes:
    Default (TTY): aligned ASCII table with column headers.
    Default (pipe/script): one JSON object per line (stable, scriptable).
    --human: force table output even when piped.
    --json: force JSON output even when on a TTY.

Usage:
    python -m ikigai.gateway.event_log_cli tail --n 20
    python -m ikigai.gateway.event_log_cli since --seconds-ago 60
    python -m ikigai.gateway.event_log_cli status
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

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


def _summarize_data(data: Any) -> str:
    """One-line summary of `data` payload for human-readable table mode.

    For dicts, tries to surface a `tool` + compact result indicator.
    Otherwise truncates a compact JSON rendering.
    """
    if isinstance(data, dict):
        if "tool" in data:
            tool = data.get("tool")
            args = data.get("arguments") or data.get("args")
            if args is not None:
                args_str = json.dumps(args, default=str)
                if len(args_str) > 60:
                    args_str = args_str[:57] + "..."
                return f"tool={tool}({args_str})"
            return f"tool={tool}"
        if "result" in data:
            return f"result={json.dumps(data['result'], default=str)[:60]}"
    compact = json.dumps(data, default=str)
    if len(compact) > 80:
        compact = compact[:77] + "..."
    return compact


def _record_row(record: dict) -> list[str]:
    """Compact cells for one record in human-readable table mode."""
    ts_iso = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(record.get("ts", 0.0)))
    return [
        ts_iso,
        str(record.get("event", "")),
        _summarize_data(record.get("data")),
    ]


def _render_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print headers + rows as aligned ASCII table."""
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


def cmd_tail(args: argparse.Namespace) -> int:
    log = EventLog(args.path)
    records = log.tail(args.n)
    if _wants_human(args):
        _render_table(
            ["ts", "event", "data"],
            [_record_row(r) for r in records],
        )
    else:
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
    if _wants_human(args):
        _render_table(
            ["ts", "event", "data"],
            [_record_row(r) for r in records],
        )
    else:
        for record in records:
            print(_format_record(record), flush=True)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    log = EventLog(args.path)
    path = Path(args.path)
    candidates = log._candidate_files()
    rows: list[list[str]] = []
    for i, candidate in enumerate(candidates):
        size = candidate.stat().st_size if candidate.exists() else 0
        label = "active" if i == len(candidates) - 1 else f".{i}"
        rows.append([label, candidate.name, str(size)])

    if _wants_human(args):
        print(f"path: {path}", flush=True)
        print(f"max_bytes: {log.max_bytes}", flush=True)
        print(f"max_rotations: {log.max_rotations}", flush=True)
        _render_table(["label", "file", "size_bytes"], rows)
        total = sum(1 for _ in log)
        print(f"total_records: {total}", flush=True)
    else:
        print(f"path: {path}", flush=True)
        print(f"max_bytes: {log.max_bytes}", flush=True)
        print(f"max_rotations: {log.max_rotations}", flush=True)
        for row in rows:
            print(f"  {row[0]}: {row[1]} ({row[2]} bytes)", flush=True)
        total = sum(1 for _ in log)
        print(f"total_records: {total}", flush=True)
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
    _add_output_flags(tail_p)

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
    _add_output_flags(since_p)

    status_p = sub.add_parser("status", help="show file sizes, rotation count, total records")
    _add_path(status_p)
    _add_output_flags(status_p)

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
