"""Journal CLI — Rich Table listing."""
from __future__ import annotations

from datetime import date

import typer
from rich.table import Table

from operational.cli._compat import make_console, maybe_print_input_summary
from operational.cli.formatters import format_as_json
from operational.cli.state import journals
from operational.meta.factories import make_journal_entry

app = typer.Typer(help="Manage journal entries.")
console = make_console(width=120)


@app.command()
def create(
    entry_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    text: str = typer.Option("", "--text", "-t", help="Texto da entrada"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Criar uma entrada de diário."""
    d = date.fromisoformat(entry_date) if entry_date else date.today()
    maybe_print_input_summary(
        title="Criando entrada de diário",
        params={"date": d.isoformat(), "text_len": len(text), "preview": text[:40] + ("…" if len(text) > 40 else "")},
        flag_legend={"-d": "--date", "-t": "--text"},
    )

    entry = make_journal_entry(entry_date=d, entry_text=text)
    journals.upsert(entry)
    if json:
        typer.echo(format_as_json(entry))
    else:
        console.print(f"  [bold green]✓[/bold green] Entrada criada: [bold]{entry.id}[/bold]")
        console.print(f"    [dim]data: {entry.date.isoformat()} · {len(text)} caracteres[/dim]")
        if text:
            preview = text.replace("\n", " ")[:60]
            console.print(f"    [italic dim]\"{preview}{'…' if len(text) > 60 else ''}\"[/italic dim]")


@app.command(name="list")
def list_entries(
    target_date: str | None = typer.Option(None, "--date", "-d", help="Filtrar por data"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Listar entradas do diário — Rich Table."""
    items = journals.list()
    if target_date:
        d = date.fromisoformat(target_date)
        items = [j for j in items if j.date == d]

    if json:
        typer.echo(format_as_json(items))
        return
    if not items:
        console.print("[yellow]⚠ Nenhuma entrada de diário.[/yellow] Use [bold]journal create[/bold].")
        return

    items_sorted = sorted(items, key=lambda j: (j.date, j.id), reverse=True)

    table = Table(
        title=f"[bold cyan]📓 Journal ({len(items)})[/bold cyan]",
        show_header=True,
        header_style="bold cyan",
        box=None,
        padding=(0, 2),
    )
    table.add_column("Data", style="bold white", min_width=12)
    table.add_column("Energia", justify="center", min_width=8)
    table.add_column("Foco", justify="center", min_width=8)
    table.add_column("Humor", justify="center", min_width=8)
    table.add_column("Pomodoros", justify="right", min_width=11)
    table.add_column("Preview", style="italic", min_width=40)
    table.add_column("ID", style="dim", min_width=20)

    for j in items_sorted:
        # Energy bar
        if j.energia_nivel:
            bar = "█" * (j.energia_nivel // 2) + "░" * (5 - j.energia_nivel // 2)
            en = f"[yellow]{bar}[/yellow] {j.energia_nivel}/10"
        else:
            en = "[dim]—[/dim]"
        # Focus bar
        if j.foco_nivel:
            bar = "█" * (j.foco_nivel // 2) + "░" * (5 - j.foco_nivel // 2)
            fo = f"[cyan]{bar}[/cyan] {j.foco_nivel}/10"
        else:
            fo = "[dim]—[/dim]"
        # Humor
        hm = "[dim]—[/dim]"
        if j.humor_morning and j.humor_evening:
            hm = f"☀{j.humor_morning} 🌙{j.humor_evening}"

        preview = j.entry_text.replace("\n", " ")[:50]
        if len(j.entry_text) > 50:
            preview += "…"

        table.add_row(
            j.date.isoformat(),
            en,
            fo,
            hm,
            str(j.pomodoros_completos),
            preview,
            j.id,
        )

    console.print(table)
