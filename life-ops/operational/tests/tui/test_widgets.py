"""Tests for operational.tui.widgets."""
from __future__ import annotations

from operational.tui.widgets.kpi_card import KPICard
from operational.tui.widgets.regime_bar import RegimeBar, REGIME_GLYPHS
from operational.tui.widgets.pomodoro_grid import PomodoroGrid
from operational.tui.widgets.time_block import TimeBlockDisplay, STATUS_INDICATORS
from operational.tui.widgets.habit_streak import HabitStreakDisplay


def test_kpi_card_render() -> None:
    kpi = KPICard(label="Sono", value="8.0h", delta="+0.5h")
    assert "Sono" in kpi.render()
    assert "8.0h" in kpi.render()


def test_regime_bar_has_glyphs() -> None:
    assert len(REGIME_GLYPHS) == 4


def test_pomodoro_grid_render() -> None:
    grid = PomodoroGrid()
    output = grid.render()
    assert "S1 manha" in output
    assert "S2 tarde" in output


def test_time_block_display_render() -> None:
    tb = TimeBlockDisplay(label="Acordar", start="06:00", end="06:30", status="OK", period="MANHA")
    output = tb.render()
    assert "Acordar" in output
    assert "06:00→06:30" in output


def test_habit_streak_display_render() -> None:
    hs = HabitStreakDisplay(name="Meditar", current_streak=7, best_streak=14, q_he=8.5)
    output = hs.render()
    assert "Meditar" in output
    assert "streak:7" in output
    assert "best:14" in output