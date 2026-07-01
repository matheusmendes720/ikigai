"""plotext chart builder functions for PAV TUI."""
from __future__ import annotations

import plotext as px  # type: ignore[import-untyped]


def build_sleep_sparkline(values: list[float]) -> str:
    px.clf()
    px.plot(values, color="cyan", marker="•")
    return px.build()  # type: ignore[no-any-return]


def build_energy_bar(values: list[int]) -> str:
    px.clf()
    px.bar([str(i) for i in range(1, len(values) + 1)], values, color="green")
    return px.build()  # type: ignore[no-any-return]


def build_focus_sparkline(values: list[float]) -> str:
    px.clf()
    px.plot(values, color="magenta", marker="•")
    return px.build()  # type: ignore[no-any-return]


def build_quadrant_plot(x: float, y: float, _quadrant: str, history: list[tuple[float, float]]) -> str:
    px.clf()
    if history:
        hx, hy = zip(*history, strict=False)
        px.scatter(list(hx), list(hy), color="grey")
    px.scatter([x], [y], color="cyan")
    return px.build()  # type: ignore[no-any-return]


def build_scenario_radar(scenario: dict[str, float]) -> str:
    px.clf()
    labels = list(scenario.keys())
    values = list(scenario.values())
    px.bar(labels, values, color="blue")
    return px.build()  # type: ignore[no-any-return]
