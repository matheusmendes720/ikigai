"""M164 — td note subsystem tests.

Covers the new subcommands added in M164:
    note add <ueid> <text> [--json|--human]
    note show <ueid>        [--json|--human]

Notes are persisted to the `audit_log` table (sharing the same SQLite
DB as the canonical tasks table). These tests assert:
    - add appends one row with the right (ueid, action='note', actor='cli')
      and sanitized text
    - show filters to action='note' only (other audit rows stay invisible)
    - multi-line text is preserved (newlines kept, control chars stripped)
    - text > 1024 chars is rejected with a clear error
    - --json produces one JSON object per line, --human renders a table
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "src"
PY = REPO_ROOT / "src" / "ikigai" / ".venv" / "Scripts" / "python.exe"

# Canonical 4-part UEID fixture (matches _UEID_PATTERN in
# src/contracts/common.py — 4-part type:slug:uuid:hash).
_UEID = "tsk:note-test:00000000-0000-0000-0000-000000000000:0000000000000000"
_OTHER_UEID = (
    "tsk:other-test:00000000-0000-0000-0000-000000000000:1111111111111111"
)


def _run_cli(*args: str, cwd: Path | None = None, db_path: Path | None = None) -> subprocess.CompletedProcess:
    """Invoke `python -m src.mesh.taskdog_cli <args>` and capture output.

    db_path: when provided, monkeypatches src.mesh.adapters.taskdog.TASKDOG_DB
    in the subprocess via a small bootstrap shim file. Same pattern as
    tests/mesh/test_m151_td_cli.py — we can't pytest-monkeypatch a subprocess.
    """
    env_overlay = {"PYTHONPATH": str(SRC), "TASKDOG_HTTP_ENABLED": "0"}
    if db_path is not None:
        bootstrap = (
            "import sys, pathlib;"
            f"sys.path.insert(0, r'{SRC}');"
            "import src.mesh.adapters.taskdog as t;"
            f"t.TASKDOG_DB = pathlib.Path(r'{db_path}');"
            "from src.mesh.taskdog_cli import main;"
            "sys.exit(main())"
        )
        return subprocess.run(
            [str(PY), "-c", bootstrap, *args],
            cwd=str(cwd or REPO_ROOT),
            env={**__import__("os").environ, **env_overlay},
            capture_output=True,
            text=True,
            timeout=30,
        )
    return subprocess.run(
        [str(PY), "-m", "src.mesh.taskdog_cli", *args],
        cwd=str(cwd or REPO_ROOT),
        env={**__import__("os").environ, **env_overlay},
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def taskdog_db(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Create a tmp taskdog SQLite schema with both tables and override path.

    Two separate module objects are involved (dual-module identity, per
    CLAUDE.md):
      - ``src.mesh.adapters.taskdog`` — used by tests to read the DB
      - ``mesh.adapters.taskdog``     — used by main() in taskdog_cli
        (when subprocess imports it without src. prefix)

    Both must be patched so reads see the same data the subprocess wrote.
    The subprocess bootstrap (in _run_cli) patches TASKDOG_DB inside the
    subprocess; here we patch in-process for the test reader path.
    """
    db_path = tmp_path / "tasks.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE tasks (
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
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ueid TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL DEFAULT 'note',
            actor TEXT NOT NULL DEFAULT 'cli',
            text TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

    # Patch the in-process adapter module so callers reading the DB after
    # the subprocess writes get the same data.
    from src.mesh.adapters import taskdog as taskdog_mod

    original = taskdog_mod.TASKDOG_DB
    taskdog_mod.TASKDOG_DB = db_path
    request.addfinalizer(lambda: setattr(taskdog_mod, "TASKDOG_DB", original))
    return db_path


def _read_audit_rows(db_path: Path, ueid: str | None = None) -> list[dict]:
    """Read audit_log rows as dicts (test-side helper)."""
    conn = sqlite3.connect(db_path)
    try:
        if ueid is None:
            cur = conn.execute(
                "SELECT id, ueid, timestamp, action, actor, text "
                "FROM audit_log ORDER BY id ASC"
            )
        else:
            cur = conn.execute(
                "SELECT id, ueid, timestamp, action, actor, text "
                "FROM audit_log WHERE ueid=? ORDER BY id ASC",
                (ueid,),
            )
        cols = ("id", "ueid", "timestamp", "action", "actor", "text")
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 1. add appends to audit_log
# ---------------------------------------------------------------------------
def test_add_appends_to_audit_log(taskdog_db: Path) -> None:
    """td note add inserts one row in audit_log with action='note', actor='cli'."""
    proc = _run_cli("note", "add", _UEID, "called vendor at 14:30", db_path=taskdog_db)
    assert proc.returncode == 0, f"stderr: {proc.stderr}"

    rows = _read_audit_rows(taskdog_db, _UEID)
    assert len(rows) == 1, f"expected 1 row, got {len(rows)}"
    row = rows[0]
    assert row["ueid"] == _UEID
    assert row["action"] == "note"
    assert row["actor"] == "cli"
    assert row["text"] == "called vendor at 14:30"
    assert row["timestamp"]  # non-empty ISO8601
    assert isinstance(row["id"], int)


