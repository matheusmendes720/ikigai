"""Integration tests for the PAV-OS v2 report/state commands.

After the v1/v2 merge, v2 is the **only** renderer — there are no
``--v1`` / ``--v2`` flags. These tests verify that ``--mock``,
``--watch``, and ``--json`` still work and that the default rendering
uses the v2 design system.

State is isolated per-test via the autouse ``_isolated_state`` fixture
in ``conftest.py``.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from operational.cli.app import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Daily: --mock
# ---------------------------------------------------------------------------


def test_report_daily_mock_q1_runs_without_error() -> None:
    """``pav report daily --mock q1`` runs and exits 0."""
    result = runner.invoke(app, ["report", "daily", "--mock", "q1"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    assert "DAILY REPORT" in result.output


def test_report_daily_mock_q3_output_contains_q3() -> None:
    """``pav report daily --mock q3`` renders Q3 in the legend/output."""
    result = runner.invoke(app, ["report", "daily", "--mock", "q3"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    assert "Q3" in result.output


def test_report_daily_mock_burnout_runs() -> None:
    """``--mock burnout`` runs without error (low-everything profile)."""
    result = runner.invoke(app, ["report", "daily", "--mock", "burnout"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    assert "DAILY REPORT" in result.output


def test_report_daily_no_mock_uses_live_data() -> None:
    """``pav report daily`` (no mock) renders the live snapshot."""
    result = runner.invoke(app, ["report", "daily"])

    assert result.exit_code in (0, 1), f"Output:\n{result.output}"
    assert "DAILY REPORT" in result.output


def test_report_daily_mock_json_shape() -> None:
    """``--mock --json`` returns JSON with design_system='v2' key."""
    import json
    result = runner.invoke(app, ["report", "daily", "--mock", "q1", "--json"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    data = json.loads(result.output)
    assert data["design_system"] == "v2"
    assert data["mock"] == "q1"
    assert data["quadrant"] == "Q1"


# ---------------------------------------------------------------------------
# Default rendering: v2 chrome is the only rendering
# ---------------------------------------------------------------------------


def test_daily_no_flag_uses_v2_by_default() -> None:
    """``pav report daily`` (no flags) uses the v2 design system."""
    result = runner.invoke(app, ["report", "daily", "--date", "1999-01-01"])

    assert result.exit_code in (0, 1)
    long_bar = "─" * 60
    assert long_bar in result.output, "default should render v2 chrome"
    assert "DAILY REPORT" in result.output


def test_weekly_no_flag_uses_v2_by_default() -> None:
    """``pav report weekly`` (no flags) uses the v2 design system."""
    result = runner.invoke(app, ["report", "weekly"])

    assert result.exit_code in (0, 1)
    long_bar = "─" * 60
    assert long_bar in result.output, "default should render v2 chrome"
    assert "WEEKLY" in result.output or "WEEKLY REPORT" in result.output


def test_state_show_no_flag_uses_v2_by_default() -> None:
    """``pav state show`` (no flags) uses the v2 design system."""
    result = runner.invoke(app, ["state", "show"])

    assert result.exit_code == 0
    long_bar = "─" * 60
    assert long_bar in result.output, "default should render v2 chrome"
    assert "STATE" in result.output or "State Dashboard" in result.output


def test_report_weekly_runs() -> None:
    """``pav report weekly`` runs and renders the v2 weekly report."""
    result = runner.invoke(app, ["report", "weekly"])

    assert result.exit_code in (0, 1)
    assert "WEEKLY" in result.output or "WEEKLY REPORT" in result.output


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_report_daily_invalid_mock_name_errors() -> None:
    """``--mock bogus`` must error with the available profiles listed."""
    result = runner.invoke(app, ["report", "daily", "--mock", "bogus"])

    assert result.exit_code != 0
    assert "ERRO" in result.output
    assert "bogus" in result.output
    assert "q1" in result.output
    assert "q3" in result.output


def test_report_weekly_invalid_mock_name_errors() -> None:
    """``report weekly --mock bogus`` errors symmetrically."""
    result = runner.invoke(app, ["report", "weekly", "--mock", "bogus"])

    assert result.exit_code != 0
    assert "ERRO" in result.output
    assert "bogus" in result.output


def test_state_show_invalid_mock_name_errors() -> None:
    """``state show --mock bogus`` errors symmetrically."""
    result = runner.invoke(app, ["state", "show", "--mock", "bogus"])

    assert result.exit_code != 0
    assert "ERRO" in result.output
    assert "bogus" in result.output


# ---------------------------------------------------------------------------
# state show
# ---------------------------------------------------------------------------


def test_state_show_mock_q1_runs() -> None:
    """``pav state show --mock q1`` runs and exits 0."""
    result = runner.invoke(app, ["state", "show", "--mock", "q1"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    assert "STATE DASHBOARD" in result.output


def test_state_show_no_mock_uses_live_data() -> None:
    """``pav state show`` (no mock) renders the live dashboard."""
    result = runner.invoke(app, ["state", "show"])

    assert result.exit_code == 0
    assert "STATE DASHBOARD" in result.output


def test_state_show_json_v2_marker() -> None:
    """``state show --mock q1 --json`` reports design_system='v2'."""
    import json
    result = runner.invoke(app, ["state", "show", "--mock", "q1", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["design_system"] == "v2"
    assert data["mock"] == "q1"


# ---------------------------------------------------------------------------
# Watch mode (smoke test: assert Live() is invoked)
# ---------------------------------------------------------------------------


def test_report_daily_watch_invokes_live() -> None:
    """``--watch 1`` wraps the renderable in rich.live.Live.

    We mock both :class:`rich.live.Live` and :func:`time.sleep` so the
    auto-refresh loop exits after one iteration. No real terminal is required.
    """
    mock_ctx = MagicMock()
    mock_live = MagicMock()
    mock_live.return_value.__enter__.return_value = mock_ctx
    mock_live.return_value.__exit__.return_value = False

    sleep_calls = {"n": 0}

    def _sleep_then_exit(_seconds: int) -> None:
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 1:
            raise SystemExit(0)

    with patch("operational.cli.commands.report_cmd.Live", mock_live), patch("time.sleep", side_effect=_sleep_then_exit):
        result = runner.invoke(app, ["report", "daily", "--watch", "1"])

    assert mock_live.called, "Live() should be invoked when --watch is used"
    assert sleep_calls["n"] >= 1
    assert result.exit_code == 0, f"Expected clean exit, got {result.exit_code}: {result.output}"


# ---------------------------------------------------------------------------
# Help text: no --v1 / --v2 mentions
# ---------------------------------------------------------------------------


def test_report_daily_help_does_not_mention_v1_v2() -> None:
    """``pav report daily --help`` does not mention --v1 or --v2."""
    result = runner.invoke(app, ["report", "daily", "--help"])
    assert result.exit_code == 0
    assert "--v1" not in result.output
    assert "--v2" not in result.output


def test_report_weekly_help_does_not_mention_v1_v2() -> None:
    """``pav report weekly --help`` does not mention --v1 or --v2."""
    result = runner.invoke(app, ["report", "weekly", "--help"])
    assert result.exit_code == 0
    assert "--v1" not in result.output
    assert "--v2" not in result.output


def test_state_show_help_does_not_mention_v1_v2() -> None:
    """``pav state show --help`` does not mention --v1 or --v2."""
    result = runner.invoke(app, ["state", "show", "--help"])
    assert result.exit_code == 0
    assert "--v1" not in result.output
    assert "--v2" not in result.output


def test_home_help_does_not_mention_v1_v2() -> None:
    """``pav home --help`` does not mention --v1 or --v2."""
    result = runner.invoke(app, ["home", "--help"])
    assert result.exit_code == 0
    assert "--v1" not in result.output
    assert "--v2" not in result.output
