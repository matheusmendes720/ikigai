"""Operator-facing CLI for the vault ↔ taskdog sync engine.

Wraps `ikigai.vault.sync.run_sync()` and `reverse_sync()` into argparse
subcommands. This is purely an operator surface — the sync engine itself
lives in `ikigai.vault.sync` and remains untouched.

Subcommands:
    sync [--vault-root PATH] [--sync-state PATH] [--taskdog-db PATH]
         [--human|--json]
        Run vault → taskdog sync. Prints summary counters.
    reverse [--sync-state PATH] [--taskdog-db PATH] [--human|--json]
        Run taskdog → vault reverse sync. Stub in Task 1.
    status [--sync-state PATH] [--reverse-state PATH] [--human|--json]
        Print counts from sync-state.json + sync-state-reverse.json.
        Stub in Task 1.

Output modes:
    Default (TTY): aligned ASCII table.
    Default (pipe/script): JSON object.
    --human: force table even when piped.
    --json: force JSON even on TTY.

Usage:
    python -m ikigai.vault.sync_cli sync
    python -m ikigai.vault.sync_cli reverse --json
    python -m ikigai.vault.sync_cli status
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ikigai.vault.sync import (
    SyncResult,
    load_reverse_state,
    load_state,
    reverse_sync,
    run_sync,
)

# ─────────────────────────────────────────────────────────────────────────────
# Module defaults — anchored at the repo root.
# ─────────────────────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VAULT_ROOT: Path = _REPO_ROOT / "vault"
SYNC_STATE: Path = _REPO_ROOT / "data" / "sync-state.json"
REVERSE_SYNC_STATE: Path = _REPO_ROOT / "data" / "sync-state-reverse.json"
TASKDOG_DB: Path = _REPO_ROOT / "data" / "taskdog" / "tasks.db"

# Captured at import time for the test sanity check
_VAULT_ROOT_DEFAULT = VAULT_ROOT
_SYNC_STATE_DEFAULT = SYNC_STATE
_REVERSE_SYNC_STATE_DEFAULT = REVERSE_SYNC_STATE
_TASKDOG_DB_DEFAULT = TASKDOG_DB


# ─────────────────────────────────────────────────────────────────────────────
# Adapter factory — overridable in tests
# ─────────────────────────────────────────────────────────────────────────────


def _build_adapter() -> Any:
    """Build the live taskdog adapter.

    The CLI does not own the live MCP client (`tools.taskdog`) — that lives
    in the ikigai tools registry and is only meaningful inside an active
    agent run. For operator-side syncs we build a thin SQLite-backed
    adapter that hits the same taskdog.db the agent writes to.

    Production: this function returns a wrapper around `ikigai.tools.taskdog`.
    Tests: monkeypatch this with a stub.
    """
    from src.mesh.adapters.taskdog import TaskdogAdapter

    return TaskdogAdapter()


# ─────────────────────────────────────────────────────────────────────────────
# Output helpers — mirror src/mesh/cli_cli.py / taskdog_cli.py (kept inline)
# ─────────────────────────────────────────────────────────────────────────────


def _wants_human(args: argparse.Namespace) -> bool:
    """Resolve output mode: --json wins, else --human wins, else TTY default."""
    if getattr(args, "json", False):
        return False
    if getattr(args, "human", False):
        return True
    return sys.stdout.isatty()


def _render_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print headers + rows as an aligned ASCII table."""
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


def _render_sync_result(result: SyncResult) -> None:
    """Render a SyncResult as a counter table."""
    _render_table(
        ["counter", "value"],
        [
            ["scanned", str(result.scanned)],
            ["added", str(result.added)],
            ["updated", str(result.updated)],
            ["completed", str(result.completed)],
            ["skipped", str(result.skipped)],
            ["parse_errors", str(result.parse_errors)],
            ["errors", str(len(result.errors))],
            ["duration_s", f"{result.duration_s:.3f}"],
        ],
    )


