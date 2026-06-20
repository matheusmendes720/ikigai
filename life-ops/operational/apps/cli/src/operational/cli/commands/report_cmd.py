"""Report generation CLI commands — thin orchestrators (MVC controller layer).

Per architecture rules:
- This file ONLY captures CLI args, calls ``core.services`` for data,
  and feeds the data into ``ui.*`` factories for rendering.
- NO business logic here.
- NO Rich construction here (no Table, Panel, Text building).
- NO string concatenation for visual layout.

The PAV-OS v2 design system is the **only** renderer for ``daily``
and ``weekly``. ``--mock`` and ``--watch`` are preserved.
"""
from __future__ import annotations

import time as time_module
from datetime import date, timedelta
from typing import Optional

import typer
from rich.console import Group
from rich.live import Live

from operational.cli.console import console
from operational.cli.formatters import format_as_json
from operational.cli.state import (
    daily_reflections,
    day_contexts,
    journals,
    pomodoros,
    sleep_records,
    time_blocks,
)
from operational.core.budget import productivity_pct
from operational.cli.services import (
    DaySnapshot,
    compute_day_quadrant,
    get_day_snapshot,
)
from operational.enums import TipoDia
from operational.ui.components_v2 import (
    error_panel_v2,
    kpi_grid_2x2,
    kpi_v2,
    metric_v2,
    next_step_v2,
    page,
    section_v2,
    sparkline_v2,
)
from operational.ui.tokens import QUADRANT, SEVERITY

app = typer.Typer(help="Generate reports (PAV-OS v2 design system — definitive edition).")


# ---------------------------------------------------------------------------
# Daily
# ---------------------------------------------------------------------------


@app.command()
def daily(
    report_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
    mock: Optional[str] = typer.Option(None, "--mock", help="Use mock profile (q1, q2, q3, q4, empty, burnout, peak)"),
    watch: int = typer.Option(0, "--watch", help="Auto-refresh every N seconds"),
) -> None:
    """Relatório diário — PAV-OS v2 design system.

    Flags:
    - ``--mock <profile>``: synthesize a DaySnapshot from a mock profile.
    - ``--watch N``: auto-refresh every N seconds (v2 Live loop).
    - ``--json``: machine-readable JSON output.
    """
    try:
        d = date.fromisoformat(report_date) if report_date else date.today()
    except ValueError:
        console.print(error_panel_v2(
            f"Data invalida: {report_date}",
            context=f"pav report daily --date {report_date}",
            expected="YYYY-MM-DD (ano-mes-dia, mes 01-12, dia 01-31)",
            suggestion="pav report daily --date 2026-06-08",
        ))
        raise typer.Exit(code=1)

    profile = None
    if mock:
        from operational.ui.mock_profiles import get_profile, list_profiles
        try:
            profile = get_profile(mock)
        except ValueError:
            console.print(error_panel_v2(
                f"Perfil mock desconhecido: {mock!r}",
                context=f"pav report daily --mock {mock}",
                expected=f"One of: {', '.join(list_profiles())}",
                suggestion="pav report daily --mock q1",
            ))
            raise typer.Exit(code=1)

    if profile is not None:
        from operational.ui.mock_snapshot import build_mock_snapshot
        snap: DaySnapshot = build_mock_snapshot(profile)
    else:
        snap = get_day_snapshot(d)

    if json:
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
            "design_system": "v2",
            "mock": mock,
        }
        typer.echo(format_as_json(payload))
        return

    from operational.ui.v2_renderers import render_daily_v2

    if watch > 0:
        from io import StringIO

        from operational.cli.console import console as _console

        def _build() -> str:
            if profile is not None:
                current_snap = build_mock_snapshot(profile)
            else:
                current_snap = get_day_snapshot(d)
            buf = StringIO()
            save_file = _console.file
            _console.file = buf
            try:
                render_daily_v2(current_snap, d)
            finally:
                _console.file = save_file
            return buf.getvalue()

        with Live(_build(), refresh_per_second=1, transient=False) as live:
            try:
                while True:
                    time_module.sleep(watch)
                    live.update(_build())
            except (KeyboardInterrupt, SystemExit):
                pass
        return

    render_daily_v2(snap, d)


# ---------------------------------------------------------------------------
# Weekly
# ---------------------------------------------------------------------------


