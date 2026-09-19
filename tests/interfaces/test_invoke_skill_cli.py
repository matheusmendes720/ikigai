"""Smoke test for invoke-skill CLI (M78).

Verifies the ``life invoke-skill`` and ``life skill-list`` subcommands
work end-to-end via Typer's CliRunner (no subprocess, no real LLM).

These cover the CLI surface layer; the underlying ``invoke_skill()``
function is tested end-to-end by tests/test_v2_invoke_skill_taskdog.py.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# Mirror life.cli.cli path setup
_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def cli_runner():
    """Provide a Typer CliRunner bound to the v2 app."""
    from typer.testing import CliRunner
    from interfaces.cli.v2 import app

    return CliRunner(), app


def test_invoke_skill_help(cli_runner):
    runner, app = cli_runner
    result = runner.invoke(app, ["invoke-skill", "--help"])
    assert result.exit_code == 0
    assert "Run a skill manifest end-to-end" in result.output
    assert "W3.5/W3.6" in result.output


def test_skill_list_shows_all_five(cli_runner):
    runner, app = cli_runner
    result = runner.invoke(app, ["skill-list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["count"] == 5
    names = {s["name"] for s in parsed["skills"]}
    assert "ikigai-daily" in names
    assert "ikigai-quarterly" in names
    assert "ikigai-weekly" in names
    assert "ikigai-monthly" in names


def test_skill_list_marks_taskdog_firing(cli_runner):
    runner, app = cli_runner
    result = runner.invoke(app, ["skill-list"])
    parsed = json.loads(result.output)
    by_name = {s["name"]: s for s in parsed["skills"]}
    # daily + monthly have empty outputs (no taskdog)
    assert by_name["ikigai-daily"]["fires_taskdog"] is False
    assert by_name["ikigai-monthly"]["fires_taskdog"] is False
    # quarterly + weekly declare taskdog_create_task
    assert by_name["ikigai-quarterly"]["fires_taskdog"] is True
    assert by_name["ikigai-weekly"]["fires_taskdog"] is True


def test_invoke_skill_daily_runs_without_taskdog(cli_runner, monkeypatch):
    """ikigai-daily has empty outputs; should run without firing taskdog."""
    runner, app = cli_runner
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    vault_root = _REPO_ROOT / "data" / "pytest-tmp" / "test_invoke_daily"
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(vault_root))
    Path(str(vault_root)).mkdir(parents=True, exist_ok=True)
    result = runner.invoke(app, ["invoke-skill", "ikigai-daily"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["skill"] == "ikigai-daily"
    assert "taskdog_result" not in parsed
    assert "taskdog_pending_review_queue" not in parsed
    assert parsed["outputs_fired"] == []


def test_invoke_skill_unknown_returns_empty_state(cli_runner, monkeypatch):
    """Non-existent skill returns a structured error dict instead of crashing."""
    runner, app = cli_runner
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    result = runner.invoke(app, ["invoke-skill", "ikigai-nonexistent"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["skill"] == "ikigai-nonexistent"
    assert "manifest not found" in parsed["graph_state"]["error"]
