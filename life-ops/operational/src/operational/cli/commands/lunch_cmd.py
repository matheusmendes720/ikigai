"""Lunch CLI — registro estruturado de almoço (PAV V3 §2).

O almoço é uma fronteira crítica: eat (5min) + rest (30min) + flag
pesado que correlaciona com cochilos além do orçamento.
"""
from __future__ import annotations

from datetime import date, datetime, UTC

import typer
from rich.table import Table

from operational.cli._compat import make_console
from operational.cli.formatters import format_as_json
from operational.cli.state import lunch_records
from operational.types import UEID

app = typer.Typer(help="Registrar almoço (eat + rest + flag pesado).")
console = make_console(width=120)


@app.command()
def create(
    target_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    eat: int = typer.Option(5, "--eat", "-e", min=0, max=120, help="Minutos comendo"),
    rest: int = typer.Option(30, "--rest", "-r", min=0, max=180, help="Minutos descansando"),
    pesado: bool = typer.Option(False, "--pesado", "-p", help="Almoço pesado (correlaciona com sonolência)"),
    notas: str = typer.Option("", "--notas", "-n", help="Notas livres"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Registrar almoço do dia."""
    d = date.fromisoformat(target_date) if target_date else date.today()
    from operational.entities.v3 import LunchRecord
    record = LunchRecord(
        id=UEID(f"lun_{d.strftime('%Y%m%d')}"),
        date=d,
        eat_min=eat,
        rest_min=rest,
        pesado=pesado,
        notas=notas,
        created_at=datetime.now(UTC),
    )
    lunch_records.upsert(record)
    if json:
        typer.echo(format_as_json(record))
    else:
        from operational.ui.receipt import receipt_panel
        emoji = "⚠️ PESADO" if pesado else "✅ OK"
        within_severity = "success" if record.within_budget else "warning"
        within_msg = "dentro do orçamento" if record.within_budget else "estourou orçamento"
        receipt = receipt_panel(
            title="LUNCH RECORD",
            icon="🍽️",
            success_message=f"Almoço registrado ({emoji}) — {within_msg}.",
            detail_pairs=[
                ("ID", str(record.id)),
                ("Data", d.isoformat()),
                ("Eat", f"{eat}min"),
                ("Rest", f"{rest}min"),
                ("Total", f"{record.duracao_total}min"),
                ("Pesado", "Sim" if pesado else "Não"),
                ("Within budget", "✓" if record.within_budget else "✗"),
            ],
            severity=within_severity,
            footer=f"Detalhes: ID {record.id} | {d.isoformat()} | Total {record.duracao_total}min",
        )
        console.print(receipt)


@app.command(name="list")
def list_lunch(
    target_date: str | None = typer.Option(None, "--date", "-d", help="Filtrar por data"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Lista registros de almoço."""
    items = lunch_records.list()
    if target_date:
        d = date.fromisoformat(target_date)
        items = [r for r in items if r.date == d]

    if json:
        typer.echo(format_as_json(items))
    elif not items:
        console.print("Nenhum almoço registrado. Use `lunch create`.")
    else:
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Data", width=12)
        table.add_column("Eat (min)", width=10)
        table.add_column("Rest (min)", width=10)
        table.add_column("Total", width=8)
        table.add_column("Pesado", width=8)
        table.add_column("Within budget", width=14)
        for r in items:
            table.add_row(
                r.date.isoformat(),
                str(r.eat_min),
                str(r.rest_min),
                f"{r.duracao_total}min",
                "⚠️" if r.pesado else "-",
                "✓" if r.within_budget else "✗",
            )
        console.print(table)
