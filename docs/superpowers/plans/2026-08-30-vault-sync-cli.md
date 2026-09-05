# Vault Sync CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an operator-facing CLI `python -m ikigai.vault.sync_cli {sync,reverse,status}` that wraps the existing `run_sync()` and `reverse_sync()` functions in `src/ikigai/src/ikigai/vault/sync.py`.

**Architecture:** Thin wrapper — same shape as `src/mesh/cli_cli.py` and `src/mesh/taskdog_cli.py`. Argparse with three subcommands; each subcommand invokes the matching existing function and prints the result. Path overrides via module-level monkeypatching (consistent with sibling CLIs). TTY-aware `--human` / `--json` output. No new logic in the sync engine itself — this is purely operator UX.

**Tech Stack:** Python 3.11+, argparse stdlib, pydantic v2 (existing models in `sync.py`), `frontmatter` (already a dep).

## Global Constraints

- **No edits to scoring/formula/qhe/regime/weight** — algorithm gate from memory `algorithm-gate-system-readiness-not-sonho-2026-08-29.md` forbids touching scoring code.
- **vault_write is the ONLY vault writer** per attribution report §7 (already shipped). This CLI never writes to vault directly — it delegates to `run_sync()` / `reverse_sync()` which in turn call `vault_write` via the propagator.
- **Pydantic v2 strict** — `frozen=True`, `extra="forbid"` on all schemas (already enforced in `sync.py`; do not change).
- **os.replace() for atomic writes** — Windows-safe per B6.4 lesson. Already used inside `save_state()` / `save_reverse_state()`. Do not introduce `Path.rename()`.
- **No new dependencies** — argparse + json + sys only.
- **Pre-flight regression mandatory** per `verify-agent-fabricated-failures.md` memory. Run `python -m pytest src/ikigai/tests/test_vault_sync*.py src/ikigai/tests/test_bidirectional_vault_sync_e2e.py src/ikigai/tests/test_reverse_sync*.py src/ikigai/tests/test_ikigai_sync_vault.py` from project root after the change to confirm no regression.
- **Pattern mirror** — `_render_table`, `_wants_human`, `_apply_*_override`, `_add_output_flags` helpers must follow `src/mesh/cli_cli.py:71-224` verbatim in shape (kept inline — no shared module).
- **Module entry** — `python -m ikigai.vault.sync_cli` (NOT `python -m ikigai.sync_cli`). Module lives under `src/ikigai/src/ikigai/vault/`.
- **Test entry** — tests live in `src/ikigai/tests/test_vault_sync_cli.py`. The existing `src/ikigai/tests/conftest.py` already handles `sys.path` for `ikigai.X` imports.
- **Per-fork adapter for sync** — `run_sync(vault_root, state_path, adapter)` expects `adapter.call_tool(name, args)` (a method on the fork adapter). For CLI invocation the adapter is the live MCP client (`tools.taskdog`) — see `src/ikigai/tests/test_vault_sync.py` for the stub pattern. The CLI builds a thin adapter wrapper.

---

## File Structure

| Path | Purpose |
|------|---------|
| `src/ikigai/src/ikigai/vault/sync_cli.py` (NEW) | CLI entry. ~250 lines. |
| `src/ikigai/tests/test_vault_sync_cli.py` (NEW) | Tests. ~250 lines. |

No other files are touched. The sync engine, lock, and vault_write are untouched.

---

## Default Paths (resolved at CLI import time)

| Variable | Default |
|----------|---------|
| `VAULT_ROOT` | `<repo>/vault/` |
| `SYNC_STATE` | `<repo>/data/sync-state.json` |
| `REVERSE_SYNC_STATE` | `<repo>/data/sync-state-reverse.json` |
| `TASKDOG_DB` | `<repo>/data/taskdog/tasks.db` |

These are module-level constants in `sync_cli.py`. `--vault-root`, `--sync-state`, `--reverse-state`, `--taskdog-db` flags override them via the same monkeypatch pattern used in `src/mesh/cli_cli.py:102-112` and `src/mesh/taskdog_cli.py:104-114`.

---

### Task 1: Build sync_cli skeleton + `sync` subcommand

**Files:**
- Create: `src/ikigai/src/ikigai/vault/sync_cli.py`
- Test: `src/ikigai/tests/test_vault_sync_cli.py`

**Interfaces:**
- Consumes: `from ikigai.vault.sync import run_sync, SyncResult, parse_vault_tasks` (existing API)
- Produces: `main(argv: list[str] | None = None) -> int` with `sync` subcommand working; `reverse` and `status` subcommands stubbed as `parser.error("not implemented")`

#### Step 1: Write the failing test for `sync` subcommand

Create `src/ikigai/tests/test_vault_sync_cli.py`:

