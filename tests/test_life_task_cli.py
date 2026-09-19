"""M83: Tests for life task {add, start, done, ls} commands.

These wrap the taskdog CLI (which talks to taskdog-server, port 8000).
Tests use a stub `_run_taskdog` to avoid spawning real subprocesses.
The goal is to verify Typer command wiring, flag handling, and JSON output.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from life.cli.cli import app


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
# M85: v2 subcommand wiring (invoke-skill, skill-list, skill-show, plan)
# ============================================================================

def test_v2_subcommand_registered(runner: CliRunner):
    """M85: `life v2 --help` should list invoke-skill, skill-list, skill-show, plan."""
    result = runner.invoke(app, ["v2", "--help"])
    assert result.exit_code == 0, result.stdout
    assert "invoke-skill" in result.stdout
    assert "skill-list" in result.stdout
    assert "skill-show" in result.stdout


def test_v2_skill_list_via_life_cli(runner: CliRunner):
    """M85: `life v2 skill-list` should list skills."""
    result = runner.invoke(app, ["v2", "skill-list"])
    # Output is JSON; should exit 0 even with no skills or some skills
    assert result.exit_code == 0, result.stdout
    assert '"count"' in result.stdout
    assert '"skills"' in result.stdout


def test_v2_skill_show_via_life_cli(runner: CliRunner, monkeypatch):
    """M85: `life v2 skill-show <name>` should show skill details."""
    manifest = {
        "name": "ikigai-test",
        "description": "Test skill",
        "entry_point": "observe",
        "actor": "agent",
        "inputs": [],
        "outputs": [{"taskdog_create_task": "test"}],
        "metadata": {},
    }
    monkeypatch.setattr(
        "interfaces.cli.invoke_skill.load_skill_manifest",
        lambda n: manifest if n == "ikigai-test" else {},
    )
    result = runner.invoke(app, ["v2", "skill-show", "ikigai-test"])
    assert result.exit_code == 0, result.stdout
    assert "=== ikigai-test ===" in result.stdout
    assert "fires taskdog: True" in result.stdout
