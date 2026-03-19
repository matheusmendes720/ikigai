"""Task central: Taskwarrior, daily/weekly review scripts, metrics."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from life.config import load_config

from .base import BaseCentral

app = typer.Typer(help="Task central: Taskwarrior, reviews, metrics.")

TASK_BIN = "task"


def _run_task(args: list[str], json_out: bool = False) -> dict[str, Any]:
    cfg = load_config()
    cmd = [TASK_BIN] + args
    if json_out:
        cmd.append("export")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = None
        if json_out and r.stdout.strip():
            try:
                import json
                data = json.loads(r.stdout)
            except Exception:
                pass
        return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr, "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.command()
def today(
    json_out: bool = typer.Option(False, "--json"),
):
    """Today's tasks (task list for today)."""
    out = _run_task(["list"], json_out=json_out)
    if json_out:
        import json
        print(json.dumps(out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command()
def daily_review(
    scripts_path: Optional[Path] = typer.Option(None, "--scripts"),
):
    """Run daily-review script (WSL bash or fallback)."""
    cfg = load_config()
    scripts = scripts_path or cfg.task_scripts
    script = scripts / "daily-review.sh"
    if not script.exists():
        typer.echo(f"Script not found: {script}", err=True)
        raise typer.Exit(1)
    try:
        subprocess.run(["bash", str(script)], cwd=scripts, check=False)
    except Exception as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)


@app.command()
def weekly_review(
    scripts_path: Optional[Path] = typer.Option(None, "--scripts"),
):
    """Run weekly-review script."""
    cfg = load_config()
    scripts = scripts_path or cfg.task_scripts
    script = scripts / "weekly-review.sh"
    if not script.exists():
        typer.echo(f"Script not found: {script}", err=True)
        raise typer.Exit(1)
    try:
        subprocess.run(["bash", str(script)], cwd=scripts, check=False)
    except Exception as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)


@app.command()
def metrics(
    scripts_path: Optional[Path] = typer.Option(None, "--scripts"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Run calculate-metrics.py."""
    cfg = load_config()
    scripts = scripts_path or cfg.task_scripts
    script = scripts / "calculate-metrics.py"
    if not script.exists():
        typer.echo(f"Script not found: {script}", err=True)
        raise typer.Exit(1)
    try:
        r = subprocess.run(
            [sys.executable, str(script)],
            cwd=scripts,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if json_out:
            import json
            print(json.dumps({"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr}))
        else:
            if r.stdout:
                typer.echo(r.stdout)
            if r.returncode != 0:
                raise typer.Exit(1)
    except Exception as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)


# For registration on main app
task_central = app
