"""Daily handler: task today, optional knowledge/research."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from life.cli.config import load_config
from life.cli.log import get_logger

app = typer.Typer(help="Daily flow: task today, optional centrals.")
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
    json_out: bool = typer.Option(False, "--json"),
):
    """Run daily flow: task today (and optionally more centrals)."""
    cfg = load_config()
    root = cfg.root
    results: dict[str, Any] = {"task": None, "errors": []}

    if not skip_task:
        logger.info("Daily: running task today")
        out = _run_life_cmd(["task", "today"], root)
        results["task"] = out.get("data") or out
        if not out.get("ok"):
            results["errors"].append(
                "task: " + (out.get("error") or out.get("stderr", "failed"))
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
        for err in results["errors"]:
            typer.echo(err, err=True)


daily_handler = app
