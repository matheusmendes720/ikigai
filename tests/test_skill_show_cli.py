"""M84: Tests for `life skill-show <name>` CLI command.

Loads skill manifest, pretty-prints or emits JSON.
Uses tmp manifest directory via env override + load_skill_manifest monkeypatch.
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
def fake_manifest(monkeypatch: pytest.MonkeyPatch):
    """Patch load_skill_manifest to return a controlled manifest."""

    def _make(name: str = "ikigai-test", description: str = "Test skill",
              entry_point: str = "observe", actor: str = "agent",
              inputs: list = None, outputs: list = None,
              metadata: dict = None):
        manifest = {
            "name": name,
            "description": description,
            "entry_point": entry_point,
            "actor": actor,
            "inputs": inputs or [],
            "outputs": outputs or [],
            "metadata": metadata or {},
        }
        # Patch at the source module (skill-show imports lazily from .invoke_skill)
        monkeypatch.setattr(
            "interfaces.cli.invoke_skill.load_skill_manifest",
            lambda n: manifest if n == name else {},
        )
        return manifest

    return _make


def test_skill_show_human(runner: CliRunner, fake_manifest):
    """M84: human-readable output for a single skill."""
    fake_manifest(
        name="ikigai-test",
        description="Test description",
        outputs=[{"taskdog_create_task": "test OKRs"}],
    )
    result = runner.invoke(app, ["invoke-skill-show-test"], catch_exceptions=False)
    # Will fail because that's not a real command. Use direct module path instead:
    # The v2 CLI is registered separately under `interfaces.cli.v2`.
    # Test via CliRunner against the v2 app.
    from interfaces.cli.v2 import app as v2_app
    result = runner.invoke(v2_app, ["skill-show", "ikigai-test"], catch_exceptions=False)
    assert result.exit_code == 0, result.stdout
    assert "=== ikigai-test ===" in result.stdout
    assert "Test description" in result.stdout
    assert "entry_point: observe" in result.stdout
    assert "actor:       agent" in result.stdout
    assert "fires taskdog: True" in result.stdout
    assert "taskdog action: test OKRs" in result.stdout


def test_skill_show_json(runner: CliRunner, fake_manifest):
    """M84: --json emits structured detail dict."""
    fake_manifest(
        name="ikigai-test",
        outputs=[{"vault_write": "path/{date}.md"}],
    )
    from interfaces.cli.v2 import app as v2_app
    result = runner.invoke(v2_app, ["skill-show", "ikigai-test", "--json"], catch_exceptions=False)
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is True
    assert parsed["name"] == "ikigai-test"
    assert parsed["fires_taskdog"] is False
    assert parsed["taskdog_target"] is None
    assert parsed["outputs"] == [{"vault_write": "path/{date}.md"}]


def test_skill_show_not_found(runner: CliRunner, monkeypatch):
    """M84: missing skill returns non-zero exit + error JSON."""
    # Default load_skill_manifest returns {} when file missing.
    result = runner.invoke(
        __import__("interfaces.cli.v2", fromlist=["app"]).app,
        ["skill-show", "nonexistent-skill-xyz"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert "not found" in parsed["error"]


def test_skill_show_lists_inputs(runner: CliRunner, fake_manifest):
    """M84: inputs section shows when present."""
    fake_manifest(
        name="ikigai-inputs-test",
        inputs=[{"vault": "meta/{date}.md"}, "user_intent"],
    )
    from interfaces.cli.v2 import app as v2_app
    result = runner.invoke(v2_app, ["skill-show", "ikigai-inputs-test"], catch_exceptions=False)
    assert result.exit_code == 0, result.stdout
    assert "inputs:" in result.stdout
    assert "vault" in result.stdout
    assert "user_intent" in result.stdout


def test_skill_show_metadata(runner: CliRunner, fake_manifest):
    """M84: metadata section shows when present."""
    fake_manifest(
        name="ikigai-meta-test",
        metadata={"cron": "1440m", "tags": ["daily", "automated"]},
    )
    from interfaces.cli.v2 import app as v2_app
    result = runner.invoke(v2_app, ["skill-show", "ikigai-meta-test"], catch_exceptions=False)
    assert result.exit_code == 0, result.stdout
    assert "metadata:" in result.stdout
    assert "cron: 1440m" in result.stdout
    assert "tags:" in result.stdout
