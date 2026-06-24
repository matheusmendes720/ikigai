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

from rich.box import DOUBLE, ROUNDED
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from operational.ui.tokens import (
    CONSOLE_WIDTH_V2,
    PADDING,
    QUADRANT,
    REGIME,
    SEVERITY,
    STYLES,
    SURFACE,
    Glyph,
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
        if y_val in {50, 52}:
            for j in range(len(line_chars)):
                if j == 0 or j % 2 == 0:
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
    if 0 <= y_pos < (height - 2) and 0 <= x_pos < (width - 7) and y_pos < len(plot_chars):
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
    grid.add_row(*list(order))
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
# Progress v2 — horizontal bar with severity color + absolute value
# ---------------------------------------------------------------------------

def progress_v2(
    value: float,
    max_value: float,
    label: str = "",
    severity: str = "primary",
    width: int = 20,
) -> RenderableType:
    """Horizontal progress bar with severity color and absolute value.

    Wireframe:
      Hardwork   ████████████░░░░░░░░  50%  (240/480)

    Args:
        value: Current value.
        max_value: Maximum value (total).
        label: Optional left-side label.
        severity: One of "primary", "success", "warning", "danger".
        width: Width of the bar in characters.

    Returns:
        A :class:`rich.text.Text` renderable.
    """
    color = SEVERITY.get(severity, SEVERITY["primary"])
    pct = 0.0 if max_value <= 0 else max(0.0, min(1.0, value / max_value))
    filled = round(pct * width)
    empty = width - filled
    t = Text()
    if label:
        t.append(f"  {label:<10}", style=STYLES["body"])
    t.append(Glyph.BAR_FULL * filled, style=color)
    t.append(Glyph.BAR_EMPTY * empty, style=SEVERITY["muted"])
    t.append(f"  {int(pct * 100):3d}%", style=f"bold {color}")
    t.append(f"  ({int(value)}/{int(max_value)})", style=STYLES["body_muted"])
    return t


# ---------------------------------------------------------------------------
# Metric v2 — table of metric values with optional severity-based coloring
# ---------------------------------------------------------------------------

def metric_v2(
    rows: list[tuple[str, str, str | None]],
    headers: list[str] | None = None,
    severity_col: int | None = None,
) -> RenderableType:
    """Table of metric values with optional severity-based row coloring.

    Wireframe:
       Métrica             Valor
       ─────────           ─────
       Sono                8.0h
       Pomodoros           12/12
       Energia             10/10

    Args:
        rows: List of ``(label, value, severity)`` tuples. Severity is
            optional (``None`` to skip coloring). One of "ok", "warn",
            "crit", "muted".
        headers: Optional column headers. Defaults to ``["Métrica", "Valor"]``.
        severity_col: Column index to color (default: the last column).

    Returns:
        A :class:`rich.table.Table` renderable.
    """
    if headers is None:
        headers = ["Métrica", "Valor"]
    sev_to_color = {
        "ok": SEVERITY["success"],
        "warn": SEVERITY["warning"],
        "crit": SEVERITY["danger"],
        "muted": SEVERITY["muted"],
    }
    target_col = severity_col if severity_col is not None else (len(headers) - 1)
    t = Table(
        show_header=bool(headers),
        header_style=f"bold {SEVERITY['primary']}",
        border_style=SEVERITY["muted"],
        box=None,
        padding=(0, 1),
        expand=False,
    )
    for h in headers:
        t.add_column(header=h, justify="left", no_wrap=False)
    for row in rows:
        # Pad to header length
        cells: list[str] = [str(c) for c in row[: len(headers)]]
        while len(cells) < len(headers):
            cells.append("")
        severity = row[2] if len(row) > 2 else None
        if severity and target_col < len(cells):
            color = sev_to_color.get(severity, SEVERITY["primary"])
            cells[target_col] = f"[{color}]{cells[target_col]}[/]"
        t.add_row(*cells)
    return t


# ---------------------------------------------------------------------------
# Severity Text v2 — simple colored Text factory
# ---------------------------------------------------------------------------

def severity_text_v2(
    text: str,
    severity: str = "info",
) -> RenderableType:
    """Simple colored :class:`rich.text.Text`.

    Args:
        text: The text to render.
        severity: One of "primary", "success", "warning", "danger",
            "info", "muted", "accent".

    Returns:
        A :class:`rich.text.Text` renderable.
    """
    color = SEVERITY.get(severity, SEVERITY["info"])
    return Text(text, style=color)


# ---------------------------------------------------------------------------
# Timeline Horizontal v2 — events on a horizontal axis with status glyphs
# ---------------------------------------------------------------------------

def timeline_h_v2(
    events: list[tuple[str, str, str]],
    width: int = 80,
) -> RenderableType:
    """Horizontal timeline with timestamp dots, labels, and status glyphs.

    Wireframe:
    ─ 06:00 ─── 07:00 ─── 09:00 ─── 12:00 ─── 14:00 ─── 18:00 ─── 22:00 ───
      ● wake     ● coffee   ● class    ● lunch     ● work     ● dinner    ● sleep
      ✓          ✓          ✓          ⚠ heavy     ✓          ✓          ◌

    Args:
        events: List of ``(timestamp, label, status)`` tuples.
            Status is one of "done", "warning", "pending", "active".
        width: Total display width.

    Returns:
        A :class:`rich.console.Group` renderable with 3 lines.
    """
    status_glyph = {
        "done": Glyph.CHECK,
        "warning": Glyph.CROSS,
        "pending": Glyph.PENDING,
        "active": Glyph.ACTIVE,
    }
    status_color = {
        "done": SEVERITY["success"],
        "warning": SEVERITY["warning"],
        "pending": SEVERITY["muted"],
        "active": SEVERITY["primary"],
    }
    if not events:
        return Text("  (no events)", style=SEVERITY["muted"])

    # Compute the time line: place each event's timestamp evenly-spaced
    # (the spec is a fixed-width wireframe — we just distribute slots).
    n = len(events)
    slot = max(8, (width - 2) // n)

    # Top row: ── timestamps connected by dashes
    top = Text("  ")
    for i, (ts, _label, _status) in enumerate(events):
        top.append(f"{Glyph.AXIS_X} {ts}", style=STYLES["body_muted"])
        if i < n - 1:
            pad = max(0, slot - len(ts) - 2)
            top.append(Glyph.AXIS_X * pad, style=SEVERITY["muted"])

    # Middle row: ● event label, left-aligned per slot
    mid = Text("  ")
    for i, (_ts, label, status) in enumerate(events):
        g = status_glyph.get(status, Glyph.MUTED_DOT)
        c = status_color.get(status, SEVERITY["muted"])
        mid.append(f"{g} {label}", style=c)
        if i < n - 1:
            pad = max(0, slot - len(label) - 2)
            mid.append(" " * pad, style=STYLES["body_muted"])

    # Bottom row: status glyphs (done/warning/pending/active)
    bot = Text("  ")
    for i, (_ts, _label, status) in enumerate(events):
        g = status_glyph.get(status, Glyph.MUTED_DOT)
        c = status_color.get(status, SEVERITY["muted"])
        bot.append(g, style=c)
        if i < n - 1:
            pad = max(0, slot - 1)
            bot.append(" " * pad, style=STYLES["body_muted"])

    return Group(top, mid, bot)


# ---------------------------------------------------------------------------
# Status Badge v2 — colored pill indicator
# ---------------------------------------------------------------------------

def status_badge_v2(
    label: str,
    severity: str = "info",
) -> RenderableType:
    """Colored pill status indicator.

    Wireframe:
      [ ● ACTIVE ]

    Args:
        label: Text to display inside the badge (will be uppercased).
        severity: One of "primary", "success", "warning", "danger",
            "info", "muted".

    Returns:
        A :class:`rich.text.Text` renderable.
    """
    color = SEVERITY.get(severity, SEVERITY["info"])
    use_active = severity in {"success", "primary"}
    glyph = Glyph.ACTIVE if use_active else Glyph.MUTED_DOT
    t = Text()
    t.append("  [ ", style=color)
    t.append(glyph, style=f"bold {color}")
    t.append(f" {label.upper()} ", style=f"bold {color}")
    t.append("] ", style=color)
    return t


# ---------------------------------------------------------------------------
# Input Summary v2 — echo what the user typed
# ---------------------------------------------------------------------------

def input_summary_v2(
    items: list[tuple[str, str]],
    title: str = "Você digitou",
) -> RenderableType:
    """Two-column table that echoes back the user's input.

    Wireframe:
    ╭─ Você digitou ─────────────────────────────────╮
    │  Nome           Morning workout                  │
    │  Período        MANHA                           │
    │  Tipo           CORE                            │
    │  Início         06:00                           │
    ╰─────────────────────────────────────────────────╯

    Args:
        items: List of ``(field, value)`` tuples.
        title: Panel title (default Portuguese).

    Returns:
        A :class:`rich.panel.Panel` renderable.
    """
    grid = Table.grid(expand=False, padding=(0, 1))
    grid.add_column(min_width=14, justify="left")
    grid.add_column(min_width=24, justify="left")
    for field, value in items:
        grid.add_row(
            Text(f"  {field}", style=STYLES["body_muted"]),
            Text(str(value), style=STYLES["emphasis"]),
        )
    return Panel(
        grid,
        title=f"[{SEVERITY['info']}] {title} [/]",
        border_style=SEVERITY["info"],
        padding=(0, 1),
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


# ---------------------------------------------------------------------------
# PRODUCTION-GRADE components — v2.1 batch
# ---------------------------------------------------------------------------

def big_panel(
    title: str,
    subtitle: str = "",
    content: RenderableType | None = None,
    severity: str = "primary",
    width: int = CONSOLE_WIDTH_V2,
) -> RenderableType:
    """Large bordered panel with thick top/bottom borders (DOUBLE box).

    Title is ALL CAPS in cyan, subtitle in grey, content centered.

    Wireframe:
    ╔══════════════════════════════════════════════════╗
    ║  TITLE                                            ║
    ║  subtitle here                                    ║
    ║                                                   ║
    ║  ... content ...                                  ║
    ║                                                   ║
    ╚══════════════════════════════════════════════════╝
    """
    color = SEVERITY.get(severity, SEVERITY["primary"])
    title_line = Text()
    title_line.append(f"  {title.upper()}", style=f"bold {color}")
    if subtitle:
        title_line.append(f"  ·  {subtitle}", style=STYLES["body_muted"])
    body: list[RenderableType] = [title_line]
    if content is not None:
        body.append(Padding(content, (0, 0)))
    return Panel(
        Group(*body),
        border_style=color,
        box=DOUBLE,
        width=width,
        padding=(0, 2),
    )


def two_column_grid(
    left: RenderableType,
    right: RenderableType,
    ratio: tuple[int, int] = (1, 1),
) -> RenderableType:
    """2-column grid layout (Rich Columns with equal=False + ratio).

    Args:
        left: Left column renderable.
        right: Right column renderable.
        ratio: Width ratio (left, right). Defaults to (1, 1).

    Wireframe:
    ┌─ left content ─────────┐  ┌─ right content ────────┐
    │ ...                    │  │ ...                     │
    └────────────────────────┘  └─────────────────────────┘
    """
    if ratio == (1, 1):
        return Columns([left, right], equal=True, expand=True)
    return Columns([left, right], equal=False, expand=True, align="left")


def kpi_grid_4x1(cards: list[RenderableType]) -> RenderableType:
    """4 KPI cards in a single row.

    Args:
        cards: Exactly 4 KPI renderables.

    Wireframe:
    [card1] [card2] [card3] [card4]
    """
    if len(cards) != 4:
        return Columns(cards, equal=True, expand=True)
    return Columns(cards, equal=True, expand=True)


def progress_bar_v2(
    value: float,
    max_value: float,
    label: str = "",
    color: str = "primary",
    width: int = 30,
    show_value: bool = True,
) -> RenderableType:
    """Better progress bar with optional label + value.

    Args:
        value: Current value.
        max_value: Maximum value.
        label: Left-side label (e.g. "Hardwork").
        color: Severity key (e.g. "primary", "success", "warning", "danger").
        width: Width of the bar in characters.
        show_value: Show "  65%  (240/480)" suffix.

    Wireframe:
      Hardwork  ████████████░░░░░░░░  65%  (240/480)
    """
    clr = SEVERITY.get(color, SEVERITY["primary"])
    pct = 0.0 if max_value <= 0 else max(0.0, min(1.0, value / max_value))
    filled = round(pct * width)
    empty = width - filled
    t = Text()
    if label:
        t.append(f"  {label:<14}", style=STYLES["body"])
    t.append(Glyph.BAR_FULL * filled, style=clr)
    t.append(Glyph.BAR_EMPTY * empty, style=SEVERITY["muted"])
    if show_value:
        t.append(f"  {int(pct * 100):3d}%", style=f"bold {clr}")
        if max_value > 0:
            t.append(f"  ({int(value)}/{int(max_value)})", style=STYLES["body_muted"])
    return t


def timeline_log(
    entries: list[tuple[str, str, str]],
    max_entries: int = 5,
) -> RenderableType:
    """Timeline with [HH:MM] [TYPE] message format.

    Args:
        entries: List of ``(timestamp, kind, message)`` tuples.
        max_entries: Maximum number of entries to display.

    Wireframe:
    [17:07] [CHECK-IN] Energia: 7, Foco: 8 (chk_20260609_170706)
    [17:07] [ROUTINE]  Start: Hardwork Dev (CORE)
    """
    color_map = {
        "ROUTINE":  SEVERITY["primary"],
        "CHECK-IN": SEVERITY["success"],
        "BLOCK":    SEVERITY["info"],
        "SYSTEM":   SEVERITY["muted"],
        "EVENT":    SEVERITY["accent"],
        "POMO":     SEVERITY["warning"],
    }
    lines: list[RenderableType] = []
    shown = entries[-max_entries:] if len(entries) > max_entries else entries
    for ts, kind, msg in shown:
        clr = color_map.get(kind.upper(), SEVERITY["muted"])
        t = Text()
        t.append(f"  [{ts}] ", style=STYLES["mono"])
        t.append(f"[{kind.upper():<9}] ", style=f"bold {clr}")
        t.append(msg, style=STYLES["body"])
        lines.append(t)
    if not lines:
        return Text("  (no timeline entries)", style=SEVERITY["muted"])
    return Group(*lines)


def kronograma_table(rows: list[tuple[str, str, str, str]]) -> RenderableType:
    """Table with Status / Período / Bloco / Outputs.

    Args:
        rows: List of ``(status, period, block, outputs)`` tuples.

    Wireframe:
    ┌──────────┬─────────┬──────────────────────┬──────────┐
    │ Status   │ Período │ Bloco                │ Outputs  │
    ├──────────┼─────────┼──────────────────────┼──────────┤
    │ [OK]     │ MANHA   │ Acordar              │ -        │
    └──────────┴─────────┴──────────────────────┴──────────┘
    """
    status_color = {
        "OK": SEVERITY["success"],
        "WARN": SEVERITY["warning"],
        "CRIT": SEVERITY["danger"],
        "PEND": SEVERITY["muted"],
        "ACTIVE": SEVERITY["primary"],
    }
    t = Table(
        show_header=True,
        header_style=f"bold {SEVERITY['primary']}",
        border_style=SEVERITY["muted"],
        box=ROUNDED,
        padding=(0, 1),
        expand=False,
    )
    t.add_column("Status", min_width=10, justify="left")
    t.add_column("Período", min_width=8, justify="left")
    t.add_column("Bloco", min_width=24, justify="left")
    t.add_column("Outputs", min_width=12, justify="right")
    for status, period, block, outputs in rows:
        sclr = status_color.get(status.upper(), SEVERITY["muted"])
        t.add_row(
            f"[{sclr}]● {status}[/]",
            period,
            block,
            outputs,
        )
    return t


def policy_actions_table(
    current_state: str,
    history: list[tuple[str, str, str]] | None = None,
) -> RenderableType:
    """Policy actions panel with current setpoint + history.

    Args:
        current_state: One of "PUSH", "MAINTAIN", "REDUCE", "RECOVER".
        history: Optional list of ``(date, transition, reason)`` tuples.

    Wireframe:
    ╭─ 🕹️ SETPOINT ATUAL ─────────────────────────────────╮
    │  MODO: [ MAINTAIN ] ◆               Atualizado em...  │
    ╰─────────────────────────────────────────────────────╯
    ╭─ 📝 ÚLTIMAS DECISÕES DE POLÍTICA ────────────────────╮
    │  2026-06-03 | PUSH → MAINTAIN | Fim de sprint...     │
    ╰─────────────────────────────────────────────────────╯
    """
    spec = REGIME.get(current_state, REGIME["MAINTAIN"])

    setpoint_grid = Table.grid(expand=False, padding=(0, 2))
    setpoint_grid.add_column(min_width=10, justify="left")
    setpoint_grid.add_column(min_width=20, justify="left")
    setpoint_grid.add_row(
        Text("  MODO:", style=STYLES["body_muted"]),
        Text(f" [ {spec.glyph} {current_state} ]", style=f"bold {spec.color}"),
    )

    setpoint_panel = Panel(
        setpoint_grid,
        title=f"[{spec.color}] 🕹️ SETPOINT ATUAL [/]",
        border_style=spec.color,
        padding=(0, 1),
    )

    parts: list[RenderableType] = [setpoint_panel]

    if history:
        history_lines: list[RenderableType] = []
        for date_str, transition, reason in history:
            t = Text()
            t.append(f"  {date_str}", style=STYLES["mono"])
            t.append("  │  ", style=SEVERITY["muted"])
            t.append(transition, style=f"bold {SEVERITY['primary']}")
            t.append("  │  ", style=SEVERITY["muted"])
            t.append(reason, style=STYLES["body"])
            history_lines.append(t)
        history_panel = Panel(
            Group(*history_lines),
            title=f"[{SEVERITY['info']}] 📝 ÚLTIMAS DECISÕES DE POLÍTICA [/]",
            border_style=SEVERITY["info"],
            padding=(0, 1),
        )
        parts.append(history_panel)

    return Group(*parts)


# ---------------------------------------------------------------------------
# Aliases for clarity in callers
# ---------------------------------------------------------------------------

big_panel_header = big_panel


__all__ = [
    # Production-grade v2.1 batch
    "big_panel",
    "big_panel_header",
    "cartesian_v2",
    "error_panel_v2",
    "header_v2",
    "input_summary_v2",
    "kpi_grid_2x2",
    "kpi_grid_4x1",
    "kpi_v2",
    "kronograma_table",
    "metric_v2",
    "next_step_v2",
    "page",
    "policy_actions_table",
    "pomodoros_v2",
    "progress_bar_v2",
    # v1 port — new in this batch
    "progress_v2",
    "regime_bar",
    "section_v2",
    "severity_text_v2",
    "sparkline_v2",
    "status_badge_v2",
    "timeline_h_v2",
    "timeline_log",
    "two_column_grid",
]
