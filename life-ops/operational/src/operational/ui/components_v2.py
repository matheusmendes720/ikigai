"""PAV-OS v2 UI components — design system v2.

This is the **new** component layer. The old ``ui/components.py``
stays untouched for backward compatibility. New commands and
mock-driven tests should use this module.

Key changes from v1:
- All colors come from ``ui.tokens`` (never hardcoded)
- All glyphs come from ``ui.tokens.Glyph`` (never hardcoded)
- Components are pure functions returning Rich renderables
- 1-line KPI cards (vs 4-line in v1)
- Cartesian plane with equation + legend + history
- Regime bar with direction
- Pomodoros grid with focus score per session
- Next-step with observation + action (2 lines)
- All widgets have a ``--mock`` mode for visual testing

See ``docs/design-system/DESIGN-SYSTEM.md`` for full spec.
"""
from __future__ import annotations

from typing import Any

from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Column, Table
from rich.text import Text

from operational.enums import PolicyState, TipoDia
from operational.ui.tokens import (
    CONSOLE_WIDTH_V2, Glyph, PADDING, QUADRANT, REGIME,
    SEVERITY, STYLES, SURFACE,
)


# Silence the linter — these may be used by callers
_ = (Glyph, SURFACE, PADDING, STYLES)


# ---------------------------------------------------------------------------
# Header v2 — 3-zone title bar
# ---------------------------------------------------------------------------

def header_v2(
    title: str,
    subtitle: str,
    context: RenderableType | None = None,
    width: int = CONSOLE_WIDTH_V2,
) -> RenderableType:
    """3-zone header: title | subtitle | context badge.

    Wireframe:
    ─────────────────────────────────────────────...
     DAILY REPORT    2026-06-08    regime: PUSH
    ─────────────────────────────────────────────...
    """
    bar_top = Text("─" * width, style=SEVERITY["primary"])
    bar_bot = Text("─" * width, style="grey30")
    line = Text()
    line.append(f" {title.upper()}", style=STYLES["h2"])
    line.append("    ")
    line.append(subtitle, style=STYLES["mono"])
    if context is not None:
        line.append("    ")
        line.append_text(Text.from_markup(str(context)) if isinstance(context, str) else context)  # type: ignore[arg-type]
    return Group(bar_top, line, bar_bot)


# ---------------------------------------------------------------------------
# KPI Card v2 — single-line high-density
# ---------------------------------------------------------------------------

def kpi_v2(
    label: str,
    value: str,
    severity: str = "primary",
    delta: str | None = None,
    icon: str = "·",
    width: int = 28,
) -> RenderableType:
    """Single-line KPI: [icon] [label] [value] [delta].

    Wireframe:
    ┌──────────────────────────┐
    │ 😴 Sono       8.0h  🟢  │
    │              +0.5h 7d   │
    └──────────────────────────┘
    """
    color = SEVERITY.get(severity, "default")
    grid = Table.grid(expand=False, padding=(0, 1))
    grid.add_column(min_width=2, justify="left")
    grid.add_column(min_width=8, justify="left")
    grid.add_column(min_width=8, justify="right")
    grid.add_column(min_width=2, justify="right")
    grid.add_row(icon, label, f"[{color}]{value}[/]", delta or "")
    if delta:
        grid2 = Table.grid(expand=False, padding=(0, 1))
        grid2.add_column(min_width=2)
        grid2.add_column(min_width=8, justify="right")
        grid2.add_row("", f"[grey58]{delta}[/]")
        body = Group(grid, grid2)
    else:
        body = grid
    return Panel(body, border_style=color, width=width, padding=(0, 1))


def kpi_grid_2x2(
    cards: list[RenderableType],
) -> RenderableType:
    """2x2 grid of KPI cards."""
    if len(cards) != 4:
        return Columns(cards, equal=True, expand=True)
    row1 = Columns([cards[0], cards[1]], equal=True, expand=True)
    row2 = Columns([cards[2], cards[3]], equal=True, expand=True)
    return Group(row1, row2)


# ---------------------------------------------------------------------------
# Section Panel v2
# ---------------------------------------------------------------------------

