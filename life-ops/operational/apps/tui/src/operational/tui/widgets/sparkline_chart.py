"""Plotext chart widgets for PAV TUI."""
from __future__ import annotations

import re
from typing import Any, ClassVar

import plotext as px
from textual.widgets import Static


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences for SVG-export-safe rendering."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


# PAV period color sets for charts
class ChartColors:
    """Period-aware color palettes for plotext charts."""

    # Sleep: cyan tones
    SLEEP: ClassVar[dict[str, str]] = {
        "primary": "21",
        "fill": "235",
        "marker": "51",
        "canvas": "235",
        "tick": "245",
        "label": "250",
    }
    # Energy: green tones
    ENERGY: ClassVar[dict[str, str]] = {
        "primary": "46",
        "fill": "235",
        "marker": "82",
        "canvas": "235",
        "tick": "245",
        "label": "250",
    }
    # Focus: magenta/pink tones
    FOCUS: ClassVar[dict[str, str]] = {
        "primary": "201",
        "fill": "235",
        "marker": "204",
        "canvas": "235",
        "tick": "245",
        "label": "250",
    }
    # Regime: 4-state policy colors
    REGIME: ClassVar[dict[str, str]] = {
        "PUSH": "46",      # green
        "MAINTAIN": "75",  # blue
        "REDUCE": "226",   # yellow
        "RECOVER": "196",  # red
    }


