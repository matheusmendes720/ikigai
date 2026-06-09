"""Time-block CLI commands — Rich Tables."""
from __future__ import annotations

import typer
from rich.table import Table

from operational.cli._compat import make_console, maybe_print_input_summary
from operational.cli.formatters import format_as_json
from operational.cli.state import time_blocks
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
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Criar um novo time block (default: agora + 1h)."""
    maybe_print_input_summary(
        title="Criando time block",
        params={"period": period.value, "label": label, "routine_id": routine_id or "—"},
        flag_legend={"-l": "--label", "-r": "--routine"},
    )

    block = make_time_block(
        period=period,
        label=label,
        routine_id=routine_id,
    )
    time_blocks.upsert(block)
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
