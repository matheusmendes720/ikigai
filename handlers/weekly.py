"""Weekly handler: weekly review script, optional metrics."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import typer
from life.cli.config import load_config
from life.cli.log import get_logger

app = typer.Typer(help="Weekly flow: weekly review, metrics.")
logger = get_logger("life.handlers.weekly")


def _run_life_cmd(args: list[str], cwd: Path) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "life.cli"] + args + ["--json"]
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
        data = None
        if r.stdout.strip():
            try:
                data = json.loads(r.stdout)
            except Exception:
                pass
        return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr, "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.command()
def run(
    skip_review: bool = typer.Option(False, "--skip-review", help="Skip weekly-review script"),
    skip_metrics: bool = typer.Option(False, "--skip-metrics"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Run weekly flow: weekly review + optional metrics."""
    cfg = load_config()
    root = cfg.root
    results: dict[str, Any] = {"review": None, "metrics": None, "errors": []}

    if not skip_review:
        logger.info("Weekly: running task weekly-review")
        out = _run_life_cmd(["task", "weekly-review"], root)
        results["review"] = out.get("data") or out
        if not out.get("ok"):
            results["errors"].append("review: " + (out.get("error") or out.get("stderr", "failed")))

    if not skip_metrics:
        logger.info("Weekly: running metrics")
        out = _run_life_cmd(["task", "metrics"], root)
        results["metrics"] = out.get("data") or out
        if not out.get("ok"):
            results["errors"].append("metrics: " + (out.get("error") or out.get("stderr", "failed")))

    if json_out:
        print(json.dumps(results))
    for err in results["errors"]:
        typer.echo(err, err=True)


weekly_handler = app
