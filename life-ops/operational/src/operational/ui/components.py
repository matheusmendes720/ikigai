"""Rich UI factory components — pure view layer, zero business logic.

All functions here receive Python data structures (dicts, dataclasses, lists)
and return Rich renderables (Table, Panel, Text, Group).

NEVER call console.print() here. NEVER do data fetching here.
NEVER concatenate strings to "align" content — use Rich Table/Table.grid.

If you find yourself reaching for `f"x{' ' * n}y"` to align text,
STOP. Use ``Table.grid(expand=False)`` with ``no_wrap=True`` columns.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Sequence

from rich.box import SIMPLE, SIMPLE_HEAD, HEAVY
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Column, Table
from rich.text import Text

from operational.cli.console import console as default_console, CONSOLE_WIDTH
from operational.enums import Period, TipoDia

# ---------------------------------------------------------------------------
# Color palette (centralized)
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = {
    "primary": "cyan",
    "ok": "bright_green",
    "warn": "yellow",
    "crit": "bold red",
    "info": "deep_sky_blue1",
    "muted": "grey58",
    "sleep": "dodger_blue2",
    "hardwork": "green3",
    "ease": "magenta",
    "energy": "yellow1",
    "focus": "deep_sky_blue1",
    "transition": "deep_pink1",
}

TIPO_DIA_COLOR: dict[str, str] = {
    TipoDia.CURSO.value: "dodger_blue1",
    TipoDia.LIVRE.value: "green3",
    TipoDia.HARDCORE.value: "red",
    TipoDia.DESCANSO.value: "grey50",
}

PERIOD_ICON: dict[str, str] = {
    Period.MANHA.value: "🌅",
    Period.TARDE.value: "💻",
    Period.NOITE.value: "🌙",
}

QUADRANT_EMOJI: dict[str, str] = {
    "Q1": "🏆",
    "Q2": "🟢",
    "Q3": "🚨",
    "Q4": "⚠️",
}

QUADRANT_COLOR: dict[str, str] = {
    "Q1": "bright_green",
    "Q2": "cyan",
    "Q3": "bold red",
    "Q4": "yellow",
}

QUADRANT_LABEL: dict[str, str] = {
    "Q1": "Excelente — manter ritmo",
    "Q2": "Otimizado mas pouco output",
    "Q3": "Crítico — revisar sistema, identificar bloqueios",
    "Q4": "Produtivo mas precisa otimizar",
}

QUADRANT_ACTION: dict[str, str] = {
    "Q1": "Manter",
    "Q2": "Aumentar volume de trabalho",
    "Q3": "Revisão urgente",
    "Q4": "Reduzir distrações",
}

SEVERITY_COLOR: dict[str, str] = {
    "ok": COLORS["ok"],
    "warn": COLORS["warn"],
    "crit": COLORS["crit"],
    "info": COLORS["info"],
    "muted": COLORS["muted"],
    None: "white",
}


# ---------------------------------------------------------------------------
# Severity helpers (used by core/services.py to attach severity to data)
# ---------------------------------------------------------------------------

def sev_for_wake_hour(hour: int | None) -> str | None:
    if hour is None:
        return "muted"
    if 3 <= hour <= 5:
        return "ok"
    if hour == 6:
        return "warn"
    if hour >= 7:
        return "crit"
    return "ok"


def sev_for_sleep_hour(hour: int | None) -> str | None:
    if hour is None:
        return "muted"
    if 18 <= hour <= 21:
        return "ok"
    if hour == 22 or hour == 17:
        return "warn"
    return "crit"


def sev_for_sleep_hours(hours: float | None) -> str | None:
    if hours is None:
        return "muted"
    if hours >= 7:
        return "ok"
    if hours >= 5:
        return "warn"
    return "crit"


def sev_for_quality(q: int | None) -> str | None:
    if q is None:
        return "muted"
    if q >= 7:
        return "ok"
    return "warn"


def sev_for_lunch(eat: int, rest: int, pesado: bool) -> str:
    if pesado:
        return "crit"
    if eat <= 5 and rest <= 30:
        return "ok"
    return "warn"


def sev_for_transicoes(done: int, total: int) -> str:
    if done == total:
        return "ok"
    if done >= max(1, total - 2):
        return "warn"
    return "crit"


def sev_for_desvio(desvio_min: int) -> str:
    """Classify a deviation in minutes."""
    if -20 <= desvio_min <= 20:
        return "ok"
    if desvio_min > 20 or desvio_min < -20:
        return "warn"
    return "crit"


def emoji_for_sleep(hours: float | None) -> str:
    if hours is None:
        return "—"
    if hours >= 9:
        return "🟢 excelente"
    if hours >= 8:
        return "🟢 bom"
    if hours >= 7:
        return "🟡 aceitável"
    if hours >= 4:
        return "🟠 hardcore"
    return "🔴 crítico"


# ---------------------------------------------------------------------------
# Atomic renderers (no logic, just formatting)
# ---------------------------------------------------------------------------

def _bar(value: float, total: float, width: int = 18) -> str:
    """Render a progress bar string (no Rich)."""
    pct = 0.0 if total <= 0 else max(0.0, min(1.0, value / total))
    filled = int(round(pct * width))
    empty = width - filled
    return "█" * filled + "░" * empty


def progress_bar(value: float, total: float, *, width: int = 18, severity: str = "ok", label: str = "") -> Text:
    """Rich-rendered progress bar."""
    color = SEVERITY_COLOR.get(severity, "white")
    bar = _bar(value, total, width)
    pct = 0.0 if total <= 0 else max(0.0, min(1.0, value / total))
    t = Text()
    t.append(bar, style=color)
    t.append(f"  {int(pct * 100):3d}%", style=f"bold {color}")
    if label:
        t.append(f"  ({label})", style="grey58")
    return t


def sparkline(values: Sequence[float], *, color: str = "primary", label: str = "") -> Text:
    """Inline 7-day trend (▁▂▃▄▅▆▇█)."""
    if not values:
        return Text("  (sem dados)", style="grey58")
    chars = "▁▂▃▄▅▆▇█"
    lo = min(values)
    hi = max(values)
    span = max(1e-9, hi - lo)
    t = Text("  ")
    for v in values:
        idx = int((v - lo) / span * (len(chars) - 1))
        t.append(chars[idx], style=COLORS.get(color, color))
    if label:
        t.append(f"  {label}", style="grey58")
    return t


def pomodoros_grid(s1: int, s2: int, s3: int, *, max_per_session: int = 4) -> Table:
    """Compact 3-row pomodoros grid as a Table.grid (NO string concat)."""
    grid = Table.grid(padding=(0, 1), expand=False)
    grid.add_column(justify="left", min_width=11)
    for _ in range(max_per_session):
        grid.add_column(justify="center", min_width=2)
    grid.add_column(min_width=6, justify="right")

    for label, n in [("S1 manhã", s1), ("S2 tarde", s2), ("S3 noite", s3)]:
        n = max(0, min(max_per_session, n))
        row: list[RenderableType] = [Text(f"  {label}", style="bold white")]
        for i in range(max_per_session):
            cell = Text("▣ " if i < n else "▢ ", style="green3" if i < n else "grey50")
            row.append(cell)
        row.append(Text(f" {n}/{max_per_session}", style="bold white"))
        grid.add_row(*row)
    return grid


def cartesian_plane(
    x: float,
    y: float,
    *,
    width: int = 18,
    height: int = 7,
) -> Table:
    """Clean Cartesian plane built as a Table.grid — NO loose Text building.

    Returns a ``rich.table.Table.grid`` that the caller can render inside
    a Panel. Axes are labels (numbers), grid lines are visible only at
    50% quadrants, the point is plotted as a colored glyph.
    """
    x = max(0.0, min(100.0, x))
    y = max(0.0, min(100.0, y))

    px = round(x / 100 * (width - 1))
    py = round((100 - y) / 100 * (height - 1))

    if x >= 50 and y >= 50:
        point_color, point_char = "bright_green", "◆"
    elif x < 50 and y >= 50:
        point_color, point_char = "cyan", "◆"
    elif x < 50 and y < 50:
        point_color, point_char = "bold red", "✗"
    else:
        point_color, point_char = "yellow", "▲"

    # All cells in the grid use FIXED widths to avoid Rich's auto-sizing
    # splitting words like "Y%" or "100" across columns.
    grid = Table.grid(expand=False, padding=(0, 0))
    grid.add_column(width=5, justify="right", no_wrap=True)  # Y axis labels
    for _ in range(width):
        grid.add_column(width=2, justify="center", no_wrap=True)  # 2-ch wide cells
    grid.add_column(width=18, justify="left", no_wrap=True)  # X axis label

    # X-axis top label — minimal header (Y% left, X% right)
    # Use width-aligned cells: 2-ch wide for each column position
    header_row: list[RenderableType] = [Text("Y% ", style="grey58")]
    for _ in range(width):
        header_row.append(Text("  ", style="grey58"))
    header_row.append(Text("X% (Produtividade)", style="grey58"))
    grid.add_row(*header_row)

    # Y-axis body rows
    for row in range(height):
        y_val = 100 - row * (100 // (height - 1)) if (height - 1) else 0
        cells: list[RenderableType] = [Text(f"{y_val:>3} ", style="grey58")]
        for col in range(width):
            is_point = (col == px and row == py)
            is_origin = (col == 0 and row == height - 1)
            is_y_axis = (col == 0)
            is_x_axis = (row == height - 1)
            is_50x = (col == width // 2) and 0 < col < width - 1
            is_50y = (row == height // 2) and 0 < row < height - 1

            if is_point and not is_origin:
                cells.append(Text(f"{point_char} ", style=f"bold {point_color}"))
            elif is_origin:
                cells.append(Text("┼ ", style="bold white"))
            elif is_y_axis:
                cells.append(Text("│ ", style="grey58"))
            elif is_x_axis:
                cells.append(Text("─ ", style="grey58"))
            elif is_50x:
                cells.append(Text("┊ ", style="grey30"))
            elif is_50y:
                cells.append(Text("┈ ", style="grey30"))
            else:
                cells.append(Text("  ", style="grey30"))
        cells.append(Text("", style="grey58"))
        grid.add_row(*cells)

    # X-axis bottom label — show 0, 50, 100 below the plane
    x_label_row: list[RenderableType] = [Text("   ", style="grey58")]
    # Place 0 at first column position, 50 in middle, 100 at last
    x_label_cells: list[RenderableType] = [Text("  ", style="grey58")] * width
    x_label_cells[0] = Text("0 ", style="grey58")
    x_label_cells[width // 2] = Text("50", style="grey58")
    x_label_cells[width - 1] = Text("10", style="grey58")  # First 2 chars of "100"
    # Add the trailing "0" of "100" to the right-side label column
    for c in x_label_cells:
        x_label_row.append(c)
    x_label_row.append(Text("0", style="grey58"))  # Last char of "100"
    grid.add_row(*x_label_row)

    return grid


def severity_text(value: str, severity: str | None) -> Text:
    """Wrap a value in severity color, defaulting to white."""
    color = SEVERITY_COLOR.get(severity, "white")
    return Text(value, style=color)


# ---------------------------------------------------------------------------
# Top-level composite components (Panels, Layouts)
# ---------------------------------------------------------------------------


def kpi_card(
    title: str,
    value: str,
    *,
    color: str = "primary",
    footer: str = "",
    icon: str = "",
    width: int = 28,
) -> Panel:
    """KPI card with big number."""
    clr = COLORS.get(color, color)
    body = Text()
    if icon:
        body.append(f"  {icon}  ", style=f"bold {clr}")
        body.append(f"{title}\n", style=f"bold {clr}")
    else:
        body.append(f"  {title}\n", style=f"bold {clr}")
    body.append(f"  {value}", style="bold white")
    if footer:
        body.append(f"\n  {footer}", style="grey58 italic")
    return Panel(body, border_style=clr, box=SIMPLE_HEAD, padding=(0, 1), width=width)


def section_panel(
    title: str,
    body: RenderableType,
    *,
    color: str = "primary",
) -> Panel:
    """Section panel with bold colored title."""
    clr = COLORS.get(color, color)
    return Panel(
        body,
        title=f"[bold {clr}]  {title}  [/bold {clr}]",
        border_style=clr,
        box=SIMPLE_HEAD,
        padding=(0, 1),
    )


def next_step_panel(text: str, *, severity: str = "ok", icon: str = "→") -> Panel:
    """A short recommendation panel."""
    clr = SEVERITY_COLOR.get(severity, "ok")
    body = Text()
    body.append(f"  {icon}  ", style=f"bold {clr}")
    body.append(text, style="bold white")
    return Panel(body, border_style=clr, box=SIMPLE_HEAD, padding=(0, 1))


def error_panel(
    mensagem: str,
    *,
    contexto: str | None = None,
    severity: str = "crit",
    hint: str | None = None,
) -> Panel:
    """A standardized error panel for the user (no raw traceback).

    The full traceback is logged via ``log_error`` for the developer;
    the user sees this clean panel with the error message, optional
    context, and a hint about how to debug.
    """
    clr = SEVERITY_COLOR.get(severity, "red")
    icon = {"crit": "❌", "warn": "⚠️", "ok": "ℹ️"}.get(severity, "❌")
    title = {
        "crit": "Erro de Execução",
        "warn": "Aviso",
        "ok": "Informação",
    }.get(severity, "Erro")

    body = Text()
    body.append(f"{icon} {title}\n\n", style=f"bold {clr}")
    body.append(mensagem, style="white")
    if contexto:
        body.append(f"\n\n[Contexto] {contexto}", style="italic dim")
    if hint:
        body.append(f"\n\n[💡 Dica] {hint}", style="italic dim")

    return Panel(
        body,
        title=f"[bold {clr}]SISTEMA FALHOU[/bold {clr}]",
        border_style=clr,
        box=SIMPLE_HEAD,
        padding=(0, 1),
        width=min(100, 120),
    )


__all__ = [
    # Constants
    "COLORS",
    "TIPO_DIA_COLOR",
    "PERIOD_ICON",
    "QUADRANT_EMOJI",
    "QUADRANT_COLOR",
    "QUADRANT_LABEL",
    "QUADRANT_ACTION",
    "SEVERITY_COLOR",
    # Severity helpers
    "sev_for_wake_hour",
    "sev_for_sleep_hour",
    "sev_for_sleep_hours",
    "sev_for_quality",
    "sev_for_lunch",
    "sev_for_transicoes",
    "sev_for_desvio",
    "emoji_for_sleep",
    # Renderers
    "progress_bar",
    "sparkline",
    "pomodoros_grid",
    "cartesian_plane",
    "severity_text",
    "kpi_card",
    "section_panel",
    "next_step_panel",
    "error_panel",
]
