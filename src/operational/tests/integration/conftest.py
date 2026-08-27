"""Integration test conftest — redirect state to a tmp dir before app import.

This file MUST set the env var BEFORE any test file imports the app,
because ``operational.cli.state`` reads TIME_TASKER_STATE_DIR at
module-load time.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# CRITICAL: Set env var before any test file imports the app.
# state.py reads TIME_TASKER_STATE_DIR at module-load time.
_TMP_STATE = Path(tempfile.gettempdir()) / "time-tasker-test-int-state"
_TMP_STATE.mkdir(parents=True, exist_ok=True)
os.environ["TIME_TASKER_STATE_DIR"] = str(_TMP_STATE)

# Ensure src is on the path so tests can import operational.* directly.
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pytest  # noqa: E402

from operational.cli import state as cli_state  # noqa: E402

# All repos that the CLI touches.
ALL_REPOS = (
    cli_state.routines,
    cli_state.routine_logs,
    cli_state.time_blocks,
    cli_state.journals,
    cli_state.habits,
    cli_state.sleep_records,
    cli_state.pomodoros,
    cli_state.policy_decisions,
    cli_state.policy_setpoints,
    cli_state.ajustes_finos,
    cli_state.day_contexts,
    cli_state.daily_reflections,
    cli_state.lunch_records,
    cli_state.transicoes,
)


@pytest.fixture(autouse=True)
def _isolated_state() -> None:
    """Clear every repo before & after each test for full isolation."""
    for repo in ALL_REPOS:
        repo.clear()
    yield
    for repo in ALL_REPOS:
        repo.clear()