def _render_reverse_result(result: Any) -> None:
    """Render a ReverseSyncResult as a counter table.

    Accepts Any to avoid a circular import for the type — reverse_sync()
    returns ikigai.vault.sync.ReverseSyncResult, which has the same field
    names: scanned, emitted, skipped, errors, duration_s.
    """
    _render_table(
        ["counter", "value"],
        [
            ["scanned", str(result.scanned)],
            ["emitted", str(result.emitted)],
            ["skipped", str(result.skipped)],
            ["errors", str(len(result.errors))],
            ["duration_s", f"{result.duration_s:.3f}"],
        ],
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


# ─────────────────────────────────────────────────────────────────────────────
# Override helpers
# ─────────────────────────────────────────────────────────────────────────────


def _apply_vault_override(path_str: str) -> None:
    global VAULT_ROOT
    if str(VAULT_ROOT) != path_str:
        VAULT_ROOT = Path(path_str)


def _apply_state_override(path_str: str) -> None:
    global SYNC_STATE
    if str(SYNC_STATE) != path_str:
        SYNC_STATE = Path(path_str)


def _apply_rev_state_override(path_str: str) -> None:
    global REVERSE_SYNC_STATE
    if str(REVERSE_SYNC_STATE) != path_str:
        REVERSE_SYNC_STATE = Path(path_str)


def _apply_taskdog_override(path_str: str) -> None:
    global TASKDOG_DB
    if str(TASKDOG_DB) != path_str:
        TASKDOG_DB = Path(path_str)


# ─────────────────────────────────────────────────────────────────────────────
# Subcommand handlers
# ─────────────────────────────────────────────────────────────────────────────


def cmd_sync(args: argparse.Namespace) -> int:
    """Run vault → taskdog sync."""
    _apply_vault_override(args.vault_root)
    _apply_state_override(args.sync_state)
    _apply_taskdog_override(args.taskdog_db)

    adapter = _build_adapter()
    result = run_sync(VAULT_ROOT, SYNC_STATE, adapter)

    if _wants_human(args):
        _render_sync_result(result)
        if result.errors:
            print("", flush=True)
            print("errors:", flush=True)
            for err in result.errors:
                print(f"  - {err}", flush=True)
    else:
        payload = {
            "scanned": result.scanned,
            "added": result.added,
            "updated": result.updated,
            "completed": result.completed,
            "skipped": result.skipped,
            "parse_errors": result.parse_errors,
            "errors": result.errors,
            "duration_s": round(result.duration_s, 3),
        }
        print(json.dumps(payload, default=str, indent=2), flush=True)

    return 0


def cmd_reverse(args: argparse.Namespace) -> int:
    """Run taskdog → vault reverse sync."""
    _apply_rev_state_override(args.sync_state)
    _apply_taskdog_override(args.taskdog_db)

    adapter = _build_adapter()
    result = reverse_sync(REVERSE_SYNC_STATE, adapter)

    if _wants_human(args):
        _render_reverse_result(result)
        if result.errors:
            print("", flush=True)
            print("errors:", flush=True)
            for err in result.errors:
                print(f"  - {err}", flush=True)
    else:
        payload = {
            "scanned": result.scanned,
            "emitted": result.emitted,
            "skipped": result.skipped,
            "errors": result.errors,
            "duration_s": round(result.duration_s, 3),
        }
        print(json.dumps(payload, default=str, indent=2), flush=True)

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Print sync-state.json + sync-state-reverse.json counts."""
    _apply_state_override(args.sync_state)
    _apply_rev_state_override(args.reverse_state)

    # Load both states (load_* returns empty state if file is absent)
    forward = load_state(SYNC_STATE)
    reverse = load_reverse_state(REVERSE_SYNC_STATE)

    payload = {
        "sync_state": str(SYNC_STATE),
        "reverse_state": str(REVERSE_SYNC_STATE),
        "forward_tasks": len(forward.tasks),
        "forward_last_sync_at": forward.last_sync_at,
        "reverse_tasks": len(reverse.tasks),
        "reverse_last_sync_at": reverse.last_sync_at,
    }

    if _wants_human(args):
        print(f"sync_state:    {payload['sync_state']}", flush=True)
        print(f"reverse_state: {payload['reverse_state']}", flush=True)
        _render_table(
            ["counter", "value"],
            [
                ["forward_tasks", str(payload["forward_tasks"])],
                ["reverse_tasks", str(payload["reverse_tasks"])],
                [
                    "forward_last_sync_at",
                    str(payload["forward_last_sync_at"] or "<never>"),
                ],
                [
                    "reverse_last_sync_at",
                    str(payload["reverse_last_sync_at"] or "<never>"),
                ],
            ],
        )
    else:
        print(json.dumps(payload, indent=2), flush=True)

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ikigai-vault-sync",
        description="Operator CLI for the vault ↔ taskdog sync engine.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sync_p = sub.add_parser("sync", help="run vault → taskdog sync")
    sync_p.add_argument(
        "--vault-root",
        type=str,
        default=str(VAULT_ROOT),
        help=f"path to vault root (default: {VAULT_ROOT})",
    )
    sync_p.add_argument(
        "--sync-state",
        type=str,
        default=str(SYNC_STATE),
        help=f"path to sync-state.json (default: {SYNC_STATE})",
    )
    sync_p.add_argument(
        "--taskdog-db",
        type=str,
        default=str(TASKDOG_DB),
        help=f"path to taskdog SQLite DB (default: {TASKDOG_DB})",
    )
    _add_output_flags(sync_p)

    rev_p = sub.add_parser("reverse", help="run taskdog → vault reverse sync (stub in Task 1)")
    rev_p.add_argument(
        "--sync-state",
        type=str,
        default=str(REVERSE_SYNC_STATE),
        help=f"path to sync-state-reverse.json (default: {REVERSE_SYNC_STATE})",
    )
    rev_p.add_argument(
        "--taskdog-db",
        type=str,
        default=str(TASKDOG_DB),
        help=f"path to taskdog SQLite DB (default: {TASKDOG_DB})",
    )
    _add_output_flags(rev_p)

    status_p = sub.add_parser("status", help="show sync state counts (stub in Task 1)")
    status_p.add_argument(
        "--sync-state",
        type=str,
        default=str(SYNC_STATE),
        help=f"path to sync-state.json (default: {SYNC_STATE})",
    )
    status_p.add_argument(
        "--reverse-state",
        type=str,
        default=str(REVERSE_SYNC_STATE),
        help=f"path to sync-state-reverse.json (default: {REVERSE_SYNC_STATE})",
    )
    _add_output_flags(status_p)

    args = parser.parse_args(argv)

    if args.command == "sync":
        return cmd_sync(args)
    if args.command == "reverse":
        return cmd_reverse(args)
    if args.command == "status":
        return cmd_status(args)
    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable


__all__ = [
    "REVERSE_SYNC_STATE",
    "SYNC_STATE",
    "TASKDOG_DB",
    "VAULT_ROOT",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
