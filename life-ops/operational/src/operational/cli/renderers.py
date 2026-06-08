"""Reusable Rich visual renderers — fully TTY, color-rich, no escape codes leaking.

Components:
- ``make_console`` — smart Console with force_terminal, no_color logic
- ``kpi_card``        — single big number with color and footer
- ``metric_table``    — colored Rich Table with severity-based row colors
- ``progress_bar``    — bar with percent
- ``pomodoros_grid``  — grid (per session)
- ``timeline_h``      — horizontal timeline of time blocks
- ``cartesian_plane`` — clean X×Y plane with axes, point, quadrant color
- ``sparkline``       — 7-day inline trend
- ``status_badge``    — colored status pill
- ``input_summary``   — "você digitou" table
- ``next_step``       — bold recommendation panel
- ``section_header``  — single-line divider header
"""
from __future__ import annotations

import os
import shutil
import sys
from typing import Sequence

from rich.box import HEAVY, SIMPLE, SIMPLE_HEAD
from rich.console import Console, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# ---------------------------------------------------------------------------
# Console factory — always force TTY behavior
# ---------------------------------------------------------------------------


def make_console(*, width: int | None = None) -> Console:
    """Build a Console that always renders with full TTY features but adapts colors.

    Key insight: when stdout is not a TTY (e.g., captured by opencode, piped,
    or redirected via StringIO), Rich's ANSI escape codes will appear as
    literal text ``[36m╭─[0m`` instead of being interpreted as colors.

    So we detect TTY at construction time:
    - Real TTY: enable colors (the terminal interprets ANSI)
    - Non-TTY (captured/pipe): disable colors (no ANSI emission), but still
      emit full Unicode box-drawing characters

    Width:
    - Real TTY: detect from terminal
    - Non-TTY: default 120 (good for dashboards)
    """
    is_tty = sys.stdout.isatty() if sys.stdout is not None else False
    if width is None:
        if is_tty:
            try:
                width = shutil.get_terminal_size().columns
            except Exception:
                width = 120
        else:
            width = 120
    width = max(60, min(140, width))

    return Console(
        force_terminal=True,
        color_system="truecolor" if is_tty else None,
        no_color=not is_tty,
        width=width,
        highlight=True,
        markup=True,
        emoji=True,
        soft_wrap=False,
        legacy_windows=False,
        safe_box=False,  # Use full Unicode box drawing
    )


def get_render_width() -> int:
    """Get the current console width."""
    is_tty = sys.stdout.isatty()
    if is_tty:
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 120
    return 100


# ---------------------------------------------------------------------------
# Color palette — rich, semantic, no defaults
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = {
    "primary": "cyan",
    "secondary": "white",
    "muted": "bright_black",
    "ok": "bright_green",
    "warn": "yellow",
    "crit": "bold red",
    "info": "blue",
    "accent": "magenta",
    "highlight": "bold cyan",
    "energy": "yellow1",
    "focus": "deep_sky_blue1",
    "sleep": "dodger_blue2",
    "hardwork": "green3",
    "ease": "magenta",
    "transition": "deep_pink1",
    "q1": "bright_green",
    "q2": "cyan",
    "q3": "red",
    "q4": "yellow",
    "gold": "yellow1",
    "orange": "dark_orange",
    "purple": "medium_purple",
}

TIPO_DIA_COLOR: dict[str, str] = {
    "curso": "dodger_blue1",
    "livre": "green3",
    "hardcore": "red",
    "descanso": "grey50",
}


def _c(name: str) -> str:
    return COLORS.get(name, name)


# ---------------------------------------------------------------------------
# kpi_card — single big number
# ---------------------------------------------------------------------------


def kpi_card(
    title: str,
    value: str,
    *,
    color: str = "primary",
    footer: str = "",
    icon: str = "",
    width: int = 22,
) -> Panel:
    """Big-number KPI card."""
    clr = _c(color)
    body = Text()
    if icon:
        body.append(f"  {icon}\n", style=f"bold {clr}")
    body.append(f"  {title}\n", style=f"bold {clr}")
    body.append(f"  {value}", style=f"bold white")
    if footer:
        body.append(f"\n  {footer}", style="grey58 italic")
    return Panel(
        body,
        border_style=clr,
        box=SIMPLE_HEAD,
        padding=(0, 1),
        width=width,
    )


