"""V2 daily/state renderer — shared between ``report daily`` and
``state show``.

Production-grade: takes a DaySnapshot and renders it with the v2
design system (big_panel, two_column_grid, timeline_log, kpi_grid_4x1).
"""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date

from rich.console import Group
from rich.padding import Padding

from operational.cli.console import console
from operational.cli.state import (
    journals, pomodoros, routine_logs, sleep_records, time_blocks,
)
from operational.cli.services import DaySnapshot, compute_day_quadrant
from operational.ui.components_v2 import (
    big_panel,
    cartesian_v2,
    kpi_grid_2x2,
    kpi_v2,
    next_step_v2,
    page,
    pomodoros_v2,
    progress_bar_v2,
    section_v2,
    timeline_log,
    two_column_grid,
)
from operational.ui.tokens import CONSOLE_WIDTH_V2, QUADRANT, SEVERITY, STYLES


def _build_telemetry_panel(snap: DaySnapshot) -> object:
    """Build the TELEMETRIA DIÁRIA panel (energia, foco, sono)."""
    from rich.panel import Panel
    from rich.table import Table

    sleep_dur = snap.sleep.duration_hours or 0.0
    sleep_color = "success" if sleep_dur >= 7 else "warning" if sleep_dur >= 5 else "danger"
    energy_color = "success" if (snap.energia or 0) >= 7 else "warning"
    focus_color = "success" if (snap.foco or 0) >= 7 else "warning"

    t = Table.grid(expand=False, padding=(0, 1))
    t.add_column(min_width=2)
    t.add_column(min_width=18, justify="left")
    t.add_column(min_width=10, justify="right")
    t.add_column(min_width=10, justify="right")
    t.add_row(
        "  ",
        f"⚡ Energia Média",
        f"[{SEVERITY[energy_color]}]{snap.energia or 0}/10[/]",
        f"[{SEVERITY[sleep_color]}]range 1-10[/]",
    )
    t.add_row(
        "  ",
        f"🎯 Foco Médio",
        f"[{SEVERITY[focus_color]}]{snap.foco or 0}/10[/]",
        f"[{SEVERITY[sleep_color]}]range 1-10[/]",
    )
    debito = max(0, 7.5 - sleep_dur)
    t.add_row(
        "  ",
        f"😴 Débito de Sono",
        f"{debito:.1f}h",
        f"({sleep_dur:.1f}h hoje)",
    )
    return Panel(
        t,
        title=f"[{SEVERITY['info']}] 📈 TELEMETRIA DIÁRIA [/]",
        border_style=SEVERITY["info"],
        padding=(0, 1),
        width=58,
    )


