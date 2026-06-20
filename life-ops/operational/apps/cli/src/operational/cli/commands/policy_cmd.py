"""Policy CLI commands."""
from __future__ import annotations

import typer

from operational.cli.formatters import format_as_json
from operational.cli.state import policy_decisions, policy_setpoints
from operational.entities.policy import PolicySetpoints
from operational.enums import PolicyState

app = typer.Typer(help="Manage policy setpoints and decisions.")


@app.command()
def setpoints(
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """View current policy setpoints."""
    items = policy_setpoints.list()
    if json:
        typer.echo(format_as_json(items))
    elif not items:
        typer.echo("No policy setpoints stored. Generating defaults...")
        for state in PolicyState:
            sp = PolicySetpoints.from_pav_defaults(state)
            policy_setpoints.upsert(sp)
            typer.echo(f"  {state.value}:")
            typer.echo(f"    hardwork_budget={sp.hardwork_budget_hours}h")
            typer.echo(f"    max_pomodoros_per_day={sp.max_pomodoros_per_day}")
            typer.echo(f"    sleep_target={sp.sleep_target_hours}h")
            typer.echo(f"    qhe_target={sp.qhe_target}")
    else:
        typer.echo(f"Policy setpoints ({len(items)}):")
        for sp in items:
            state = sp.state if hasattr(sp, "state") else "?"
            typer.echo(f"  State={state}: budget={sp.hardwork_budget_hours}h  "
                       f"sleep={sp.sleep_target_hours}h  qhe={sp.qhe_target}")


@app.command()
def decisions(
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """List recent policy decisions."""
    items = policy_decisions.list()
    if json:
        typer.echo(format_as_json(items))
    elif not items:
        typer.echo("No policy decisions yet.")
    else:
        typer.echo(f"Policy decisions ({len(items)}):")
        for d in items:
            typer.echo(f"  {d.date}  state={d.state}  severity={d.severity}  {d.rationale[:60]}")
