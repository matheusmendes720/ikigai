"""Routine CLI commands — Rich Tables for beautiful listing."""
from __future__ import annotations

from datetime import time

import typer
from rich.console import Console
from rich.table import Table

from operational.cli.formatters import format_as_json
from operational.cli.input_summary import maybe_print_input_summary
from operational.cli.renderers import COLORS, make_console
from operational.cli.state import routines
from operational.enums import Period, RoutineType
from operational.meta.factories import make_routine

app = typer.Typer(help="Manage routines.")
console = make_console(width=120)

# Color for each routine type
ROUTINE_TYPE_COLOR: dict[str, str] = {
    "ENTRY": "green",
    "CORE": "cyan",
    "TRANSITION": "yellow",
    "EXIT": "magenta",
}

PERIOD_COLOR: dict[str, str] = {
    "MANHA": "yellow",
    "TARDE": "cyan",
    "NOITE": "blue",
}

PERIOD_ICON: dict[str, str] = {
    "MANHA": "🌅",
    "TARDE": "💻",
    "NOITE": "🌙",
}


@app.command()
def create(
    name: str = typer.Argument(..., help="Routine name"),
    period: Period = typer.Argument(Period.MANHA, help="Period"),
    routine_type: RoutineType = typer.Argument(RoutineType.CORE, help="Type"),
    start_hour: int = typer.Option(6, "--start-hour", "-sh", help="Start hour (0-23)"),
    start_minute: int = typer.Option(0, "--start-minute", "-sm", help="Start minute"),
    end_hour: int = typer.Option(6, "--end-hour", "-eh", help="End hour"),
    end_minute: int = typer.Option(50, "--end-minute", "-em", help="End minute"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Create a new routine."""
    maybe_print_input_summary(
        title="Criando rotina",
        params={
            "name": name,
            "period": period.value,
            "type": routine_type.value,
            "start": f"{start_hour:02d}:{start_minute:02d}",
            "end": f"{end_hour:02d}:{end_minute:02d}",
        },
        flag_legend={"-sh": "--start-hour", "-sm": "--start-minute", "-eh": "--end-hour", "-em": "--end-minute"},
    )

    routine = make_routine(
        name=name,
        period=period,
        routine_type=routine_type,
        start_time=time(start_hour, start_minute),
        end_time=time(end_hour, end_minute),
    )
    routines.upsert(routine)
    if json:
        typer.echo(format_as_json(routine))
    else:
        tipo_color = ROUTINE_TYPE_COLOR.get(routine_type.value, "white")
        console.print(
            f"  [bold {tipo_color}]✓[/bold {tipo_color}] "
            f"Rotina criada: [bold]{routine.name}[/bold] "
            f"[dim]({period.value} · {routine_type.value})[/dim]"
        )
        console.print(f"    [dim]id: {routine.id}  ·  {routine.start_time.isoformat()}→{routine.end_time.isoformat()}[/dim]")


@app.command(name="list")
def list_routines(
    period: Period | None = typer.Option(None, "--period", "-p", help="Filter by period"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """List saved routines — Rich Table."""
    filters = {}
    if period:
        filters["period"] = period
    items = routines.list(filters or None)

    if json:
        typer.echo(format_as_json(items))
        return

    if not items:
        console.print("[yellow]⚠ Nenhuma rotina cadastrada.[/yellow] Use [bold]routine create[/bold].")
        return

    # Sort by period then by start time
    period_order = {Period.MANHA: 0, Period.TARDE: 1, Period.NOITE: 2}
    items_sorted = sorted(items, key=lambda r: (period_order.get(r.period, 9), r.start_time))

    table = Table(
        title=f"[bold cyan]🕐 Rotinas ({len(items)})[/bold cyan]",
        show_header=True,
        header_style="bold cyan",
        box=None,
        padding=(0, 2),
    )
    table.add_column("Período", style="bold", min_width=8)
    table.add_column("Tipo", min_width=12)
    table.add_column("Nome", style="white", min_width=30)
    table.add_column("Horário", justify="right", min_width=14)
    table.add_column("Duração", justify="right", min_width=8)
    table.add_column("ID", style="dim", min_width=20)

    for r in items_sorted:
        tipo_color = ROUTINE_TYPE_COLOR.get(r.routine_type.value, "white")
        per_color = PERIOD_COLOR.get(r.period.value, "white")
        # Compute duration
        start_min = r.start_time.hour * 60 + r.start_time.minute
        end_min = r.end_time.hour * 60 + r.end_time.minute
        if end_min < start_min:
            end_min += 24 * 60
        dur = end_min - start_min
        dur_str = f"{dur}min"
        if dur >= 60:
            dur_str = f"{dur // 60}h{dur % 60:02d}"

        table.add_row(
            f"[{per_color}]{PERIOD_ICON.get(r.period.value, '·')} {r.period.value}[/{per_color}]",
            f"[{tipo_color}]{r.routine_type.value}[/{tipo_color}]",
            r.name,
            f"{r.start_time.isoformat()}→{r.end_time.isoformat()}",
            dur_str,
            r.id,
        )

    console.print(table)
