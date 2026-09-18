"""Read-only ops CLI for the CliAdapter tasks.jsonl store.

The CliAdapter is the user-facing fork — it persists tasks to a
human-readable JSONL file that the CLI/TUI consumers read from.
This CLI is the operator's window into that file: list what we
have, show details for a single UEID. No write path here —
propagation goes through the review queue.

Subcommands:
    list [--priority PRIORITY] [--limit N] [--path PATH] [--human|--json]
        Show task slices (default: all, sorted by written_at DESC).
    show <ueid> [--path PATH] [--human|--json]
        Show the full slice for one task (or "not found").
    status [--path PATH] [--human|--json]
        Show task counts by priority.

Output modes:
    Default (TTY): aligned ASCII table with column headers.
    Default (pipe/script): one JSON object per line.
    --human: force table output even when piped.
    --json: force JSON output even when on a TTY.

Usage:
    python -m src.mesh.cli_cli list
    python -m src.mesh.cli_cli list --priority high --limit 10
    python -m src.mesh.cli_cli show ikigai:task:abc:1:2
    python -m src.mesh.cli_cli status
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.mesh.adapters import cli as cli_mod
from src.mesh.adapters.cli import CliAdapter

# Priority values seen on the CLI fork's task records. Kept as a closed
# list for argparse's --priority choices. New values can be added as
# the lifecycle expands; the CLI does not enforce a fixed enum on reads.
_KNOWN_PRIORITIES: tuple[str, ...] = ("high", "medium", "low")

_MAX_TITLE = 40
_MAX_UEID = 36


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
        _truncate(str(slice.get("title") or ""), _MAX_TITLE),
        str(slice.get("priority") or ""),
        str(slice.get("due") or ""),
        str(slice.get("source_fork") or ""),
    ]


def _render_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print headers + rows as an aligned ASCII table.

    Mirrors taskdog_cli._render_table (kept inline — CLI-to-CLI imports
    inside the same package are noisy).
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


def _apply_path_override(path_str: str) -> None:
    """Mutate module-level TASKS_JSONL to honor --path (test + ops override).

    The adapter reads from the module-global TASKS_JSONL. The cleanest way
    to redirect it is to update the module attr before each call. This is
    process-local and intentional — production code defaults to the module
    constant; this helper only fires when --path differs from it.
    """
    if str(cli_mod.TASKS_JSONL) != path_str:
        cli_mod.TASKS_JSONL = Path(path_str)


def _read_all_tasks() -> list[dict]:
    """Return all task slices from TASKS_JSONL, skipping malformed lines.

    The CliAdapter's own read() returns one slice; for `list` we need
    every slice. We can't use the adapter's read directly without doing
    O(n^2) — so we walk the file once and return all parsed rows.
    """
    if not cli_mod.TASKS_JSONL.exists():
        return []
    tasks: list[dict] = []
    for line in cli_mod.TASKS_JSONL.read_text().splitlines():
        if not line.strip():
            continue
        try:
            tasks.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return tasks


def cmd_list(args: argparse.Namespace) -> int:
    _apply_path_override(args.path)
    tasks = _read_all_tasks()

    if args.priority is not None:
        tasks = [t for t in tasks if t.get("priority") == args.priority]

    # Newest first. written_at is an ISO timestamp string — sorts lexicographically.
    tasks.sort(key=lambda t: t.get("written_at") or "", reverse=True)

    if args.limit is not None:
        tasks = tasks[: args.limit]

    if _wants_human(args):
        _render_table(
            ["ueid", "title", "priority", "due", "source_fork"],
            [_list_row(t) for t in tasks],
        )
    else:
        for task in tasks:
            print(_summarize(task), flush=True)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    _apply_path_override(args.path)
    adapter = CliAdapter()
    slice_ = adapter.read(args.ueid)
    if slice_ is None:
        print(f"ueid not found: {args.ueid}", file=sys.stderr)
        return 1

    if _wants_human(args):
        for key in ("ueid", "title", "priority", "due", "written_at", "source_fork"):
            print(f"{key + ':':15}{slice_.get(key) or ''}", flush=True)
    else:
        print(json.dumps(slice_, default=str, indent=2), flush=True)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _apply_path_override(args.path)
    tasks = _read_all_tasks()

    # Initialize counts with zeros so the table always renders the same
    # shape even on empty/partial files.
    priority_counts: dict[str, int] = {p: 0 for p in _KNOWN_PRIORITIES}
    for task in tasks:
        p = task.get("priority")
        if p in priority_counts:
            priority_counts[p] += 1

    if _wants_human(args):
        print(
            f"path: {cli_mod.TASKS_JSONL}    total: {len(tasks)}",
            flush=True,
        )
        _render_table(
            ["priority", "count"],
            [[p, str(priority_counts[p])] for p in _KNOWN_PRIORITIES],
        )
    else:
        print(f"path: {cli_mod.TASKS_JSONL}", flush=True)
        print(f"total: {len(tasks)}", flush=True)
        for priority in _KNOWN_PRIORITIES:
            print(f"  {priority}: {priority_counts[priority]}", flush=True)
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


def _add_path(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--path",
        type=str,
        default=str(cli_mod.TASKS_JSONL),
        help=f"path to tasks.jsonl (default: {cli_mod.TASKS_JSONL})",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ikigai-cli-fork",
        description="Read-only ops CLI for the CliAdapter tasks.jsonl store.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="list task slices")
    list_p.add_argument(
        "--priority",
        type=str,
        choices=list(_KNOWN_PRIORITIES),
        default=None,
        help="filter by priority (default: all)",
    )
    list_p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="max number of tasks to print (default: unlimited)",
    )
    _add_path(list_p)
    _add_output_flags(list_p)

    show_p = sub.add_parser("show", help="show full slice for one ueid")
    show_p.add_argument("ueid", help="UEID to inspect (5-part format)")
    _add_path(show_p)
    _add_output_flags(show_p)

    status_p = sub.add_parser("status", help="show task counts by priority")
    _add_path(status_p)
    _add_output_flags(status_p)

    args = parser.parse_args(argv)

    if args.command == "list":
        return cmd_list(args)
    if args.command == "show":
        return cmd_show(args)
    if args.command == "status":
        return cmd_status(args)
    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
