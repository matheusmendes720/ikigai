"""Tests for ikigai.cli.app — all CLI commands."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from ikigai.cli.app import app

runner = CliRunner()


class TestCLI:
    """Smoke tests for all CLI commands."""

    def test_version(self) -> None:
        """version command must exit 0."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0

    def test_version_json(self) -> None:
        """version --json must return valid JSON."""
        result = runner.invoke(app, ["--json", "version"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "version" in data["data"]

    def test_health(self) -> None:
        """health command must exit 0."""
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0

    def test_health_json(self) -> None:
        """health --json must return valid JSON with vault_exists."""
        result = runner.invoke(app, ["--json", "health"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"]["vault_exists"] is not None

    def test_vector_list(self) -> None:
        """vector list must exit 0."""
        result = runner.invoke(app, ["vector", "list"])
        assert result.exit_code == 0
        assert "passion" in result.stdout.lower() or "PASSION" in result.stdout

    def test_vector_score(self) -> None:
        """vector score is archived per attribution §3 — must raise NotImplementedError."""
        result = runner.invoke(app, ["vector", "score", "--passion-streak", "30"])
        assert isinstance(result.exception, NotImplementedError)
        assert "archived per attribution" in str(result.exception)

    def test_vector_meta(self) -> None:
        """vector meta is archived per attribution §3 — must raise NotImplementedError."""
        result = runner.invoke(
            app,
            ["vector", "meta", "--passion", "70", "--skill", "80"],
        )
        assert isinstance(result.exception, NotImplementedError)
        assert "archived per attribution" in str(result.exception)

    def test_regime_status(self) -> None:
        """regime status is archived per attribution §3 — must raise NotImplementedError."""
        result = runner.invoke(
            app,
            ["regime", "status", "--qhe", "0.75"],
        )
        assert isinstance(result.exception, NotImplementedError)
        assert "archived per attribution" in str(result.exception)

    def test_regime_status_json(self) -> None:
        """regime status --json is archived per attribution §3 — must raise NotImplementedError."""
        result = runner.invoke(
            app,
            ["--json", "regime", "status", "--qhe", "0.70"],
        )
        assert isinstance(result.exception, NotImplementedError)
        assert "archived per attribution" in str(result.exception)

    def test_phase_status(self) -> None:
        """phase status is archived per attribution §3 — must raise NotImplementedError."""
        result = runner.invoke(
            app,
            ["phase", "status", "--ikigai-score", "65.0"],
        )
        assert isinstance(result.exception, NotImplementedError)
        assert "archived per attribution" in str(result.exception)

    def test_phase_status_json(self) -> None:
        """phase status --json is archived per attribution §3 — must raise NotImplementedError."""
        result = runner.invoke(
            app,
            ["--json", "phase", "status", "--ikigai-score", "60.0"],
        )
        assert isinstance(result.exception, NotImplementedError)
        assert "archived per attribution" in str(result.exception)

    def test_plan_list_empty_vault(self) -> None:
        """plan list on empty vault → exit 0, empty list."""
        result = runner.invoke(app, ["plan", "list", "--entity-type", "goal"])
        assert result.exit_code == 0

    def test_sync_index(self) -> None:
        """sync index must exit 0."""
        result = runner.invoke(app, ["sync", "index"])
        assert result.exit_code == 0
        assert "index" in result.stdout.lower()

    def test_sync_run_markdown(self) -> None:
        """sync run --prefer markdown must exit 0."""
        result = runner.invoke(app, ["--json", "sync", "run", "--prefer", "markdown"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"]["action"] == "markdown→sqlite"

    def test_sync_run_invalid_prefer(self) -> None:
        """sync run --prefer invalid → exit 1."""
        result = runner.invoke(app, ["sync", "run", "--prefer", "invalid"])
        assert result.exit_code == 1

    def test_help_command(self) -> None:
        """--help must exit 0."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