# ---------------------------------------------------------------------------
# section_header — single-line cinematic divider
# ---------------------------------------------------------------------------


def section_header(title: str, *, color: str = "primary", subtitle: str = "") -> RenderableType:
    """A cinematic one-line section divider (no panel box, just visual punch)."""
    clr = _c(color)
    text = Text()
    text.append("── ", style=f"dim {clr}")
    text.append(f"  {title}  ", style=f"bold {clr}")
    if subtitle:
        text.append(f"  {subtitle}  ", style="dim italic")
    text.append(" ", style=f"dim {clr}")
    text.append("─" * 60, style=f"dim {clr}")
    return text


# ---------------------------------------------------------------------------
# progress_bar
# ---------------------------------------------------------------------------


def progress_bar(value: float, total: float, *, width: int = 18, color: str = "primary", label: str = "") -> Text:
    clr = _c(color)
    pct = 0.0 if total <= 0 else max(0.0, min(1.0, value / total))
    filled = int(round(pct * width))
    empty = width - filled
    t = Text()
    t.append("█" * filled, style=clr)
    t.append("░" * empty, style="grey50")
    t.append(f"  {int(pct * 100):3d}%", style=f"bold {clr}")
    if label:
        t.append(f"  ({label})", style="grey58")
    return t


# ---------------------------------------------------------------------------
# pomodoros_grid
# ---------------------------------------------------------------------------


def pomodoros_grid(
    s1: int,
    s2: int,
    s3: int,
    *,
    max_per_session: int = 4,
) -> Text:
    """Compact 3-row pomodoros grid with strong color contrast."""
    def _row(label: str, n: int) -> Text:
        n = max(0, min(max_per_session, n))
        row = Text()
        row.append(f"  {label}  ", style="bold")
        for i in range(max_per_session):
            if i < n:
                row.append("▣ ", style="bold green3")
            else:
                row.append("▢ ", style="grey50")
        row.append(f"  {n}/{max_per_session}", style="bold white")
        return row

    text = Text()
    text.append(_row("S1 manhã ", s1))
    text.append("\n")
    text.append(_row("S2 tarde ", s2))
    text.append("\n")
    text.append(_row("S3 noite ", s3))
    return text


# ---------------------------------------------------------------------------
# timeline_h — compact horizontal time-blocks timeline
# ---------------------------------------------------------------------------


def timeline_h(
    blocks: Sequence[tuple[int, int, str]],
    *,
    width: int = 60,
    color: str = "hardwork",
) -> Text:
    clr = _c(color)
    if not blocks:
        return Text("  (sem blocos no período)", style="grey58")

    min_h = min(b[0] for b in blocks)
    max_h = max(b[1] for b in blocks)
    span = max(1, max_h - min_h)

    bar = Text("  ")
    for start_h, end_h, label in blocks:
        left = int((start_h - min_h) / span * width)
        right = int((end_h - min_h) / span * width)
        length = max(1, right - left)
        bar.append("█" * length, style=clr)
        bar.append(f" {start_h:02d}h {label}  ", style="grey58")
        bar.append("\n")
    return bar


# ---------------------------------------------------------------------------
# cartesian_plane — CLEAN VERSION
# ---------------------------------------------------------------------------