def _quadrant_for_pct(x: float) -> str:
    if x >= 80:
        return "Q1"
    if x >= 50:
        return "Q2"
    if x >= 20:
        return "Q4"
    return "Q3"


def _build_weekly_v2(ws: date, we: date, profile):
    """Build the v2 weekly report body and footer."""
    daily_data: list[tuple[date, int, int, int]] = []
    n_pomodoros = 0
    for offset in range((we - ws).days + 1):
        d = ws + timedelta(days=offset)
        if profile is not None and d == we:
            from operational.ui.mock_snapshot import build_mock_snapshot
            snap = build_mock_snapshot(profile)
        else:
            snap = get_day_snapshot(d)
        n_pomodoros += snap.n_pomodoros
        daily_data.append(
            (d, snap.hardwork_orcado_min, snap.hardwork_realizado_min, snap.n_pomodoros)
        )

    sleeps = [s for s in sleep_records.list() if ws <= s.date <= we]
    sleep_hours = [s.duration_hours for s in sleeps if s.duration_hours]
    avg_sleep = sum(sleep_hours) / len(sleep_hours) if sleep_hours else 0.0
    min_sleep = min(sleep_hours) if sleep_hours else 0.0
    max_sleep = max(sleep_hours) if sleep_hours else 0.0
    orcado_total = sum(o for _, o, _, _ in daily_data)
    realizado_total = sum(r for _, _, r, _ in daily_data)
    n_days = (we - ws).days + 1
    avg_x = (
        sum(productivity_pct(r, o) for _, o, r, _ in daily_data) / max(1, len(daily_data))
    )

    k1 = kpi_v2(
        "Hardwork",
        f"{realizado_total // 60}h{realizado_total % 60:02d}",
        "ok" if realizado_total >= orcado_total * 0.8 else "warning",
        delta=f"orcado {orcado_total // 60}h · {int(realizado_total / max(orcado_total, 1) * 100)}%",
        icon="💻",
    )
    k2 = kpi_v2(
        "Pomodoros",
        str(n_pomodoros),
        "ok" if n_pomodoros >= 12 else "warning",
        delta=f"média {n_pomodoros / max(1, n_days):.1f}/dia",
        icon="🍅",
    )
    k3 = kpi_v2(
        "Sono Médio",
        f"{avg_sleep:.1f}h",
        "ok" if avg_sleep >= 7 else "warning" if avg_sleep >= 5 else "danger",
        delta=f"min {min_sleep:.1f}h · max {max_sleep:.1f}h",
        icon="😴",
    )
    k4 = kpi_v2(
        "Reflexões",
        f"{len([r for r in daily_reflections.list() if ws <= r.date <= we])}/{n_days}",
        "ok",
        delta="dias com OKRs",
        icon="🎯",
    )

    pom_by_day: list[float] = []
    sleep_by_day: list[float] = []
    prod_by_day: list[float] = []
    for d, orcado, realizado, n_pom in daily_data:
        sleep_by_day.append(
            next((s.duration_hours for s in sleeps if s.date == d), 0) or 0
        )
        prod_by_day.append(productivity_pct(realizado, orcado))
        pom_by_day.append(float(min(n_pom, 11)))

    spark_block = Group(
        sparkline_v2(sleep_by_day, "Sono"),
        sparkline_v2(prod_by_day, "Produtividade"),
        sparkline_v2(pom_by_day, "Pomodoros"),
    )

    tipo_count: dict[str, int] = {t.value: 0 for t in TipoDia}
    for ctx in day_contexts.list():
        if ws <= ctx.date <= we:
            tipo_count[ctx.tipo_dia.value] = tipo_count.get(ctx.tipo_dia.value, 0) + 1

    tipo_rows: list[tuple[str, str, str | None]] = [
        (tipo.upper(), str(n), "ok" if n > 0 else "muted")
        for tipo, n in tipo_count.items()
    ]

    q_count: dict[str, int] = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    for _, orcado, realizado, _ in daily_data:
        q_count[_quadrant_for_pct(productivity_pct(realizado, orcado))] += 1

    quad_rows: list[tuple[str, str, str | None]] = [
        (q, str(n), "ok" if q == "Q1" else "warning" if q in ("Q2", "Q4") else "danger")
        for q, n in q_count.items()
    ]

    daily_rows: list[tuple[str, str, str | None]] = []
    for d, orcado, realizado, n_pom in daily_data:
        code = _quadrant_for_pct(productivity_pct(realizado, orcado))
        ctx = next((c for c in day_contexts.list() if c.date == d), None)
        tipo = ctx.tipo_dia.value if ctx else ("curso" if d.weekday() < 5 else "livre")
        sev = "ok" if code == "Q1" else "warning" if code in ("Q2", "Q4") else "danger"
        daily_rows.append((d.isoformat(), f"{tipo} · {code} · 🍅{n_pom}", sev))

    body = Group(
        kpi_grid_2x2([k1, k2, k3, k4]),
        "",
        section_v2("TENDENCIAS", icon="📈", subtitle="7 dias", content=spark_block, severity="primary"),
        "",
        section_v2(
            "DISTRIBUICAO POR TIPO DE DIA",
            icon="🗓️",
            content=metric_v2(tipo_rows, headers=["Tipo", "Dias"]),
            severity="primary",
        ),
        "",
        section_v2(
            "DISTRIBUICAO POR QUADRANTE",
            icon="📊",
            content=metric_v2(quad_rows, headers=["Quadrante", "Dias"]),
            severity="primary",
        ),
        "",
        section_v2(
            "POSICAO DIARIA",
            icon="📅",
            content=metric_v2(daily_rows, headers=["Data", "Tipo · Q · 🍅"]),
            severity="primary",
        ),
    )

    if q_count.get("Q3", 0) > 0:
        footer = next_step_v2(
            f"{q_count['Q3']} dia(s) em Q3 (Crítico). Revisar padrão sono+trabalho urgente.",
            "Revisão urgente do sistema",
            severity="danger",
        )
    elif avg_x < 50:
        footer = next_step_v2(
            f"Produtividade média {avg_x:.0f}% (abaixo de 50%). Aumentar volume de trabalho.",
            "Aumentar carga gradualmente",
            severity="warning",
        )
    else:
        footer = next_step_v2(
            f"Semana dentro do padrão ({avg_x:.0f}% médio). Manter ritmo.",
            "Manter ritmo",
            severity="success",
        )

    return body, footer


