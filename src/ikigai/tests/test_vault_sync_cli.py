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


def test_reverse_with_no_state_returns_zero(cli_env: dict, capsys: pytest.CaptureFixture) -> None:
    """First-ever reverse_sync() with no snapshot → no orphans, all skipped."""
    # No state file, taskdog DB has no rows → scanned: 0
    rc = main(["reverse", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert _read_counter(out, "scanned") == "0"


def test_reverse_emits_for_known_ueid(cli_env: dict, capsys: pytest.CaptureFixture) -> None:
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

    rc = main(["reverse", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert _read_counter(out, "scanned") == "1"
    assert _read_counter(out, "emitted") == "1"
    # The review queue file should now exist
    from src.mesh.queue import QUEUE_DIR

    queue_files = list(QUEUE_DIR.glob("*.json"))
    assert len(queue_files) >= 1


def test_reverse_skips_unknown_ueids(cli_env: dict, capsys: pytest.CaptureFixture) -> None:
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
    rc = main(["reverse", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert _read_counter(out, "scanned") == "1"
    assert _read_counter(out, "emitted") == "0"
    assert _read_counter(out, "skipped") == "1"


def test_reverse_json_flag_emits_object(cli_env: dict, capsys: pytest.CaptureFixture) -> None:
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
    rc = main(["status", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "sync_state" in out
    assert "forward_tasks" in out
    assert "reverse_tasks" in out
    assert _read_counter(out, "forward_tasks") == "0"
    assert _read_counter(out, "reverse_tasks") == "0"


def test_status_counts_state_entries(cli_env: dict, capsys: pytest.CaptureFixture) -> None:
    """Pre-populated state files → counts match."""
    # Forward state
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
                        "taskdog_id": "1",
                        "vault_path": "plans/q3/a.md",
                    },
                    "tsk:b:22222222-2222-2222-2222-222222222222:2222222222222222": {
                        "last_synced_at": "2026-08-30T00:00:00+00:00",
                        "last_status": "done",
                        "taskdog_id": "2",
                        "vault_path": "plans/q3/b.md",
                    },
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

    rc = main(["status", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert _read_counter(out, "forward_tasks") == "2"
    assert _read_counter(out, "reverse_tasks") == "1"


def test_status_json_flag_emits_object(cli_env: dict, capsys: pytest.CaptureFixture) -> None:
    """`status --json` prints a JSON object with both state paths + counts."""
    rc = main(["status", "--json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out.strip())
    assert parsed["forward_tasks"] == 0
    assert parsed["reverse_tasks"] == 0
    assert "sync_state" in parsed
    assert "reverse_state" in parsed
