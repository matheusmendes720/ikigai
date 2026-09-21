"""M100 tests: `life taskdog *` direct MCP-backed commands.

Per M100: the `taskdog` sub-app exposes all 26 taskdog-mcp tools as
direct Typer subcommands (no LLM roundtrip). These tests verify:
- sub-app registers without import error
- `--help` lists all 26 commands
- MCP unavailability → graceful error
- Create + delete roundtrip works end-to-end
- Array params (comma-separated strings) are auto-converted
"""
from __future__ import annotations

import json
import os
import subprocess

import pytest

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir)
) if "__file__" in globals() else os.getcwd()


@pytest.fixture
def ikigai_python():
    """Path to ikigai venv python (has langchain-mcp-adapters + mcp)."""
    p = os.path.join(REPO_ROOT, "src", "ikigai", ".venv", "Scripts", "python.exe")
    if not os.path.exists(p):
        pytest.skip(f"ikigai venv not found: {p}")
    return p


def _run_cli(ikigai_python: str, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run `python -m life.cli <args>` with ikigai venv + PYTHONPATH=repo root."""
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT
    return subprocess.run(
        [ikigai_python, "-m", "life.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_taskdog_subapp_lists_26_commands(ikigai_python: str) -> None:
    """`life taskdog --help` must list all 26 MCP tools as commands."""
    r = _run_cli(ikigai_python, "taskdog", "--help")
    assert r.returncode == 0, f"stderr: {r.stderr}"
    expected = [
        "list-tasks", "get-task", "create-task", "update-task", "delete-task",
        "restore-task", "start-task", "complete-task", "pause-task", "cancel-task",
        "reopen-task", "fix-actual-times", "get-statistics", "get-tag-statistics",
        "get-executable-tasks", "decompose-task", "add-dependency", "remove-dependency",
        "set-task-tags", "update-task-notes", "get-task-notes", "delete-tag",
        "list-audit-logs", "get-audit-log", "optimize-schedule", "list-algorithms",
    ]
    found = sum(1 for name in expected if name in r.stdout)
    assert found == 26, f"expected 26 commands, found {found}: {r.stdout}"


def test_taskdog_subapp_registered_in_main_help(ikigai_python: str) -> None:
    """`life --help` must include the `taskdog` subcommand."""
    r = _run_cli(ikigai_python, "--help")
    assert r.returncode == 0
    assert "taskdog" in r.stdout
    assert "Direct taskdog-mcp commands" in r.stdout


def test_taskdog_list_tasks_returns_json(ikigai_python: str) -> None:
    """`life taskdog list-tasks --status PENDING` must return parseable JSON."""
    r = _run_cli(ikigai_python, "taskdog", "list-tasks", "--status", "PENDING", timeout=30)
    assert r.returncode == 0, f"stderr: {r.stderr}"
    data = json.loads(r.stdout)
    assert "tasks" in data
    assert isinstance(data["tasks"], list)


def test_taskdog_create_then_delete_roundtrip(ikigai_python: str) -> None:
    """Create a task with priority + tags (array auto-split) then delete it."""
    # CREATE
    r = _run_cli(
        ikigai_python,
        "taskdog",
        "create-task",
        "--name",
        "M100 test task (pytest)",
        "--priority",
        "5",
        "--tags",
        "smoke,m100",
        timeout=30,
    )
    assert r.returncode == 0, f"create stderr: {r.stderr}"
    created = json.loads(r.stdout)
    assert "id" in created
    task_id = created["id"]
    assert created["name"] == "M100 test task (pytest)"
    assert created["priority"] == 5
    try:
        # VERIFY tags were set as a list (not string)
        r = _run_cli(
            ikigai_python,
            "taskdog",
            "get-task",
            "--task-id",
            str(task_id),
            timeout=30,
        )
        assert r.returncode == 0
        fetched = json.loads(r.stdout)
        tags = fetched.get("tags", [])
        assert "smoke" in tags and "m100" in tags, f"tags not parsed as list: {tags}"
    finally:
        # CLEANUP — hard-delete the test task
        _run_cli(
            ikigai_python,
            "taskdog",
            "delete-task",
            "--task-id",
            str(task_id),
            "--hard",
            "true",
            timeout=30,
        )


def test_taskdog_disable_mcp_escape_hatch(ikigai_python: str) -> None:
    """IKIGAI_DISABLE_MCP_TASKDOG=1 must surface a clean error (not crash).

    With MCP disabled, the sub-app registers a single `__unavailable`
    command that prints a JSON error and exits 1.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT
    env["IKIGAI_DISABLE_MCP_TASKDOG"] = "1"
    r = subprocess.run(
        [ikigai_python, "-m", "life.cli", "taskdog", "--help"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0  # --help itself exits 0
    assert "__unavailable" in r.stdout  # only placeholder registered, not 26 cmds
    # The 26 real commands must NOT be registered
    assert "list-tasks" not in r.stdout
    assert "create-task" not in r.stdout
    # When invoked, the placeholder returns the JSON error
    r2 = subprocess.run(
        [ikigai_python, "-m", "life.cli", "taskdog", "__unavailable"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r2.returncode != 0
    assert "IKIGAI_DISABLE_MCP_TASKDOG=1" in r2.stdout + r2.stderr


def test_taskdog_create_without_required_name_fails_gracefully(ikigai_python: str) -> None:
    """Missing required `name` arg → Typer exit non-zero (parse error)."""
    r = _run_cli(ikigai_python, "taskdog", "create-task", timeout=15)
    assert r.returncode != 0
    assert "Missing" in r.stderr or "required" in r.stderr.lower()