@app.command()
def weekly(
    start: str | None = typer.Option(None, "--start", "-s", help="Início da semana (YYYY-MM-DD)"),
    end: str | None = typer.Option(None, "--end", "-e", help="Fim da semana (YYYY-MM-DD)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
    mock: Optional[str] = typer.Option(None, "--mock", help="[daily only] Reuse a mock profile for the latest day in the range"),
) -> None:
    """Relatório semanal — PAV-OS v2 design system.

    Flags:
    - ``--mock <profile>``: feed a mock profile's snapshot into the latest day
      in the range.
    """
    profile = None
    if mock:
        from operational.ui.mock_profiles import get_profile, list_profiles
        try:
            profile = get_profile(mock)
        except ValueError:
            console.print(error_panel_v2(
                f"Perfil mock desconhecido: {mock!r}",
                context=f"pav report weekly --mock {mock}",
                expected=f"One of: {', '.join(list_profiles())}",
                suggestion="pav report weekly --mock q1",
            ))
            raise typer.Exit(code=1)

    ws = date.fromisoformat(start) if start else date.today() - timedelta(days=6)
    we = date.fromisoformat(end) if end else date.today()

    if json:
        n_pomodoros = 0
        for offset in range((we - ws).days + 1):
            d = ws + timedelta(days=offset)
            if profile is not None and d == we:
                from operational.ui.mock_snapshot import build_mock_snapshot
                snap = build_mock_snapshot(profile)
            else:
                snap = get_day_snapshot(d)
            n_pomodoros += snap.n_pomodoros
        payload = {
            "start": ws.isoformat(),
            "end": we.isoformat(),
            "n_days": (we - ws).days + 1,
            "n_pomodoros": n_pomodoros,
            "n_reflections": len([r for r in daily_reflections.list() if ws <= r.date <= we]),
            "design_system": "v2",
            "mock": mock,
        }
        typer.echo(format_as_json(payload))
        return

    body, footer = _build_weekly_v2(ws, we, profile)
    full_page = page(
        "Weekly Report",
        f"{ws.isoformat()} → {we.isoformat()}",
        body,
        footer=footer,
    )
    console.print(full_page)
