"""State dashboard CLI command — view current day snapshot.

Layout (2x2 KPI grid + activity section + next step):
- Top: 2x2 grid of KPI cards (Sono, Pomodoros, Hardwork, Energia)
- Middle: Pomodoros grid + Activity table
- Bottom: Next-step recommendation

Opt-in flags for v2 A/B testing:
- ``--v2``: render the dashboard chrome with v2 components.
- ``--mock <profile>``: synthesize the day's metrics from a mock profile
  (does not affect repos, only the rendered snapshot).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Optional

import typer
from rich.box import SIMPLE_HEAD
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from operational.cli.console import console as pav_console
from operational.cli.formatters import format_as_json
from operational.cli.renderers import (
    COLORS,
    make_console,
    kpi_card,
    metric_table,
    next_step,
    pomodoros_grid,
    progress_bar,
    timeline_h,
)
from operational.cli.state import (
    ajustes_finos,
    journals,
    pomodoros,
    routine_logs,
    sleep_records,
    time_blocks,
)
from operational.constants import DEFAULT as PAV
from operational.enums import Period
from operational.ui.components_v2 import error_panel_v2

app = typer.Typer(help="Dashboard do dia corrente (onde estou, o que está logado).")
console = make_console(width=120)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _period_now(dt: datetime) -> Period:
    h = dt.hour
    if PAV.HORARIO_ACORDAR_MIN <= h <= PAV.HORARIO_ACORDAR_MAX:
        return Period.MANHA
    if 6 <= h < PAV.HORARIO_DORMIR_MIN:
        return Period.TARDE
    return Period.NOITE


def _minutes_between(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def _budget_for_period(period: Period) -> int:
    if period is Period.MANHA:
        return 180
    if period is Period.TARDE:
        return 240
    return 0


@app.command(name="show")
def show(
    target_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
    v2: bool = typer.Option(False, "--v2", help="Use PAV-OS v2 design system (BETA)"),
    mock: Optional[str] = typer.Option(None, "--mock", help="Use mock profile (q1, q2, q3, q4, empty, burnout, peak)"),
) -> None:
    """Dashboard do dia — onde estou, o que está logado, estou no plano?"""
    # --- Mock profile resolution ---
    profile = None
    if mock:
        from operational.ui.mock_profiles import get_profile, list_profiles
        try:
            profile = get_profile(mock)
        except ValueError:
            pav_console.print(error_panel_v2(
                f"Perfil mock desconhecido: {mock!r}",
                context=f"pav state show --mock {mock}",
                expected=f"One of: {', '.join(list_profiles())}",
                suggestion="pav state show --mock q1",
            ))
            raise typer.Exit(code=1)

    d = date.fromisoformat(target_date) if target_date else date.today()
    now = _now()
    period_now = _period_now(now)

    # Pull today's entities
    sleep = next((s for s in sleep_records.list() if s.date == d), None)
    blocks = [b for b in time_blocks.list() if b.start.date() == d]
    day_pomodoros = [p for p in pomodoros.list() if p.started_at.date() == d]
    day_logs = [l for l in routine_logs.list() if l.date == d]
    day_ajustes = [a for a in ajustes_finos.list() if a.date == d]
    day_journal = next((j for j in journals.list() if j.date == d), None)

    total_block_min = sum(_minutes_between(b.start, b.end) for b in blocks)
    completed_pomodoros = sum(
        1 for p in day_pomodoros if getattr(p, "state", None) and "COMPLETE" in str(p.state)
    )
    budget_min = _budget_for_period(period_now)
    actual_min = total_block_min

    # --- Apply mock override (only when --v2) ---
    if profile is not None:
        from operational.ui.mock_snapshot import build_mock_snapshot
        mock_snap = build_mock_snapshot(profile)
        # Build a DaySnapshot for the v2 renderer from the mock
        from operational.core.services import get_day_snapshot
        # For state_cmd v2 path, prefer the mock_snap directly
        # (it has all the right data already)
        sleep = SimpleNamespace(
            bedtime=mock_snap.sleep.bedtime,
            wake_time=mock_snap.sleep.wake_time,
            quality_score=mock_snap.sleep.quality,
            duration_hours=mock_snap.sleep.duration_hours,
        )
        completed_pomodoros = mock_snap.n_pomodoros
        actual_min = mock_snap.hardwork_realizado_min
        budget_min = mock_snap.hardwork_orcado_min
        day_journal = SimpleNamespace(
            energia_nivel=mock_snap.energia,
            foco_nivel=mock_snap.foco,
        )
        # When mocking, force period to MANHA so the v2 footer suggests action
        if period_now == Period.NOITE and mock:
            period_now = Period.MANHA

    if json:
        payload = {
            "date": d.isoformat(),
            "period_now": period_now.value,
            "sleep": {
                "bedtime": sleep.bedtime.isoformat() if sleep else None,
                "wake_time": sleep.wake_time.isoformat() if sleep else None,
                "quality": sleep.quality_score if sleep else None,
                "duration_hours": sleep.duration_hours if sleep else None,
            } if sleep else None,
            "blocks_today": len(blocks),
            "total_block_minutes": total_block_min,
            "pomodoros_completed": completed_pomodoros,
            "routine_logs": len(day_logs),
            "ajustes_finos": len(day_ajustes),
            "has_journal": day_journal is not None,
            "budget_minutes": budget_min,
            "actual_minutes": actual_min,
            "design_system": "v2" if v2 else "v1",
            "mock": mock,
        }
        typer.echo(format_as_json(payload))
        return

    # --- v2 rendering path ---
    if v2:
        from operational.ui.v2_renderers import render_state_v2
        # Build or get the DaySnapshot for the v2 renderer
        if profile is not None:
            # mock_snap already built above
            from operational.ui.mock_snapshot import build_mock_snapshot
            state_snap = build_mock_snapshot(profile)
        else:
            from operational.core.services import get_day_snapshot
            state_snap = get_day_snapshot(d)
        render_state_v2(
            snap=state_snap,
            target_date=d,
            period_label=period_now.value,
        )
        return

    _render_dashboard(
        d=d,
        period_now=period_now,
        sleep=sleep,
        blocks=blocks,
        n_pomodoros=completed_pomodoros,
        n_logs=len(day_logs),
        n_ajustes=len(day_ajustes),
        has_journal=day_journal is not None,
        budget_min=budget_min,
        actual_min=total_block_min,
        day_journal=day_journal,
    )


def _render_dashboard(
    *,
    d: date,
    period_now: Period,
    sleep,
    blocks,
    n_pomodoros: int,
    n_logs: int,
    n_ajustes: int,
    has_journal: bool,
    budget_min: int,
    actual_min: int,
    day_journal,
) -> None:
    """Render dashboard: 2x2 KPI grid + pomodoros + activity + next step."""
    # === Header ===
    period_color = {
        Period.MANHA: "yellow1",
        Period.TARDE: "deep_sky_blue1",
        Period.NOITE: "medium_purple",
    }.get(period_now, "white")
    period_emoji = {Period.MANHA: "🌅", Period.TARDE: "💻", Period.NOITE: "🌙"}[period_now]

    header = Text()
    header.append("  ⚡  ", style="bold cyan")
    header.append(f"STATE  ·  {d.isoformat()}", style="bold white")
    header.append("  ·  ", style="dim")
    header.append(f"{period_emoji} {period_now.value}", style=f"bold {period_color}")
    console.print()
    console.print(Panel(header, border_style="cyan", box=SIMPLE_HEAD, padding=(0, 1)))

    # === 2x2 KPI grid ===
    # Card 1: Sleep
    if sleep:
        sleep_card = kpi_card(
            "Sono", f"{sleep.duration_hours:.1f}h",
            color="sleep",
            footer=f"Q={sleep.quality_score}/10  ·  {sleep.bedtime.isoformat()[:5]}→{sleep.wake_time.isoformat()[:5]}",
            icon="😴",
            width=30,
        )
    else:
        sleep_card = kpi_card("Sono", "—", color="crit", footer="não registrado", icon="😴", width=30)

    # Card 2: Pomodoros
    pom_card = kpi_card("Pomodoros", str(n_pomodoros), color="hardwork", footer="completos hoje", icon="🍅", width=30)

    # Card 3: Hardwork (orçado vs real)
    if budget_min > 0:
        pct = int(actual_min / max(budget_min, 1) * 100)
        hw_color = "hardwork" if actual_min >= budget_min else "warn"
        hw_footer = f"{actual_min}/{budget_min}min · {pct}% atingido"
    else:
        hw_color = "ease"
        hw_footer = "noite — sem hardwork"
    hw_card = kpi_card("Hardwork", f"{actual_min // 60}h{actual_min % 60:02d}", color=hw_color, footer=hw_footer, icon="💻", width=30)

    # Card 4: Energia/Foco
    energia = day_journal.energia_nivel if day_journal and day_journal.energia_nivel else 0
    foco = day_journal.foco_nivel if day_journal and day_journal.foco_nivel else 0
    if energia and foco:
        avg = (energia + foco) // 2
        ef_color = "energy" if avg >= 7 else "warn" if avg >= 5 else "crit"
        ef_footer = f"média {avg}/10  ·  E{energia} F{foco}"
    else:
        ef_color = "muted"
        ef_footer = "não registrado"
    ef_card = kpi_card("Energia/Foco", f"{energia or '—'}/{foco or '—'}", color=ef_color, footer=ef_footer, icon="⚡", width=30)

    # 2x2 grid: row 1 = (Sono, Pomodoros), row 2 = (Hardwork, Energia/Foco)
    row1 = Table.grid(padding=(0, 1))
    row1.add_column()
    row1.add_column()
    row1.add_row(sleep_card, pom_card)

    row2 = Table.grid(padding=(0, 1))
    row2.add_column()
    row2.add_column()
    row2.add_row(hw_card, ef_card)

    console.print(row1)
    console.print(row2)

    # === Pomodoros grid (3 sessions) ===
    s1 = min(4, n_pomodoros) if period_now == Period.MANHA else 0
    if n_pomodoros > 4:
        s2 = 4
        s1 = min(4, n_pomodoros - 4)
    else:
        s2 = n_pomodoros if period_now in (Period.TARDE, Period.NOITE) else 0
    s3 = max(0, min(4, n_pomodoros - 8))

    pom_grid = pomodoros_grid(s1, s2, s3)
    console.print()
    console.print(Panel(
        pom_grid,
        title="[bold green3]🍅 Pomodoros (S1 manhã · S2 tarde · S3 noite)[/bold green3]",
        border_style="green3",
        box=SIMPLE_HEAD,
        padding=(0, 1),
    ))

    # === Time blocks timeline (if any) ===
    if blocks:
        period_order = {Period.MANHA: 0, Period.TARDE: 1, Period.NOITE: 2}
        blocks_sorted = sorted(blocks, key=lambda b: (period_order.get(b.period, 9), b.start))
        timeline_data = [(b.start.hour, b.end.hour, b.label or b.period.value) for b in blocks_sorted]
        tl_text = timeline_h(timeline_data, width=58, color="hardwork")
        console.print(Panel(
            tl_text,
            title=f"[bold green3]📦 Time Blocks ({len(blocks)} blocos, {actual_min}min)[/bold green3]",
            border_style="green3",
            box=SIMPLE_HEAD,
            padding=(0, 1),
        ))

    # === Activity table ===
    rows = [
        ("🕐 Rotinas logs", str(n_logs), "ok" if n_logs >= 5 else "warn"),
        ("🔧 Ajustes finos", str(n_ajustes), "ok" if n_ajustes <= 3 else "warn"),
        ("📓 Journal", "✓" if has_journal else "pendente", "ok" if has_journal else "warn"),
        ("📦 Blocos", f"{len(blocks)}", "ok" if blocks else "muted"),
    ]
    console.print()
    console.print(metric_table("Atividade do Dia", rows, title_color="primary"))

    # === Next step ===
    console.print()
    prompts = {
        Period.MANHA: "Iniciar Manhã → opção 1 do menu (sleep retroativo + ENTRY + workout)",
        Period.TARDE: "Iniciar Tarde → opção 2 (lunch + pomodoros + CORE)",
        Period.NOITE: "Encerrar Dia → opção 3 (jantar + shutdown + reflexão OKRs)",
    }
    if not has_journal and period_now == Period.NOITE:
        console.print(next_step(
            "Journal de hoje não foi feito. Use reflect saida para registrar OKRs de saída.",
            color="warn", icon="!",
        ))
    elif n_pomodoros == 0 and period_now in (Period.MANHA, Period.TARDE):
        console.print(next_step(
            f"Nenhum pomodoro registrado em {period_now.value}. Use metric energy -e 7 -f 8 para check-in.",
            color="warn", icon="!",
        ))
    else:
        console.print(next_step(prompts[period_now], color="ok", icon="→"))
    console.print()
