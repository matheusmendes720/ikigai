"""Demo CLI commands — seed / clear / show / week / csv."""
from __future__ import annotations

from typing import Any

import typer

from operational.cli.formatters import format_as_json
from operational.cli.seed import clear_demo_data, demo_stats, seed_demo_data
from operational.cli.state import (
    ajustes_finos,
    daily_reflections,
    day_contexts,
    habits,
    journals,
    lunch_records,
    policy_decisions,
    policy_setpoints,
    pomodoros,
    routine_logs,
    routines,
    sleep_records,
    time_blocks,
    transicoes,
)

app = typer.Typer(help="Gerenciar dados de demonstração (7 dias PAV).")


@app.command()
def seed(
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Populate 7 days of realistic PAV mock data."""
    if json:
        summary = seed_demo_data()
        typer.echo(format_as_json({"status": "seeded", "summary": summary}))
    else:
        from operational.cli.console import console
        with console.status("[cyan]Seeding 7 days of PAV mock data...[/]", spinner="dots"):
            summary = seed_demo_data()
        console.print(summary)


@app.command()
def clear(
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Remove all demo data."""
    if json:
        msg = clear_demo_data()
        typer.echo(format_as_json({"status": "cleared"}))
    else:
        from operational.cli.console import console
        with console.status("[yellow]Clearing all state...[/]", spinner="dots"):
            msg = clear_demo_data()
        console.print(msg)


@app.command()
def show(
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Show current data counts."""
    stats = demo_stats()
    if json:
        typer.echo(format_as_json({"entities": stats}))
    else:
        typer.echo(stats)


@app.command()
def week(
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Seed data and show weekly report."""
    seed_demo_data()
    from operational.cli.commands.report_cmd import app as report_app
    args = ["weekly"]
    if json:
        args.append("--json")
    report_app(args=args, standalone_mode=False)


@app.command()
def export_csv(
    path: str = typer.Argument(..., help="Destination CSV path"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Export all current state to a single CSV file (one row per entity)."""
    from pathlib import Path

    from operational.cli.csv_loader import export_to_csv

    rows: list[tuple[str, str, dict[str, Any]]] = []
    repos = {
        "routine": routines,
        "routine_log": routine_logs,
        "time_block": time_blocks,
        "journal_entry": journals,
        "habit": habits,
        "sleep_record": sleep_records,
        "pomodoro_round": pomodoros,
        "policy_decision": policy_decisions,
        "policy_setpoints": policy_setpoints,
        "ajuste_fino": ajustes_finos,
        "day_context": day_contexts,
        "daily_reflection": daily_reflections,
        "lunch_record": lunch_records,
        "transicao": transicoes,
    }
    for etype, repo in repos.items():
        for ent in repo:
            data = ent.model_dump(mode="python")
            rows.append((etype, str(ent.id), data))
    if json:
        written = export_to_csv(rows, Path(path))
        typer.echo(format_as_json({"path": str(path), "rows": written}))
    else:
        from operational.cli.console import console
        with console.status(f"[cyan]Exporting to {path}...[/]", spinner="dots"):
            written = export_to_csv(rows, Path(path))
        console.print(f"[green]OK[/] Exported {written} rows to {path}")


@app.command()
def import_csv(
    path: str = typer.Argument(..., help="Source CSV path"),
    replace: bool = typer.Option(False, "--replace", help="Clear existing state first"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Import entities from a CSV file into the current state."""
    from pathlib import Path

    from rich.progress import Progress

    from operational.cli.console import console
    from operational.cli.csv_loader import import_from_csv_as_entities

    csv_path = Path(path)
    if not csv_path.exists():
        typer.echo(f"CSV not found: {path}", err=True)
        raise typer.Exit(code=1)
    if replace:
        for repo in (
            routines,
            routine_logs,
            time_blocks,
            journals,
            habits,
            sleep_records,
            pomodoros,
            policy_decisions,
            policy_setpoints,
            ajustes_finos,
            day_contexts,
            daily_reflections,
            lunch_records,
            transicoes,
        ):
            repo.clear()
    groups = import_from_csv_as_entities(csv_path)
    repo_map = {
        "routine": routines,
        "routine_log": routine_logs,
        "time_block": time_blocks,
        "journal_entry": journals,
        "habit": habits,
        "sleep_record": sleep_records,
        "pomodoro_round": pomodoros,
        "policy_decision": policy_decisions,
        "policy_setpoints": policy_setpoints,
        "ajuste_fino": ajustes_finos,
        "day_context": day_contexts,
        "daily_reflection": daily_reflections,
        "lunch_record": lunch_records,
        "transicao": transicoes,
    }
    counts: dict[str, int] = {}
    with Progress(console=console, transient=True) as progress:
        for etype, entities in groups.items():
            if etype in repo_map:
                task = progress.add_task(f"  {etype}", total=len(entities))
                for ent in entities:
                    repo_map[etype].upsert(ent)
                    progress.update(task, advance=1)
                counts[etype] = len(entities)
    if json:
        typer.echo(format_as_json({"imported": counts}))
    else:
        typer.echo(f"Imported {sum(counts.values())} rows from {path}")
        for etype, n in counts.items():
            typer.echo(f"  {etype}: {n}")


@app.command()
def dataset(
    name: str | None = typer.Argument(None, help="Dataset name to use (synthetic/golden/production)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """List available datasets or set the active dataset for this session.

    Without arguments, lists all built-in datasets and shows the
    currently-active one (from TIME_TASKER_DATASET env var).
    With a name argument, prints the export command to switch.
    """
    import os

    from operational.cli.dataset_selector import list_datasets, resolve_dataset

    if name is None:
        current = os.environ.get("TIME_TASKER_DATASET", "production")
        all_datasets = list_datasets()
        if json:
            typer.echo(
                format_as_json(
                    {
                        "active": current,
                        "datasets": [
                            {
                                "name": d.name,
                                "path": str(d.csv_path),
                                "exists": d.csv_path.exists() if d.csv_path else False,
                                "description": d.description,
                            }
                            for d in all_datasets
                        ],
                    }
                )
            )
        else:
            typer.echo(f"Active dataset: {current}\n")
            for d in all_datasets:
                exists = "OK" if (not d.csv_path or d.csv_path.exists()) else "MISSING"
                typer.echo(f"  [{exists}] {d.name:12} — {d.description}")
                if d.csv_path:
                    typer.echo(f"               {d.csv_path}")
    else:
        ref = resolve_dataset(name)
        env_var = f"TIME_TASKER_DATASET={name}"
        if json:
            typer.echo(
                format_as_json(
                    {"dataset": name, "env_var": env_var, "path": str(ref.csv_path)}
                )
            )
        else:
            typer.echo(f"Dataset: {name}")
            typer.echo(f"  Path: {ref.csv_path}")
            typer.echo(f"  To activate: {env_var} operational home")
