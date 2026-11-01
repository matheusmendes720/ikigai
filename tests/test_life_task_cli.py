"""M83: Tests for life task {add, start, done, ls} commands.

These wrap the taskdog CLI (which talks to taskdog-server, port 8000).
Tests use a stub `_run_taskdog` to avoid spawning real subprocesses.
The goal is to verify Typer command wiring, flag handling, and JSON output.

M112: HTTP-first path added — tests force CLI fallback by setting
`task.ENABLE_HTTP = False` (server unreachable) + stubbing _run_taskdog.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from life.cli.cli import app
from life.centrals import task as task_central


@pytest.fixture(autouse=True)
def _force_cli_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """M112: HTTP path bypassed so existing tests can still stub CLI."""
    monkeypatch.setattr(task_central, "ENABLE_HTTP", False)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def taskdog_stub(monkeypatch: pytest.MonkeyPatch):
    """Stub _run_taskdog with a controllable callable."""

    def make_stub(success: bool = True, stdout: str = "", stderr: str = "") -> Any:
        def _stub(args: list[str]) -> dict[str, Any]:
            return {
                "ok": success,
                "stdout": stdout,
                "stderr": stderr,
                "error": None if success else "taskdog failed",
                "transport": "cli",
            }

        return _stub

    return make_stub


def test_task_add_invokes_taskdog_add(runner: CliRunner, taskdog_stub, monkeypatch):
    """M83: life task add 'X' should call taskdog add with the title."""
    calls: list[list[str]] = []

    def fake_run(args: list[str]) -> dict[str, Any]:
        calls.append(args)
        return {"ok": True, "stdout": "Added: X (ID: 1)", "stderr": "", "error": None}

    monkeypatch.setattr("life.centrals.task._run_taskdog", fake_run)
    result = runner.invoke(app, ["task", "add", "Write cover letter"])
    assert result.exit_code == 0, result.stdout
    assert calls == [["add", "Write cover letter"]]


def test_task_add_with_priority_and_tag(runner: CliRunner, taskdog_stub, monkeypatch):
    """M83: --priority and --tag should be passed through to taskdog."""
    calls: list[list[str]] = []

    def fake_run(args: list[str]) -> dict[str, Any]:
        calls.append(args)
        return {"ok": True, "stdout": "Added: X (ID: 1)", "stderr": "", "error": None}

    monkeypatch.setattr("life.centrals.task._run_taskdog", fake_run)
    result = runner.invoke(app, ["task", "add", "Apply BYD", "--priority", "8", "--tag", "byd", "--tag", "urgent"])
    assert result.exit_code == 0, result.stdout
    expected = ["add", "Apply BYD", "--priority", "8", "--tag", "byd", "--tag", "urgent"]
    assert calls == [expected]


def test_task_add_json_output(runner: CliRunner, taskdog_stub, monkeypatch):
    """M83: --json returns the taskdog result as JSON."""
    def fake_run(args: list[str]) -> dict[str, Any]:
        return {"ok": True, "stdout": "Added: X", "stderr": "", "error": None}

    monkeypatch.setattr("life.centrals.task._run_taskdog", fake_run)
    result = runner.invoke(app, ["task", "add", "X", "--json"])
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout.strip())
    assert parsed["ok"] is True
    assert parsed["stdout"] == "Added: X"


def test_task_add_failure_exit_code(runner: CliRunner, taskdog_stub, monkeypatch):
    """M83: failed taskdog add should return non-zero exit code."""
    def fake_run(args: list[str]) -> dict[str, Any]:
        return {"ok": False, "stdout": "", "stderr": "connection refused", "error": None}

    monkeypatch.setattr("life.centrals.task._run_taskdog", fake_run)
    result = runner.invoke(app, ["task", "add", "X"])
    assert result.exit_code != 0


def test_task_start_invokes_taskdog_start(runner: CliRunner, monkeypatch):
    """M83: life task start <id> should call taskdog start."""
    calls: list[list[str]] = []

    def fake_run(args: list[str]) -> dict[str, Any]:
        calls.append(args)
        return {"ok": True, "stdout": "Started: 5", "stderr": "", "error": None}

    monkeypatch.setattr("life.centrals.task._run_taskdog", fake_run)
    result = runner.invoke(app, ["task", "start", "5"])
    assert result.exit_code == 0, result.stdout
    assert calls == [["start", "5"]]


def test_task_done_invokes_taskdog_done(runner: CliRunner, monkeypatch):
    """M83: life task done <id> should call taskdog done."""
    calls: list[list[str]] = []

    def fake_run(args: list[str]) -> dict[str, Any]:
        calls.append(args)
        return {"ok": True, "stdout": "Done: 5", "stderr": "", "error": None}

    monkeypatch.setattr("life.centrals.task._run_taskdog", fake_run)
    result = runner.invoke(app, ["task", "done", "5"])
    assert result.exit_code == 0, result.stdout
    assert calls == [["done", "5"]]


def test_task_ls_invokes_taskdog_list(runner: CliRunner, monkeypatch):
    """M83: life task ls should call taskdog list."""
    calls: list[list[str]] = []

    def fake_run(args: list[str]) -> dict[str, Any]:
        calls.append(args)
        return {"ok": True, "stdout": "ID  Name\n1   Foo", "stderr": "", "error": None}

    monkeypatch.setattr("life.centrals.task._run_taskdog", fake_run)
    result = runner.invoke(app, ["task", "ls"])
    assert result.exit_code == 0, result.stdout
    assert calls == [["list"]]


def test_task_ls_with_filter(runner: CliRunner, monkeypatch):
    """M83: life task ls --q foo passes --filter foo to taskdog."""
    calls: list[list[str]] = []

    def fake_run(args: list[str]) -> dict[str, Any]:
        calls.append(args)
        return {"ok": True, "stdout": "", "stderr": "", "error": None}

    monkeypatch.setattr("life.centrals.task._run_taskdog", fake_run)
    result = runner.invoke(app, ["task", "ls", "--q", "byd"])
    assert result.exit_code == 0, result.stdout
    assert calls == [["list", "--filter", "byd"]]


# ============================================================================
# Canonical CLI surface (ADR-037 / M198 — canonical-only, serverless scope)
# ============================================================================

def test_life_cli_does_not_expose_harness_v2_subapp():
    """`life v2` was a PC-only harness entry point and must not ship.

    The v2 sub-app wired invoke-skill / skill-list / skill-show against the
    local deep-agent graph (langchain/langgraph harness). That harness is
    not part of the canonical remote scope (ADR-037), so the sub-app is gone.
    """
    names = {cmd.name for cmd in app.registered_commands}
    assert "v2" not in names


def test_interfaces_cli_exposes_canonical_mesh_commands():
    """The canonical entry point exposes the mesh command surface.

    `python -m interfaces.cli` is the consumer/producer CLI: task reading,
    mesh read path, and the mesh create cycle. The harness sub-apps are
    not mounted here.
    """
    from interfaces.cli import app as interfaces_app

    result = CliRunner().invoke(interfaces_app, ["--help"])
    assert result.exit_code == 0, result.stdout
    for command in ("list", "done", "stats", "mesh-show", "task-add", "plan-add", "plan-list"):
        assert command in result.stdout, f"missing canonical command: {command}"