def _build_pomodoros_panel(snap: DaySnapshot) -> object:
    """Build the POMODOROS panel with progress bar + sequence count."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    n_pom = snap.n_pomodoros
    meta = max(1, snap.pomodoros_meta or 12)
    completed_today = sum(
        1 for p in pomodoros.list()
        if p.started_at.date() == snap.date
        and getattr(p, "state", None)
        and "COMPLETE" in str(p.state)
    )
    t = Table.grid(expand=False, padding=(0, 0))
    t.add_column(min_width=4)
    t.add_column(min_width=36)
    t.add_column(min_width=8, justify="right")
    t.add_row("  ", progress_bar_v2(n_pom, meta, "", "primary", 30, show_value=True), "")

    last_ts = "—"
    for p in sorted(pomodoros.list(), key=lambda p: p.started_at, reverse=True):
        if p.started_at.date() == snap.date:
            last_ts = p.started_at.strftime("%H:%M")
            break
    seq = completed_today if completed_today <= 5 else 3

    last_line = Text()
    last_line.append(f"  Último: {last_ts}", style=STYLES["body_muted"])
    last_line.append("  ·  ", style=SEVERITY["muted"])
    last_line.append(f"Sequência Atual: {seq} ciclos", style=STYLES["body_muted"])

    body = Group(t, last_line)
    return Panel(
        body,
        title=f"[{SEVERITY['warning']}] 🍅 POMODOROS (Meta: {meta}) [/]",
        border_style=SEVERITY["warning"],
        padding=(0, 1),
        width=58,
    )


def _build_status_panel(snap: DaySnapshot, period_label: str = "") -> object:
    """Build the STATUS ATUAL panel (shift + active block + progress)."""
    from rich.panel import Panel
    from rich.text import Text

    period = period_label or "TARDE"
    active_block = next(
        (b for b in time_blocks.list() if b.start.date() == snap.date),
        None,
    )
    if active_block:
        block_label = f"{active_block.label}"
        block_range = f"{active_block.start.strftime('%H:%M')} → {active_block.end.strftime('%H:%M')}"
        pct_done = min(100, int((snap.hardwork_realizado_min / max(1, snap.hardwork_orcado_min)) * 100))
    else:
        block_label = "(nenhum bloco ativo)"
        block_range = "—"
        pct_done = 0

    body_lines: list = []
    line1 = Text()
    line1.append("  Turno: ", style=STYLES["body_muted"])
    line1.append(period, style="bold cyan")
    line1.append("        Bloco Ativo: ", style=STYLES["body_muted"])
    line1.append(f"{block_label} ", style="bold white")
    line1.append(f"({block_range})", style=SEVERITY["muted"])
    body_lines.append(line1)
    body_lines.append(Text(""))
    body_lines.append(progress_bar_v2(pct_done, 100, "", "primary", 60, show_value=True))
    body_lines.append(Text(""))

    return Panel(
        Group(*body_lines),
        title=f"[{SEVERITY['primary']}] 📍 STATUS ATUAL [/]",
        border_style=SEVERITY["primary"],
        padding=(0, 1),
        width=CONSOLE_WIDTH_V2 - 4,
    )


def _build_timeline_panel(snap: DaySnapshot) -> object:
    """Build the TIMELINE & LOGS RECENTES panel."""
    from rich.panel import Panel

    entries: list[tuple[str, str, str]] = []

    # routine_logs
    for log in sorted(
        [l for l in routine_logs.list() if l.date == snap.date],
        key=lambda l: l.started_at,
        reverse=True,
    )[:5]:
        ts = log.started_at.strftime("%H:%M") if hasattr(log, "started_at") else "—"
        entries.append((ts, "ROUTINE", f"Start: {log.routine_name} ({log.routine_type or 'CORE'})"))

    # time_blocks
    for blk in sorted(
        [b for b in time_blocks.list() if b.start.date() == snap.date],
        key=lambda b: b.start,
        reverse=True,
    )[:5]:
        ts = blk.start.strftime("%H:%M")
        entries.append((ts, "BLOCK", f"End: {blk.label}"))

    # check-ins
    for chk in sorted(
        [b for b in time_blocks.list() if b.start.date() == snap.date and "check" in b.label.lower()],
        key=lambda b: b.start,
        reverse=True,
    )[:3]:
        ts = chk.start.strftime("%H:%M")
        e = getattr(chk, "energia_nivel", "?")
        f = getattr(chk, "foco_nivel", "?")
        entries.append((ts, "CHECK-IN", f"Energia: {e}, Foco: {f} ({chk.id})"))

    # system: sleep
    sleep = next((s for s in sleep_records.list() if s.date == snap.date), None)
    if sleep:
        quality = sleep.quality_score or 0
        quality_emoji = "🟢" if quality >= 7 else "🟡" if quality >= 5 else "🔴"
        quality_label = "Bom" if quality >= 7 else "Regular" if quality >= 5 else "Crítico"
        entries.append((
            "04:00",
            "SYSTEM",
            f"Sleep logged: {sleep.duration_hours:.1f}h ({quality_emoji} {quality_label})",
        ))

    return Panel(
        timeline_log(entries, max_entries=8),
        title=f"[{SEVERITY['info']}] 📋 TIMELINE & LOGS RECENTES [/]",
        border_style=SEVERITY["info"],
        padding=(0, 1),
        width=CONSOLE_WIDTH_V2 - 4,
    )


def render_state_v2(snap: DaySnapshot, target_date: date, period_label: str = "") -> None:
    """Render the v2 state dashboard from a DaySnapshot — production-grade."""
    try:
        q_code, x, y = compute_day_quadrant(snap)
    except Exception:
        q_code, x, y = "Q1", 0.0, 0.0

    body = Group(
        _build_status_panel(snap, period_label),
        Padding("", (1, 0)),
        two_column_grid(
            _build_telemetry_panel(snap),
            _build_pomodoros_panel(snap),
        ),
        Padding("", (1, 0)),
        _build_timeline_panel(snap),
    )

    if q_code == "Q1":
        obs, act, sev = "No plano", "Manter ritmo", "success"
    elif q_code == "Q3":
        obs, act, sev = "Drift crítico", "Revisão urgente", "danger"
    else:
        obs, act, sev = "Atenção requerida", "Ajustar cadência", "warning"
    footer = next_step_v2(obs, act, severity=sev)
    d_str = str(target_date) if target_date is not None else ""
    console.print(page("📊 State Dashboard", d_str, body, footer=footer))


def render_daily_v2(snap: DaySnapshot, target_date: date) -> None:
    """Render the v2 daily report from a DaySnapshot — production-grade."""
    q_code, x, y = compute_day_quadrant(snap)
    qspec = QUADRANT.get(q_code, QUADRANT["Q1"])

    sleep_dur = snap.sleep.duration_hours
    k1 = kpi_v2(
        "Sono", f"{sleep_dur:.1f}h" if sleep_dur is not None else "-",
        "success" if (sleep_dur or 0) >= 7 else "danger",
        icon="😴",
    )
    k2 = kpi_v2(
        "Pomodoros", f"{snap.n_pomodoros}/{snap.pomodoros_meta}",
        "success" if snap.n_pomodoros >= snap.pomodoros_meta * 0.8 else "warning",
        icon="🍅",
    )
    k3 = kpi_v2(
        "Hardwork", f"{snap.hardwork_realizado_min // 60}h{snap.hardwork_realizado_min % 60:02d}",
        "success" if snap.hardwork_realizado_min >= snap.hardwork_orcado_min * 0.8 else "warning",
        delta=f"orçado {snap.hardwork_orcado_min // 60}h",
        icon="💻",
    )
    k4 = kpi_v2(
        "Energia", f"{snap.energia}/10" if snap.energia else "-",
        "success" if (snap.energia or 0) >= 7 else "warning",
        icon="⚡",
    )

    regime = (
        "PUSH" if q_code == "Q1" and (snap.energia or 0) >= 7 else
        "MAINTAIN" if q_code == "Q1" else
        "REDUCE" if q_code == "Q4" else "RECOVER"
    )
    regime_color = {
        "PUSH": SEVERITY["success"], "MAINTAIN": SEVERITY["primary"],
        "REDUCE": SEVERITY["warning"], "RECOVER": SEVERITY["danger"],
    }[regime]
    context = f"[{regime_color}]regime: {regime}[/]"

    kpi_grid = kpi_grid_2x2([k1, k2, k3, k4])
    cart = cartesian_v2(x, y, q_code, show_legend=True, show_equation=True)
    pomo = pomodoros_v2(
        s1_done=min(4, snap.n_pomodoros),
        s1_focus=(snap.foco or 0),
        s2_done=min(4, max(0, snap.n_pomodoros - 4)),
        s2_focus=(snap.foco or 0) * 0.9,
        s3_done=min(4, max(0, snap.n_pomodoros - 8)),
        s3_focus=0.0,
    )

    body = Group(
        kpi_grid,
        "",
        section_v2("HARDWORK", icon="💻", subtitle="Cartesian plane", content=cart, severity="primary"),
        "",
        section_v2("POMODOROS", icon="🍅", subtitle="3 sessions × 4 rounds", content=pomo, severity="primary"),
    )

    if q_code == "Q1":
        obs, act, sev = f"{qspec.label_pt} mantido", "Manter ritmo, monitorar fadiga", "success"
    elif q_code == "Q3":
        obs, act, sev = "Drift crítico detectado", "Revisão urgente do sistema", "danger"
    else:
        obs, act, sev = qspec.label_pt, qspec.action_pt, "warning"
    footer = next_step_v2(obs, act, severity=sev)

    full_page = page("Daily Report", target_date.isoformat(), body, footer=footer)
    console.print(full_page)


def snapshot_to_json_str(snap: DaySnapshot, quadrant: str, x: float, y: float) -> str:
    """Serialize a DaySnapshot to a JSON string."""
    d = asdict(snap) if is_dataclass(snap) else snap.__dict__
    d["quadrant"] = quadrant
    d["x"] = x
    d["y"] = y
    return json.dumps(d, indent=2, default=str, ensure_ascii=False)


__all__ = ["render_daily_v2", "snapshot_to_json_str", "render_state_v2"]
