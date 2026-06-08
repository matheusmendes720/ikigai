"""Habit CLI — Rich Table listing."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from operational.cli.formatters import format_as_json
from operational.cli.input_summary import maybe_print_input_summary
from operational.cli.renderers import make_console, progress_bar
from operational.cli.state import habits
from operational.enums import HabitCategory
from operational.meta.factories import make_habit

app = typer.Typer(help="Manage habits.")
console = make_console(width=120)

CATEGORY_ICON: dict[str, str] = {
    "physiological": "💧",
    "ritual": "🧘",
    "cognitive": "🧠",
    "social": "👥",
    "creative": "🎨",
}
CATEGORY_COLOR: dict[str, str] = {
    "physiological": "blue",
    "ritual": "magenta",
    "cognitive": "cyan",
    "social": "yellow",
    "creative": "green",
}


@app.command()
def create(
    name: str = typer.Argument(..., help="Nome do hábito"),
    category: HabitCategory = typer.Argument(HabitCategory.PHYSIOLOGICAL, help="Categoria"),
    resistance: float = typer.Option(5.0, "--resistance", "-r", min=0.0, max=10.0, help="Resistência (0-10)"),
    weight: float = typer.Option(0.25, "--weight", "-w", min=0.0, max=1.0, help="Peso Q_HE"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Criar um novo hábito."""
    maybe_print_input_summary(
        title="Criando hábito",
        params={"name": name, "category": category.value, "resistance": resistance, "weight": weight},
        flag_legend={"-r": "--resistance", "-w": "--weight"},
    )

    habit = make_habit(
        name=name,
        category=category,
        resistance=resistance,
        weight_in_qhe=weight,
    )
    habits.upsert(habit)
    if json:
        typer.echo(format_as_json(habit))
    else:
        cat_color = CATEGORY_COLOR.get(category.value, "white")
        console.print(f"  [bold {cat_color}]✓[/bold {cat_color}] Hábito criado: [bold]{habit.name}[/bold]")
        console.print(f"    [dim]id: {habit.id}  ·  {category.value}  ·  R={resistance}  W={weight}[/dim]")


@app.command(name="list")
def list_habits(
    category: HabitCategory | None = typer.Option(None, "--category", "-c", help="Filtrar por categoria"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Listar hábitos salvos — Rich Table."""
    filters = {}
    if category:
        filters["category"] = category
    items = habits.list(filters or None)

    if json:
        typer.echo(format_as_json(items))
        return
    if not items:
        console.print("[yellow]⚠ Nenhum hábito cadastrado.[/yellow] Use [bold]habit create[/bold].")
        return

    items_sorted = sorted(items, key=lambda h: h.weight_in_qhe, reverse=True)

    table = Table(
        title=f"[bold green]✅ Habits ({len(items)})[/bold green]",
        show_header=True,
        header_style="bold green",
        box=None,
        padding=(0, 2),
    )
    table.add_column("Categoria", min_width=14)
    table.add_column("Nome", style="white", min_width=28)
    table.add_column("Resistência", min_width=22)
    table.add_column("Q_HE", min_width=20)
    table.add_column("ID", style="dim", min_width=20)

    for h in items_sorted:
        cat_value = h.category.value if hasattr(h.category, "value") else str(h.category)
        cat_color = CATEGORY_COLOR.get(cat_value, "white")
        icon = CATEGORY_ICON.get(cat_value, "·")
        # Resistance bar
        r_bar = progress_bar(h.resistance, 10, width=10, color="warn", label=f"{h.resistance}/10")
        # Weight bar (0-1 → 0-100%)
        w_pct = int(h.weight_in_qhe * 100)
        w_bar = progress_bar(h.weight_in_qhe, 1.0, width=10, color="energy", label=f"{w_pct}%")

        table.add_row(
            f"[{cat_color}]{icon} {cat_value}[/{cat_color}]",
            h.name,
            r_bar,
            w_bar,
            h.id,
        )

    console.print(table)
