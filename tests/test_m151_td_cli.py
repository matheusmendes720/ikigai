"""M151 — td CLI write path tests.

Covers the new subcommands added in M151:
    add --ueid ... --title ... [--priority N] [--due YYYY-MM-DD]
    done <ueid>
    update <ueid> [--priority N] [--status X] [--due YYYY-MM-DD]
    propagate

All writes go through the review queue (ADR-014). The CLI only
enqueues; the worker (review_queue_worker.run_once) propagates to
adapters. So these tests assert:
    - the CLI enqueues a valid TaskChange JSON in data/review_queue/
    - the TaskChange has the right action + fields
    - validation rejects bad UEIDs / dates / priorities / titles
    - 'propagate' runs the worker and reports RunResult counts
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
PY = REPO_ROOT / "src" / "ikigai" / ".venv" / "Scripts" / "python.exe"


def _run_cli(*args: str, cwd: Path | None = None, queue_dir: Path | None = None) -> subprocess.CompletedProcess:
    """Invoke `python -m src.mesh.taskdog_cli <args>` and capture output.

    queue_dir: when provided, monkeypatches src.mesh.queue.QUEUE_DIR in the
    subprocess via a small bootstrap shim file. We can't rely on pytest's
    monkeypatch because the subprocess is a separate Python process.
    """
    env_overlay = {"PYTHONPATH": str(SRC)}
    if queue_dir is not None:
        # Bootstrap script that monkeypatches QUEUE_DIR before importing CLI.
        bootstrap = (
            "import sys, pathlib;"
            f"sys.path.insert(0, r'{SRC}');"
            "import src.mesh.queue as q;"
            f"q.QUEUE_DIR = pathlib.Path(r'{queue_dir}');"
            "from src.mesh.taskdog_cli import main;"
            "sys.exit(main())"
        )
        # Inject via -c instead of -m.
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


def _read_queue_files(queue_dir: Path) -> list[dict]:
    """Load every .json file in queue_dir and parse it as TaskChange dict."""
    out = []
    for p in sorted(queue_dir.glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except Exception:
            pass
    return out


@pytest.fixture
def clean_queue(tmp_path, monkeypatch):
    """Redirect QUEUE_DIR to a temp dir and clean it before each test."""
    from src.mesh import queue as queue_mod
    monkeypatch.setattr(queue_mod, "QUEUE_DIR", tmp_path)
    return tmp_path


# --- tests ----------------------------------------------------------------


def test_cli_help_lists_all_subcommands():
    """Sanity: the CLI exposes 7 subcommands."""
    proc = _run_cli("--help")
    assert proc.returncode == 0
    for cmd in ("list", "status", "show", "add", "done", "update", "propagate"):
        assert cmd in proc.stdout, f"missing {cmd} in help:\n{proc.stdout}"


def test_add_enqueues_create_taskchange(clean_queue, tmp_path):
    proc = _run_cli(
        "add",
        "--ueid", "tsk:test:m151add:aaaa:1111",
        "--title", "M151 add test",
        "--priority", "1",
        "--due", "2026-12-31",
        queue_dir=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert "enqueued CREATE event" in proc.stdout
    files = _read_queue_files(tmp_path)
    assert len(files) == 1
    evt = files[0]
    assert evt["action"] == "create"
    assert evt["ueid"] == "tsk:test:m151add:aaaa:1111"
    assert evt["fields"]["title"] == "M151 add test"
    assert evt["fields"]["priority"] == 1
    assert evt["fields"]["due"] == "2026-12-31"
    assert evt["source_fork"] == "cli"
    assert evt["status"] == "pending"


def test_done_enqueues_done_taskchange(clean_queue, tmp_path):
    proc = _run_cli("done", "tsk:test:m151done:bbbb:2222", queue_dir=tmp_path)
    assert proc.returncode == 0, proc.stderr
    files = _read_queue_files(tmp_path)
    assert len(files) == 1
    evt = files[0]
    assert evt["action"] == "done"
    assert evt["ueid"] == "tsk:test:m151done:bbbb:2222"
    assert evt["fields"] == {}


def test_update_enqueues_only_provided_fields(clean_queue, tmp_path):
    proc = _run_cli(
        "update",
        "tsk:test:m151upd:cccc:3333",
        "--priority", "2",
        "--due", "2026-11-15",
        queue_dir=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    files = _read_queue_files(tmp_path)
    assert len(files) == 1
    evt = files[0]
    assert evt["action"] == "update"
    assert evt["fields"] == {"priority": 2, "due": "2026-11-15"}
    assert "status" not in evt["fields"]
    assert "title" not in evt["fields"]


def test_update_rejects_when_no_fields_provided():
    proc = _run_cli("update", "tsk:test:m151upd:cccc:3333")
    assert proc.returncode == 2
    assert "required" in proc.stderr.lower()


def test_add_rejects_invalid_ueid():
    proc = _run_cli(
        "add",
        "--ueid", "BAD-UEID",
        "--title", "x",
    )
    assert proc.returncode == 2
    assert "invalid ueid" in proc.stderr.lower() or "ueid" in proc.stderr.lower()


def test_add_rejects_invalid_priority():
    proc = _run_cli(
        "add",
        "--ueid", "tsk:test:m151prio:dddd:4444",
        "--title", "x",
        "--priority", "9",
    )
    assert proc.returncode == 2
    assert "priority" in proc.stderr.lower()


def test_add_rejects_invalid_due_date():
    proc = _run_cli(
        "add",
        "--ueid", "tsk:test:m151due:eeee:5555",
        "--title", "x",
        "--due", "31/12/2026",
    )
    assert proc.returncode == 2
    assert "due" in proc.stderr.lower() or "date" in proc.stderr.lower()


def test_add_rejects_empty_title():
    proc = _run_cli(
        "add",
        "--ueid", "tsk:test:m151empty:ffff:6666",
        "--title", "   ",
    )
    assert proc.returncode == 2
    assert "title" in proc.stderr.lower()


def test_done_validates_ueid_format():
    proc = _run_cli("done", "INVALID")
    assert proc.returncode == 2


def test_update_validates_status_enum():
    proc = _run_cli(
        "update",
        "tsk:test:m151stat:1111:aaaa",
        "--status", "bogus",
    )
    assert proc.returncode == 2
    assert "status" in proc.stderr.lower()


def test_propagate_runs_worker_and_reports(clean_queue, tmp_path, monkeypatch):
    """propagate enqueues + drains in one shot, reports RunResult.

    Uses tmp_path for QUEUE_DIR so we don't pollute the real queue. After
    propagation, asserts that the TaskdogAdapter has a row for our ueid in
    the REAL DB (because apply_change writes there directly).
    """
    # Enqueue a known task first.
    _run_cli(
        "add",
        "--ueid", "tsk:test:m151prop:2222:bbbb",
        "--title", "propagate smoke",
        queue_dir=tmp_path,
    )
    # The propagate subcommand uses the real queue dir (it loads src.mesh.queue
    # directly without our bootstrap shim). Copy the enqueued file to the real
    # queue dir so propagate can drain it.
    import shutil
    real_queue = REPO_ROOT / "data" / "review_queue"
    for src in tmp_path.glob("*.json"):
        shutil.copy(src, real_queue / src.name)
    try:
        proc = _run_cli("propagate")
    finally:
        # Clean up the copy we made.
        for src in tmp_path.glob("*.json"):
            (real_queue / src.name).unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    assert "consumed=" in proc.stdout
    assert "approved=" in proc.stdout
    # The TaskdogAdapter should now have a row for the new ueid.
    from src.mesh.adapters import taskdog as taskdog_mod
    tasks = taskdog_mod.TaskdogAdapter().list_all()
    assert any(t.get("ueid") == "tsk:test:m151prop:2222:bbbb" for t in tasks)
    # Clean up the test row so other tests start clean.
    import sqlite3
    db = REPO_ROOT / "data" / "taskdog" / "tasks.db"
    conn = sqlite3.connect(str(db))
    conn.execute("DELETE FROM tasks WHERE ueid=?", ("tsk:test:m151prop:2222:bbbb",))
    conn.commit()
    conn.close()


def test_status_command_reports_zero_when_db_empty():
    proc = _run_cli("status", "--json")
    assert proc.returncode == 0
    assert "total: 0" in proc.stdout or "\"total\":" in proc.stdout


def test_list_command_handles_empty_db():
    proc = _run_cli("list")
    assert proc.returncode == 0
    # Empty table, no error