class PlotextChart(Static):
    """Embed a plotext chart in a Textual Static widget.

    Supports: sparkline (filled area), bar_chart, scatter, line,
    dual_axis (two y-axes), and subplot layouts.
    """

    def __init__(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the PlotextChart widget."""
        super().__init__(**kwargs)

    def _plot(self) -> None:
        """Render current plotext canvas to the widget, stripping ANSI."""
        out = px.build()
        self.update(_strip_ansi(out))

    def _apply_canvas_style(  # noqa: PLR0913
        self,
        width: int | None = None,
        height: int | None = None,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        *,
        hide_x_axis: bool = False,
        hide_y_axis: bool = False,
        hide_ticks: bool = False,
        hide_grid: bool = True,
    ) -> None:
        """Apply common canvas styling options."""
        if width or height:
            px.plot_size(width=width, height=height)
        if hide_x_axis:
            _false = False
            px.xaxes(_false, _false)
        if hide_y_axis:
            _false = False
            px.yaxes(_false, _false)
        if hide_ticks:
            px.xticks([])
            px.yticks([])
        if hide_grid:
            _false = False
            px.grid(_false, _false)
        if title:
            px.title(title)
        if x_label:
            px.xlabel(x_label)
        if y_label:
            px.ylabel(y_label)

    def plot(  # noqa: PLR0913
        self,
        x: list[float],
        y: list[float],
        kind: str = "scatter",
        color: str = "21",
        line_style: str = "solid",
        point_type: str = "dot",
        marker_size: float = 1.0,
        width: int | None = None,
        height: int | None = None,
        x_label: str = "",
        y_label: str = "",
        title: str = "",
        *,
        show: bool = True,
        **kw: Any,  # noqa: ANN401
    ) -> None:
        """Render a scatter, bar, or line plot with full styling options."""
        px.clf()
        valid = {"marker", "color", "style", "fillx", "filly", "xside", "yside", "label", "size"}
        clean_kw = {k: v for k, v in kw.items() if k in valid}
        if kind == "scatter":
            px.scatter(x, y, color=color, marker=point_type, size=marker_size, **clean_kw)
        elif kind == "bar":
            px.bar(x, y, color=color, **clean_kw)
        elif kind == "line":
            px.plot(x, y, color=color, style=line_style, **clean_kw)
        self._apply_canvas_style(
            width=width,
            height=height,
            title=title,
            x_label=x_label,
            y_label=y_label,
        )
        if show:
            self._plot()

    def sparkline(  # noqa: PLR0913
        self,
        values: list[float],
        color: str = "21",
        line_style: str = "solid",
        width: int | None = None,
        height: int | None = None,
        y_label: str = "",
        title: str = "",
        *,
        fill: bool = True,
        show: bool = True,
        hide_x_axis: bool = True,
        hide_y_axis: bool = False,
        hide_ticks: bool = False,
        hide_grid: bool = True,
        **kw: Any,  # noqa: ANN401
    ) -> None:
        """Render a filled sparkline with period-aware styling."""
        px.clf()
        valid = {"marker", "color", "style", "fillx", "filly", "xside", "yside", "label"}
        clean_kw = {k: v for k, v in kw.items() if k in valid}
        if fill:
            px.plot(values, color=color, style=line_style, fillx=True, **clean_kw)
        else:
            px.plot(values, color=color, style=line_style, **clean_kw)
        self._apply_canvas_style(
            width=width,
            height=height,
            title=title,
            y_label=y_label,
            hide_x_axis=hide_x_axis,
            hide_y_axis=hide_y_axis,
            hide_ticks=hide_ticks,
            hide_grid=hide_grid,
        )
        if show:
            self._plot()

    def bar_chart(  # noqa: PLR0913
        self,
        labels: list[str],
        values: list[float],
        color: str = "21",
        orientation: str = "v",
        max_value: float | None = None,
        width: int | None = None,
        height: int | None = None,
        x_label: str = "",
        y_label: str = "",
        title: str = "",
        *,
        show: bool = True,
        hide_x_axis: bool = False,
        hide_y_axis: bool = False,
        hide_ticks: bool = False,
        hide_grid: bool = True,
        **kw: Any,  # noqa: ANN401
    ) -> None:
        """Render a styled bar chart with period-aware colors."""
        px.clf()
        valid = {
            "marker", "color", "style", "fillx", "filly",
            "xside", "yside", "label", "size", "orientation",
        }
        clean_kw = {k: v for k, v in kw.items() if k in valid}
        px.bar(labels, values, color=color, orientation=orientation, **clean_kw)
        if max_value is not None:
            px.ylim(0, max_value)
        self._apply_canvas_style(
            width=width,
            height=height,
            title=title,
            x_label=x_label,
            y_label=y_label,
            hide_x_axis=hide_x_axis,
            hide_y_axis=hide_y_axis,
            hide_ticks=hide_ticks,
            hide_grid=hide_grid,
        )
        if show:
            self._plot()

    def dual_axis(  # noqa: PLR0913
        self,
        x: list[float],
        y1: list[float],
        y2: list[float],
        color1: str = "21",
        color2: str = "226",
        label1: str = "",
        label2: str = "",
        kind1: str = "line",
        kind2: str = "line",
        marker_size: float = 1.0,
        width: int | None = None,
        height: int | None = None,
        title: str = "",
        *,
        show: bool = True,
        hide_x_axis: bool = False,
        hide_grid: bool = True,
        **kw: Any,  # noqa: ANN401
    ) -> None:
        """Render a dual-axis chart (two y-axes, shared x-axis)."""
        px.clf()
        valid = {"marker", "color", "style", "fillx", "filly", "xside", "yside", "label", "size"}
        clean_kw = {k: v for k, v in kw.items() if k in valid}
        if kind1 == "scatter":
            px.scatter(
                x, y1, color=color1, marker="dot", size=marker_size, label=label1, **clean_kw
            )
        else:
            px.plot(x, y1, color=color1, style="solid", label=label1, **clean_kw)
        if kind2 == "scatter":
            px.scatter(
                x, y2, color=color2, marker="dot", size=marker_size, label=label2, **clean_kw
            )
        else:
            px.plot(x, y2, color=color2, style="solid", label=label2, **clean_kw)
        _true = True
        px.yaxes(_true, _true)
        self._apply_canvas_style(
            width=width,
            height=height,
            title=title,
            hide_x_axis=hide_x_axis,
            hide_grid=hide_grid,
        )
        if show:
            self._plot()

    def subplot(  # noqa: PLR0913, C901, PLR0912
        self,
        rows: int,  # noqa: ARG002
        cols: int,
        plots: list[dict[str, Any]],
        width: int | None = None,
        height: int | None = None,
        *,
        show: bool = True,
    ) -> None:
        """Render a subplot grid."""
        px.clf()
        _false = False
        for i, spec in enumerate(plots):
            row = spec.get("row", (i // cols) + 1)
            col = spec.get("col", (i % cols) + 1)
            px.subplot(row=row, col=col)
            x = spec.get("x")
            y = spec.get("y", [])
            kind = spec.get("kind", "line")
            color = spec.get("color", "21")
            fill = spec.get("fill", False)
            ls = spec.get("line_style", "solid")
            pt = spec.get("point_type", "dot")
            ms = spec.get("marker_size", 1.0)
            w = spec.get("width")
            h = spec.get("height")
            title = spec.get("title", "")
            x_label = spec.get("x_label", "")
            y_label = spec.get("y_label", "")
            hx = spec.get("hide_x_axis", False)
            hy = spec.get("hide_y_axis", False)
            ht = spec.get("hide_ticks", False)
            hg = spec.get("hide_grid", True)

            if kind == "scatter":
                px.scatter(x, y, color=color, marker=pt, size=ms)
            elif kind == "bar":
                px.bar(x, y, color=color)
            else:
                px.plot(x or y, y, color=color, style=ls, fillx=fill)
            if w or h:
                px.plot_size(width=w, height=h)
            if hx:
                px.xaxes(_false, _false)
            if hy:
                px.yaxes(_false, _false)
            if ht:
                px.xticks([])
                px.yticks([])
            if hg:
                px.grid(_false, _false)
            if title:
                px.title(title)
            if x_label:
                px.xlabel(x_label)
            if y_label:
                px.ylabel(y_label)

        if width or height:
            px.plot_size(width=width, height=height)
        if show:
            self._plot()
