"""Habit CLI — Rich Table listing."""
from __future__ import annotations

import typer
from rich.table import Table

from operational.cli._compat import make_console, maybe_print_input_summary, progress_bar
from operational.cli.formatters import format_as_json
from operational.cli.state import habits
from operational.cli.telemetry import get_logger, trace_command
from operational.enums import HabitCategory
from operational.meta.factories import make_habit

log = get_logger("habit_cmd")

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
    with trace_command(log, "habit.create", command="habit create") as ctx:
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
        ctx.info("habit.created", habit_id=habit.id, habit_name=habit.name, category=category.value)
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
    with trace_command(log, "habit.list", command="habit list") as ctx:
        filters = {}
        if category:
            filters["category"] = category
        items = habits.list(filters or None)
        ctx.info("habits.listed", count=len(items), category=category.value if category else None)

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

# ── Stats: aggregate stats from CSV ──────────────────────────────────────────

@app.command(name="stats")
def habit_stats(
    days: int = typer.Option(30, "--days", "-d", help="Lookback window in days"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Aggregate habit stats from CSV data — completion rates, H(t), streaks."""
    with trace_command(log, "habit.stats", command="habit stats", days=days) as ctx:
        from datetime import date, timedelta
        from pathlib import Path

        today = date.today()
        start = today - timedelta(days=days)

        # Load habit + habit_state CSVs
        csv_dir = Path(__file__).parent.parent.parent.parent.parent / "datasets" / "6month" / "csv"
        habit_rows = []
        state_rows = []
        if (csv_dir / "habit.csv").exists():
            import csv as _csv
            with (csv_dir / "habit.csv").open() as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    d = date.fromisoformat(row["date"][:10]) if row.get("date") else None
                    if d and start <= d <= today:
                        habit_rows.append(row)
        if (csv_dir / "habit_state.csv").exists():
            import csv as _csv
            with (csv_dir / "habit_state.csv").open() as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    d = date.fromisoformat(row["date"][:10]) if row.get("date") else None
                    if d and start <= d <= today:
                        state_rows.append(row)

        if not habit_rows:
            console.print(f"[yellow]No habit data in last {days} days.[/yellow]")
            return

        # Per-habit completion rate
        from collections import defaultdict
        by_name: dict[str, list] = defaultdict(list)
        for r in state_rows:
            name = r.get("habit_name", r.get("habit_id", "unknown"))
            by_name[name].append(r)

        table = Table(
            title=f"[bold cyan]Habit Stats — last {days} days[/bold cyan]",
            show_header=True,
            header_style="bold cyan",
            box=None,
            padding=(0, 2),
        )
        table.add_column("Habit", style="bold", min_width=24)
        table.add_column("Days Active", justify="right", min_width=12)
        table.add_column("Completed", justify="right", min_width=11)
        table.add_column("Rate", justify="right", min_width=8)
        table.add_column("Avg Streak", justify="right", min_width=11)
        table.add_column("Best Streak", justify="right", min_width=11)

        results = []
        for name, rows in sorted(by_name.items()):
            total = len(rows)
            completed = sum(1 for r in rows if str(r.get("completed", "")).lower() in ("1", "true", "yes"))
            rate = completed / total if total else 0
            streaks = [int(r.get("streak", 0)) for r in rows]
            avg_s = sum(streaks) / len(streaks) if streaks else 0
            best_s = max(streaks) if streaks else 0
            bar = "█" * int(rate * 10) + "░" * (10 - int(rate * 10))
            good_thresh, ok_thresh = 0.8, 0.5
            color = "green" if rate >= good_thresh else "yellow" if rate >= ok_thresh else "red"
            rate_str = f"[{color}]{bar}[/{color}] {rate:.0%}"
            results.append({
                "habit": name, "days_active": total, "completed": completed,
                "rate": rate, "avg_streak": round(avg_s, 1), "best_streak": best_s,
            })
            table.add_row(
                name[:24],
                str(total),
                str(completed),
                rate_str,
                f"{avg_s:.1f}",
                str(best_s),
            )

        ctx.info("habit.stats.computed", habits_count=len(results), days=days)
        console.print(table)
        if json:
            import json as _json
            typer.echo(_json.dumps(results, indent=2, default=str))


# ── Today: record habit state for today ──────────────────────────────────────

@app.command(name="today")
def habit_today(
    habit_id: str = typer.Argument(..., help="Habit ID (e.g. hab_sleep_8h)"),
    completed: bool = typer.Option(True, "--done/--miss", help="Mark as completed or missed"),
    effort: float = typer.Option(5.0, "--effort", "-e", help="Effort spent (1-10)"),
    notes: str = typer.Option("", "--notes", "-n", help="Optional notes"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Record today's habit state — completion, effort, notes."""
    with trace_command(log, "habit.today", command="habit today", habit_id=habit_id) as ctx:
        from datetime import date
        from operational.entities.habit import HabitState
        from operational.types import UEID

        today = date.today()
        h = habits.get(habit_id)
        if not h:
            console.print(f"[red]✗ Habit '{habit_id}' not found.[/red] Use `habit list` to see IDs.")
            return

        # Build HabitState for today
        state = HabitState(
            id=UEID(f"hs_{habit_id}_{today.strftime('%Y%m%d')}"),
            habit_id=habit_id,
            date=today,
            completed=completed,
            effort_minutes=effort,  # type: ignore[call-arg]
            notes=notes,
        )
        # Persist via state.habit_states if available
        from operational.cli.state import habit_states
        if hasattr(habit_states, "upsert"):
            habit_states.upsert(state)

        ctx.info("habit.today.recorded", habit_id=habit_id, completed=completed, effort=effort)
        if json:
            typer.echo(format_as_json(state))
        else:
            icon = "✅" if completed else "❌"
            color = "green" if completed else "red"
            console.print(f"  [{color}]{icon}[/{color}] [bold]{h.name}[/bold] — {'completed' if completed else 'missed'} today")
            if notes:
                console.print(f"    [dim]{notes}[/dim]")