def section_v2(
    title: str,
    icon: str = "·",
    subtitle: str = "",
    content: RenderableType | None = None,
    severity: str = "primary",
    footer: RenderableType | None = None,
) -> RenderableType:
    """Section panel with title, subtitle, content, optional footer."""
    color = SEVERITY.get(severity, "default")
    title_line = Text()
    title_line.append(f"  {icon}  ", style=color)
    title_line.append(f"{title.upper()}", style=f"bold {color}")
    if subtitle:
        title_line.append(f"  {subtitle}", style=STYLES["body_muted"])
    body: list[RenderableType] = [title_line, content] if content else [title_line]
    if footer:
        body.append(footer)
    return Panel(
        Group(*body),
        border_style=color,
        padding=(0, 1),
    )


# ---------------------------------------------------------------------------
# Cartesian Plane v2 — with legend, equation, history
# ---------------------------------------------------------------------------

def cartesian_v2(
    x: float,
    y: float,
    quadrant: str,
    show_legend: bool = True,
    show_equation: bool = True,
    historical: list[tuple[float, float]] | None = None,
    width: int = 30,
    height: int = 9,
) -> RenderableType:
    """Cartesian plane with quadrant fill, legend, equation, history.

    x: 0-100 (produtividade)
    y: 0-100 (eficiencia)
    quadrant: "Q1" | "Q2" | "Q3" | "Q4"
    """
    spec = QUADRANT.get(quadrant, QUADRANT["Q1"])
    glyph = spec.glyph

    # Build the grid: 1 row for "Y%", rows for y=100..0, 1 row for x-axis labels
    grid = Table.grid(expand=False, padding=(0, 0))
    grid.add_column(min_width=4, justify="right")  # Y label
    grid.add_column(min_width=2, justify="right")  # axis
    grid.add_column(min_width=width - 8, justify="left")  # plot area
    grid.add_column(min_width=2, justify="left")  # right pad

    # Header row
    y_label = Text("Y%", style=STYLES["body_muted"])
    grid.add_row(y_label, "", "", "")

    # 7 horizontal lines (Y from 100 to 0)
    y_ticks = [100, 84, 68, 52, 36, 20, 4, 0]
    plot_chars: list[list[str]] = []
    for i, y_val in enumerate(y_ticks[:-1]):
        line_chars = [" "] * (width - 6)
        # Add the Y-axis tick mark
        if y_val == 50 or y_val == 52:
            for j in range(len(line_chars)):
                if j == 0:
                    line_chars[j] = Glyph.LINE_H
                elif j % 2 == 0:
                    line_chars[j] = Glyph.LINE_H
        # Add the point
        if historical and i < len(historical):
            hx_pct, hy_pct = historical[i]
            x_pos = int(hx_pct / 100 * (width - 7))
            y_pos = int((100 - hy_pct) / 100 * (height - 2))
            if 0 <= y_pos < (height - 1) and 0 <= x_pos < (width - 7):
                if 0 <= y_pos < len(plot_chars):
                    plot_chars[y_pos][x_pos] = "·"
        plot_chars.append(line_chars)

    # Place the point
    x_pos = int(x / 100 * (width - 7))
    y_pos = int((100 - y) / 100 * (height - 2))
    if 0 <= y_pos < (height - 2) and 0 <= x_pos < (width - 7):
        if y_pos < len(plot_chars):
            plot_chars[y_pos][x_pos] = glyph

    # Render rows
    for i, y_val in enumerate(y_ticks[:-1]):
        y_text = Text(f"{y_val:>3}", style=STYLES["body_muted"])
        sep_text = Text(Glyph.AXIS_Y, style=STYLES["body_muted"])
        if i < len(plot_chars):
            plot_text = Text("".join(plot_chars[i]), style=spec.color)
        else:
            plot_text = Text(" " * (width - 6), style=STYLES["body_muted"])
        grid.add_row(y_text, sep_text, plot_text, "")

    # X axis row (with ──── and labels)
    x_axis_line = Glyph.AXIS_X * (width - 6)
    grid.add_row(
        Text("  0", style=STYLES["body_muted"]),
        Text(Glyph.AXIS_CROSS, style=SEVERITY["muted"]),
        Text(x_axis_line, style=SEVERITY["muted"]),
        "",
    )
    # X labels row
    label_text = Text()
    label_text.append("0", style=STYLES["body_muted"])
    label_text.append(" " * (width // 2 - 3))
    label_text.append("50", style=STYLES["body_muted"])
    label_text.append(" " * (width // 2 - 3))
    label_text.append("100", style=STYLES["body_muted"])
    grid.add_row("", "", label_text, "")

    # Wrap in a panel with optional legend
    body: list[RenderableType] = [grid]
    if show_equation:
        eq = Text()
        eq.append("X = realizado / orcado x 100\n", style=STYLES["mono"])
        eq.append("Y = foco / total x 100", style=STYLES["mono"])
        body.append(eq)
    if show_legend:
        leg = Text()
        for q, qspec in QUADRANT.items():
            leg.append(f"  {qspec.glyph} {q} {qspec.label_pt}\n", style=qspec.color)
        body.append(leg)
    if historical:
        spk = Text()
        spk.append("  historico 7d: ", style=STYLES["body_muted"])
        # Convert historical to sparkline (y values only)
        y_vals = [h[1] for h in historical]
        if y_vals:
            chars = Glyph.SPARK_CHARS
            mn, mx = min(y_vals), max(y_vals)
            rng = max(1.0, mx - mn)
            spark = ""
            for v in y_vals:
                idx = int((v - mn) / rng * 7)
                spark += chars[idx]
            spk.append(spark, style=SEVERITY["info"])
        body.append(spk)

    return Panel(
        Group(*body),
        title=f"[{spec.color}] {glyph} {quadrant} — {spec.label_pt} [/]",
        border_style=spec.color,
        width=width + 2,
    )


# ---------------------------------------------------------------------------
# Pomodoros Grid v2 — focus score per session
# ---------------------------------------------------------------------------

def pomodoros_v2(
    s1_done: int = 0,
    s1_focus: float = 0.0,
    s2_done: int = 0,
    s2_focus: float = 0.0,
    s3_done: int = 0,
    s3_focus: float = 0.0,
    target_per_session: int = 4,
) -> RenderableType:
    """Per-session progress bar with focus score.

    Wireframe:
    S1 manha  ▣ ▣ ▣ ▢  75%   ⭐ 8/10
    S2 tarde  ▣ ▣ ▢ ▢  50%   ⭐ 6/10
    S3 noite  ▢ ▢ ▢ ▢   0%   ⭐ -
    """
    def render_session(label: str, done: int, focus: float) -> Text:
        cells = " ".join([Glyph.POMO_DONE if i < done else Glyph.POMO_SKIP for i in range(target_per_session)])
        pct = int(done / target_per_session * 100) if target_per_session else 0
        focus_str = f"{focus:.0f}/10" if focus > 0 else "-"
        color = SEVERITY["success"] if pct >= 80 else (SEVERITY["warning"] if pct >= 50 else SEVERITY["danger"])
        t = Text()
        t.append(f"  {label:<8}", style=STYLES["body"])
        t.append(f"  {cells}", style=color)
        t.append(f"  {pct:>3}%", style=color)
        t.append(f"   ⭐ {focus_str}", style=STYLES["mono"])
        return t

    s1 = render_session("S1 manha", s1_done, s1_focus)
    s2 = render_session("S2 tarde", s2_done, s2_focus)
    s3 = render_session("S3 noite", s3_done, s3_focus)

    total = s1_done + s2_done + s3_done
    max_total = target_per_session * 3
    total_pct = int(total / max_total * 100) if max_total else 0
    total_text = Text()
    total_text.append(f"\n  Total: {total}/{max_total} ({total_pct}%)", style=STYLES["emphasis"])

    return Group(s1, s2, s3, total_text)


# ---------------------------------------------------------------------------
# Regime Bar v2 — direction indicator
# ---------------------------------------------------------------------------

def regime_bar(
    current: str,
    history: list[str] | None = None,
) -> RenderableType:
    """Bar showing PUSH -> MAINTAIN -> REDUCE -> RECOVER with marker.

    Wireframe:
            PUSH    MAINTAIN   REDUCE   RECOVER
             ▲◆      ◇◇◇        ◇◇       ◇◇◇
            today   3 dias    2 dias   2 dias
    """
    order = ["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]
    grid = Table.grid(expand=False, padding=(0, 2))
    for r in order:
        spec = REGIME[r]
        grid.add_column(min_width=10, justify="center")
    header_row = Text()
    for r in order:
        spec = REGIME[r]
        header_row.append(f"{r:^10}", style=f"bold {spec.color}")
    grid.add_row(*[r for r in order])
    grid.add_row(*[
        Text(
            f"{spec.glyph}{spec.glyph}{spec.glyph}" if r == current
            else (f"{Glyph.MUTED_DOT}{Glyph.MUTED_DOT}{Glyph.MUTED_DOT}" if history is None else f"{Glyph.MUTED_DOT}"),
            style=spec.color if r == current else SEVERITY["muted"],
        )
        for r in order
    ])
    return Panel(grid, title=f"[{REGIME[current].color}] REGIME: {current} [/]", border_style=REGIME[current].color)


# ---------------------------------------------------------------------------
# Sparkline v2 — with min/max labels
# ---------------------------------------------------------------------------

def sparkline_v2(
    values: list[float],
    label: str,
    show_min_max: bool = True,
    current_format: str = "{:.0f}",
) -> RenderableType:
    """Sparkline with min/max labels and current value."""
    if not values:
        return Text(f"  {label}: (no data)", style=SEVERITY["muted"])
    chars = Glyph.SPARK_CHARS
    mn, mx = min(values), max(values)
    cur = values[-1]
    rng = max(1.0, mx - mn)
    spark = "".join(chars[min(7, max(0, int((v - mn) / rng * 7)))] for v in values)
    t = Text()
    t.append(f"  {label:<12}", style=STYLES["body"])
    t.append(spark, style=SEVERITY["info"])
    t.append(f"  atual: {current_format.format(cur)}", style=STYLES["emphasis"])
    if show_min_max:
        t.append(f"  ({current_format.format(mn)} - {current_format.format(mx)})", style=STYLES["body_muted"])
    return t


# ---------------------------------------------------------------------------
# Next Step v2 — observation + action (2 lines)
# ---------------------------------------------------------------------------

def next_step_v2(
    observation: str,
    action: str,
    severity: str = "primary",
) -> RenderableType:
    """Two-line next step: OBSERVACAO + ACAO.

    Wireframe:
    OBSERVACAO: Q1 mantido por 5 dias consecutivos.
    ACAO:       Aumentar pomodoros de 12 para 14 (gradual).
    """
    color = SEVERITY.get(severity, "default")
    t = Text()
    t.append("  OBSERVACAO: ", style=f"bold {color}")
    t.append(observation + "\n", style=STYLES["body"])
    t.append("  ACAO:       ", style=f"bold {color}")
    t.append(action, style=STYLES["emphasis"])
    return Panel(t, border_style=color, title=f"[{color}] NEXT STEP [/]")


# ---------------------------------------------------------------------------
# Error Panel v2
# ---------------------------------------------------------------------------

def error_panel_v2(
    message: str,
    context: str = "",
    expected: str = "",
    suggestion: str = "",
) -> RenderableType:
    """Error panel with context, expected format, suggested fix.

    Wireframe:
    ┌─ ⚠ ERRO ─────────────────────────────┐
    │ Data invalida: 2026-13-99            │
    │                                       │
    │ Contexto:    pav report today --date 2026-13-99
    │ Esperado:    YYYY-MM-DD               │
    │ Sugestao:    pav report today --date 2026-06-08
    └───────────────────────────────────────┘
    """
    body = Text()
    body.append(f"  {message}\n\n", style=f"bold {SEVERITY['danger']}")
    if context:
        body.append(f"  Contexto:    {context}\n", style=STYLES["body_muted"])
    if expected:
        body.append(f"  Esperado:    {expected}\n", style=STYLES["body_muted"])
    if suggestion:
        body.append(f"  Sugestao:    {suggestion}\n", style=STYLES["emphasis"])
    return Panel(
        body,
        title=f"[{SEVERITY['danger']}] ⚠ ERRO [/]",
        border_style=SEVERITY["danger"],
    )


# ---------------------------------------------------------------------------
# Page (NEW) — composes header + body + footer
# ---------------------------------------------------------------------------

def page(
    title: str,
    subtitle: str,
    body: RenderableType,
    footer: RenderableType | None = None,
    width: int = CONSOLE_WIDTH_V2,
) -> RenderableType:
    """Standard page: header + body + optional footer."""
    parts: list[RenderableType] = [header_v2(title, subtitle, width=width), Padding(body, (1, 0))]
    if footer is not None:
        parts.append(Padding(footer, (1, 0)))
    return Group(*parts)


__all__ = [
    "header_v2",
    "kpi_v2",
    "kpi_grid_2x2",
    "section_v2",
    "cartesian_v2",
    "pomodoros_v2",
    "regime_bar",
    "sparkline_v2",
    "next_step_v2",
    "error_panel_v2",
    "page",
]
