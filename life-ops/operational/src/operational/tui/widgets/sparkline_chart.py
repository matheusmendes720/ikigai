"""Plotext chart widgets for PAV TUI."""
from __future__ import annotations

from typing import Any

import plotext as px
from textual.widgets import Static


class PlotextChart(Static):
    """Embed a plotext chart in a Textual Static widget."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def plot(self, x: list[float], y: list[float], kind: str = "scatter", **kw: Any) -> None:
        px.clf()
        if kind == "scatter":
            px.scatter(x, y, **kw)
        elif kind == "bar":
            px.bar(x, y, **kw)
        elif kind == "line":
            px.plot(x, y, **kw)
        self.update(px.build())

    def sparkline(self, values: list[float], **kw: Any) -> None:
        px.clf()
        px.plot(values, **kw)
        self.update(px.build())

    def bar_chart(self, labels: list[str], values: list[float], **kw: Any) -> None:
        px.clf()
        px.bar(labels, values, **kw)
        self.update(px.build())