```python
"""Tests for ikigai.vault.sync_cli — operator wrapper for vault sync engine."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

# Ensure src/ is on sys.path (handled by src/ikigai/tests/conftest.py)
from ikigai.vault.sync_cli import (
    _REVERSE_SYNC_STATE_DEFAULT,
    _SYNC_STATE_DEFAULT,
    _TASKDOG_DB_DEFAULT,
    _VAULT_ROOT_DEFAULT,
    main,
)


# ──────────────────── Stub adapter (mimics MCP tools.taskdog) ────────────────────


class _StubTaskdogAdapter:
    """Mimics the interface `run_sync()` and `reverse_sync()` need.

    run_sync() uses `adapter.call_tool(name, args)` (sync engine line 264-276).
    reverse_sync() uses `adapter.list_all()` (sync engine line 396).

    Stores all `taskdog_add`/`taskdog_done` calls in `_calls` and persists
    rows to a SQLite DB at `db_path` with the columns the sync engine
    expects from list_all():
      ueid, name, status, priority, planned_start, planned_end, deadline, created_at
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ueid TEXT UNIQUE,
                    name TEXT,
                    status TEXT,
                    priority INTEGER,
                    planned_start TEXT,
                    planned_end TEXT,
                    deadline TEXT,
                    created_at TEXT
                );
            """)
            conn.commit()
        finally:
            conn.close()
        self._calls: list[dict] = []

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Stub MCP call_tool — mimics tools.taskdog.{taskdog_add,taskdog_done}."""
        self._calls.append({"tool": name, "arguments": arguments})
        if name == "taskdog_add":
            conn = sqlite3.connect(self.db_path)
            try:
                cur = conn.execute(
                    "INSERT INTO tasks (ueid, name, status, priority, deadline, created_at) "
                    "VALUES (?, ?, 'planned', ?, ?, ?) "
                    "ON CONFLICT(ueid) DO UPDATE SET name=excluded.name",
                    (
                        arguments["ueid"],
                        arguments.get("title"),
                        arguments.get("priority"),
                        arguments.get("due"),
                        "2026-08-30T00:00:00+00:00",
                    ),
                )
                conn.commit()
                return {"id": cur.lastrowid}
            finally:
                conn.close()
        return {}

    def list_all(self) -> list[dict]:
        """Stub adapter.list_all() — return rows in the shape reverse_sync() expects."""
        if not self.db_path.exists():
            return []
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT ueid, name, status, priority, planned_start, "
                "planned_end, deadline, created_at FROM tasks"
            ).fetchall()
            return [
                {
                    "ueid": r[0],
                    "name": r[1],
                    "status": r[2],
                    "priority": r[3],
                    "planned_start": r[4],
                    "planned_end": r[5],
                    "deadline": r[6],
                    "created_at": r[7],
                }
                for r in rows
            ]
        finally:
            conn.close()


# ──────────────────── Fixtures ────────────────────


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Isolated env: tmp vault, tmp taskdog DB, tmp sync-state files.

    Also patches `src.mesh.queue.QUEUE_DIR` to a tmp dir (reverse_sync enqueues
    TaskChange events through the review queue — must be writable).
    """
    vault = tmp_path / "vault"
    (vault / "plans").mkdir(parents=True)
    state = tmp_path / "sync-state.json"
    rev_state = tmp_path / "sync-state-reverse.json"
    taskdog_db = tmp_path / "taskdog" / "tasks.db"

    adapter = _StubTaskdogAdapter(taskdog_db)

    # Patch module-level defaults before importing sync_cli
    import ikigai.vault.sync_cli as cli_mod

    monkeypatch.setattr(cli_mod, "VAULT_ROOT", vault)
    monkeypatch.setattr(cli_mod, "SYNC_STATE", state)
    monkeypatch.setattr(cli_mod, "REVERSE_SYNC_STATE", rev_state)
    monkeypatch.setattr(cli_mod, "TASKDOG_DB", taskdog_db)

    # Patch the adapter factory inside sync_cli to return our stub.
    # We do this by monkeypatching the module-level _build_adapter fn (Task 1
    # defines it; the test sets it before invoking main()).
    monkeypatch.setattr(cli_mod, "_build_adapter", lambda: adapter)

    # Patch review queue dir (reverse_sync enqueues to it)
    import src.mesh.queue as queue_mod

    monkeypatch.setattr(queue_mod, "QUEUE_DIR", tmp_path / "review_queue")

    return {
        "vault": vault,
        "state": state,
        "rev_state": rev_state,
        "taskdog_db": taskdog_db,
        "adapter": adapter,
    }


def _write_task_md(
    vault_root: Path,
    rel_path: str,
    ueid: str,
    title: str,
    status: str = "planned",
    priority: str = "high",
    due: str = "2026-09-15",
) -> None:
    """Helper: write a frontmatter-tagged task markdown to the vault."""
    full = vault_root / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(
        "---\n"
        f"ueid: {ueid}\n"
        f"title: {title}\n"
        f"status: {status}\n"
        f"priority: {priority}\n"
        f"due: {due}\n"
        "tags: [task]\n"
        "---\n\n"
        f"# {title}\n\nTask body.\n",
        encoding="utf-8",
    )


# ──────────────────── Module defaults ────────────────────


def test_module_defaults_resolve_under_repo() -> None:
    """Sanity: the module defaults point at <repo>/vault/ and <repo>/data/.

    The exact paths can drift as the repo grows; assert only that they
    exist (or could be created) and are anchored at the right places.
    """
    assert _VAULT_ROOT_DEFAULT.name == "vault"
    assert _SYNC_STATE_DEFAULT.name == "sync-state.json"
    assert _REVERSE_SYNC_STATE_DEFAULT.name == "sync-state-reverse.json"
    assert _TASKDOG_DB_DEFAULT.name == "tasks.db"


# ──────────────────── sync subcommand ────────────────────


def test_sync_returns_zero_and_persists_state(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`sync` runs run_sync(), prints result summary, exits 0."""
    _write_task_md(
        cli_env["vault"],
        "plans/q3/build-wiremesh.md",
        "tsk:build-wiremesh:11111111-1111-1111-1111-111111111111:1111111111111111",
        "Build wiremesh",
    )
    rc = main(["sync"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "scanned: 1" in out
    assert "added: 1" in out
    # State file should now exist with one entry
    assert cli_env["state"].exists()
    state_data = json.loads(cli_env["state"].read_text())
    assert state_data["version"] == 1
    assert len(state_data["tasks"]) == 1


def test_sync_with_no_tasks_returns_zero(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """Empty vault → scanned: 0, added: 0, exit 0."""
    rc = main(["sync"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "scanned: 0" in out


def test_sync_with_vault_override(
    cli_env: dict, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`--vault-root` reads from a different path than the module default."""
    other_vault = tmp_path / "other_vault"
    (other_vault / "plans").mkdir(parents=True)
    _write_task_md(
        other_vault,
        "plans/x.md",
        "tsk:x:22222222-2222-2222-2222-222222222222:2222222222222222",
        "X",
    )
    rc = main(["sync", "--vault-root", str(other_vault)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "scanned: 1" in out
    assert "added: 1" in out


def test_sync_human_flag_renders_table(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`--human` prints an aligned table; `--json` prints JSON object."""
    _write_task_md(
        cli_env["vault"],
        "plans/q3/a.md",
        "tsk:a:33333333-3333-3333-3333-333333333333:3333333333333333",
        "A",
    )
    rc = main(["sync", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    # Table header
    assert "COUNTER" in out
    assert "VALUE" in out


def test_sync_json_flag_emits_object(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`--json` prints one JSON object (not JSON-per-line)."""
    rc = main(["sync", "--json"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    parsed = json.loads(out)
    assert "scanned" in parsed
    assert "added" in parsed
    assert "duration_s" in parsed


def test_main_without_command_exits_nonzero() -> None:
    """argparse must reject missing subcommand."""
    with pytest.raises(SystemExit):
        main([])


def test_reverse_subcommand_stub_not_implemented(cli_env: dict) -> None:
    """Task 2 implements reverse — for now it must exit non-zero cleanly."""
    with pytest.raises(SystemExit):
        main(["reverse"])


def test_status_subcommand_stub_not_implemented(cli_env: dict) -> None:
    """Task 2 implements status — for now it must exit non-zero cleanly."""
    with pytest.raises(SystemExit):
        main(["status"])
```

