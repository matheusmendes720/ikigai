"""Time-block CLI commands — Rich Tables."""
from __future__ import annotations

from datetime import datetime, timedelta

import typer
from rich.table import Table

from operational.cli._compat import make_console, maybe_print_input_summary
from operational.cli.formatters import format_as_json
from operational.cli.state import time_blocks
from operational.cli.telemetry import get_logger, trace_command
from operational.enums import Period
from operational.meta.factories import make_time_block

app = typer.Typer(help="Manage time blocks.")
console = make_console(width=120)

PERIOD_ICON = {"MANHA": "🌅", "TARDE": "💻", "NOITE": "🌙"}
PERIOD_COLOR = {"MANHA": "yellow", "TARDE": "cyan", "NOITE": "blue"}


@app.command()
def create(
    period: Period = typer.Argument(Period.MANHA, help="Período (MANHA/TARDE/NOITE)"),
    label: str = typer.Option("", "--label", "-l", help="Rótulo do bloco"),
    routine_id: str | None = typer.Option(None, "--routine", "-r", help="UEID da rotina vinculada"),
    start: str | None = typer.Option(None, "--start", "-s", help="ISO start datetime (e.g. 2026-06-23T09:00)"),
    end: str | None = typer.Option(None, "--end", "-e", help="ISO end datetime (e.g. 2026-06-23T10:30)"),
    duration_minutes: int = typer.Option(60, "--duration", "-d", help="Duration in minutes (used when --start/--end not provided)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Criar um novo time block.

    Default: agora + 1h (ou --duration minutos).
    Use --start/--end para datetime explícito (formato ISO, ex: 2026-06-23T09:00).
    Para blocos no passado use --start com data no passado.
    """
    log = get_logger("block_cmd")
    with trace_command(log, "block.create", command="pav block create", entity_type="time_block") as ctx:
        maybe_print_input_summary(
            title="Criando time block",
            params={
                "period": period.value,
                "label": label,
                "routine_id": routine_id or "—",
                "start": start or "agora",
                "end": end or f"+{duration_minutes}min",
            },
            flag_legend={"-l": "--label", "-r": "--routine", "-s": "--start", "-e": "--end", "-d": "--duration"},
        )

        # Parse explicit start/end if provided
        start_dt: datetime | None = None
        end_dt: datetime | None = None
        if start:
            # Try ISO format, with/without seconds
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    start_dt = datetime.strptime(start, fmt)
                    break
                except ValueError:
                    continue
            if start_dt is None:
                msg = f"Data inválida: {start!r}. Use ISO formato: 2026-06-23T09:00 ou 2026-06-23 09:00"
                raise typer.BadParameter(msg)
        if end:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    end_dt = datetime.strptime(end, fmt)
                    break
                except ValueError:
                    continue
            if end_dt is None:
                msg = f"Data inválida: {end!r}. Use ISO formato: 2026-06-23T09:00 ou 2026-06-23 09:00"
                raise typer.BadParameter(msg)

        # duration_minutes only used when start is explicit and end is not
        if start_dt and not end_dt:
            end_dt = start_dt + timedelta(minutes=duration_minutes)

        block = make_time_block(
            period=period,
            label=label,
            routine_id=routine_id,
            start=start_dt,
            end=end_dt,
        )
        time_blocks.upsert(block)
        ctx.info("entity.created", entity_id=block.id, entity_type="time_block", period=period.value)

        if json:
            typer.echo(format_as_json(block))
        else:
            per_color = PERIOD_COLOR.get(period.value, "white")
            console.print(
                f"  [bold {per_color}]✓[/bold {per_color}] "
                f"Bloco criado: [bold]{block.label or '(sem label)'}[/bold]"
            )
            console.print(
                f"    [dim]id: {block.id}  ·  {block.start.isoformat()} → {block.end.isoformat()}[/dim]"
            )


@app.command(name="list")
def list_blocks(
    period: Period | None = typer.Option(None, "--period", "-p", help="Filtrar por período"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Listar time blocks salvos — Rich Table."""
    filters = {}
    if period:
        filters["period"] = period
    items = time_blocks.list(filters or None)

    if json:
        typer.echo(format_as_json(items))
        return
    if not items:
        console.print("[yellow]⚠ Nenhum time block cadastrado.[/yellow] Use [bold]block create[/bold].")
        return

    # Sort by date then start
    items_sorted = sorted(items, key=lambda b: (b.start.date(), b.start))

    table = Table(
        title=f"[bold magenta]📦 Time Blocks ({len(items)})[/bold magenta]",
        show_header=True,
        header_style="bold magenta",
        box=None,
        padding=(0, 2),
    )
    table.add_column("Data", style="bold white", min_width=12)
    table.add_column("Período", min_width=10)
    table.add_column("Label", style="white", min_width=30)
    table.add_column("Início → Fim", justify="right", min_width=22)
    table.add_column("Duração", justify="right", min_width=8)
    table.add_column("ID", style="dim", min_width=20)

    for b in items_sorted:
        per_color = PERIOD_COLOR.get(b.period.value, "white")
        # Duration
        dur = int((b.end - b.start).total_seconds() // 60)
        dur_str = f"{dur}min"
        if dur >= 60:
            dur_str = f"{dur // 60}h{dur % 60:02d}m"

        table.add_row(
            b.start.date().isoformat(),
            f"[{per_color}]{PERIOD_ICON.get(b.period.value, '·')} {b.period.value}[/{per_color}]",
            b.label or "[dim](sem label)[/dim]",
            f"{b.start.strftime('%H:%M')}→{b.end.strftime('%H:%M')}",
            dur_str,
            b.id,
        )

    console.print(table)
