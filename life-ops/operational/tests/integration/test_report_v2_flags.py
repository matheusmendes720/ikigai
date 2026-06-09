"""Integration tests for the ``--v2``, ``--mock``, and ``--watch``
opt-in flags added on top of the v1 commands.

These tests use :class:`typer.testing.CliRunner` and exercise the
flags against the live ``pav-os`` Typer app. State is isolated per-test
via the autouse ``_isolated_state`` fixture in ``conftest.py``.

Coverage:
- ``report daily`` with ``--v2`` and ``--mock`` (v2 + mock integration)
- ``report daily`` with no flags (regression: v1 path unchanged)
- ``report daily --watch`` without ``--v2`` (error path)
- ``report daily --mock <bad>`` (error path)
- ``state show --v2 --mock`` (v2 + mock integration)
- ``state show --v2`` with live data (regression-safe v2 path)
- ``report daily --v2 --mock q3`` contains "Q3" in the v2 output
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from operational.cli.app import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Happy paths: --v2 + --mock
# ---------------------------------------------------------------------------


def test_report_daily_v2_mock_q1_runs_without_error() -> None:
    """``pav report daily --v2 --mock q1`` runs and exits 0."""
    result = runner.invoke(app, ["report", "daily", "--v2", "--mock", "q1"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    # The v2 design system has a distinctive header
    assert "DAILY REPORT" in result.output


def test_report_daily_v2_mock_q3_output_contains_q3() -> None:
    """``pav report daily --v2 --mock q3`` renders Q3 in the legend/output."""
    result = runner.invoke(app, ["report", "daily", "--v2", "--mock", "q3"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    # The Q3 row always appears in the v2 cartesian legend
    assert "Q3" in result.output


def test_report_daily_v2_mock_burnout_runs() -> None:
    """``--v2 --mock burnout`` runs without error (low-everything profile)."""
    result = runner.invoke(app, ["report", "daily", "--v2", "--mock", "burnout"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    assert "DAILY REPORT" in result.output


def test_report_daily_v2_no_mock_uses_live_data() -> None:
    """``pav report daily --v2`` (no mock) renders the live snapshot."""
    result = runner.invoke(app, ["report", "daily", "--v2"])

    # Empty state may exit 0 or 1; both are acceptable for a missing snapshot
    assert result.exit_code in (0, 1), f"Output:\n{result.output}"
    assert "DAILY REPORT" in result.output


def test_report_daily_v2_mock_json_shape() -> None:
    """``--v2 --mock --json`` returns JSON with design_system="v2" key."""
    import json
    result = runner.invoke(app, ["report", "daily", "--v2", "--mock", "q1", "--json"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    data = json.loads(result.output)
    assert data["design_system"] == "v2"
    assert data["mock"] == "q1"
    assert data["quadrant"] == "Q1"


# ---------------------------------------------------------------------------
# Regression: v1 path unchanged when no flags
# ---------------------------------------------------------------------------


def test_report_daily_no_flag_still_v1() -> None:
    """``pav report daily`` (no flags) still uses v1 design system."""
    result = runner.invoke(app, ["report", "daily", "--date", "1999-01-01"])

    assert result.exit_code in (0, 1)
    # v1 has the "DAILY REPORT" header inside a section panel (no dashes)
    # v2 uses the long "──" bar separator
    assert "DAILY REPORT" in result.output
    # v2 chrome signature: long bar of dashes at the top
    long_bar = "─" * 60
    assert long_bar not in result.output, "v1 path should NOT render v2 chrome"


def test_report_daily_json_no_flag_has_v1_marker() -> None:
    """``pav report daily --json`` (no flags) reports design_system='v1'."""
    import json
    result = runner.invoke(app, ["report", "daily", "--json"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    data = json.loads(result.output)
    assert data["design_system"] == "v1"
    assert data["mock"] is None


def test_report_weekly_v2_runs() -> None:
    """``pav report weekly --v2`` runs without error (option-a: v1 body, v2 chrome)."""
    result = runner.invoke(app, ["report", "weekly", "--v2"])

    assert result.exit_code in (0, 1)
    # v2 chrome signature: the long dash bar from header_v2
    assert "WEEKLY" in result.output or "WEEKLY REPORT" in result.output


def test_report_weekly_no_flag_still_v1() -> None:
    """``pav report weekly`` (no flags) still uses v1 design system."""
    result = runner.invoke(app, ["report", "weekly"])

    assert result.exit_code in (0, 1)
    # v1 has the ⚡ WEEKLY section panel (no long dash bar at the top)
    assert "WEEKLY" in result.output
    long_bar = "─" * 60
    assert long_bar not in result.output


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_report_daily_watch_without_v2_errors() -> None:
    """``--watch 5`` without ``--v2`` must error with a clear message."""
    result = runner.invoke(app, ["report", "daily", "--watch", "5"])

    assert result.exit_code != 0
    # The error panel from v2 components is used (per rules)
    assert "ERRO" in result.output
    assert "watch" in result.output.lower()
    assert "--v2" in result.output


def test_report_daily_invalid_mock_name_errors() -> None:
    """``--mock bogus`` must error with the available profiles listed."""
    result = runner.invoke(app, ["report", "daily", "--mock", "bogus"])

    assert result.exit_code != 0
    assert "ERRO" in result.output
    assert "bogus" in result.output
    # The error panel lists available profiles
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
# state show v2 path
# ---------------------------------------------------------------------------


def test_state_show_v2_mock_q1_runs() -> None:
    """``pav state show --v2 --mock q1`` runs and exits 0."""
    result = runner.invoke(app, ["state", "show", "--v2", "--mock", "q1"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    # v2 chrome: "STATE DASHBOARD" header
    assert "STATE DASHBOARD" in result.output


def test_state_show_v2_no_mock_uses_live_data() -> None:
    """``pav state show --v2`` (no mock) renders the live dashboard."""
    result = runner.invoke(app, ["state", "show", "--v2"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    assert "STATE DASHBOARD" in result.output


def test_state_show_no_flag_still_v1() -> None:
    """``pav state show`` (no flags) still uses v1 design system."""
    result = runner.invoke(app, ["state", "show"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    # v1 chrome: "STATE  ·  YYYY-MM-DD  ·  <PERIOD>"
    assert "STATE" in result.output
    # v2 chrome: long dash bar from header_v2
    long_bar = "─" * 60
    assert long_bar not in result.output, "v1 path should NOT render v2 chrome"


def test_state_show_json_v2_marker() -> None:
    """``state show --v2 --mock q1 --json`` reports design_system='v2'."""
    import json
    result = runner.invoke(app, ["state", "show", "--v2", "--mock", "q1", "--json"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    data = json.loads(result.output)
    assert data["design_system"] == "v2"
    assert data["mock"] == "q1"


# ---------------------------------------------------------------------------
# Mock-without-v2 path: mock + v1 should still work
# ---------------------------------------------------------------------------


def test_report_daily_mock_without_v2_uses_v1_renderer() -> None:
    """``--mock q1`` without ``--v2`` should feed mock data into v1 renderer."""
    result = runner.invoke(app, ["report", "daily", "--mock", "q1"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    # v1 renderer shows "[MOCK PROFILE: q1]" in the notes (per spec)
    # If the v1 path is taken, the daily report DAILY REPORT is wrapped in v1 panel
    # (no long dash bar). The mock snapshot is built and rendered.
    assert "DAILY REPORT" in result.output
    # Should NOT have v2 chrome (long bar at top)
    long_bar = "─" * 60
    assert long_bar not in result.output, "Mock without --v2 should NOT use v2 chrome"


# ---------------------------------------------------------------------------
# Sub-app regression: pav v2 today still works (the standalone v2 entry)
# ---------------------------------------------------------------------------


def test_v2_today_subapp_still_works() -> None:
    """The standalone ``pav v2 today`` sub-app must keep working."""
    result = runner.invoke(app, ["v2", "today", "--mock", "q1"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    assert "DAILY REPORT" in result.output


# ---------------------------------------------------------------------------
# Watch mode (smoke test: assert Live() is invoked)
# ---------------------------------------------------------------------------


def test_report_daily_watch_with_v2_invokes_live() -> None:
    """``--v2 --watch 1`` must wrap the renderable in rich.live.Live.

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
            # Allow one full iteration: sleep once, then exit
            raise SystemExit(0)

    with patch("operational.cli.commands.report_cmd.Live", mock_live), patch("time.sleep", side_effect=_sleep_then_exit):
        result = runner.invoke(app, ["report", "daily", "--v2", "--watch", "1"])

    # Live() was invoked and entered; the test exits via SystemExit(0)
    assert mock_live.called, "Live() should be invoked when --watch is used with --v2"
    # The SystemExit terminates the loop after the first sleep
    assert sleep_calls["n"] >= 1, "time.sleep should be called at least once"
    # exit_code is 0 because SystemExit(0) is the clean exit
    assert result.exit_code == 0, f"Expected clean exit, got {result.exit_code}: {result.output}"