def cartesian_plane(
    x: float,
    y: float,
    *,
    width: int = 14,
    height: int = 7,
) -> Text:
    """Clean Cartesian plane: 4 quadrant lines (50% each) + axes + clear point.

    Compact: no extra padding, just the chart.
    """
    x = max(0.0, min(100.0, x))
    y = max(0.0, min(100.0, y))

    px = round(x / 100 * (width - 1))
    py = round((100 - y) / 100 * (height - 1))  # invert Y for top-down

    # Quadrant color for the point
    if x >= 50 and y >= 50:
        point_color = "bright_green"
        point_char = "◆"
    elif x < 50 and y >= 50:
        point_color = "cyan"
        point_char = "◆"
    elif x < 50 and y < 50:
        point_color = "bold red"
        point_char = "✗"
    else:
        point_color = "yellow"
        point_char = "▲"

    out = Text()
    out.append(" Y% ", style="dim")
    for col in range(width):
        x_val = col * (100 // (width - 1)) if width > 1 else 0
        if x_val in (0, 50, 100):
            out.append(f"{x_val:>3}", style="dim")
        else:
            out.append("   ", style="dim")
    out.append("\n", style="dim")

    for row in range(height):
        y_val = 100 - row * (100 // (height - 1)) if (height - 1) else 0
        out.append(f"{y_val:>3} ", style="dim")

        for col in range(width):
            is_point = (col == px and row == py)
            is_origin = (col == 0 and row == height - 1)
            is_y_axis = (col == 0)
            is_x_axis = (row == height - 1)
            is_50y = (row == height // 2) and not (y_val == 0 or y_val == 100)
            is_50x = (col == width // 2) and col > 0 and col < width - 1

            if is_point and not is_origin:
                out.append(point_char, style=f"bold {point_color}")
            elif is_origin:
                out.append("┼", style="bold white")
            elif is_y_axis:
                out.append("│", style="grey50")
            elif is_x_axis:
                out.append("─", style="grey50")
            elif is_50x and not is_y_axis and not is_x_axis:
                out.append("┊", style="grey30")  # vertical quadrant line
            elif is_50y and not is_y_axis and not is_x_axis:
                out.append("┈", style="grey30")  # horizontal quadrant line
            else:
                out.append(" ", style="grey30")
        out.append("\n")

    # X axis label
    out.append("    ", style="dim")
    out.append("0", style="dim")
    for col in range(1, width):
        x_val = col * (100 // (width - 1)) if width > 1 else 0
        if x_val == 50:
            out.append("       50        ", style="dim")
        elif col == width - 1:
            out.append(f"               100", style="dim")
        else:
            out.append("   ", style="dim")
    out.append("  X% (Produtividade)\n", style="dim")
    return out


# ---------------------------------------------------------------------------
# sparkline
# ---------------------------------------------------------------------------


_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(
    values: Sequence[float],
    *,
    width: int | None = None,
    color: str = "primary",
    label: str = "",
) -> Text:
    if not values:
        return Text("  (sem dados)", style="grey58")
    clr = _c(color)
    width = width or len(values)
    if len(values) != width:
        values = _resample(list(values), width)

    lo = min(values)
    hi = max(values)
    span = max(1e-9, hi - lo)

    text = Text("  ")
    for v in values:
        idx = int((v - lo) / span * (len(_SPARK_CHARS) - 1))
        text.append(_SPARK_CHARS[idx], style=clr)
    if label:
        text.append(f"  {label}", style="grey58")
    return text


def _resample(values: list[float], n: int) -> list[float]:
    if len(values) == n:
        return values
    if len(values) < n:
        return values + [values[-1]] * (n - len(values))
    out: list[float] = []
    bin_size = len(values) / n
    for i in range(n):
        start = int(i * bin_size)
        end = int((i + 1) * bin_size)
        out.append(sum(values[start:end]) / max(1, end - start))
    return out


# ---------------------------------------------------------------------------
# metric_table
# ---------------------------------------------------------------------------


def metric_table(
    title: str,
    rows: Sequence[tuple[str, str, str | None]],
    *,
    title_color: str = "primary",
    show_header: bool = True,
) -> Table:
    """Colored Rich Table — compact, no header by default, tight columns."""
    clr = _c(title_color)
    t = Table(
        title=f"[bold {clr}]  {title}  [/bold {clr}]",
        show_header=show_header,
        header_style=f"bold {clr}",
        border_style=clr,
        box=SIMPLE,
        title_justify="left",
        padding=(0, 1),
        expand=False,
    )
    t.add_column("Métrica", style="bold white", min_width=22, no_wrap=True)
    t.add_column("Valor", justify="left", min_width=12, no_wrap=False)
    for label, value, severity in rows:
        style = COLORS.get(severity or "", "white") if severity else "white"
        if severity:
            t.add_row(label, f"[{style}]{value}[/{style}]")
        else:
            t.add_row(label, value)
    return t


# ---------------------------------------------------------------------------
# input_summary
# ---------------------------------------------------------------------------


def input_summary(
    title: str,
    params: dict,
    *,
    flag_legend: dict | None = None,
) -> Panel:
    t = Table(show_header=True, header_style="bold cyan", box=SIMPLE, border_style="cyan", padding=(0, 1))
    t.add_column("Parâmetro", style="bold cyan", min_width=14)
    t.add_column("Valor", style="white", min_width=18)
    t.add_column("Flag", style="dim", min_width=18)

    for k, v in params.items():
        flag_hint = ""
        if flag_legend:
            for short, long in flag_legend.items():
                if long.endswith(k) or long.replace("--", "") == k:
                    flag_hint = f"{short} / {long}"
                    break
        t.add_row(k, str(v), flag_hint)
    return Panel(t, title=f"[bold cyan]📝 {title}[/bold cyan]", border_style="cyan", box=SIMPLE_HEAD, padding=(0, 1))


# ---------------------------------------------------------------------------
# next_step
# ---------------------------------------------------------------------------


def next_step(
    text: str,
    *,
    color: str = "ok",
    icon: str = "→",
) -> Panel:
    clr = _c(color)
    body = Text()
    body.append(f"  {icon}  ", style=f"bold {clr}")
    body.append(text, style="bold white")
    return Panel(body, border_style=clr, box=SIMPLE_HEAD, padding=(0, 1))


# ---------------------------------------------------------------------------
# Flag glossary
# ---------------------------------------------------------------------------


FLAG_GLOSSARY: dict[str, str] = {
    "-d": "Data (YYYY-MM-DD). Default: hoje.",
    "-e": "--energia  Energia 1-10 (registrar agora).",
    "-f": "--foco  Foco 1-10 (registrar agora).",
    "-bh": "--bed-hour  Hora que dormiu (0-23).",
    "-bm": "--bed-minute  Minuto que dormiu (0-59).",
    "-wh": "--wake-hour  Hora que acordou (0-23).",
    "-wm": "--wake-minute  Minuto que acordou (0-59).",
    "-q": "--quality  Qualidade do sono (1-10).",
    "-r": "--rest  Descanso pós-refeição (min)  OU  --resistance (habit).",
    "-p": "--pesado  Almoço pesado  OU  --period (bloco).",
    "-l": "--label  Rótulo (bloco, checkin).",
    "-w": "--weight  Peso QHE (habit).",
    "-j / --json": "Output em JSON (machine-readable).",
    "-s": "--start  Início (relatório semanal).",
    "-en": "--end  Fim (relatório semanal).",
}


def flag_glossary_panel() -> Panel:
    t = Table(show_header=True, header_style="bold cyan", box=SIMPLE, border_style="cyan", padding=(0, 1))
    t.add_column("Flag", style="bold yellow", min_width=10)
    t.add_column("Significado", style="white")
    for flag, desc in FLAG_GLOSSARY.items():
        t.add_row(flag, desc)
    return Panel(t, title="[bold cyan]📖 Glossário de Flags[/bold cyan]", border_style="cyan", box=SIMPLE_HEAD, padding=(0, 1))


__all__ = [
    "COLORS",
    "TIPO_DIA_COLOR",
    "FLAG_GLOSSARY",
    "make_console",
    "get_render_width",
    "kpi_card",
    "section_header",
    "progress_bar",
    "pomodoros_grid",
    "timeline_h",
    "cartesian_plane",
    "sparkline",
    "metric_table",
    "input_summary",
    "next_step",
    "flag_glossary_panel",
]
