"""Daily handler: task today, finance report (day/week), optional knowledge/research."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from life.cli.config import load_config
from life.cli.log import get_logger

app = typer.Typer(help="Daily flow: task today, finance report, optional centrals.")
logger = get_logger("life.handlers.daily")


def _run_life_cmd(args: list[str], cwd: Path) -> dict[str, Any]:
    """Run life CLI subcommand (e.g. life task today, life finance report)."""
    cmd = [sys.executable, "-m", "life.cli"] + args + ["--json"]
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
        data = None
        if r.stdout.strip():
            try:
                data = json.loads(r.stdout)
            except Exception:
                pass
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "data": data,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.command()
def run(
    skip_task: bool = typer.Option(False, "--skip-task", help="Skip task central"),
    skip_finance: bool = typer.Option(
        False, "--skip-finance", help="Skip finance report"
    ),
    finance_period: str = typer.Option("day", "--finance-period", help="day|week"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Run daily flow: task today + finance report (and optionally more)."""
    cfg = load_config()
    root = cfg.root
    results = {"task": None, "finance": None, "errors": []}

    if not skip_task:
        logger.info("Daily: running task today")
        out = _run_life_cmd(["task", "today"], root)
        results["task"] = out.get("data") or out
        if not out.get("ok"):
            results["errors"].append(
                "task: " + (out.get("error") or out.get("stderr", "failed"))
            )

    if not skip_finance:
        logger.info("Daily: running finance report")
        out = _run_life_cmd(["finance", "report", "--period", finance_period], root)
        results["finance"] = out.get("data") or out
        if not out.get("ok"):
            results["errors"].append(
                "finance: " + (out.get("error") or out.get("stderr", "failed"))
            )

    if json_out:
        print(json.dumps(results))
    else:
        if (
            results["task"]
            and isinstance(results["task"], dict)
            and results["task"].get("stdout")
        ):
            typer.echo(results["task"]["stdout"])
        if results["finance"] and isinstance(results["finance"], dict):
            d = results["finance"].get("data") or results["finance"]
            if isinstance(d, dict):
                typer.echo(
                    f"Finance ({finance_period}): total={d.get('total', 'n/a')} count={d.get('count', 0)}"
                )
        for err in results["errors"]:
            typer.echo(err, err=True)


daily_handler = app