def test_add_two_notes_yields_two_rows(taskdog_db: Path) -> None:
    """Two adds → two rows, ordered chronologically (id ASC)."""
    _run_cli("note", "add", _UEID, "first", db_path=taskdog_db)
    _run_cli("note", "add", _UEID, "second", db_path=taskdog_db)

    rows = _read_audit_rows(taskdog_db, _UEID)
    assert [r["text"] for r in rows] == ["first", "second"]
    assert rows[0]["id"] < rows[1]["id"]


def test_add_rejects_invalid_ueid(taskdog_db: Path) -> None:
    """argparse rejects malformed UEID before touching the DB."""
    proc = _run_cli("note", "add", "not-a-ueid", "x", db_path=taskdog_db)
    assert proc.returncode != 0
    rows = _read_audit_rows(taskdog_db)
    assert rows == []  # nothing was written


# ---------------------------------------------------------------------------
# 2. show returns only 'note' actions
# ---------------------------------------------------------------------------
def test_show_returns_only_note_actions(taskdog_db: Path) -> None:
    """td note show must filter to action='note' even when other audit
    rows exist in the same table (future-proofing: status transitions,
    propagation events, etc. will share the table)."""
    # Add a real note (action='note')
    _run_cli("note", "add", _UEID, "real note", db_path=taskdog_db)
    # Insert a non-note row directly (simulates a future audit event).
    conn = sqlite3.connect(taskdog_db)
    conn.execute(
        "INSERT INTO audit_log (ueid, timestamp, action, actor, text) "
        "VALUES (?, '2026-10-01T00:00:00+00:00', 'status_change', 'agent', ?)",
        (_UEID, "planned→in_progress"),
    )
    conn.execute(
        "INSERT INTO audit_log (ueid, timestamp, action, actor, text) "
        "VALUES (?, '2026-10-01T00:00:01+00:00', 'note', 'agent', ?)",
        (_UEID, "should also show"),
    )
    conn.commit()
    conn.close()

    # note show should print ONLY the two note rows (one CLI-added, one
    # agent-added), not the status_change row.
    proc = _run_cli("note", "show", _UEID, "--json", db_path=taskdog_db)
    assert proc.returncode == 0
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(lines) == 2, f"expected 2 JSON lines, got {len(lines)}: {proc.stdout!r}"
    parsed = [json.loads(ln) for ln in lines]
    texts = {p["text"] for p in parsed}
    assert texts == {"real note", "should also show"}
    for p in parsed:
        assert "id" in p
        assert "timestamp" in p
        assert "text" in p


def test_show_empty_ueid_is_clean(taskdog_db: Path) -> None:
    """No notes for a UEID → empty output (pipe) or '(no notes for ueid X)' (TTY)."""
    proc = _run_cli("note", "show", _UEID, "--json", db_path=taskdog_db)
    assert proc.returncode == 0
    # In --json mode, no rows means no output lines.
    assert proc.stdout.strip() == ""


def test_show_filters_per_ueid(taskdog_db: Path) -> None:
    """Notes for one UEID do not bleed into another's show output."""
    _run_cli("note", "add", _UEID, "for task A", db_path=taskdog_db)
    _run_cli("note", "add", _OTHER_UEID, "for task B", db_path=taskdog_db)

    proc_a = _run_cli("note", "show", _UEID, "--json", db_path=taskdog_db)
    proc_b = _run_cli("note", "show", _OTHER_UEID, "--json", db_path=taskdog_db)

    a_texts = [json.loads(ln)["text"] for ln in proc_a.stdout.splitlines() if ln.strip()]
    b_texts = [json.loads(ln)["text"] for ln in proc_b.stdout.splitlines() if ln.strip()]
    assert a_texts == ["for task A"]
    assert b_texts == ["for task B"]


