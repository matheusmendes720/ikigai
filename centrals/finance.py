"""Finance central: fin_ops (track, report, simulate, derivatives)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from life.config import load_config
from life.centrals.base import BaseCentral

app = typer.Typer(help="Finance central: fin_ops track, report, simulate, derivatives.")


def _run_fin_ops(args: list[str], json_out: bool = True) -> dict:
    cfg = load_config()
    path = cfg.get_submodule_path("fin_ops")
    if not path or not path.exists():
        return {"ok": False, "error": "fin_ops submodule not found"}
    return BaseCentral(config=cfg).run_cli(path, "fin_ops.cli", args, json_out=json_out)


@app.command()
def track(
    amount: float = typer.Option(0, "--amount"),
    category: str = typer.Option("other", "--category"),
    expense_type: str = typer.Option("opex", "--expense-type"),
    description: str = typer.Option("", "--desc"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """Record expense via fin_ops."""
    args = ["track", "--amount", str(amount), "--category", category, "--expense_type", expense_type]
    if description:
        args += ["--desc", description]
    out = _run_fin_ops(args, json_out=json_out)
    if json_out:
        import json
        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command()
def report(
    period: str = typer.Option("week", "--period"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """Finance report (fin_ops report)."""
    out = _run_fin_ops(["report", "--period", period], json_out=json_out)
    if json_out:
        import json
        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command()
def simulate(
    scenario: str = typer.Option("default", "--scenario"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """Run simulation (fin_ops simulate)."""
    out = _run_fin_ops(["simulate", "--scenario", scenario], json_out=json_out)
    if json_out:
        import json
        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command()
def derivatives(json_out: bool = typer.Option(True, "--json/--no-json")):
    """Opportunity evaluations (fin_ops derivatives)."""
    out = _run_fin_ops(["derivatives"], json_out=json_out)
    if json_out:
        import json
        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


finance_central = app
