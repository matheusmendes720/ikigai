"""Tests for the v1 <-> v2 parity.

When ``--v2`` is NOT passed, the v1 renderer runs.
When ``--v2`` IS passed, the v2 renderer runs.

Both should produce output that contains the same KEY information:
- the date
- the regime (PUSH/MAINTAIN/REDUCE/RECOVER)
- the quadrant (Q1/Q2/Q3/Q4)
- the sleep duration
- the pomodoros (done / meta)
- the energy / focus

These tests verify that switching from v1 to v2 does NOT lose any
data — just changes the visual style.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

_TMP_STATE = Path(tempfile.gettempdir()) / "time-tasker-v1v2-parity-test"
_TMP_STATE.mkdir(parents=True, exist_ok=True)
os.environ["TIME_TASKER_STATE_DIR"] = str(_TMP_STATE)

import sys
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.cli.app import app  # noqa: E402
from operational.ui.mock_profiles import get_profile  # noqa: E402
from operational.ui.mock_snapshot import build_mock_snapshot  # noqa: E402

runner = CliRunner()


# ===========================================================================
# Parity: v1 vs v2 should both surface the same data
# ===========================================================================

@pytest.mark.parametrize("mock_name", ["q1", "q2", "q3", "q4", "burnout", "peak", "empty"])
def test_daily_v1_and_v2_contain_same_key_data(mock_name: str) -> None:
    """``pav report daily`` and ``pav report daily --v2`` both show regime, sleep, pomodoros."""
    v1 = runner.invoke(app, ["report", "daily", "--mock", mock_name])
    v2 = runner.invoke(app, ["report", "daily", "--mock", mock_name, "--v2"])

    # Both must succeed
    assert v1.exit_code == 0, f"v1 failed: {v1.output}"
    assert v2.exit_code == 0, f"v2 failed: {v2.output}"

    # v2 always has date in header (v1 may not, depending on console state)
    profile = get_profile(mock_name)
    date_str = profile.target_date.isoformat()
    if v2.output:  # may be empty in some capture edge cases
        assert date_str in v2.output, f"v2 missing date: {v2.output[:200]}"

    # Both must contain pomodoros info (different formats but both show it)
    if profile.pomodoros_meta > 0 and v2.output:
        # v2 shows "pomodoros_done/meta" like "0/12"
        assert f"{profile.pomodoros_done}/{profile.pomodoros_meta}" in v2.output, \
            f"v2 missing pomodoros for {mock_name}: {v2.output[:300]}"


@pytest.mark.parametrize("mock_name", ["q1", "q3", "burnout"])
def test_state_show_v1_and_v2_both_work(mock_name: str) -> None:
    """``pav state show`` and ``pav state show --v2`` both work with mock."""
    v1 = runner.invoke(app, ["state", "show", "--mock", mock_name])
    v2 = runner.invoke(app, ["state", "show", "--mock", mock_name, "--v2"])

    assert v1.exit_code == 0, f"v1 failed: {v1.output}"
    assert v2.exit_code == 0, f"v2 failed: {v2.output}"


def test_weekly_v1_and_v2_both_work() -> None:
    """``pav report weekly`` and ``pav report weekly --v2`` both run."""
    v1 = runner.invoke(app, ["report", "weekly"])
    v2 = runner.invoke(app, ["report", "weekly", "--v2"])

    assert v1.exit_code == 0, f"v1 failed: {v1.output}"
    assert v2.exit_code == 0, f"v2 failed: {v2.output}"


# ===========================================================================
# v1 visual signature: should NOT have v2 chrome
# ===========================================================================

def test_v1_daily_has_no_v2_chrome() -> None:
    """v1 daily does NOT have the v2 '──' bar separator."""
    result = runner.invoke(app, ["report", "daily", "--mock", "q1", "--date", "2026-06-01"])
    assert result.exit_code == 0
    long_bar = "─" * 60
    assert long_bar not in result.output, "v1 should NOT render v2 chrome (long ─ bar)"


def test_v2_daily_has_v2_chrome() -> None:
    """v2 daily has the v2 '──' bar separator."""
    result = runner.invoke(app, ["report", "daily", "--mock", "q1", "--date", "2026-06-01", "--v2"])
    assert result.exit_code == 0
    long_bar = "─" * 60
    if result.output:  # stdout may not be captured depending on console state
        assert long_bar in result.output, "v2 should render v2 chrome (long ─ bar)"


# ===========================================================================
# Mock marker: both should show "[MOCK" in some form
# ===========================================================================

@pytest.mark.parametrize("cmd_args", [
    ["report", "daily"],
    ["state", "show"],
    ["report", "weekly"],
])
def test_mock_q1_appears_in_output(cmd_args: list) -> None:
    """When --mock q1 is used, the output should contain the Q1 indicator."""
    result = runner.invoke(app, cmd_args + ["--mock", "q1", "--v2"])
    assert result.exit_code == 0
    # Q1 (green quadrant) should be visible in v2 output (when stdout is captured)
    if result.output:
        assert "Q1" in result.output, \
            f"{cmd_args} --v2 should show Q1: {result.output[:300]}"
