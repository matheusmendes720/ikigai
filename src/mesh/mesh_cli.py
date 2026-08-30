"""Read-only cross-fork join CLI.

This is the canonical `life mesh show <ueid>` operator surface described in
CLAUDE.md — it joins the slices held by every fork adapter (CLI / taskdog /
solverforge_calendar) into a single view. Each adapter is consulted
independently; the join is purely additive (no schema reconciliation).

Subcommands:
    show <ueid> [--cli-path PATH] [--taskdog-db PATH] [--upi-db PATH]
                 [--human|--json]
        Show the slices for one UEID across all three adapters.
        Returns 0 if at least one fork has the slice, 1 if none do.

Output modes:
    Default (TTY): three per-fork sections with key:value lines.
    Default (pipe/script): one JSON object with one key per adapter.
    --human: force per-fork sections even when piped.
    --json: force JSON object even when on a TTY.

Usage:
    python -m src.mesh.mesh_cli show ikigai:task:abc:1:2
    python -m src.mesh.mesh_cli show --json ikigai:task:abc:1:2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.mesh.adapters import cli as cli_mod
from src.mesh.adapters import solverforge_calendar as calendar_mod
from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.adapters.cli import CliAdapter
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter
from src.mesh.adapters.taskdog import TaskdogAdapter

# Per-fork override state — module-globals the adapters read from. The CLI
# mutates them only when an override flag was passed; the module defaults
# remain authoritative for production reads. We resolve the *current* default
# at argparse-construction time (inside main()) so test fixtures that
# monkeypatch the adapter globals see the patched value in --help text.


def _wants_human(args: argparse.Namespace) -> bool:
    """Resolve output mode: --json wins, else --human wins, else TTY default."""
    if getattr(args, "json", False):
        return False
    if getattr(args, "human", False):
        return True
    return sys.stdout.isatty()


def _apply_cli_override(path_str: str) -> None:
    if str(cli_mod.TASKS_JSONL) != path_str:
        cli_mod.TASKS_JSONL = Path(path_str)


def _apply_taskdog_override(path_str: str) -> None:
    if str(taskdog_mod.TASKDOG_DB) != path_str:
        taskdog_mod.TASKDOG_DB = Path(path_str)


def _apply_calendar_override(path_str: str) -> None:
    if str(calendar_mod.UPI_DB) != path_str:
        calendar_mod.UPI_DB = Path(path_str)


def _collect_slices(ueid: str) -> dict[str, dict[str, Any] | None]:
    """Read the UEID from every adapter. Returns a mapping fork -> slice|None.

    Each adapter's read() is best-effort: a missing file is "not present",
    not an error. We never raise out of an adapter call — the whole point
    of cross-fork join is to show what each fork knows independently.
    """
    return {
        "cli": CliAdapter().read(ueid),
        "taskdog": TaskdogAdapter().read(ueid),
        "solverforge_calendar": SolverforgeCalendarAdapter().read(ueid),
    }


def _format_join_human(ueid: str, slices: dict[str, dict[str, Any] | None]) -> str:
    """Render the cross-fork join as a human-readable string.

    Three sections (one per adapter), each headed by `[fork: <name>]` and
    `present: yes/no`. Per-fork slices are rendered as sorted key: value
    lines. Missing forks say `not present` instead of showing empty keys.
    """
    lines: list[str] = []
    lines.append(f"ueid: {ueid}")
    for fork in ("cli", "taskdog", "solverforge_calendar"):
        slice_ = slices[fork]
        lines.append("")
        lines.append(f"[fork: {fork}]")
        if slice_ is None:
            lines.append("  present: no")
            continue
        lines.append("  present: yes")
        for key in sorted(slice_.keys()):
            value = slice_[key]
            # Empty containers / None values render as `<empty>` so the
            # human reader can distinguish "missing" from "explicitly null".
            if value in (None, "", [], {}):
                rendered = "<empty>"
            else:
                rendered = str(value)
            lines.append(f"  {key + ':':14}{rendered}")
    return "\n".join(lines) + "\n"


def cmd_show(args: argparse.Namespace) -> int:
    _apply_cli_override(args.cli_path)
    _apply_taskdog_override(args.taskdog_db)
    _apply_calendar_override(args.upi_db)

    slices = _collect_slices(args.ueid)
    present_count = sum(1 for s in slices.values() if s is not None)

    if _wants_human(args):
        sys.stdout.write(_format_join_human(args.ueid, slices))
        sys.stdout.flush()
    else:
        payload = {
            "ueid": args.ueid,
            "present_count": present_count,
            **slices,
        }
        print(json.dumps(payload, default=str, indent=2), flush=True)

    if present_count == 0:
        print(
            f"ueid not found in any fork: {args.ueid}",
            file=sys.stderr,
            flush=True,
        )
        return 1
    return 0


def _add_output_flags(p: argparse.ArgumentParser) -> None:
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


def main(argv: list[str] | None = None) -> int:
    # Resolve defaults at argparse time, NOT module-load time. This way
    # test fixtures that monkeypatch the adapter globals before invoking
    # main() see the patched paths in --help text and the default values.
    cli_default = str(cli_mod.TASKS_JSONL)
    taskdog_default = str(taskdog_mod.TASKDOG_DB)
    calendar_default = str(calendar_mod.UPI_DB)

    parser = argparse.ArgumentParser(
        prog="ikigai-mesh",
        description="Read-only cross-fork join CLI for the IKIGAi mesh.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    show_p = sub.add_parser("show", help="show joined slices for one ueid")
    show_p.add_argument("ueid", help="UEID to inspect (5-part format)")
    show_p.add_argument(
        "--cli-path",
        type=str,
        default=cli_default,
        help=f"path to tasks.jsonl (default: {cli_default})",
    )
    show_p.add_argument(
        "--taskdog-db",
        type=str,
        default=taskdog_default,
        help=f"path to taskdog SQLite DB (default: {taskdog_default})",
    )
    show_p.add_argument(
        "--upi-db",
        type=str,
        default=calendar_default,
        help=f"path to UPI SQLite DB (default: {calendar_default})",
    )
    _add_output_flags(show_p)

    args = parser.parse_args(argv)

    if args.command == "show":
        return cmd_show(args)
    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
