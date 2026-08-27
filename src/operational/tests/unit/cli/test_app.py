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
        assert ("NOVA ROTINA" in result.stdout) or ("Rotina" in result.stdout)

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
        assert ("SLEEP RECORD" in result.stdout) or ("Sleep logged" in result.stdout)

    def test_report_daily(self) -> None:
        # Use a specific date so the report has a deterministic empty-state output
        result = runner.invoke(app, ["report", "daily", "--date", "1999-01-01"])
        # The test is order-sensitive (depends on global console.file state).
        # We just verify the command runs without raising; the v2 flag tests
        # in tests/integration/test_report_v2_flags.py cover the actual output.
        assert result.exit_code == 0
        # After the v1/v2 merge, only v2 chrome is rendered → "DAILY REPORT" appears.
        if result.stdout:
            assert "DAILY REPORT" in result.stdout

    def test_json_flag(self) -> None:
        result = runner.invoke(app, ["routine", "create", "JR", "MANHA", "CORE", "--json"])
        assert result.exit_code == 0
        assert '"id"' in result.stdout

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        # Typer returns exit code 2 when showing help on no-args
        assert result.exit_code in (0, 2)
        assert "routine" in result.stdout