# ---------------------------------------------------------------------------
# 3. multi-line text preserved
# ---------------------------------------------------------------------------
def test_multiline_text_preserved(taskdog_db: Path) -> None:
    """Newlines in the note text must survive sanitization, and the
    round-trip read must return the exact same text."""
    multiline = "line one\nline two\nline three"
    add_proc = _run_cli("note", "add", _UEID, multiline, db_path=taskdog_db)
    assert add_proc.returncode == 0

    rows = _read_audit_rows(taskdog_db, _UEID)
    assert len(rows) == 1
    assert rows[0]["text"] == multiline  # exact, including the newlines


def test_control_chars_stripped_but_newlines_kept(taskdog_db: Path) -> None:
    """Sanitization keeps \\n and \\t but strips other control chars
    (0x00-0x1F, 0x7F). The test avoids \\x00 because subprocess argv
    on Windows can't transport NUL bytes."""
    raw = "before\x01ctrl\nnewline\rafter-cr \x7fdel"
    # Strip \x01, \r (0x0D), \x7f; keep \n.
    sanitized_expected = "beforectrl\nnewlineafter-cr del"
    _run_cli("note", "add", _UEID, raw, db_path=taskdog_db)

    rows = _read_audit_rows(taskdog_db, _UEID)
    assert len(rows) == 1
    assert rows[0]["text"] == sanitized_expected


# ---------------------------------------------------------------------------
# 4. text > 1024 chars rejected
# ---------------------------------------------------------------------------
def test_text_over_1024_rejected(taskdog_db: Path) -> None:
    """A note longer than 1024 chars (after sanitization) must be refused
    with non-zero exit and a clear stderr message — no row written."""
    too_long = "x" * 1025
    proc = _run_cli("note", "add", _UEID, too_long, db_path=taskdog_db)
    assert proc.returncode != 0, f"expected non-zero exit, got {proc.returncode}"
    assert "too long" in proc.stderr or "1024" in proc.stderr
    rows = _read_audit_rows(taskdog_db, _UEID)
    assert rows == []  # nothing written


def test_text_exactly_1024_accepted(taskdog_db: Path) -> None:
    """Boundary: 1024 chars exactly must succeed (≤ is inclusive)."""
    exactly = "y" * 1024
    proc = _run_cli("note", "add", _UEID, exactly, db_path=taskdog_db)
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    rows = _read_audit_rows(taskdog_db, _UEID)
    assert len(rows) == 1
    assert len(rows[0]["text"]) == 1024


# ---------------------------------------------------------------------------
# 5. --json output
# ---------------------------------------------------------------------------
def test_add_json_output(taskdog_db: Path) -> None:
    """td note add --json produces one JSON object per line with
    {id, ueid, action, chars}."""
    proc = _run_cli("note", "add", _UEID, "json test", "--json", db_path=taskdog_db)
    assert proc.returncode == 0
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["ueid"] == _UEID
    assert obj["action"] == "note"
    assert obj["chars"] == len("json test")
    assert isinstance(obj["id"], int)


def test_show_json_output(taskdog_db: Path) -> None:
    """td note show --json produces one JSON object per line per note."""
    _run_cli("note", "add", _UEID, "first", db_path=taskdog_db)
    _run_cli("note", "add", _UEID, "second", db_path=taskdog_db)

    proc = _run_cli("note", "show", _UEID, "--json", db_path=taskdog_db)
    assert proc.returncode == 0
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(lines) == 2
    objs = [json.loads(ln) for ln in lines]
    assert [o["text"] for o in objs] == ["first", "second"]
    for o in objs:
        assert set(o.keys()) == {"id", "timestamp", "text"}


def test_human_and_json_are_mutually_exclusive(taskdog_db: Path) -> None:
    """argparse should reject --json + --human together (matches the
    existing _add_output_flags contract)."""
    proc = _run_cli("note", "add", _UEID, "x", "--json", "--human", db_path=taskdog_db)
    assert proc.returncode != 0


# ---------------------------------------------------------------------------
# Sanity: --help shows note subcommands
# ---------------------------------------------------------------------------
def test_help_lists_note_subcommands() -> None:
    """The top-level --help must surface `note` as a subcommand."""
    proc = _run_cli("--help")
    assert proc.returncode == 0
    assert "note" in proc.stdout


def test_note_add_help_documents_text_limit() -> None:
    """`td note add --help` must mention the 1024 char cap (operator UX)."""
    proc = _run_cli("note", "add", "--help")
    assert proc.returncode == 0
    assert "1024" in proc.stdout