"""Read-only ops CLI for the TaskdogAdapter SQLite store.

The TaskdogAdapter is the only-connected MCP fork — it persists tasks
that flow through the mesh review queue. This CLI is the operator's
window into that store: list what we have, show details for a single
UEID. There is no write path here — propagation goes through the
review queue.

Subcommands:
    list [--status STATUS] [--limit N] [--db-path PATH] [--human|--json]
        Show task slices (default: all, sorted by created_at DESC).
    show <ueid> [--db-path PATH] [--human|--json]
        Show the full slice for one task (or "not found").

Output modes:
    Default (TTY): aligned ASCII table with column headers.
    Default (pipe/script): one JSON object per line.
    --human: force table output even when piped.
    --json: force JSON output even when on a TTY.

Usage:
    python -m src.mesh.taskdog_cli list
    python -m src.mesh.taskdog_cli list --status planned --limit 10
    python -m src.mesh.taskdog_cli show ikigai:task:abc:1:2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.adapters.taskdog import TaskdogAdapter

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
