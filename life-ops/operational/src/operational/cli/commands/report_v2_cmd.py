"""PAV-OS v2 report commands — uses design system v2 + mock data.

Entry point: ``pav v2 today``. The actual rendering lives in
``ui.v2_renderers.render_daily_v2`` so it's shared with
``report_cmd.py --v2`` and ``state_cmd.py --v2``.

For the old v1 behavior, see ``commands/report_cmd.py``.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import typer
from rich.json import JSON as RichJSON

from operational.cli.console import console
from operational.core.services import compute_day_quadrant, get_day_snapshot
from operational.ui.components_v2 import error_panel_v2
from operational.ui.mock_profiles import get_profile, list_profiles
from operational.ui.mock_snapshot import build_mock_snapshot
from operational.ui.v2_renderers import render_daily_v2, snapshot_to_json_str

app = typer.Typer(help="PAV-OS v2 reports — design system v2 + mock data.")


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
    except ValueError:
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
            console.print(RichJSON(snapshot_to_json_str(snap, profile.quadrant, profile.x_pct, profile.y_pct)))
            return
        render_daily_v2(snap, d)
        return

    snap = get_day_snapshot(d)
    if json_out:
        q_code, x, y = compute_day_quadrant(snap)
        console.print(RichJSON(snapshot_to_json_str(snap, q_code, x, y)))
        return
    render_daily_v2(snap, d)


@app.command(name="mock-list")
def mock_list() -> None:
    """List available mock profiles."""
    from rich.table import Table
    from operational.ui.mock_profiles import PROFILES
    from operational.ui.tokens import QUADRANT
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
