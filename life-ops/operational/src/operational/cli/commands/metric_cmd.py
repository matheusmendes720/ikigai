"""Metric CLI commands — sleep & energy tracking with Rich Tables."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import typer
from rich.console import Console
from rich.table import Table

from operational.cli.formatters import format_as_json
from operational.cli.input_summary import maybe_print_input_summary
from operational.cli.renderers import make_console, progress_bar
from operational.cli.state import sleep_records, time_blocks
from operational.core.services import parse_iso_date
from operational.entities.time_block import TimeBlock
from operational.enums import Period
from operational.meta.factories import make_sleep_record
from operational.types import UEID
from operational.ui.components import error_panel
from operational.ui.logging_setup import log_error

app = typer.Typer(help="Manage metrics (sleep, energy, daily logs).")
console = make_console(width=120)


def _infer_period(hour: int) -> Period:
    if 3 <= hour <= 5:
        return Period.MANHA
    if 6 <= hour < 18:
        return Period.TARDE
    return Period.NOITE


def _sleep_emoji(quality: int) -> str:
    if quality >= 9:
        return "🟢"
    if quality >= 7:
        return "🟢"
    if quality >= 5:
        return "🟡"
    if quality >= 4:
        return "🟠"
    return "🔴"


def _sleep_label(quality: int) -> str:
    if quality >= 9:
        return "excelente"
    if quality >= 7:
        return "bom"
    if quality >= 5:
        return "regular"
    if quality >= 4:
        return "hardcore"
    return "crítico"


@app.command()
def sleep(
    record_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    quality: int = typer.Option(8, "--quality", "-q", min=1, max=10, help="Qualidade (1-10)"),
    bed_hour: int = typer.Option(23, "--bed-hour", "-bh", help="Hora que dormiu (0-23)"),
    bed_minute: int = typer.Option(0, "--bed-minute", "-bm", help="Minuto que dormiu (0-59)"),
    wake_hour: int = typer.Option(7, "--wake-hour", "-wh", help="Hora que acordou (0-23)"),
    wake_minute: int = typer.Option(0, "--wake-minute", "-wm", help="Minuto que acordou (0-59)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Registrar sono retroativo."""
    d = date.fromisoformat(record_date) if record_date else date.today()
    maybe_print_input_summary(
        title="Registrando sono",
        params={
            "date": d.isoformat(),
            "quality": quality,
            "bedtime": f"{bed_hour:02d}:{bed_minute:02d}",
            "wake": f"{wake_hour:02d}:{wake_minute:02d}",
        },
        flag_legend={"-d": "--date", "-q": "--quality", "-bh": "--bed-hour", "-bm": "--bed-minute", "-wh": "--wake-hour", "-wm": "--wake-minute"},
    )

    record = make_sleep_record(
        record_date=d,
        quality_score=quality,
        bedtime=time(bed_hour, bed_minute),
        wake_time=time(wake_hour, wake_minute),
    )
    sleep_records.upsert(record)
    if json:
        typer.echo(format_as_json(record))
    else:
        emoji = _sleep_emoji(quality)
        label = _sleep_label(quality)
        console.print(f"  [bold blue]✓[/bold blue] Sono registrado: [bold]{record.id}[/bold]")
        console.print(f"    [dim]data: {d.isoformat()}  ·  Q={quality}/10 {emoji} {label}  ·  {record.duration_hours:.1f}h[/dim]")


@app.command(name="list")
def list_sleep(
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Listar registros de sono — Rich Table."""
    items = sleep_records.list()
    if json:
        typer.echo(format_as_json(items))
        return
    if not items:
        console.print("[yellow]⚠ Nenhum registro de sono.[/yellow] Use [bold]metric sleep[/bold].")
        return

    items_sorted = sorted(items, key=lambda s: s.date, reverse=True)
    table = Table(
        title=f"[bold blue]😴 Sleep Records ({len(items)})[/bold blue]",
        show_header=True,
        header_style="bold blue",
        box=None,
        padding=(0, 2),
    )
    table.add_column("Data", style="bold white", min_width=12)
    table.add_column("Dormiu", justify="right", min_width=10)
    table.add_column("Acordou", justify="right", min_width=10)
    table.add_column("Duração", justify="right", min_width=10)
    table.add_column("Qualidade", min_width=18)
    table.add_column("Notas", style="dim italic", min_width=30)
    table.add_column("ID", style="dim", min_width=20)

    for s in items_sorted:
        emoji = _sleep_emoji(s.quality_score)
        label = _sleep_label(s.quality_score)
        quality_cell = f"{emoji} [bold]{s.quality_score}[/bold]/10 [dim]({label})[/dim]"
        notes = (s.notes or "").replace("\n", " ")[:40]

        table.add_row(
            s.date.isoformat(),
            s.bedtime.strftime("%H:%M"),
            s.wake_time.strftime("%H:%M"),
            f"{s.duration_hours:.1f}h",
            quality_cell,
            notes,
            s.id,
        )

    console.print(table)


@app.command()
def energy(
    energia: int = typer.Option(..., "--energia", "-e", min=1, max=10, help="Energia (1-10)"),
    foco: int = typer.Option(..., "--foco", "-f", min=1, max=10, help="Foco (1-10)"),
    target_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    block_id: str | None = typer.Option(None, "--block", "-b", help="Vincular a bloco existente (UEID)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Check-in rápido de energia/foco (cria bloco instantâneo se não passar --block)."""
    maybe_print_input_summary(
        title="Check-in de energia/foco",
        params={"energia": energia, "foco": foco, "date": target_date or "hoje", "block_id": block_id or "(novo bloco)"},
        flag_legend={"-e": "--energia", "-f": "--foco", "-d": "--date", "-b": "--block"},
    )

    d = date.fromisoformat(target_date) if target_date else date.today()
    now = datetime.now(timezone.utc)

    if block_id:
        existing = time_blocks.get(block_id)
        if existing is None:
            console.print(f"[red]✗ Bloco {block_id} não encontrado.[/red]")
            raise typer.Exit(code=1)
        updated = existing.model_copy(update={
            "energia_nivel": energia,
            "foco_nivel": foco,
        })
        time_blocks.upsert(updated)
        if json:
            typer.echo(format_as_json(updated))
        else:
            console.print(f"  [bold green]✓[/bold green] Check-in registrado no bloco [dim]{block_id}[/dim]")
            console.print(f"    [dim]energia: {energia}/10  ·  foco: {foco}/10  ·  média: {(energia + foco) // 2}/10[/dim]")
    else:
        # Create instant 1s block at the current time
        period = _infer_period(now.hour)
        new_block = TimeBlock(
            id=UEID(f"chk_{now.strftime('%Y%m%d_%H%M%S')}"),
            label=f"Check-in energia/foco",
            start=now,
            end=now + timedelta(seconds=1),
            period=period,
            energia_nivel=energia,
            foco_nivel=foco,
            created_at=now,
        )
        time_blocks.upsert(new_block)
        if json:
            typer.echo(format_as_json(new_block))
        else:
            avg = (energia + foco) // 2
            color = "green" if avg >= 7 else "yellow" if avg >= 5 else "red"
            console.print(f"  [bold {color}]✓[/bold {color}] Check-in criado: [bold]E={energia}/10 F={foco}/10[/bold]")
            console.print(f"    [dim]média {avg}/10  ·  bloco {new_block.id}  ·  período {period.value}[/dim]")
