"""Operator-facing CLI for the vault ↔ taskdog sync engine.

Wraps `ikigai.vault.sync.run_sync()` and `reverse_sync()` into argparse
subcommands. This is purely an operator surface — the sync engine itself
lives in `ikigai.vault.sync` and remains untouched.

Subcommands:
    sync [--vault-root PATH] [--sync-state PATH] [--taskdog-db PATH]
         [--dry-run] [--human|--json]
        Run vault → taskdog sync. Prints summary counters.
    reverse [--sync-state PATH] [--taskdog-db PATH] [--dry-run]
            [--human|--json]
        Run taskdog → vault reverse sync (emits TaskChange events).
    status [--sync-state PATH] [--reverse-state PATH] [--human|--json]
        Print counts from sync-state.json + sync-state-reverse.json.
    list [--direction forward|reverse] [--sync-state PATH]
         [--reverse-state PATH] [--human|--json]
        Enumerate entries in the sync state.
    validate [--sync-state PATH] [--human|--json]
        Check that every sync-state entry's vault_path still exists on disk.

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
    diff,
    load_reverse_state,
    load_state,
    parse_vault_tasks,
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

    if args.dry_run:
        # Parse + diff against current state, but DO NOT push or save state.
        state = load_state(SYNC_STATE)
        try:
            tasks = parse_vault_tasks(VAULT_ROOT)
        except Exception as exc:
            payload = {
                "dry_run": True,
                "scanned": 0,
                "planned_actions": [],
                "errors": [{"error": f"vault_parse_failed: {exc}"}],
            }
            print(json.dumps(payload, default=str, indent=2), flush=True)
            return 0

        actions = diff(tasks, state)
        planned: list[dict[str, Any]] = []
        for action in actions:
            planned.append(
                {
                    "kind": action.kind.value,
                    "ueid": action.record.ueid,
                    "title": action.record.title,
                    "status": action.record.status,
                    "taskdog_id": action.taskdog_id,
                }
            )

        payload = {
            "dry_run": True,
            "scanned": len(tasks),
            "planned_actions": planned,
            "errors": [],
        }
        print(json.dumps(payload, default=str, indent=2), flush=True)
        return 0

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

    if args.dry_run:
        # list_all + diff vs snapshot, but DO NOT enqueue or save state.
        state = load_reverse_state(REVERSE_SYNC_STATE)
        # Build adapter WITHOUT calling call_tool — list_all() is read-only.
        adapter = _build_adapter()
        try:
            rows = adapter.list_all()
        except Exception as exc:
            payload = {
                "dry_run": True,
                "scanned": 0,
                "planned_emits": [],
                "errors": [{"error": f"adapter_list_failed: {exc}"}],
            }
            print(json.dumps(payload, default=str, indent=2), flush=True)
            return 0

        planned: list[dict[str, Any]] = []
        for row in rows:
            ueid = row.get("ueid")
            if not ueid:
                continue
            status = row.get("status", "planned")
            title = row.get("name", "")
            entry = state.tasks.get(ueid)
            if entry is None:
                # Orphan — v1 skips
                continue
            if entry.last_seen_status == status and entry.last_seen_title == title:
                continue
            action_kind = (
                "done" if status == "done" and entry.last_seen_status != "done" else "update"
            )
            planned.append(
                {
                    "ueid": ueid,
                    "action": action_kind,
                    "status": status,
                    "title": title,
                }
            )

        payload = {
            "dry_run": True,
            "scanned": len(rows),
            "planned_emits": planned,
            "errors": [],
        }
        print(json.dumps(payload, default=str, indent=2), flush=True)
        return 0

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


def cmd_list(args: argparse.Namespace) -> int:
    """Enumerate entries in sync-state.json (forward) or sync-state-reverse.json."""
    _apply_state_override(args.sync_state)
    _apply_rev_state_override(args.reverse_state)

    if args.direction == "reverse":
        state = load_reverse_state(REVERSE_SYNC_STATE)
        entries_iter = ((ueid, entry) for ueid, entry in state.tasks.items())
        fields = ("ueid", "last_seen_status", "last_seen_title", "taskdog_id", "vault_path")
    else:
        state = load_state(SYNC_STATE)
        entries_iter = ((ueid, entry) for ueid, entry in state.tasks.items())
        fields = ("ueid", "last_status", "taskdog_id", "vault_path")

    if _wants_human(args):
        rows = []
        for ueid, entry in entries_iter:
            row = [ueid]
            for f in fields[1:]:
                row.append(str(getattr(entry, f, "") or ""))
            rows.append(row)
        _render_table(list(fields), rows)
    else:
        # JSON-per-line — one entry per line, mirrors cli_cli/taskdog_cli
        for ueid, entry in entries_iter:
            payload: dict[str, Any] = {"ueid": ueid}
            for f in fields[1:]:
                payload[f] = getattr(entry, f, None)
            print(json.dumps(payload, default=str), flush=True)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Check that every sync-state entry's vault_path still exists on disk."""
    _apply_state_override(args.sync_state)
    state = load_state(SYNC_STATE)

    missing: list[dict[str, Any]] = []
    for ueid, entry in state.tasks.items():
        vault_path = entry.vault_path
        if not vault_path:
            missing.append({"ueid": ueid, "reason": "no_vault_path"})
            continue
        if not Path(vault_path).exists():
            missing.append({"ueid": ueid, "vault_path": vault_path, "reason": "missing_file"})

    checked = len(state.tasks)
    payload = {
        "sync_state": str(SYNC_STATE),
        "checked": checked,
        "missing_vault_files": len(missing),
        "missing": missing,
    }

    if _wants_human(args):
        print(f"sync_state: {payload['sync_state']}", flush=True)
        _render_table(
            ["counter", "value"],
            [
                ["checked", str(checked)],
                ["missing_vault_files", str(len(missing))],
            ],
        )
        if missing:
            print("", flush=True)
            print("missing:", flush=True)
            for m in missing:
                print(
                    f"  - {m['ueid']}: {m.get('vault_path', m.get('reason'))}",
                    flush=True,
                )
    else:
        print(json.dumps(payload, indent=2), flush=True)

    return 1 if missing else 0


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
    sync_p.add_argument(
        "--dry-run",
        action="store_true",
        help="parse + diff against current state but DO NOT push to taskdog or save state",
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
    rev_p.add_argument(
        "--dry-run",
        action="store_true",
        help="list taskdog + diff vs snapshot but DO NOT enqueue TaskChange or save state",
    )
    _add_output_flags(rev_p)

    status_p = sub.add_parser("status", help="show sync state counts")
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

    list_p = sub.add_parser("list", help="enumerate sync-state entries")
    list_p.add_argument(
        "--direction",
        type=str,
        choices=["forward", "reverse"],
        default="forward",
        help="which state file to enumerate (default: forward)",
    )
    list_p.add_argument(
        "--sync-state",
        type=str,
        default=str(SYNC_STATE),
        help=f"path to sync-state.json (default: {SYNC_STATE})",
    )
    list_p.add_argument(
        "--reverse-state",
        type=str,
        default=str(REVERSE_SYNC_STATE),
        help=f"path to sync-state-reverse.json (default: {REVERSE_SYNC_STATE})",
    )
    _add_output_flags(list_p)

    validate_p = sub.add_parser("validate", help="check sync-state entries for missing vault files")
    validate_p.add_argument(
        "--sync-state",
        type=str,
        default=str(SYNC_STATE),
        help=f"path to sync-state.json (default: {SYNC_STATE})",
    )
    _add_output_flags(validate_p)

    args = parser.parse_args(argv)

    if args.command == "sync":
        return cmd_sync(args)
    if args.command == "reverse":
        return cmd_reverse(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "validate":
        return cmd_validate(args)
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
