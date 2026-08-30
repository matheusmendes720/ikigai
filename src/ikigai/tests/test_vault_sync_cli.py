"""Tests for ikigai.vault.sync_cli — operator wrapper for vault sync engine."""

from __future__ import annotations

import json
import sqlite3
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
                return {"id": str(cur.lastrowid)}
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


def _read_counter(out: str, name: str) -> str:
    """Pull the value cell for a given counter name from the rendered table."""
    for line in out.splitlines():
        if line.startswith(name):
            return line[len(name) :].strip()
    raise AssertionError(f"counter {name!r} not found in output:\n{out}")


def test_sync_returns_zero_and_persists_state(cli_env: dict, capsys: pytest.CaptureFixture) -> None:
    """`sync` runs run_sync(), prints result summary, exits 0."""
    _write_task_md(
        cli_env["vault"],
        "plans/q3/build-wiremesh.md",
        "tsk:build-wiremesh:11111111-1111-1111-1111-111111111111:1111111111111111",
        "Build wiremesh",
    )
    rc = main(["sync", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert _read_counter(out, "scanned") == "1"
    assert _read_counter(out, "added") == "1"
    # State file should now exist with one entry
    assert cli_env["state"].exists()
    state_data = json.loads(cli_env["state"].read_text())
    assert state_data["version"] == 1
    assert len(state_data["tasks"]) == 1


def test_sync_with_no_tasks_returns_zero(cli_env: dict, capsys: pytest.CaptureFixture) -> None:
    """Empty vault → scanned: 0, added: 0, exit 0."""
    rc = main(["sync", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert _read_counter(out, "scanned") == "0"


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
    rc = main(["sync", "--human", "--vault-root", str(other_vault)])
    assert rc == 0
    out = capsys.readouterr().out
    assert _read_counter(out, "scanned") == "1"
    assert _read_counter(out, "added") == "1"


def test_sync_human_flag_renders_table(cli_env: dict, capsys: pytest.CaptureFixture) -> None:
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


def test_sync_json_flag_emits_object(cli_env: dict, capsys: pytest.CaptureFixture) -> None:
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
