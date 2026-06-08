"""Report generation CLI commands — thin orchestrators (MVC controller layer).

Per architecture rules:
- This file ONLY captures CLI args, calls ``core.services`` for data,
  and feeds the data into ``ui.*`` factories for rendering.
- NO business logic here.
- NO Rich construction here (no Table, Panel, Text building).
- NO string concatenation for visual layout.
"""
from __future__ import annotations

from datetime import date, timedelta

import typer

from operational.cli.console import console
from operational.cli.state import (
    daily_reflections,
    day_contexts,
    journals,
    pomodoros,
    sleep_records,
    time_blocks,
)
from operational.cli.formatters import format_as_json
from operational.core.budget import (
    classify_quadrant,
    productivity_pct,
)
from operational.core.services import (
    DaySnapshot,
    compute_day_quadrant,
    get_day_snapshot,
)
from operational.ui.daily_report import render_daily_report

app = typer.Typer(help="Generate reports (V3 — Cartesian, recovery, OKRs).")


# ---------------------------------------------------------------------------
# Daily
# ---------------------------------------------------------------------------


@app.command()
def daily(
    report_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Relatório diário V3 — Cartesian + recovery + OKRs."""
    d = date.fromisoformat(report_date) if report_date else date.today()

    # 1. Core: load data
    snap: DaySnapshot = get_day_snapshot(d)

    if json:
        # Plain dict for machine consumption
        q_code, x, y = compute_day_quadrant(snap)
        payload = {
            "date": d.isoformat(),
            "tipo_dia": snap.tipo_dia.value,
            "wake_hour": snap.wake_hour,
            "sleep_hour": snap.sleep_hour,
            "sleep_hours": snap.sleep.duration_hours,
            "sleep_quality": snap.sleep.quality,
            "energia": snap.energia,
            "foco": snap.foco,
            "hardwork_orcado_min": snap.hardwork_orcado_min,
            "hardwork_realizado_min": snap.hardwork_realizado_min,
            "n_blocks": snap.n_blocks,
            "n_pomodoros": snap.n_pomodoros,
            "pomodoros_meta": snap.pomodoros_meta,
            "n_transicoes_completas": snap.n_transicoes_completas,
            "n_transicoes_total": snap.n_transicoes_total,
            "workout_done": snap.workout_done,
            "meditacao_done": snap.meditacao_done,
            "lunch_eat_min": snap.lunch_eat_min,
            "lunch_rest_min": snap.lunch_rest_min,
            "lunch_pesado": snap.lunch_pesado,
            "desvios": snap.desvios,
            "licoes": snap.licoes,
            "ajustes": snap.ajustes,
            "big_win": snap.big_win,
            "parar_de_fazer": snap.parar_de_fazer,
            "repetir": snap.repetir,
            "deu_certo": snap.deu_certo,
            "deu_errado": snap.deu_errado,
            "maior_aprendizado": snap.maior_aprendizado,
            "quadrant": q_code,
            "x": x, "y": y,
        }
        typer.echo(format_as_json(payload))
        return

    # 2. UI: render
    report = render_daily_report(snap)
    console.print(report)


# ---------------------------------------------------------------------------
# Weekly (kept lighter — delegate to daily report for now)
# ---------------------------------------------------------------------------


@app.command()
def weekly(
    start: str | None = typer.Option(None, "--start", "-s", help="Início da semana (YYYY-MM-DD)"),
    end: str | None = typer.Option(None, "--end", "-e", help="Fim da semana (YYYY-MM-DD)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Relatório semanal V3 — distribuição por TipoDia + quadrante dominante."""
    from rich.console import Group
    from rich.table import Table
    from rich.text import Text

    from operational.cli.console import CONSOLE_WIDTH
    from operational.core.budget import budget_for_date
    from operational.enums import TipoDia
    from operational.ui.components import (
        COLORS,
        TIPO_DIA_COLOR,
        QUADRANT_COLOR,
        sparkline,
    )

    ws = date.fromisoformat(start) if start else date.today() - timedelta(days=6)
    we = date.fromisoformat(end) if end else date.today()

    # Core data
    sleeps = [s for s in sleep_records.list() if ws <= s.date <= we]
    daily_data: list[tuple[date, int, int, int]] = []
    n_pomodoros = 0
    pom_by_day: list[int] = []
    sleep_by_day: list[float] = []
    prod_by_day: list[float] = []
    for offset in range((we - ws).days + 1):
        d = ws + timedelta(days=offset)
        snap = get_day_snapshot(d)
        orcado = snap.hardwork_orcado_min
        realizado = snap.hardwork_realizado_min
        n_pomodoros += snap.n_pomodoros
        pom_by_day.append(snap.n_pomodoros)
        sleep_by_day.append(snap.sleep.duration_hours or 0)
        prod_by_day.append(productivity_pct(realizado, orcado))
        daily_data.append((d, orcado, realizado, snap.n_pomodoros))

    # JSON
    if json:
        payload = {
            "start": ws.isoformat(),
            "end": we.isoformat(),
            "n_days": (we - ws).days + 1,
            "n_pomodoros": n_pomodoros,
            "n_reflections": len([r for r in daily_reflections.list() if ws <= r.date <= we]),
        }
        typer.echo(format_as_json(payload))
        return

    # Aggregate stats
    sleep_hours = [s.duration_hours for s in sleeps if s.duration_hours]
    avg_sleep = sum(sleep_hours) / len(sleep_hours) if sleep_hours else 0
    min_sleep = min(sleep_hours) if sleep_hours else 0
    max_sleep = max(sleep_hours) if sleep_hours else 0
    orcado_total = sum(o for _, o, _, _ in daily_data)
    realizado_total = sum(r for _, _, r, _ in daily_data)
    avg_x = sum(productivity_pct(r, o) for _, o, r, _ in daily_data) / len(daily_data) if daily_data else 0

    parts: list = []
    # Header
    header = Table.grid(expand=False, padding=(0, 1))
    header.add_column(min_width=4, justify="left")
    header.add_column(justify="left")
    header.add_row(
        Text("  📈  ", style="bold cyan"),
        Text(f"WEEKLY REPORT  ·  {ws.isoformat()} → {we.isoformat()}  ·  {(we - ws).days + 1} dias", style="bold white"),
    )
    parts.append(_panel("⚡ WEEKLY", header, "primary"))

    # 2x2 KPI grid
    k1 = _kpi("Hardwork", f"{realizado_total // 60}h{realizado_total % 60:02d}", "hardwork",
             f"orçado {orcado_total // 60}h · {int(realizado_total / max(orcado_total, 1) * 100)}%", "💻")
    k2 = _kpi("Pomodoros", str(n_pomodoros), "hardwork",
             f"média {n_pomodoros / max(1, (we - ws).days + 1):.1f}/dia", "🍅")
    k3 = _kpi("Sono Médio", f"{avg_sleep:.1f}h", "sleep",
             f"min {min_sleep:.1f}h · max {max_sleep:.1f}h", "😴")
    k4 = _kpi("Reflexões",
             f"{len([r for r in daily_reflections.list() if ws <= r.date <= we])}/{(we - ws).days + 1}",
             "ease", "dias com OKRs", "🎯")
    kpi_grid = Table.grid(expand=False, padding=(0, 1))
    kpi_grid.add_column(justify="left")
    kpi_grid.add_column(justify="left")
    kpi_grid.add_row(k1, k2)
    kpi_grid.add_row(k3, k4)
    parts.append(kpi_grid)

    # Sparklines
    day_labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    label_text = "  " + "  ".join(day_labels[i % 7] for i in range(len(pom_by_day)))
    spark_table = Table.grid(expand=False, padding=(0, 1))
    spark_table.add_column(min_width=14, justify="left")
    spark_table.add_column(justify="left")
    spark_table.add_row(Text("😴 Sono", style="bold"), sparkline(sleep_by_day, color="sleep", label=f"min {min_sleep:.0f}h / max {max_sleep:.0f}h"))
    spark_table.add_row(Text("📈 Produtividade", style="bold"), sparkline(prod_by_day, color="hardwork", label=f"média {avg_x:.0f}%"))
    spark_table.add_row(Text("🍅 Pomodoros", style="bold"), sparkline([min(p, 11) for p in pom_by_day], color="hardwork", label=f"total {n_pomodoros}"))
    spark_block = Table.grid(expand=False, padding=(0, 0))
    spark_block.add_column(justify="left")
    spark_block.add_row(spark_table)
    spark_block.add_row(Text(label_text, style="grey58"))
    parts.append(_panel("📈 Tendências 7-dias", spark_block, "primary"))

    # TipoDia distribution
    tipo_count: dict[str, int] = {t.value: 0 for t in TipoDia}
    for ctx in day_contexts.list():
        if ws <= ctx.date <= we:
            tipo_count[ctx.tipo_dia.value] = tipo_count.get(ctx.tipo_dia.value, 0) + 1
    tipo_table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1), expand=False)
    tipo_table.add_column("Tipo", style="bold", min_width=10, no_wrap=True)
    tipo_table.add_column("Dias", justify="right", min_width=6, no_wrap=True)
    tipo_table.add_column("Bar", min_width=24)
    for tipo, n in tipo_count.items():
        clr = TIPO_DIA_COLOR.get(tipo, "white")
        bar_len = max(0, n) * 3
        tipo_table.add_row(
            Text(tipo.upper(), style=f"bold {clr}"),
            Text(str(n), style=clr),
            Text("█" * bar_len, style=clr) if bar_len else Text("—", style="grey58"),
        )
    parts.append(_panel("🗓️ Distribuição por TipoDia", tipo_table, "ease"))

    # Quadrant distribution
    q_count: dict[str, int] = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    for _, orcado, realizado, _ in daily_data:
        x = productivity_pct(realizado, orcado)
        y = x
        code, _, _ = classify_quadrant(x, y)
        q_count[code] = q_count.get(code, 0) + 1
    q_table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1), expand=False)
    q_table.add_column("Quadrante", style="bold", min_width=10, no_wrap=True)
    q_table.add_column("Dias", justify="right", min_width=6, no_wrap=True)
    q_table.add_column("Bar", min_width=24)
    for q, n in q_count.items():
        clr = QUADRANT_COLOR.get(q, "white")
        bar_len = max(0, n) * 3
        q_table.add_row(
            Text(q, style=f"bold {clr}"),
            Text(str(n), style=clr),
            Text("█" * bar_len, style=clr) if bar_len else Text("—", style="grey58"),
        )
    parts.append(_panel("📊 Distribuição por Quadrante", q_table, "primary"))

    # Daily positions
    daily_table = Table(show_header=True, header_style="bold green3", box=None, padding=(0, 1), expand=False)
    daily_table.add_column("Data", style="bold white", min_width=12, no_wrap=True)
    daily_table.add_column("Tipo", min_width=10, no_wrap=True)
    daily_table.add_column("X", justify="right", min_width=5, no_wrap=True)
    daily_table.add_column("Y", justify="right", min_width=5, no_wrap=True)
    daily_table.add_column("Quadrante", justify="center", min_width=10, no_wrap=True)
    daily_table.add_column("🍅", justify="right", min_width=4, no_wrap=True)
    for d, orcado, realizado, n_pom in daily_data:
        x = productivity_pct(realizado, orcado)
        y = x
        code, _, _ = classify_quadrant(x, y)
        clr = QUADRANT_COLOR.get(code, "white")
        ctx = next((c for c in day_contexts.list() if c.date == d), None)
        tipo = ctx.tipo_dia.value if ctx else ("curso" if d.weekday() < 5 else "livre")
        tipo_clr = TIPO_DIA_COLOR.get(tipo, "white")
        daily_table.add_row(
            Text(d.isoformat(), style="bold white"),
            Text(tipo, style=f"bold {tipo_clr}"),
            Text(f"{x:.0f}%", style=clr),
            Text(f"{y:.0f}%", style=clr),
            Text(code, style=f"bold {clr}"),
            Text(str(n_pom)),
        )
    parts.append(_panel("🗓️ Posição Diária (X, Y, Quadrante)", daily_table, "hardwork"))

    # Sleep breakdown
    sev_avg = "ok" if avg_sleep >= 7 else "warn" if avg_sleep >= 5 else "crit"
    sev_min = "ok" if min_sleep >= 7 else "warn" if min_sleep >= 4 else "crit"
    sleep_table = Table.grid(expand=False, padding=(0, 1))
    sleep_table.add_column(min_width=22, justify="left")
    sleep_table.add_column(min_width=10, justify="left")
    for label, val, sev in [
        ("Média", f"{avg_sleep:.1f}h", sev_avg),
        ("Mínimo", f"{min_sleep:.1f}h", sev_min),
        ("Máximo", f"{max_sleep:.1f}h", "ok"),
        ("Dias < 6h", str(sum(1 for h in sleep_hours if h < 6)), "ok" if sum(1 for h in sleep_hours if h < 6) == 0 else "warn"),
        ("Dias 7-9h", str(sum(1 for h in sleep_hours if 7 <= h <= 9)), "ok"),
        ("Dias > 9h", str(sum(1 for h in sleep_hours if h > 9)), "ok"),
    ]:
        from operational.ui.components import severity_text
        sleep_table.add_row(Text(label, style="bold white"), severity_text(val, sev))
    parts.append(_panel("😴 Distribuição do Sono (7 dias)", sleep_table, "sleep"))

    # Next step
    if q_count.get("Q3", 0) > 0:
        from operational.ui.components import next_step_panel
        parts.append(next_step_panel(
            f"⚠️  {q_count['Q3']} dia(s) em Q3 (Crítico). Revisar padrão sono+trabalho urgente.",
            severity="crit", icon="!",
        ))
    elif avg_x < 50:
        from operational.ui.components import next_step_panel
        parts.append(next_step_panel(
            f"Produtividade média {avg_x:.0f}% (abaixo de 50%). Aumentar volume de trabalho.",
            severity="warn", icon="↑",
        ))
    else:
        from operational.ui.components import next_step_panel
        parts.append(next_step_panel(
            f"Semana dentro do padrão ({avg_x:.0f}% médio). Manter ritmo.",
            severity="ok", icon="✓",
        ))

    console.print(Group(*parts))


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _kpi(title: str, value: str, color: str, footer: str, icon: str) -> "object":
    from operational.ui.components import kpi_card
    return kpi_card(title, value, color=color, footer=footer, icon=icon, width=30)


def _panel(title: str, body, color: str):
    from operational.ui.components import section_panel
    return section_panel(title, body, color=color)
