"""Daily reflection CLI — OKRs V3 (PAV V3 §2)."""
from __future__ import annotations

from datetime import date, datetime, UTC

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from operational.cli.formatters import format_as_json
from operational.cli.renderers import make_console
from operational.cli.state import daily_reflections
from operational.enums import EstadoPsicomatico
from operational.types import UEID

app = typer.Typer(help="OKRs diários (entrada/saída) — PAV V3.")
console = make_console(width=120)


def _prompt_list(label: str, default: str = "") -> list[str]:
    """Prompt for a comma-separated list."""
    raw = Prompt.ask(f"  {label} (separar por ;)", default=default)
    if not raw.strip():
        return []
    return [s.strip() for s in raw.split(";") if s.strip()]


@app.command()
def entrada(
    target_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """OKRs de ENTRADA (manhã) — parar de fazer, repetir, big-win.

    Reflete sobre o dia de ontem e define intenção para hoje.
    """
    d = date.fromisoformat(target_date) if target_date else date.today()

    console.print(f"\n[bold cyan]🌅 OKRs de Entrada — {d.isoformat()}[/bold cyan]\n")
    console.print("[dim]Reflita sobre ONTEM para definir intenção de HOJE[/dim]\n")

    parar = _prompt_list("O que fiz ontem que devo PARAR de fazer")
    repetir = _prompt_list("O que fiz ontem que devo REPETIR")
    sempre = _prompt_list("O que devo SEMPRE fazer (indexador de eficácia)")
    big_win = Prompt.ask("  Big-win (única coisa que torna outras mais fáceis)", default="")

    # Estado geral
    e = Prompt.ask("  Estado geral (1-10)", default="7")
    estado = EstadoPsicomatico.from_score(int(e))

    ref = __import__("operational.entities.v3", fromlist=["DailyReflection"]).DailyReflection(
        id=UEID(f"ref_{d.strftime('%Y%m%d')}"),
        date=d,
        parar_de_fazer=parar,
        repetir=repetir,
        sempre_fazer=sempre,
        big_win=big_win,
        estado_geral=estado,
        created_at=datetime.now(UTC),
    )
    daily_reflections.upsert(ref)

    if json:
        typer.echo(format_as_json(ref))
    else:
        console.print("\n[bold green]✔ OKRs de entrada registrados![/bold green]")


@app.command()
def saida(
    target_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """OKRs de SAÍDA (noite) — deu certo, deu errado, aprendizado, ajustes."""
    d = date.fromisoformat(target_date) if target_date else date.today()

    console.print(f"\n[bold cyan]🌙 OKRs de Saída — {d.isoformat()}[/bold cyan]\n")
    console.print("[dim]Reflita sobre HOJE para alimentar o sistema[/dim]\n")

    deu_certo = _prompt_list("O que deu certo hoje (execução sistemática)")
    deu_errado = _prompt_list("O que deu errado (equívocos)")
    aprendizado = Prompt.ask("  Maior aprendizado do dia (antítese + síntese)", default="")
    ajustes = _prompt_list("Ajustes finos para amanhã")

    # Estado final
    e = Prompt.ask("  Estado final do dia (1-10)", default="6")
    estado = EstadoPsicomatico.from_score(int(e))

    # Try to merge with existing reflection (entrada fields preserved)
    existing = daily_reflections.get(UEID(f"ref_{d.strftime('%Y%m%d')}"))
    if existing:
        ref_data = existing.model_dump()
        ref_data["deu_certo"] = deu_certo
        ref_data["deu_errado"] = deu_errado
        ref_data["maior_aprendizado"] = aprendizado
        ref_data["ajustes_para_amanha"] = ajustes
        ref_data["estado_geral"] = estado
        from operational.entities.v3 import DailyReflection
        ref = DailyReflection.model_validate(ref_data)
    else:
        from operational.entities.v3 import DailyReflection
        ref = DailyReflection(
            id=UEID(f"ref_{d.strftime('%Y%m%d')}"),
            date=d,
            deu_certo=deu_certo,
            deu_errado=deu_errado,
            maior_aprendizado=aprendizado,
            ajustes_para_amanha=ajustes,
            estado_geral=estado,
            created_at=datetime.now(UTC),
        )
    daily_reflections.upsert(ref)

    if json:
        typer.echo(format_as_json(ref))
    else:
        console.print("\n[bold green]✔ OKRs de saída registrados![/bold green]")


@app.command(name="list")
def list_reflections(
    target_date: str | None = typer.Option(None, "--date", "-d", help="Filtrar por data"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Lista todas as reflexões diárias registradas."""
    items = daily_reflections.list()
    if target_date:
        d = date.fromisoformat(target_date)
        items = [r for r in items if r.date == d]

    if json:
        typer.echo(format_as_json(items))
    elif not items:
        console.print("Nenhuma reflexão registrada. Use `reflect entrada` ou `reflect saida`.")
    else:
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Data", width=12)
        table.add_column("Estado", width=12)
        table.add_column("Big-Win", width=40)
        table.add_column("Aprendizado", width=40)
        for r in items:
            table.add_row(
                r.date.isoformat(),
                r.estado_geral.value,
                r.big_win[:38] + "…" if len(r.big_win) > 40 else r.big_win,
                r.maior_aprendizado[:38] + "…" if len(r.maior_aprendizado) > 40 else r.maior_aprendizado,
            )
        console.print(table)
