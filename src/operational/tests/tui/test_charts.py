"""Tests for operational.tui.charts."""
from __future__ import annotations

from operational.tui.charts import (
    build_sleep_sparkline,
    build_energy_bar,
    build_focus_sparkline,
    build_quadrant_plot,
    build_scenario_radar,
)


def test_build_sleep_sparkline_returns_string() -> None:
    result = build_sleep_sparkline([7.0, 8.0, 6.5, 7.5])
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_energy_bar_returns_string() -> None:
    result = build_energy_bar([7, 8, 6, 9])
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_focus_sparkline_returns_string() -> None:
    result = build_focus_sparkline([8.0, 7.5, 9.0, 6.0])
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_quadrant_plot_returns_string() -> None:
    result = build_quadrant_plot(7.0, 8.0, "Q1", [(6.0, 7.0), (5.5, 6.5)])
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_scenario_radar_returns_string() -> None:
    result = build_scenario_radar({"focus": 8.5, "energy": 7.0, "sleep": 9.0})
    assert isinstance(result, str)
    assert len(result) > 0