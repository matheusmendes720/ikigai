"""Demo CLI commands — seed / clear / show / week."""
from __future__ import annotations

import typer

from operational.cli.formatters import format_as_json
from operational.cli.seed import clear_demo_data, demo_stats, seed_demo_data

app = typer.Typer(help="Gerenciar dados de demonstração (7 dias PAV).")


@app.command()
def seed(
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Populate 7 days of realistic PAV mock data."""
    summary = seed_demo_data()
    if json:
        typer.echo(format_as_json({"status": "seeded", "summary": summary}))
    else:
        typer.echo(summary)


@app.command()
def clear(
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Remove all demo data."""
    msg = clear_demo_data()
    if json:
        typer.echo(format_as_json({"status": "cleared"}))
    else:
        typer.echo(msg)


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
