"""M164: td tag subsystem — tag management subcommands.

Four subcommands (add / remove / list / clear) all target the canonical
SQLite `tags` column on the taskdog fork. Tags are JSON-encoded strings
(max 32 chars, alphanumeric + hyphen + underscore); the CLI reuses the
adapter's module-level helpers (add_tags / remove_tags / clear_tags /
get_tags) so the validation + audit log + idempotency story is owned in
exactly one place.

Wire-in: imported by ``src/mesh/taskdog_cli.py`` and registered under
the ``tag`` sub-command via ``register_tag_subparser`` + ``run_tag_command``.

Output modes:
    Default (TTY): aligned ASCII table or one tag per line.
    --json: force JSON output.

Usage:
    python -m src.mesh.taskdog_cli tag add <ueid> <tag1> [tag2 ...]
    python -m src.mesh.taskdog_cli tag remove <ueid> <tag1> [tag2 ...]
    python -m src.mesh.taskdog_cli tag list <ueid>
    python -m src.mesh.taskdog_cli tag clear <ueid>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Re-use the adapter's module-level helpers so validation + audit log live
# in exactly one place. Importing the whole module (rather than copying the
# regex here) is the drift-safe pattern.
from src.mesh.adapters import taskdog as taskdog_mod


def _wants_human(args: argparse.Namespace) -> bool:
    """Resolve output mode: --json wins, else TTY default."""
    if getattr(args, "json", False):
        return False
    return sys.stdout.isatty()


def _validate_tag(s: str) -> str:
    """argparse type= callback. Returns the tag if valid, raises ArgumentTypeError."""
    if not taskdog_mod._is_valid_tag(s):
        raise argparse.ArgumentTypeError(
            f"invalid tag: {s!r} (max 32 chars, alphanumeric+hyphen+underscore)"
        )
    return s


def _apply_db_override(db_path_str: str) -> None:
    """Mutate module-level TASKDOG_DB to honor --db-path override."""
    if str(taskdog_mod.TASKDOG_DB) != db_path_str:
        taskdog_mod.TASKDOG_DB = Path(db_path_str)


def _emit_tags(args: argparse.Namespace, ueid: str, tags: list[str]) -> None:
    """Render tags either as JSON or human-readable."""
    if _wants_human(args):
        if tags:
            for t in tags:
                print(t, flush=True)
        else:
            print("(no tags)", flush=True)
        return
    payload = {"ueid": ueid, "tags": tags, "count": len(tags)}
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)


def _emit_change(
    args: argparse.Namespace,
    ueid: str,
    action: str,
    tags: list[str],
    fields_diff: dict[str, Any] | None = None,
) -> None:
    """Render the post-mutation tag list + an action echo."""
    if _wants_human(args):
        verb = {
            "tag_add": "added",
            "tag_remove": "removed",
            "tag_clear": "cleared",
        }.get(action, action)
        if tags:
            print(f"{verb} tags on {ueid}: {', '.join(tags)}", flush=True)
        else:
            print(f"{verb} tags on {ueid}: (none)", flush=True)
        return
    payload: dict[str, Any] = {
        "ueid": ueid,
        "action": action,
        "tags": tags,
        "count": len(tags),
    }
    if fields_diff is not None:
        payload["fields_diff"] = fields_diff
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)


# ----------------------------------------------------------------------
# Subcommand handlers
# ----------------------------------------------------------------------

def cmd_tag_add(args: argparse.Namespace) -> int:
    """Append tags to a task. Idempotent on already-present tags."""
    _apply_db_override(args.db_path)
    try:
        new_tags = taskdog_mod.add_tags(args.ueid, list(args.tag))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    added = [t for t in new_tags if t in set(args.tag)]
    _emit_change(args, args.ueid, "tag_add", new_tags, fields_diff={"added": added})
    return 0


def cmd_tag_remove(args: argparse.Namespace) -> int:
    """Remove tags from a task. Missing tags are silently ignored."""
    _apply_db_override(args.db_path)
    try:
        new_tags = taskdog_mod.remove_tags(args.ueid, list(args.tag))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    removed = [t for t in args.tag if t not in set(new_tags)]
    _emit_change(
        args, args.ueid, "tag_remove", new_tags, fields_diff={"removed": removed}
    )
    return 0


def cmd_tag_list(args: argparse.Namespace) -> int:
    """Print the canonical tag list for a task."""
    _apply_db_override(args.db_path)
    try:
        tags = taskdog_mod.get_tags(args.ueid)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _emit_tags(args, args.ueid, tags)
    return 0


def cmd_tag_clear(args: argparse.Namespace) -> int:
    """Remove all tags from a task."""
    _apply_db_override(args.db_path)
    try:
        new_tags = taskdog_mod.clear_tags(args.ueid)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _emit_change(args, args.ueid, "tag_clear", new_tags)
    return 0


# ----------------------------------------------------------------------
# Parser wiring — called from taskdog_cli.main()
# ----------------------------------------------------------------------

def register_tag_subparser(
    sub: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    """Attach the ``tag`` sub-parser and return the parent ``tag`` parser.

    Each leaf subcommand gets its own ``argparse`` sub-sub-parser so the
    help text stays clean (`td tag add --help` etc.).
    """
    tag_p = sub.add_parser(
        "tag",
        help="manage task tags (add / remove / list / clear)",
        description=(
            "Tag management for taskdog forks. Tags are JSON-encoded strings "
            "(max 32 chars, alphanumeric+hyphen+underscore). All writes flow "
            "through the adapter and produce an audit_log entry on the row."
        ),
    )
    tag_sub = tag_p.add_subparsers(dest="tag_command", required=True)

    # tag add <ueid> <tag1> [tag2 ...]
    add_p = tag_sub.add_parser("add", help="append tags to a task (idempotent)")
    add_p.add_argument("ueid", help="UEID of the target task")
    add_p.add_argument(
        "tag",
        nargs="+",
        type=_validate_tag,
        help="one or more tags to add (max 32 chars each)",
    )
    add_p.add_argument(
        "--db-path",
        type=str,
        default=str(taskdog_mod.TASKDOG_DB),
        help="path to taskdog SQLite DB (default: production DB)",
    )
    add_p.add_argument(
        "--json", action="store_true", help="force JSON output"
    )

    # tag remove <ueid> <tag1> [tag2 ...]
    rm_p = tag_sub.add_parser(
        "remove",
        help="remove tags from a task (missing tags are no-ops)",
    )
    rm_p.add_argument("ueid", help="UEID of the target task")
    rm_p.add_argument(
        "tag",
        nargs="+",
        type=_validate_tag,
        help="one or more tags to remove",
    )
    rm_p.add_argument(
        "--db-path",
        type=str,
        default=str(taskdog_mod.TASKDOG_DB),
        help="path to taskdog SQLite DB (default: production DB)",
    )
    rm_p.add_argument(
        "--json", action="store_true", help="force JSON output"
    )

    # tag list <ueid>
    list_p = tag_sub.add_parser("list", help="list tags on a task")
    list_p.add_argument("ueid", help="UEID of the target task")
    list_p.add_argument(
        "--db-path",
        type=str,
        default=str(taskdog_mod.TASKDOG_DB),
        help="path to taskdog SQLite DB (default: production DB)",
    )
    list_p.add_argument(
        "--json", action="store_true", help="force JSON output"
    )

    # tag clear <ueid>
    clear_p = tag_sub.add_parser("clear", help="remove all tags from a task")
    clear_p.add_argument("ueid", help="UEID of the target task")
    clear_p.add_argument(
        "--db-path",
        type=str,
        default=str(taskdog_mod.TASKDOG_DB),
        help="path to taskdog SQLite DB (default: production DB)",
    )
    clear_p.add_argument(
        "--json", action="store_true", help="force JSON output"
    )

    return tag_p


def run_tag_command(args: argparse.Namespace) -> int:
    """Dispatch a parsed `td tag ...` command to the right cmd_* handler."""
    if args.tag_command == "add":
        return cmd_tag_add(args)
    if args.tag_command == "remove":
        return cmd_tag_remove(args)
    if args.tag_command == "list":
        return cmd_tag_list(args)
    if args.tag_command == "clear":
        return cmd_tag_clear(args)
    print(f"unknown tag command: {args.tag_command}", file=sys.stderr)
    return 2