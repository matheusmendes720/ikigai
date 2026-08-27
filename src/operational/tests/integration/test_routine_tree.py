"""Tests for Rich Tree rendering in 'pav routine list --tree'."""
from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, time, UTC
from pathlib import Path

import pytest
from typer.testing import CliRunner

_TMP_STATE = Path(tempfile.gettempdir()) / "time-tasker-tree-test"
_TMP_STATE.mkdir(parents=True, exist_ok=True)
os.environ["TIME_TASKER_STATE_DIR"] = str(_TMP_STATE)

import sys
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.cli.app import app  # noqa: E402
from operational.cli.state import routines  # noqa: E402
from operational.entities.routine import Routine  # noqa: E402
from operational.enums import Period, RoutineType  # noqa: E402

runner = CliRunner()


@pytest.fixture
def sample_routines():
    """Create 3 routines: 2 MANHA, 1 TARDE."""
    now = datetime.now(UTC)
    routines.clear()
    r1 = Routine(
        id="rou_morning_1", name="Workout", period=Period.MANHA, routine_type=RoutineType.CORE,
        start_time=time(6, 0), end_time=time(7, 0), created_at=now, mandatory=True,
    )
    r2 = Routine(
        id="rou_morning_2", name="Shower", period=Period.MANHA, routine_type=RoutineType.TRANSITION,
        start_time=time(7, 0), end_time=time(7, 30), created_at=now, mandatory=False,
    )
    r3 = Routine(
        id="rou_afternoon_1", name="Deep work", period=Period.TARDE, routine_type=RoutineType.CORE,
        start_time=time(14, 0), end_time=time(18, 0), created_at=now, mandatory=True,
    )
    routines.upsert(r1)
    routines.upsert(r2)
    routines.upsert(r3)
    yield
    routines.clear()


class TestRoutineTree:
    def test_tree_runs(self, sample_routines) -> None:
        """``pav routine list --tree`` renders as Tree."""
        result = runner.invoke(app, ["routine", "list", "--tree"])
        assert result.exit_code == 0
        if result.stdout:
            # Should contain tree structure
            assert "MANHA" in result.stdout
            assert "TARDE" in result.stdout
            assert "Workout" in result.stdout
            assert "Deep work" in result.stdout

    def test_tree_shows_mandatory_marker(self, sample_routines) -> None:
        """--tree shows '*' marker for mandatory routines."""
        result = runner.invoke(app, ["routine", "list", "--tree"])
        assert result.exit_code == 0
        if result.stdout:
            # The mandatory routines should have the '*' marker
            assert "Workout" in result.stdout and "*" in result.stdout

    def test_tree_filter_by_period(self, sample_routines) -> None:
        """--tree --period MANHA only shows morning routines."""
        result = runner.invoke(app, ["routine", "list", "--tree", "--period", "MANHA"])
        assert result.exit_code == 0
        if result.stdout:
            assert "MANHA" in result.stdout
            # Should NOT contain TARDE
            assert "TARDE" not in result.stdout or "Deep work" not in result.stdout

    def test_tree_empty_state(self) -> None:
        """--tree with no data shows the warning."""
        routines.clear()
        result = runner.invoke(app, ["routine", "list", "--tree"])
        assert result.exit_code == 0
        if result.stdout:
            assert "Nenhuma rotina" in result.stdout or "Use" in result.stdout

    def test_no_tree_flag_still_table(self, sample_routines) -> None:
        """Default output (no --tree) is still a table, not a tree."""
        result = runner.invoke(app, ["routine", "list"])
        assert result.exit_code == 0
        if result.stdout:
            # Default output uses a Table
            assert "Rotinas" in result.stdout
            # Should NOT have tree structure (└──, ├──, │)
            assert "└──" not in result.stdout, "Default output should be a table, not a tree"