#### Step 2: Run the failing tests

Run from project root:

```bash
python -m pytest src/ikigai/tests/test_vault_sync_cli.py -v --no-header
```

Expected: ALL tests FAIL with `ModuleNotFoundError: No module named 'ikigai.vault.sync_cli'` (the file doesn't exist yet).

#### Step 3: Implement `sync_cli.py`

Create `src/ikigai/src/ikigai/vault/sync_cli.py`:

```python
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
    """Stub — Task 2 implements the real reverse-sync CLI."""
    sys.stderr.write(
        "reverse subcommand not yet implemented (Task 2)\n",
        flush=True,
    )
    parser_err = argparse.ArgumentParser()
    parser_err.error("not implemented")
    return 2  # unreachable


def cmd_status(args: argparse.Namespace) -> int:
    """Stub — Task 2 implements the real status subcommand."""
    sys.stderr.write(
        "status subcommand not yet implemented (Task 2)\n",
        flush=True,
    )
    parser_err = argparse.ArgumentParser()
    parser_err.error("not implemented")
    return 2  # unreachable


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

    rev_p = sub.add_parser(
        "reverse", help="run taskdog → vault reverse sync (stub in Task 1)"
    )
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

    status_p = sub.add_parser(
        "status", help="show sync state counts (stub in Task 1)"
    )
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
    "main",
    "VAULT_ROOT",
    "SYNC_STATE",
    "REVERSE_SYNC_STATE",
    "TASKDOG_DB",
]


if __name__ == "__main__":
    raise SystemExit(main())
```

#### Step 4: Run tests and confirm pass

```bash
python -m pytest src/ikigai/tests/test_vault_sync_cli.py -v --no-header
```

Expected: 7 tests PASS (the 2 stub-not-implemented tests also PASS because `parser.error` raises `SystemExit`).

#### Step 5: Run ruff on the new file

```bash
python -m ruff check src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
python -m ruff format --check src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
```

Expected: clean. If ruff complains, fix the file(s) and re-run.

#### Step 6: Run pre-flight regression on existing vault sync tests

```bash
python -m pytest src/ikigai/tests/test_vault_sync.py src/ikigai/tests/test_vault_sync_e2e.py src/ikigai/tests/test_reverse_sync.py src/ikigai/tests/test_reverse_sync_state.py src/ikigai/tests/test_bidirectional_vault_sync_e2e.py src/ikigai/tests/test_ikigai_sync_vault.py -v --no-header
```

Expected: all existing tests still PASS (no regression from the new module existing).

#### Step 7: Commit Task 1

```bash
git add src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
git commit -m "feat(vault): sync_cli skeleton + sync subcommand (Task 1)"
```

---

### Task 2: Implement `reverse` and `status` subcommands

**Files:**
- Modify: `src/ikigai/src/ikigai/vault/sync_cli.py:200-225` (replace `cmd_reverse` and `cmd_status` stubs)
- Modify: `src/ikigai/tests/test_vault_sync_cli.py` (replace stub-assertion tests with real-assertion tests)

**Interfaces:**
- Consumes: `reverse_sync(state_path, adapter, source_fork="taskdog")` from `ikigai.vault.sync` (already imported)
- Consumes: `load_state(state_path)`, `load_reverse_state(state_path)` from `ikigai.vault.sync` (already imported)
- Produces: `cmd_reverse` runs `reverse_sync`, prints summary; `cmd_status` reads both state files, prints counts.

#### Step 1: Replace the stub-assertion tests with real-assertion tests

In `src/ikigai/tests/test_vault_sync_cli.py`, find:

```python
def test_reverse_subcommand_stub_not_implemented(cli_env: dict) -> None:
    """Task 2 implements reverse — for now it must exit non-zero cleanly."""
    with pytest.raises(SystemExit):
        main(["reverse"])


def test_status_subcommand_stub_not_implemented(cli_env: dict) -> None:
    """Task 2 implements status — for now it must exit non-zero cleanly."""
    with pytest.raises(SystemExit):
        main(["status"])
```

Replace with:

```python
# ──────────────────── reverse subcommand ────────────────────


def _seed_reverse_state(
    state_path: Path,
    entries: dict[str, dict],
) -> None:
    """Pre-populate sync-state-reverse.json so reverse_sync() can match orphans.

    reverse_sync() v1 ORPHAN HANDLING: NEW UEIDs not in the snapshot are
    SKIPPED. To exercise `emitted`, the snapshot must already contain the
    UEID. To exercise `skipped` on new rows, just call reverse_sync()
    with a taskdog row whose UEID is not in the snapshot.
    """
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"version": 1, "last_sync_at": None, "tasks": entries}),
        encoding="utf-8",
    )


def test_reverse_with_no_state_returns_zero(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """First-ever reverse_sync() with no snapshot → no orphans, all skipped."""
    # No state file, taskdog DB has no rows → scanned: 0
    rc = main(["reverse"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "scanned: 0" in out


def test_reverse_emits_for_known_ueid(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """UEID in snapshot + taskdog row with changed status → emits TaskChange."""
    ueid = "tsk:known:44444444-4444-4444-4444-444444444444:4444444444444444"
    _seed_reverse_state(
        cli_env["rev_state"],
        {
            ueid: {
                "last_seen_status": "planned",
                "last_seen_title": "Known",
                "taskdog_id": 1,
                "vault_path": "plans/q3/known.md",
            }
        },
    )
    # Seed taskdog DB with same UEID but status=done (changed)
    cli_env["adapter"].call_tool(
        "taskdog_add",
        {
            "ueid": ueid,
            "title": "Known",
            "priority": 1,
            "due": "2026-09-15",
        },
    )
    # Promote to done via direct SQL (taskdog_done would need MCP plumbing)
    conn = sqlite3.connect(cli_env["taskdog_db"])
    try:
        conn.execute("UPDATE tasks SET status = 'done' WHERE ueid = ?", (ueid,))
        conn.commit()
    finally:
        conn.close()

    rc = main(["reverse"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "scanned: 1" in out
    assert "emitted: 1" in out
    # The review queue file should now exist
    from src.mesh.queue import QUEUE_DIR

    queue_files = list(QUEUE_DIR.glob("*.json"))
    assert len(queue_files) >= 1


def test_reverse_skips_unknown_ueids(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """UEID in taskdog but NOT in snapshot → orphan, skipped (v1 behavior)."""
    cli_env["adapter"].call_tool(
        "taskdog_add",
        {
            "ueid": "tsk:orphan:55555555-5555-5555-5555-555555555555:5555555555555555",
            "title": "Orphan",
            "priority": 2,
            "due": "2026-10-01",
        },
    )
    rc = main(["reverse"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "scanned: 1" in out
    assert "emitted: 0" in out
    assert "skipped: 1" in out


def test_reverse_json_flag_emits_object(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`reverse --json` prints a JSON object."""
    rc = main(["reverse", "--json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out.strip())
    assert "scanned" in parsed
    assert "emitted" in parsed
    assert "skipped" in parsed


# ──────────────────── status subcommand ────────────────────


def test_status_with_no_state_files_returns_zero(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """Both state files missing → status prints zeros, exits 0."""
    rc = main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "sync_state" in out
    assert "forward_tasks" in out
    assert "reverse_tasks" in out
    assert "forward_tasks: 0" in out
    assert "reverse_tasks: 0" in out


def test_status_counts_state_entries(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """Pre-populated state files → counts match."""
    # Forward state
    cli_env["state"].parent.mkdir(parents=True, exist_ok=True)
    cli_env["state"].write_text(
        json.dumps(
            {
                "version": 1,
                "last_sync_at": "2026-08-30T00:00:00+00:00",
                "tasks": {
                    "tsk:a:11111111-1111-1111-1111-111111111111:1111111111111111": {},
                    "tsk:b:22222222-2222-2222-2222-222222222222:2222222222222222": {},
                },
            }
        ),
        encoding="utf-8",
    )
    # Reverse state
    cli_env["rev_state"].parent.mkdir(parents=True, exist_ok=True)
    cli_env["rev_state"].write_text(
        json.dumps(
            {
                "version": 1,
                "last_sync_at": "2026-08-30T00:00:00+00:00",
                "tasks": {
                    "tsk:x:33333333-3333-3333-3333-333333333333:3333333333333333": {}
                },
            }
        ),
        encoding="utf-8",
    )

    rc = main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "forward_tasks: 2" in out
    assert "reverse_tasks: 1" in out


def test_status_json_flag_emits_object(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`status --json` prints a JSON object with both state paths + counts."""
    rc = main(["status", "--json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out.strip())
    assert parsed["forward_tasks"] == 0
    assert parsed["reverse_tasks"] == 0
    assert "sync_state" in parsed
    assert "reverse_state" in parsed
```

#### Step 2: Run the failing tests

```bash
python -m pytest src/ikigai/tests/test_vault_sync_cli.py -v --no-header
```

Expected: the new `reverse_*` and `status_*` tests FAIL because `cmd_reverse` / `cmd_status` are still stubs. The sync_* tests should still PASS.

#### Step 3: Replace `cmd_reverse` and `cmd_status` stubs

In `src/ikigai/src/ikigai/vault/sync_cli.py`, find the stubs:

```python
def cmd_reverse(args: argparse.Namespace) -> int:
    """Stub — Task 2 implements the real reverse-sync CLI."""
    sys.stderr.write(
        "reverse subcommand not yet implemented (Task 2)\n",
        flush=True,
    )
    parser_err = argparse.ArgumentParser()
    parser_err.error("not implemented")
    return 2  # unreachable


def cmd_status(args: argparse.Namespace) -> int:
    """Stub — Task 2 implements the real status subcommand."""
    sys.stderr.write(
        "status subcommand not yet implemented (Task 2)\n",
        flush=True,
    )
    parser_err = argparse.ArgumentParser()
    parser_err.error("not implemented")
    return 2  # unreachable
```

Replace with:

```python
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
```

#### Step 4: Run the full vault_sync_cli test file

```bash
python -m pytest src/ikigai/tests/test_vault_sync_cli.py -v --no-header
```

Expected: all 17 tests PASS.

#### Step 5: Run ruff on the modified files

```bash
python -m ruff check src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
python -m ruff format --check src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
```

Expected: clean. If ruff complains, fix and re-run.

#### Step 6: Run pre-flight regression on ALL vault-related tests

```bash
python -m pytest src/ikigai/tests/test_vault_sync.py src/ikigai/tests/test_vault_sync_e2e.py src/ikigai/tests/test_reverse_sync.py src/ikigai/tests/test_reverse_sync_state.py src/ikigai/tests/test_bidirectional_vault_sync_e2e.py src/ikigai/tests/test_ikigai_sync_vault.py src/ikigai/tests/test_vault_sync_cli.py -v --no-header
```

Expected: ALL existing tests still PASS, plus the new vault_sync_cli tests PASS. Total: 17+ new tests PASS, zero regressions.

#### Step 7: Commit Task 2

```bash
git add src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
git commit -m "feat(vault): sync_cli reverse + status subcommands (Task 2)"
```

---

## Self-Review

**1. Spec coverage:** The user's directive was "we made the vault sync cli?" — answer was no, so the plan fills that gap. Three subcommands (sync / reverse / status) cover the operator surface for the existing sync engine. No spec gaps.

**2. Placeholder scan:**
- ❌ "TBD" → none
- ❌ "TODO" → none
- ❌ "implement later" → none (the stub functions in Task 1 are explicitly scoped to Task 2, which immediately implements them)
- ❌ "Add appropriate error handling" → error rendering is concrete: `result.errors` is iterated and printed
- ❌ "Similar to Task N" → no cross-task copying; each step shows its own code
- ❌ Step without code → every code-changing step has a `def` block

**3. Type consistency:**
- `SyncResult` fields: scanned, added, updated, completed, skipped, parse_errors, errors, duration_s — used consistently in `_render_sync_result` and `cmd_sync`'s JSON output
- `ReverseSyncResult` fields: scanned, emitted, skipped, errors, duration_s — used consistently in `_render_reverse_result` and `cmd_reverse`'s JSON output
- `load_state` → `SyncState` with `.tasks` (dict) + `.last_sync_at` (str | None) — used in `cmd_status`
- `load_reverse_state` → `ReverseSyncState` with `.tasks` (dict) + `.last_sync_at` (str | None) — used in `cmd_status`
- `_build_adapter()` returns `Any` because tests override it with `MonkeyPatch` and we don't want a tight type coupling at this layer
- `_StubTaskdogAdapter.call_tool(name, args)` and `.list_all()` match the existing interfaces used by `run_sync()` and `reverse_sync()` respectively

**4. Smoke test for live invocation:** After both tasks commit, the executor should also run this bash smoke (mirrors the pattern from `phase-b6-combo-a-bidirectional-vault-sync-shipped-2026-08-29.md`):

```bash
# With a real (or empty) vault + taskdog DB
python -m ikigai.vault.sync_cli sync --json
python -m ikigai.vault.sync_cli reverse --json
python -m ikigai.vault.sync_cli status --json
```

Expected: each prints a JSON object; status returns forward_tasks + reverse_tasks counts.

---

### Task 3: Add `list` and `validate` subcommands

**Files:**
- Modify: `src/ikigai/src/ikigai/vault/sync_cli.py` (replace the bottom-of-file `cmd_status` is fine; add `cmd_list` and `cmd_validate` between `cmd_reverse` and `cmd_status`)
- Modify: `src/ikigai/tests/test_vault_sync_cli.py` (append new tests)

**Interfaces:**
- `cmd_list(args)` reads `sync-state.json` (forward) and optionally `sync-state-reverse.json` (with `--direction reverse`); prints entries as a table or one JSON per line.
- `cmd_validate(args)` reads `sync-state.json` and checks each entry's `vault_path` still exists on disk; flags entries where the vault file is missing or unreadable.

#### Step 1: Write the failing tests

Append to `src/ikigai/tests/test_vault_sync_cli.py`:

```python
# ──────────────────── list subcommand ────────────────────


def test_list_default_direction_is_forward(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`list` (no flag) reads sync-state.json and prints entries."""
    cli_env["state"].parent.mkdir(parents=True, exist_ok=True)
    cli_env["state"].write_text(
        json.dumps(
            {
                "version": 1,
                "last_sync_at": "2026-08-30T00:00:00+00:00",
                "tasks": {
                    "tsk:a:11111111-1111-1111-1111-111111111111:1111111111111111": {
                        "last_synced_at": "2026-08-30T00:00:00+00:00",
                        "last_status": "planned",
                        "taskdog_id": 1,
                        "vault_path": "plans/q3/a.md",
                    },
                    "tsk:b:22222222-2222-2222-2222-222222222222:2222222222222222": {
                        "last_synced_at": "2026-08-30T00:00:00+00:00",
                        "last_status": "done",
                        "taskdog_id": 2,
                        "vault_path": "plans/q3/b.md",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    rc = main(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    # Human mode default in tests = pipe → JSON-per-line
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    assert len(lines) == 2
    parsed = [json.loads(ln) for ln in lines]
    ueids = {p["ueid"] for p in parsed}
    assert "tsk:a:11111111-1111-1111-1111-111111111111:1111111111111111" in ueids
    assert "tsk:b:22222222-2222-2222-2222-222222222222:2222222222222222" in ueids


def test_list_direction_reverse(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`list --direction reverse` reads sync-state-reverse.json."""
    cli_env["rev_state"].parent.mkdir(parents=True, exist_ok=True)
    cli_env["rev_state"].write_text(
        json.dumps(
            {
                "version": 1,
                "last_sync_at": "2026-08-30T00:00:00+00:00",
                "tasks": {
                    "tsk:x:33333333-3333-3333-3333-333333333333:3333333333333333": {
                        "last_seen_status": "planned",
                        "last_seen_title": "X",
                        "taskdog_id": 5,
                        "vault_path": "plans/q3/x.md",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    rc = main(["list", "--direction", "reverse"])
    assert rc == 0
    parsed = [json.loads(ln) for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(parsed) == 1
    assert parsed[0]["ueid"].startswith("tsk:x:")


def test_list_with_empty_state_prints_nothing(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """No state file → empty output, exit 0."""
    rc = main(["list"])
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_list_human_flag_renders_table(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`list --human` prints an aligned table."""
    cli_env["state"].parent.mkdir(parents=True, exist_ok=True)
    cli_env["state"].write_text(
        json.dumps(
            {
                "version": 1,
                "last_sync_at": None,
                "tasks": {
                    "tsk:a:11111111-1111-1111-1111-111111111111:1111111111111111": {
                        "last_synced_at": "2026-08-30T00:00:00+00:00",
                        "last_status": "planned",
                        "taskdog_id": None,
                        "vault_path": "plans/a.md",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    rc = main(["list", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "UEID" in out
    assert "VAULT_PATH" in out
    assert "LAST_STATUS" in out


# ──────────────────── validate subcommand ────────────────────


def test_validate_with_no_state_returns_zero(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """No state file → nothing to validate, exit 0."""
    rc = main(["validate"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "checked: 0" in out
    assert "missing_vault_files: 0" in out


def test_validate_flags_missing_vault_files(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """State entry whose vault_path does NOT exist on disk → flagged."""
    cli_env["state"].parent.mkdir(parents=True, exist_ok=True)
    cli_env["state"].write_text(
        json.dumps(
            {
                "version": 1,
                "last_sync_at": "2026-08-30T00:00:00+00:00",
                "tasks": {
                    "tsk:gone:11111111-1111-1111-1111-111111111111:1111111111111111": {
                        "last_synced_at": "2026-08-30T00:00:00+00:00",
                        "last_status": "planned",
                        "taskdog_id": 1,
                        "vault_path": "plans/q3/gone.md",  # does NOT exist
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    rc = main(["validate"])
    assert rc == 1  # non-zero: drift detected
    out = capsys.readouterr().out
    assert "checked: 1" in out
    assert "missing_vault_files: 1" in out


def test_validate_with_existing_files_returns_zero(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """State entry whose vault_path exists → no drift, exit 0."""
    _write_task_md(
        cli_env["vault"],
        "plans/q3/alive.md",
        "tsk:alive:22222222-2222-2222-2222-222222222222:2222222222222222",
        "Alive",
    )
    cli_env["state"].parent.mkdir(parents=True, exist_ok=True)
    cli_env["state"].write_text(
        json.dumps(
            {
                "version": 1,
                "last_sync_at": "2026-08-30T00:00:00+00:00",
                "tasks": {
                    "tsk:alive:22222222-2222-2222-2222-222222222222:2222222222222222": {
                        "last_synced_at": "2026-08-30T00:00:00+00:00",
                        "last_status": "planned",
                        "taskdog_id": 1,
                        "vault_path": str(
                            cli_env["vault"] / "plans" / "q3" / "alive.md"
                        ),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    rc = main(["validate"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "checked: 1" in out
    assert "missing_vault_files: 0" in out


def test_validate_json_flag_emits_object(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`validate --json` prints a JSON object."""
    rc = main(["validate", "--json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out.strip())
    assert "checked" in parsed
    assert "missing_vault_files" in parsed
    assert "missing" in parsed
    assert parsed["missing"] == []
```

#### Step 2: Run the failing tests

```bash
python -m pytest src/ikigai/tests/test_vault_sync_cli.py -v --no-header -k "list_ or validate_"
```

Expected: all 7 new tests FAIL with `parser.error("unknown command")` (the subcommands don't exist yet).

#### Step 3: Add `cmd_list`, `cmd_validate`, and wire them into `main`

In `src/ikigai/src/ikigai/vault/sync_cli.py`, after `cmd_reverse` and before `cmd_status`, add:

```python
def cmd_list(args: argparse.Namespace) -> int:
    """Enumerate entries in sync-state.json (forward) or sync-state-reverse.json."""
    _apply_state_override(args.sync_state)
    _apply_rev_state_override(args.reverse_state)

    if args.direction == "reverse":
        state = load_reverse_state(REVERSE_SYNC_STATE)
        entries_iter = (
            (ueid, entry) for ueid, entry in state.tasks.items()
        )
        fields = ("ueid", "last_seen_status", "last_seen_title", "taskdog_id", "vault_path")
    else:
        state = load_state(SYNC_STATE)
        entries_iter = (
            (ueid, entry) for ueid, entry in state.tasks.items()
        )
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
            print(json.dumps(payload, default=str, flush=True))
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
                print(f"  - {m['ueid']}: {m.get('vault_path', m.get('reason'))}", flush=True)
    else:
        print(json.dumps(payload, indent=2, flush=True))

    return 1 if missing else 0
```

Then update `main()` — find the subparser block and add `list_p` and `validate_p` BEFORE `status_p`:

```python
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

    validate_p = sub.add_parser(
        "validate", help="check sync-state entries for missing vault files"
    )
    validate_p.add_argument(
        "--sync-state",
        type=str,
        default=str(SYNC_STATE),
        help=f"path to sync-state.json (default: {SYNC_STATE})",
    )
    _add_output_flags(validate_p)
```

And in the dispatch block at the bottom of `main()`, add:

```python
    if args.command == "list":
        return cmd_list(args)
    if args.command == "validate":
        return cmd_validate(args)
```

#### Step 4: Run the new tests

```bash
python -m pytest src/ikigai/tests/test_vault_sync_cli.py -v --no-header -k "list_ or validate_"
```

Expected: all 7 new tests PASS.

#### Step 5: Run ruff on the modified file

```bash
python -m ruff check src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
python -m ruff format --check src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
```

Expected: clean.

#### Step 6: Commit Task 3

```bash
git add src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
git commit -m "feat(vault): sync_cli list + validate subcommands (Task 3)"
```

---

### Task 4: Add `--dry-run` flag to `sync` and `reverse`

**Files:**
- Modify: `src/ikigai/src/ikigai/vault/sync_cli.py:cmd_sync`, `:cmd_reverse`, and the `sync_p` / `rev_p` subparsers in `main()`
- Modify: `src/ikigai/tests/test_vault_sync_cli.py` (append new tests)

**Interfaces:**
- `--dry-run` (boolean) is added to both `sync` and `reverse` subcommands.
- In `cmd_sync`: when `args.dry_run` is True, **do NOT call `run_sync()`** (which writes state); instead call `parse_vault_tasks(vault_root)` and `diff(tasks, SyncState())` and print the planned actions.
- In `cmd_reverse`: when `args.dry_run` is True, **do NOT call `reverse_sync()`** (which writes state and enqueues events); instead call `adapter.list_all()`, compute what `reverse_sync` would emit, and print the planned events.

This is purely an operator preview — no state writes, no adapter calls (for `sync` dry-run), no queue enqueues.

#### Step 1: Write the failing tests

Append to `src/ikigai/tests/test_vault_sync_cli.py`:

```python
# ──────────────────── --dry-run on sync ────────────────────


def test_sync_dry_run_does_not_write_state(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`sync --dry-run` parses + diffs but does NOT touch sync-state.json."""
    _write_task_md(
        cli_env["vault"],
        "plans/q3/dry.md",
        "tsk:dry:66666666-6666-6666-6666-666666666666:6666666666666666",
        "Dry",
    )
    rc = main(["sync", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    # Should report what would happen (planned: NEW action)
    assert "planned_new: 1" in out or "DRY-RUN" in out.upper()
    # State file MUST NOT exist
    assert not cli_env["state"].exists()


def test_sync_dry_run_does_not_call_adapter(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`sync --dry-run` MUST NOT invoke adapter.call_tool — preview only."""
    _write_task_md(
        cli_env["vault"],
        "plans/q3/dry.md",
        "tsk:dry:77777777-7777-7777-7777-777777777777:7777777777777777",
        "Dry",
    )
    adapter = cli_env["adapter"]
    rc = main(["sync", "--dry-run"])
    assert rc == 0
    assert adapter._calls == []  # no adapter invocations


def test_sync_dry_run_json_flag(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`sync --dry-run --json` prints a JSON object with the planned actions."""
    _write_task_md(
        cli_env["vault"],
        "plans/q3/dry.md",
        "tsk:dry:88888888-8888-8888-8888-888888888888:8888888888888888",
        "Dry",
    )
    rc = main(["sync", "--dry-run", "--json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out.strip())
    assert "dry_run" in parsed
    assert parsed["dry_run"] is True
    assert "planned_actions" in parsed
    assert len(parsed["planned_actions"]) == 1
    assert parsed["planned_actions"][0]["kind"] == "new"


# ──────────────────── --dry-run on reverse ────────────────────


def test_reverse_dry_run_does_not_enqueue(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`reverse --dry-run` MUST NOT enqueue TaskChange events."""
    ueid = "tsk:known:99999999-9999-9999-9999-999999999999:9999999999999999"
    _seed_reverse_state(
        cli_env["rev_state"],
        {
            ueid: {
                "last_seen_status": "planned",
                "last_seen_title": "Known",
                "taskdog_id": 1,
                "vault_path": "plans/q3/known.md",
            }
        },
    )
    cli_env["adapter"].call_tool(
        "taskdog_add",
        {"ueid": ueid, "title": "Known", "priority": 1, "due": "2026-09-15"},
    )
    # Promote to done directly via SQL
    conn = sqlite3.connect(cli_env["taskdog_db"])
    try:
        conn.execute("UPDATE tasks SET status = 'done' WHERE ueid = ?", (ueid,))
        conn.commit()
    finally:
        conn.close()

    rc = main(["reverse", "--dry-run"])
    assert rc == 0
    # No review queue files
    from src.mesh.queue import QUEUE_DIR

    queue_files = list(QUEUE_DIR.glob("*.json"))
    assert queue_files == []


def test_reverse_dry_run_json_flag(
    cli_env: dict, capsys: pytest.CaptureFixture
) -> None:
    """`reverse --dry-run --json` prints planned emits."""
    rc = main(["reverse", "--dry-run", "--json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out.strip())
    assert "dry_run" in parsed
    assert parsed["dry_run"] is True
    assert "planned_emits" in parsed
```

#### Step 2: Run the failing tests

```bash
python -m pytest src/ikigai/tests/test_vault_sync_cli.py -v --no-header -k "dry_run"
```

Expected: all 5 new tests FAIL because `--dry-run` is not yet wired.

#### Step 3: Add `--dry-run` to `cmd_sync`

In `src/ikigai/src/ikigai/vault/sync_cli.py`, replace `cmd_sync` with:

```python
def cmd_sync(args: argparse.Namespace) -> int:
    """Run vault → taskdog sync (or preview without side effects)."""
    from ikigai.vault.sync import (
        SyncState,
        diff as sync_diff,
        parse_vault_tasks,
    )

    _apply_vault_override(args.vault_root)
    _apply_state_override(args.sync_state)
    _apply_taskdog_override(args.taskdog_db)

    if args.dry_run:
        # Preview-only: parse + diff against empty state, do NOT call adapter,
        # do NOT write state file.
        tasks = parse_vault_tasks(VAULT_ROOT)
        actions = sync_diff(tasks, SyncState())
        planned = [{"kind": a.kind.value, "ueid": a.record.ueid, "title": a.record.title} for a in actions]
        payload = {
            "dry_run": True,
            "scanned": len(tasks),
            "planned_actions": planned,
        }
        if _wants_human(args):
            print("DRY-RUN — no state writes, no adapter calls", flush=True)
            _render_table(
                ["kind", "ueid", "title"],
                [[a["kind"], a["ueid"], a["title"]] for a in planned] or [["<none>", "", ""]],
            )
        else:
            print(json.dumps(payload, indent=2, flush=True))
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
```

Add the flag to the `sync_p` subparser in `main()`:

```python
    sync_p.add_argument(
        "--dry-run",
        action="store_true",
        help="preview changes without writing state or calling the adapter",
    )
```

#### Step 4: Add `--dry-run` to `cmd_reverse`

Replace `cmd_reverse` with:

```python
def cmd_reverse(args: argparse.Namespace) -> int:
    """Run taskdog → vault reverse sync (or preview without side effects)."""
    _apply_rev_state_override(args.sync_state)
    _apply_taskdog_override(args.taskdog_db)

    if args.dry_run:
        # Preview-only: enumerate adapter + diff vs snapshot, do NOT enqueue,
        # do NOT write state.
        adapter = _build_adapter()
        state = load_reverse_state(REVERSE_SYNC_STATE)
        try:
            rows = adapter.list_all()
        except Exception as exc:
            sys.stderr.write(f"adapter.list_all() failed: {exc}\n", flush=True)
            return 2
        planned_emits: list[dict[str, Any]] = []
        for row in rows:
            ueid = row.get("ueid")
            if not ueid:
                continue
            status = row.get("status", "planned")
            title = row.get("name", "")
            entry = state.tasks.get(ueid)
            if entry is None:
                continue  # orphan → skipped in real run, skip in dry-run too
            if entry.last_seen_status == status and entry.last_seen_title == title:
                continue  # unchanged
            planned_emits.append({"ueid": ueid, "status": status, "title": title})
        payload = {
            "dry_run": True,
            "scanned": len(rows),
            "planned_emits": planned_emits,
        }
        if _wants_human(args):
            print("DRY-RUN — no state writes, no queue enqueues", flush=True)
            _render_table(
                ["ueid", "status", "title"],
                [[e["ueid"], e["status"], e["title"]] for e in planned_emits]
                or [["<none>", "", ""]],
            )
        else:
            print(json.dumps(payload, indent=2, flush=True))
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
```

Add the flag to the `rev_p` subparser in `main()`:

```python
    rev_p.add_argument(
        "--dry-run",
        action="store_true",
        help="preview emits without writing state or enqueueing TaskChange events",
    )
```

#### Step 5: Run all vault_sync_cli tests

```bash
python -m pytest src/ikigai/tests/test_vault_sync_cli.py -v --no-header
```

Expected: all 22 tests PASS (17 from Tasks 1-2 + 5 new from Task 4).

#### Step 6: Run ruff + format

```bash
python -m ruff check src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
python -m ruff format --check src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
```

Expected: clean.

#### Step 7: Pre-flight regression

```bash
python -m pytest src/ikigai/tests/test_vault_sync.py src/ikigai/tests/test_vault_sync_e2e.py src/ikigai/tests/test_reverse_sync.py src/ikigai/tests/test_reverse_sync_state.py src/ikigai/tests/test_bidirectional_vault_sync_e2e.py src/ikigai/tests/test_ikigai_sync_vault.py src/ikigai/tests/test_vault_sync_cli.py -v --no-header
```

Expected: 22+ new tests PASS, zero regressions in the existing 6 files.

#### Step 8: Commit Task 4

```bash
git add src/ikigai/src/ikigai/vault/sync_cli.py src/ikigai/tests/test_vault_sync_cli.py
git commit -m "feat(vault): sync_cli --dry-run on sync + reverse (Task 4)"
```

---

## Updated Self-Review

**1. Spec coverage:** After Tasks 1-4 the CLI has 5 subcommands and 2 flags:
- `sync` — full vault → taskdog sync
- `reverse` — full taskdog → vault sync (with queue enqueue)
- `status` — state file counts
- `list` — enumerate entries (forward or reverse direction)
- `validate` — drift check (missing vault files)
- `--dry-run` — preview mode on `sync` / `reverse`
- `--human` / `--json` — output mode (TTY-aware default)

The only remaining operator gap is destructive ops (`reset`, `rebuild`) — explicitly deferred as YAGNI for v1.

**2. Placeholder scan:** Same as before — no TBDs, no "implement later", every code-changing step has its `def` block.

**3. Type consistency:**
- `SyncState.tasks` is `dict[str, SyncTaskEntry]` — `cmd_list` iterates it directly (✓)
- `ReverseSyncState.tasks` is `dict[str, ReverseSyncTaskEntry]` — `cmd_list --direction reverse` iterates it directly (✓)
- `SyncTaskEntry` fields: `last_synced_at`, `last_status`, `taskdog_id`, `vault_path` (✓ used in `cmd_list`)
- `ReverseSyncTaskEntry` fields: `last_seen_status`, `last_seen_title`, `taskdog_id`, `vault_path` (✓ used in `cmd_list --direction reverse`)
- `parse_vault_tasks(vault_root: Path) -> list[TaskRecord]` (✓ used in `cmd_sync --dry-run`)
- `diff(tasks: list[TaskRecord], state: SyncState) -> list[SyncAction]` (✓ used in `cmd_sync --dry-run`)
- `SyncAction.kind: SyncActionKind` is an enum; `.value` returns the string ("new", "changed", etc.) (✓ used in dry-run payload)

**4. Live smoke after Tasks 1-4:**

```bash
python -m ikigai.vault.sync_cli sync --dry-run --json
python -m ikigai.vault.sync_cli sync --json
python -m ikigai.vault.sync_cli list --json
python -m ikigai.vault.sync_cli validate --json
python -m ikigai.vault.sync_cli status --json
python -m ikigai.vault.sync_cli reverse --dry-run --json
python -m ikigai.vault.sync_cli reverse --json
```

Expected: each prints a JSON object; `validate` exits 1 if any vault file is missing, 0 otherwise.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-30-vault-sync-cli.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh implementer subagent per task, two-stage review after each.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch with checkpoints.

Which approach?
