"""State dashboard CLI command — view current day snapshot.

The PAV-OS v2 design system is the **only** renderer for ``state show``.
``--mock`` is preserved.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Optional

import typer

from operational.cli.console import console as pav_console
from operational.cli.formatters import format_as_json
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
from operational.ui.v2_renderers import render_state_v2

app = typer.Typer(help="Dashboard do dia corrente (PAV-OS v2 design system — definitive edition).")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _period_now(dt: datetime) -> Period:
    h = dt.hour
    if PAV.HORARIO_ACORDAR_MIN <= h <= PAV.HORARIO_ACORDAR_MAX:
        return Period.MANHA
    if 6 <= h < PAV.HORARIO_DORMIR_MIN:
        return Period.TARDE
    return Period.NOITE


@app.command(name="show")
def show(
    target_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
    mock: Optional[str] = typer.Option(None, "--mock", help="Use mock profile (q1, q2, q3, q4, empty, burnout, peak)"),
) -> None:
    """Dashboard do dia — onde estou, o que está logado, estou no plano?

    Flags:
    - ``--mock <profile>``: synthesize a DaySnapshot from a mock profile.
    - ``--json``: machine-readable JSON output.
    """
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

    sleep = next((s for s in sleep_records.list() if s.date == d), None)
    blocks = [b for b in time_blocks.list() if b.start.date() == d]
    day_pomodoros = [p for p in pomodoros.list() if p.started_at.date() == d]
    day_logs = [l for l in routine_logs.list() if l.date == d]
    day_ajustes = [a for a in ajustes_finos.list() if a.date == d]
    day_journal = next((j for j in journals.list() if j.date == d), None)

    completed_pomodoros = sum(
        1 for p in day_pomodoros if getattr(p, "state", None) and "COMPLETE" in str(p.state)
    )

    if profile is not None:
        from operational.ui.mock_snapshot import build_mock_snapshot
        mock_snap = build_mock_snapshot(profile)
        sleep = SimpleNamespace(
            bedtime=mock_snap.sleep.bedtime,
            wake_time=mock_snap.sleep.wake_time,
            quality_score=mock_snap.sleep.quality,
            duration_hours=mock_snap.sleep.duration_hours,
        )
        completed_pomodoros = mock_snap.n_pomodoros
        day_journal = SimpleNamespace(
            energia_nivel=mock_snap.energia,
            foco_nivel=mock_snap.foco,
        )
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
            "pomodoros_completed": completed_pomodoros,
            "routine_logs": len(day_logs),
            "ajustes_finos": len(day_ajustes),
            "has_journal": day_journal is not None,
            "design_system": "v2",
            "mock": mock,
        }
        typer.echo(format_as_json(payload))
        return

    if profile is not None:
        from operational.ui.mock_snapshot import build_mock_snapshot
        state_snap = build_mock_snapshot(profile)
    else:
        from operational.cli.services import get_day_snapshot
        state_snap = get_day_snapshot(d)

    render_state_v2(
        snap=state_snap,
        target_date=d,
        period_label=period_now.value,
    )
