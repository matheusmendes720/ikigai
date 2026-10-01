"""Dependency subsystem CLI for the taskdog fork (M164).

Provides 4 subcommands for managing the `deps` column (JSON array of UEID
strings, M163 schema) on the local taskdog SQLite:

    add <ueid> <other_ueid>      — A blocked-by B (A depends on B)
    remove <ueid> <other_ueid>   — remove dependency edge
    list <ueid>                  — list deps in both directions
    blocked                      — list tasks with one or more unmet deps

Cycle detection is performed via ``dep_subsystem.detect_cycle`` (iterative
DFS, O(V+E)). Self-loops and existing-cycle paths are rejected with a
clear error before any mutation hits the DB.

Audit log:
    Every successful add/remove records one line in
    ``<data>/taskdog/.dep_audit.log``.

Output modes:
    Default (TTY): aligned ASCII table for list/blocked, key:value for add/remove.
    Default (pipe/script): JSON object (single-line).
    --json: force JSON output even on a TTY.
    --human: force human-readable table output even when piped.

Usage:
    python -m src.mesh.td_dep add tsk:a:ueid1:hash1 tsk:b:ueid2:hash2
    python -m src.mesh.td_dep remove tsk:a:ueid1:hash1 tsk:b:ueid2:hash2
    python -m src.mesh.td_dep list tsk:a:ueid1:hash1 --json
    python -m src.mesh.td_dep blocked --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.dep_subsystem import (
    CycleDetected,
    SelfLoopError,
    add_dep,
    get_deps,
    list_blocked,
    remove_dep,
)


# UEID regex (4-part per ADR-014). Mirrors the canonical regex in
# src/contracts/common.py.
_UEID_REGEX = re.compile(
    r"^(?:"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
    r"|"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{4,64}"
    r"|"
    r"[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
    r")$"
)


def _validate_ueid(s: str) -> str:
    """argparse type= callback. Returns the UEID if valid."""
    if not _UEID_REGEX.match(s):
        raise argparse.ArgumentTypeError(
            f"invalid UEID format: {s!r} "
            "(expected <cluster>:<entity>:<uuid>:<hash>)"
        )
    return s


def _wants_human(args: argparse.Namespace) -> bool:
    if getattr(args, "json", False):
        return False
    if getattr(args, "human", False):
        return True
    return sys.stdout.isatty()


def _apply_db_override(db_path_str: str) -> None:
    """Honor --db-path by mutating the module-level TASKDOG_DB."""
    if str(taskdog_mod.TASKDOG_DB) != db_path_str:
        taskdog_mod.TASKDOG_DB = Path(db_path_str)


def _add_db_path(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--db-path",
        type=str,
        default=str(taskdog_mod.TASKDOG_DB),
        help=f"path to taskdog SQLite DB (default: {taskdog_mod.TASKDOG_DB})",
    )


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


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def cmd_add(args: argparse.Namespace) -> int:
    """`td dep add <ueid> <other_ueid>` — A blocked-by B."""
    _apply_db_override(args.db_path)
    try:
        add_dep(args.ueid, args.other_ueid)
    except SelfLoopError as exc:
        payload = {"error": "self_loop", "ueid": exc.ueid}
        print(json.dumps(payload), file=sys.stderr, flush=True)
        return 2
    except CycleDetected as exc:
        payload = {
            "error": "cycle_detected",
            "path": exc.path,
        }
        if _wants_human(args):
            print(f"error: cycle_detected: {' -> '.join(exc.path)}",
                  file=sys.stderr, flush=True)
        else:
            print(json.dumps(payload), file=sys.stderr, flush=True)
        return 2
    except LookupError as exc:
        payload = {"error": "ueid_not_found", "detail": str(exc)}
        if _wants_human(args):
            print(f"error: {exc}", file=sys.stderr, flush=True)
        else:
            print(json.dumps(payload), file=sys.stderr, flush=True)
        return 2
    except ValueError as exc:
        payload = {"error": "invalid_ueid", "detail": str(exc)}
        if _wants_human(args):
            print(f"error: {exc}", file=sys.stderr, flush=True)
        else:
            print(json.dumps(payload), file=sys.stderr, flush=True)
        return 2

    payload = {
        "ok": True,
        "action": "add_dep",
        "ueid": args.ueid,
        "target": args.other_ueid,
    }
    if _wants_human(args):
        print(f"added dep: {args.ueid} blocked-by {args.other_ueid}",
              flush=True)
    else:
        print(json.dumps(payload), flush=True)
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    """`td dep remove <ueid> <other_ueid>` — remove edge."""
    _apply_db_override(args.db_path)
    try:
        removed = remove_dep(args.ueid, args.other_ueid)
    except ValueError as exc:
        payload = {"error": "invalid_ueid", "detail": str(exc)}
        if _wants_human(args):
            print(f"error: {exc}", file=sys.stderr, flush=True)
        else:
            print(json.dumps(payload), file=sys.stderr, flush=True)
        return 2

    payload = {
        "ok": True,
        "action": "remove_dep",
        "ueid": args.ueid,
        "target": args.other_ueid,
        "removed": removed,
    }
    if _wants_human(args):
        if removed:
            print(
                f"removed dep: {args.ueid} no longer blocked-by "
                f"{args.other_ueid}",
                flush=True,
            )
        else:
            print(
                f"no-op: edge {args.ueid}->{args.other_ueid} was not present",
                flush=True,
            )
    else:
        print(json.dumps(payload), flush=True)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """`td dep list <ueid>` — list deps in both directions."""
    _apply_db_override(args.db_path)
    try:
        result = get_deps(args.ueid)
    except ValueError as exc:
        payload = {"error": "invalid_ueid", "detail": str(exc)}
        if _wants_human(args):
            print(f"error: {exc}", file=sys.stderr, flush=True)
        else:
            print(json.dumps(payload), file=sys.stderr, flush=True)
        return 2

    payload: dict[str, Any] = {
        "ueid": args.ueid,
        "blocked_by": result["blocked_by"],
        "blocks": result["blocks"],
    }
    if _wants_human(args):
        print(f"ueid: {args.ueid}", flush=True)
        if result["blocked_by"]:
            print("  blocked_by:", flush=True)
            for d in result["blocked_by"]:
                print(f"    - {d}", flush=True)
        else:
            print("  blocked_by: <empty>", flush=True)
        if result["blocks"]:
            print("  blocks:", flush=True)
            for d in result["blocks"]:
                print(f"    - {d}", flush=True)
        else:
            print("  blocks: <empty>", flush=True)
    else:
        print(json.dumps(payload), flush=True)
    return 0


def cmd_blocked(args: argparse.Namespace) -> int:
    """`td dep blocked` — list tasks with one or more unmet deps."""
    _apply_db_override(args.db_path)
    rows = list_blocked()
    if _wants_human(args):
        if not rows:
            print("(no blocked tasks)", flush=True)
            return 0
        print(f"blocked: {len(rows)} task(s)", flush=True)
        print("-" * 60, flush=True)
        for row in rows:
            print(
                f"{row['ueid']:50}{row.get('status') or '-':12}"
                f"unmet={len(row['unmet_deps'])}",
                flush=True,
            )
            for d in row["unmet_deps"]:
                print(f"    blocked-by: {d}", flush=True)
        return 0
    # JSON output — single object with a `blocked` array.
    print(json.dumps({"blocked": rows, "count": len(rows)}), flush=True)
    return 0


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ikigai-td-dep",
        description=(
            "Manage taskdog dependencies (M164). "
            "Adds/removes edges in the deps column; rejects cycles "
            "via iterative DFS before any write."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add <ueid> <other_ueid>
    add_p = sub.add_parser(
        "add",
        help="add dependency: <ueid> blocked-by <other_ueid>",
    )
    add_p.add_argument(
        "ueid",
        type=_validate_ueid,
        help="UEID that will be blocked-by (4-part format)",
    )
    add_p.add_argument(
        "other_ueid",
        type=_validate_ueid,
        help="UEID that blocks (the dependency target)",
    )
    _add_db_path(add_p)
    _add_output_flags(add_p)

    # remove <ueid> <other_ueid>
    rm_p = sub.add_parser(
        "remove",
        help="remove dependency: <ueid> no longer blocked-by <other_ueid>",
    )
    rm_p.add_argument(
        "ueid",
        type=_validate_ueid,
        help="UEID that will no longer be blocked-by the target",
    )
    rm_p.add_argument(
        "other_ueid",
        type=_validate_ueid,
        help="UEID to remove from the blocked-by list",
    )
    _add_db_path(rm_p)
    _add_output_flags(rm_p)

    # list <ueid>
    list_p = sub.add_parser(
        "list",
        help="list deps for a task (both directions: blocked_by + blocks)",
    )
    list_p.add_argument(
        "ueid",
        type=_validate_ueid,
        help="UEID whose deps to enumerate",
    )
    _add_db_path(list_p)
    _add_output_flags(list_p)

    # blocked
    blk_p = sub.add_parser(
        "blocked",
        help="list all tasks with one or more unmet deps",
    )
    _add_db_path(blk_p)
    _add_output_flags(blk_p)

    args = parser.parse_args(argv)

    if args.command == "add":
        return cmd_add(args)
    if args.command == "remove":
        return cmd_remove(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "blocked":
        return cmd_blocked(args)
    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())