"""PAV-OS v2 report commands — uses design system v2 + mock data.

This is the **new** report command (entry point: ``pav`` instead of
``operational``). It uses:
- ``ui.components_v2`` for rendering
- ``ui.mock_snapshot.build_mock_snapshot`` for ``--mock`` mode
- ``ui.tokens`` for all colors/glyphs

For the old v1 behavior, see ``commands/report_cmd.py``.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import typer
from rich.console import Group
from rich.json import JSON as RichJSON

from operational.cli.console import console
from operational.core.services import compute_day_quadrant
from operational.ui.components_v2 import (
    cartesian_v2,
    error_panel_v2,
    header_v2,
    kpi_v2,
    kpi_grid_2x2,
    next_step_v2,
    page,
    pomodoros_v2,
    section_v2,
)
from operational.ui.mock_profiles import get_profile, list_profiles
from operational.ui.mock_snapshot import build_mock_snapshot
from operational.ui.tokens import CONSOLE_WIDTH_V2, QUADRANT, SEVERITY

app = typer.Typer(help="PAV-OS v2 reports — design system v2 + mock data.")


def _render_daily_v2(snap, target_date: date) -> None:
    """Render the v2 daily report from a DaySnapshot."""
    q_code, x, y = compute_day_quadrant(snap)
    qspec = QUADRANT.get(q_code, QUADRANT["Q1"])

    # KPI grid (2x2): Sono, Pomodoros, Hardwork, Energia
    k1 = kpi_v2(
        "Sono", f"{snap.sleep.duration_hours:.1f}h",
        "ok" if (snap.sleep.duration_hours or 0) >= 7 else "danger",
        icon="😴",
    )
    k2 = kpi_v2(
        "Pomodoros", f"{snap.n_pomodoros}/{snap.pomodoros_meta}",
        "ok" if snap.n_pomodoros >= snap.pomodoros_meta * 0.8 else "warning",
        icon="🍅",
    )
    k3 = kpi_v2(
        "Hardwork", f"{snap.hardwork_realizado_min // 60}h{snap.hardwork_realizado_min % 60:02d}",
        "ok" if snap.hardwork_realizado_min >= snap.hardwork_orcado_min * 0.8 else "warning",
        delta=f"orcado {snap.hardwork_orcado_min // 60}h",
        icon="💻",
    )
    k4 = kpi_v2(
        "Energia", f"{snap.energia}/10" if snap.energia else "-",
        "ok" if (snap.energia or 0) >= 7 else "warning",
        icon="⚡",
    )

    # Regime context (from quadrant)
    regime = "PUSH" if q_code == "Q1" and (snap.energia or 0) >= 7 else \
             "MAINTAIN" if q_code == "Q1" else \
             "REDUCE" if q_code == "Q4" else "RECOVER"
    regime_color = {"PUSH": SEVERITY["success"], "MAINTAIN": SEVERITY["primary"],
                    "REDUCE": SEVERITY["warning"], "RECOVER": SEVERITY["danger"]}[regime]

    context = f"[{regime_color}]regime: {regime}[/]"

    header = header_v2("Daily Report", target_date.isoformat(), context=context)

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
        "\n",
        section_v2("HARDWORK", icon="💻", subtitle="Cartesian plane", content=cart, severity="primary"),
        "\n",
        section_v2("POMODOROS", icon="🍅", subtitle="3 sessions x 4 rounds", content=pomo, severity="primary"),
    )

    if q_code == "Q1":
        obs = f"{qspec.label_pt} mantido"
        act = "Manter ritmo, monitorar fadiga"
        sev = "success"
    elif q_code == "Q3":
        obs = "Drift critico detectado"
        act = "Revisao urgente do sistema"
        sev = "danger"
    else:
        obs = f"{qspec.label_pt}"
        act = qspec.action_pt
        sev = "warning"
    footer = next_step_v2(obs, act, severity=sev)

    full_page = page("Daily Report", target_date.isoformat(), body, footer=footer)
    console.print(full_page)


@app.command(name="today")
def today(
    mock: Optional[str] = typer.Option(
        None, "--mock", help=f"Use mock profile. Available: {', '.join(list_profiles())}"
    ),
    json_out: bool = typer.Option(False, "--json", help="JSON output"),
    target_date: Optional[str] = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
) -> None:
    """Render today's snapshot using PAV-OS v2 design system."""
    try:
        d = date.fromisoformat(target_date) if target_date else date.today()
    except ValueError as e:
        console.print(error_panel_v2(
            f"Data invalida: {target_date}",
            context=f"pav report today --date {target_date}",
            expected="YYYY-MM-DD (ano-mes-dia, mes 01-12, dia 01-31)",
            suggestion="pav report today --date 2026-06-08",
        ))
        raise typer.Exit(code=1)

    if mock:
        try:
            profile = get_profile(mock)
        except ValueError as e:
            console.print(error_panel_v2(
                str(e),
                context=f"pav report today --mock {mock}",
                expected=f"One of: {', '.join(list_profiles())}",
                suggestion="pav report today --mock q1",
            ))
            raise typer.Exit(code=1)
        snap = build_mock_snapshot(profile)
        if json_out:
            console.print(RichJSON(_snapshot_to_json(snap, profile.quadrant, profile.x_pct, profile.y_pct)))
            return
        _render_daily_v2(snap, d)
        return

    # Live data path
    from operational.cli.state import day_contexts, journals, pomodoros, sleep_records, time_blocks
    from operational.core.services import get_day_snapshot
    snap = get_day_snapshot(d)
    if json_out:
        q_code, x, y = compute_day_quadrant(snap)
        console.print(RichJSON(_snapshot_to_json(snap, q_code, x, y)))
        return
    _render_daily_v2(snap, d)


def _snapshot_to_json(snap, quadrant: str, x: float, y: float) -> str:
    """Serialize a DaySnapshot to a JSON string."""
    import json
    from dataclasses import asdict, is_dataclass
    d = asdict(snap) if is_dataclass(snap) else snap.__dict__
    d["quadrant"] = quadrant
    d["x"] = x
    d["y"] = y
    return json.dumps(d, indent=2, default=str, ensure_ascii=False)


@app.command(name="mock-list")
def mock_list() -> None:
    """List available mock profiles."""
    from rich.table import Table
    from operational.ui.mock_profiles import PROFILES
    t = Table(title="[bold cyan]Mock Profiles (--mock <name>)")
    t.add_column("Name", style="cyan")
    t.add_column("Description", style="white")
    t.add_column("Quadrant", style="bold")
    t.add_column("Regime", style="bold")
    for name, p in PROFILES.items():
        qspec = QUADRANT.get(p.quadrant, QUADRANT["Q1"])
        t.add_row(
            name,
            p.description,
            f"[{qspec.color}]{p.quadrant} {qspec.glyph}[/]",
            p.regime.value,
        )
    console.print(t)


__all__ = ["app"]
