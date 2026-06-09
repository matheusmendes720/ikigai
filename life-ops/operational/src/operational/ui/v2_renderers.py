"""V2 daily renderer — shared between ``report_v2_cmd.py`` and
``report_cmd.py --v2`` and ``state_cmd.py --v2``.

This is the v2 equivalent of ``ui.daily_report.render_daily_report``.
Takes a DaySnapshot and renders it with v2 components.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from rich.console import Group
from rich.json import JSON as RichJSON

from operational.cli.console import console
from operational.core.services import DaySnapshot, compute_day_quadrant
from operational.ui.components_v2 import (
    cartesian_v2,
    kpi_grid_2x2,
    kpi_v2,
    next_step_v2,
    page,
    pomodoros_v2,
    section_v2,
)
from operational.ui.tokens import CONSOLE_WIDTH_V2, QUADRANT, SEVERITY


def render_daily_v2(snap: DaySnapshot, target_date: date) -> None:
    """Render the v2 daily report from a DaySnapshot."""
    q_code, x, y = compute_day_quadrant(snap)
    qspec = QUADRANT.get(q_code, QUADRANT["Q1"])

    sleep_dur = snap.sleep.duration_hours
    k1 = kpi_v2(
        "Sono", f"{sleep_dur:.1f}h" if sleep_dur is not None else "-",
        "ok" if (sleep_dur or 0) >= 7 else "danger",
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

    from operational.ui.components_v2 import header_v2
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
        obs, act, sev = f"{qspec.label_pt} mantido", "Manter ritmo, monitorar fadiga", "success"
    elif q_code == "Q3":
        obs, act, sev = "Drift critico detectado", "Revisao urgente do sistema", "danger"
    else:
        obs, act, sev = qspec.label_pt, qspec.action_pt, "warning"
    footer = next_step_v2(obs, act, severity=sev)

    full_page = page("Daily Report", target_date.isoformat(), body, footer=footer)
    console.print(full_page)


def snapshot_to_json_str(snap: DaySnapshot, quadrant: str, x: float, y: float) -> str:
    """Serialize a DaySnapshot to a JSON string."""
    import json
    from dataclasses import asdict, is_dataclass
    d = asdict(snap) if is_dataclass(snap) else snap.__dict__
    d["quadrant"] = quadrant
    d["x"] = x
    d["y"] = y
    return json.dumps(d, indent=2, default=str, ensure_ascii=False)


def _wrap_v1_in_v2_page(title: str, body=None, subtitle: str = "", v1_renderable=None, footer=None) -> None:
    """Wrap a v1 Rich renderable in v2 chrome (header + footer).

    Accepts either ``body=`` (preferred) or legacy ``v1_renderable=``.
    """
    from operational.ui.components_v2 import header_v2
    from rich.console import Group
    from rich.padding import Padding

    if body is None and v1_renderable is not None:
        body = v1_renderable

    parts = [
        header_v2(title, subtitle, width=CONSOLE_WIDTH_V2),
        Padding(body, (1, 0)),
    ]
    if footer is not None:
        parts.append(Padding(footer, (1, 0)))
    console.print(Group(*parts))


def render_state_v2(snap: DaySnapshot, target_date=None, period_label: str = "", d=None) -> None:
    """Render the v2 state dashboard from a DaySnapshot.

    Accepts either ``target_date=`` (preferred) or legacy ``d=`` alias.
    """
    from operational.core.services import compute_day_quadrant
    from operational.ui.components_v2 import (
        cartesian_v2, kpi_grid_2x2, kpi_v2, next_step_v2, page, section_v2,
    )

    # Backwards-compat: accept d= as alias for target_date=
    if target_date is None and d is not None:
        target_date = d

    try:
        q_code, x, y = compute_day_quadrant(snap)
    except Exception:
        q_code, x, y = "Q1", 0.0, 0.0

    k1 = kpi_v2("Sono", f"{snap.sleep.duration_hours:.1f}h" if snap.sleep.duration_hours else "-",
                "ok" if (snap.sleep.duration_hours or 0) >= 7 else "danger", icon="😴")
    k2 = kpi_v2("Pomodoros", f"{snap.n_pomodoros}/{snap.pomodoros_meta}",
                "ok" if snap.n_pomodoros >= snap.pomodoros_meta * 0.8 else "warning", icon="🍅")
    k3 = kpi_v2("Hardwork", f"{snap.hardwork_realizado_min // 60}h{snap.hardwork_realizado_min % 60:02d}",
                "ok" if snap.hardwork_realizado_min >= snap.hardwork_orcado_min * 0.8 else "warning",
                delta=f"orcado {snap.hardwork_orcado_min // 60}h", icon="💻")
    k4 = kpi_v2("Energia", f"{snap.energia}/10" if snap.energia else "-",
                "ok" if (snap.energia or 0) >= 7 else "warning", icon="⚡")

    cart = cartesian_v2(x, y, q_code, show_legend=True, show_equation=True)
    kpi_grid = kpi_grid_2x2([k1, k2, k3, k4])

    body = Group(
        f" Period: [bold cyan]{period_label}[/]",
        "",
        kpi_grid,
        "",
        section_v2("HARDWORK", icon="💻", subtitle="Cartesian", content=cart, severity="primary"),
    )
    if q_code == "Q1":
        obs, act, sev = "No plano", "Manter ritmo", "success"
    elif q_code == "Q3":
        obs, act, sev = "Drift critico", "Revisao urgente", "danger"
    else:
        obs, act, sev = "Atencao", "Ajustar", "warning"
    footer = next_step_v2(obs, act, severity=sev)
    d_str = str(target_date) if target_date is not None else ""
    console.print(page("State Dashboard", d_str, body, footer=footer))


__all__ = ["render_daily_v2", "snapshot_to_json_str", "_wrap_v1_in_v2_page", "render_state_v2"]
