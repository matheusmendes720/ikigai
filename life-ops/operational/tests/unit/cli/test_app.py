"""Smoke tests for the CLI application."""
from __future__ import annotations

from typer.testing import CliRunner

from operational.cli import app

runner = CliRunner()


class TestCliApp:
    def test_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "routine" in result.stdout
        assert "block" in result.stdout
        assert "journal" in result.stdout
        assert "habit" in result.stdout
        assert "metric" in result.stdout
        assert "policy" in result.stdout
        assert "report" in result.stdout

    def test_routine_help(self) -> None:
        result = runner.invoke(app, ["routine", "--help"])
        assert result.exit_code == 0
        assert "create" in result.stdout

    def test_block_help(self) -> None:
        result = runner.invoke(app, ["block", "--help"])
        assert result.exit_code == 0
        assert "create" in result.stdout

    def test_journal_help(self) -> None:
        result = runner.invoke(app, ["journal", "--help"])
        assert result.exit_code == 0

    def test_habit_help(self) -> None:
        result = runner.invoke(app, ["habit", "--help"])
        assert result.exit_code == 0

    def test_metric_help(self) -> None:
        result = runner.invoke(app, ["metric", "--help"])
        assert result.exit_code == 0

    def test_policy_help(self) -> None:
        result = runner.invoke(app, ["policy", "--help"])
        assert result.exit_code == 0

    def test_report_help(self) -> None:
        result = runner.invoke(app, ["report", "--help"])
        assert result.exit_code == 0

    def test_routine_create(self) -> None:
        result = runner.invoke(app, ["routine", "create", "TestRoutine", "MANHA", "CORE"])
        assert result.exit_code == 0
        # Rich-rendered: ✓ Rotina criada
        assert ("✓" in result.stdout) or ("Created routine" in result.stdout)

    def test_block_create(self) -> None:
        result = runner.invoke(app, ["block", "create", "MANHA", "--label", "Test"])
        assert result.exit_code == 0
        assert ("✓" in result.stdout) or ("Created time block" in result.stdout)

    def test_journal_create(self) -> None:
        result = runner.invoke(app, ["journal", "create"])
        assert result.exit_code == 0
        assert ("✓" in result.stdout) or ("Created journal entry" in result.stdout)

    def test_habit_create(self) -> None:
        result = runner.invoke(app, ["habit", "create", "TestHabit", "physiological"])
        assert result.exit_code == 0
        assert ("✓" in result.stdout) or ("Created habit" in result.stdout)

    def test_metric_sleep(self) -> None:
        result = runner.invoke(app, ["metric", "sleep"])
        assert result.exit_code == 0
        # Rich-rendered sleep output contains the record id
        assert ("Sono registrado" in result.stdout) or ("Sleep record" in result.stdout)

    def test_report_daily(self) -> None:
        result = runner.invoke(app, ["report", "daily"])
        assert result.exit_code == 0
        # Rich-rendered: "EASE — Sono & Higiene" appears in the panel
        assert ("EASE" in result.stdout) or ("Daily" in result.stdout)

    def test_json_flag(self) -> None:
        result = runner.invoke(app, ["routine", "create", "JR", "MANHA", "CORE", "--json"])
        assert result.exit_code == 0
        assert '"id"' in result.stdout

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        # Typer returns exit code 2 when showing help on no-args
        assert result.exit_code in (0, 2)
        assert "routine" in result.stdout
