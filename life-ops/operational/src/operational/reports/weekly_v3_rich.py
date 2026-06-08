"""Weekly V3 report — Cinematic Rich-rendered, fully TTY.

Layout (6 sections):
1. Header (week range)
2. 2x2 KPI grid (Hardwork, Pomodoros, Sono, Reflexões)
3. Tendências (sparklines 7-dias)
4. TipoDia distribution (mini bar chart)
5. Quadrant distribution (mini bar chart)
6. Daily positions table
7. Next-step
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from rich.box import SIMPLE, SIMPLE_HEAD
from rich.console import Console, Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from operational.cli.renderers import (
    COLORS,
    TIPO_DIA_COLOR,
    cartesian_plane,
    kpi_card,
    make_console,
    metric_table,
    next_step,
    sparkline,
)
from operational.core.budget import (
    budget_for_date,
    classify_quadrant,
    productivity_pct,
)
from operational.enums import TipoDia

__all__ = ["generate_weekly_v3_rich", "generate_weekly_v3_markdown"]


def generate_weekly_v3_rich(
    *,
    ws: date,
    we: date,
    sleeps: list[Any],
    blocks: list[Any],
    n_pomodoros: int,
    reflections: list[Any],
    daily_data: list[tuple[date, int, int, int]],
) -> RenderableType:
    """Build the Rich weekly report."""
    sections: list[RenderableType] = []

    n_days = (we - ws).days + 1
    sleep_hours = [s.duration_hours for s in sleeps if s.duration_hours]
    avg_sleep = sum(sleep_hours) / len(sleep_hours) if sleep_hours else 0
    min_sleep = min(sleep_hours) if sleep_hours else 0
    max_sleep = max(sleep_hours) if sleep_hours else 0
    orcado_total = sum(orcado for _, orcado, _, _ in daily_data)
    realizado_total = sum(realizado for _, _, realizado, _ in daily_data)
    avg_x = sum(productivity_pct(r, o) for _, o, r, _ in daily_data) / len(daily_data) if daily_data else 0

    # === Header ===
    header = Text()
    header.append("  📈  ", style="bold cyan")
    header.append(f"WEEKLY REPORT  ·  {ws.isoformat()} → {we.isoformat()}", style="bold white")
    header.append("  ·  ", style="dim")
    header.append(f"{n_days} dias", style="dim")
    sections.append(Panel(header, border_style="cyan", box=SIMPLE_HEAD, padding=(0, 1)))

    # === 2x2 KPI grid ===
    k1 = kpi_card("Hardwork", f"{realizado_total // 60}h{realizado_total % 60:02d}", color="hardwork", footer=f"orçado {orcado_total // 60}h · {int(realizado_total / max(orcado_total, 1) * 100)}%", icon="💻", width=30)
    k2 = kpi_card("Pomodoros", f"{n_pomodoros}", color="hardwork", footer=f"média {n_pomodoros / max(1, n_days):.1f}/dia", icon="🍅", width=30)
    k3 = kpi_card("Sono Médio", f"{avg_sleep:.1f}h", color="sleep", footer=f"min {min_sleep:.1f}h · max {max_sleep:.1f}h", icon="😴", width=30)
    k4 = kpi_card("Reflexões", f"{len(reflections)}/{n_days}", color="ease", footer="dias com OKRs", icon="🎯", width=30)

    row1 = Table.grid(padding=(0, 1))
    row1.add_column()
    row1.add_column()
    row1.add_row(k1, k2)
    row2 = Table.grid(padding=(0, 1))
    row2.add_column()
    row2.add_column()
    row2.add_row(k3, k4)
    sections.append(row1)
    sections.append(row2)

    # === Sparklines (Tendências) ===
    sleep_by_day: list[float] = []
    prod_by_day: list[float] = []
    pom_by_day: list[int] = []
    for day_d, orcado, realizado, n_pom in daily_data:
        day_sleep = next((s.duration_hours for s in sleeps if s.date == day_d), 0)
        sleep_by_day.append(day_sleep)
        prod_by_day.append(productivity_pct(realizado, orcado))
        pom_by_day.append(n_pom)

    day_labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    label_text = "  " + "  ".join(day_labels[i % 7] for i in range(n_days))

    spark_table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
    spark_table.add_column("Métrica", style="bold", min_width=14, no_wrap=True)
    spark_table.add_column("Trend", style="white")
    spark_table.add_row("😴 Sono", sparkline(sleep_by_day, color="sleep", label=f"min {min_sleep:.0f}h / max {max_sleep:.0f}h"))
    spark_table.add_row("📈 Produtividade", sparkline(prod_by_day, color="hardwork", label=f"média {avg_x:.0f}%"))
    spark_table.add_row("🍅 Pomodoros", sparkline([min(p, 11) for p in pom_by_day], color="green3", label=f"total {n_pomodoros}"))
    sections.append(Panel(
        Group(spark_table, Text(" "), Text(label_text, style="dim")),
        title="[bold cyan]📈 Tendências 7-dias[/bold cyan]",
        border_style="cyan",
        box=SIMPLE_HEAD,
        padding=(0, 1),
    ))

    # === TipoDia distribution ===
    tipo_count: dict[str, int] = {t.value: 0 for t in TipoDia}
    from operational.cli.state import day_contexts
    for ctx in day_contexts.list():
        if ws <= ctx.date <= we:
            tipo_count[ctx.tipo_dia.value] = tipo_count.get(ctx.tipo_dia.value, 0) + 1
    # Fallback: infer for days without DayContext
    for day_d, _, _, _ in daily_data:
        wd = day_d.weekday()
        if wd < 5 and tipo_count.get("curso", 0) == 0:
            tipo_count["curso"] = tipo_count.get("curso", 0) + 1
        elif wd >= 5 and tipo_count.get("livre", 0) == 0:
            tipo_count["livre"] = tipo_count.get("livre", 0) + 1

    tipo_table = Table(show_header=True, header_style="bold magenta", box=SIMPLE, padding=(0, 1), expand=False)
    tipo_table.add_column("Tipo", style="bold", min_width=10, no_wrap=True)
    tipo_table.add_column("Dias", justify="right", min_width=6, no_wrap=True)
    tipo_table.add_column("Bar", min_width=24)
    for tipo, n in tipo_count.items():
        color = TIPO_DIA_COLOR.get(tipo, "white")
        bar_len = max(0, n) * 3
        tipo_table.add_row(
            f"[{color}]{tipo.upper()}[/{color}]",
            f"[{color}]{n}[/{color}]",
            f"[{color}]{'█' * bar_len}[/{color}]" if bar_len else "[grey50]—[/grey50]",
        )
    sections.append(Panel(tipo_table, title="[bold magenta]🗓️ Distribuição por TipoDia[/bold magenta]", border_style="magenta", box=SIMPLE_HEAD, padding=(0, 1)))

    # === Quadrant distribution ===
    q_count: dict[str, int] = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    for day_d, orcado, realizado, _ in daily_data:
        x = productivity_pct(realizado, orcado)
        y = x
        code, _, _ = classify_quadrant(x, y)
        q_count[code] = q_count.get(code, 0) + 1

    q_table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1), expand=False)
    q_table.add_column("Quadrante", style="bold", min_width=10, no_wrap=True)
    q_table.add_column("Dias", justify="right", min_width=6, no_wrap=True)
    q_table.add_column("Bar", min_width=24)
    for q, n in q_count.items():
        color = COLORS.get(q.lower(), "white")
        bar_len = max(0, n) * 3
        q_table.add_row(
            f"[{color}]{q}[/{color}]",
            f"[{color}]{n}[/{color}]",
            f"[{color}]{'█' * bar_len}[/{color}]" if bar_len else "[grey50]—[/grey50]",
        )
    sections.append(Panel(q_table, title="[bold cyan]📊 Distribuição por Quadrante[/bold cyan]", border_style="cyan", box=SIMPLE_HEAD, padding=(0, 1)))

    # === Daily positions ===
    daily_table = Table(show_header=True, header_style="bold green3", box=SIMPLE, padding=(0, 1), expand=False)
    daily_table.add_column("Data", style="bold white", min_width=12, no_wrap=True)
    daily_table.add_column("Tipo", min_width=10, no_wrap=True)
    daily_table.add_column("X", justify="right", min_width=5, no_wrap=True)
    daily_table.add_column("Y", justify="right", min_width=5, no_wrap=True)
    daily_table.add_column("Quadrante", justify="center", min_width=10, no_wrap=True)
    daily_table.add_column("🍅", justify="right", min_width=4, no_wrap=True)
    for day_d, orcado, realizado, n_pom in daily_data:
        x = productivity_pct(realizado, orcado)
        y = x
        code, _, _ = classify_quadrant(x, y)
        color = COLORS.get(code.lower(), "white")
        ctx = next((c for c in day_contexts.list() if c.date == day_d), None)
        tipo = ctx.tipo_dia.value if ctx else ("curso" if day_d.weekday() < 5 else "livre")
        tipo_color = TIPO_DIA_COLOR.get(tipo, "white")
        daily_table.add_row(
            day_d.isoformat(),
            f"[{tipo_color}]{tipo}[/{tipo_color}]",
            f"[{color}]{x:.0f}%[/{color}]",
            f"[{color}]{y:.0f}%[/{color}]",
            f"[bold {color}]{code}[/bold {color}]",
            str(n_pom),
        )
    sections.append(Panel(daily_table, title="[bold green3]🗓️ Posição Diária (X, Y, Quadrante)[/bold green3]", border_style="green3", box=SIMPLE_HEAD, padding=(0, 1)))

    # === Sleep breakdown ===
    sleep_rows: list[tuple[str, str, str | None]] = [
        ("Média", f"{avg_sleep:.1f}h", "ok" if avg_sleep >= 7 else "warn" if avg_sleep >= 5 else "crit"),
        ("Mínimo", f"{min_sleep:.1f}h", "crit" if min_sleep < 4 else "warn" if min_sleep < 6 else "ok"),
        ("Máximo", f"{max_sleep:.1f}h", "ok"),
        ("Dias < 6h", str(sum(1 for h in sleep_hours if h < 6)), "ok" if sum(1 for h in sleep_hours if h < 6) == 0 else "warn"),
        ("Dias 7-9h", str(sum(1 for h in sleep_hours if 7 <= h <= 9)), "ok"),
        ("Dias > 9h", str(sum(1 for h in sleep_hours if h > 9)), "ok"),
    ]
    sections.append(metric_table("😴 Distribuição do Sono (7 dias)", sleep_rows, title_color="sleep"))

    # === Next step ===
    if q_count.get("Q3", 0) > 0:
        sections.append(next_step(
            f"⚠️  {q_count['Q3']} dia(s) em Q3 (Crítico). Revisar padrão sono+trabalho urgente.",
            color="crit", icon="!",
        ))
    elif avg_x < 50:
        sections.append(next_step(
            f"Produtividade média {avg_x:.0f}% (abaixo de 50%). Aumentar volume de trabalho.",
            color="warn", icon="↑",
        ))
    else:
        sections.append(next_step(
            f"Semana dentro do padrão ({avg_x:.0f}% médio). Manter ritmo.",
            color="ok", icon="✓",
        ))

    return Group(*sections)


def generate_weekly_v3_markdown(
    *,
    ws: date,
    we: date,
    sleeps: list,
    blocks: list,
    n_pomodoros: int,
    reflections: list,
    daily_data: list,
) -> str:
    """Plain-text fallback for --json."""
    lines = [
        "---",
        "type: weekly_v3",
        f"week: {ws.isoformat()} to {we.isoformat()}",
        f"generated_at: {datetime.now().isoformat()}",
        "---",
        "",
        f"# 📈 Weekly V3 — {ws.isoformat()} to {we.isoformat()}",
        "",
    ]
    sleep_hours = [s.duration_hours for s in sleeps if s.duration_hours]
    if sleep_hours:
        avg = sum(sleep_hours) / len(sleep_hours)
        lines.append(f"**Sono médio:** {avg:.1f}h")
    lines.append(f"**Pomodoros:** {n_pomodoros}")
    lines.append(f"**Reflexões OKRs:** {len(reflections)}/{len(daily_data)}")
    return "\n".join(lines)
