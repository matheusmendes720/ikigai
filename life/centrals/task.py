"""Task central: Taskwarrior, daily/weekly review scripts, metrics."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from life.cli.config import load_config

from .base import BaseCentral

app = typer.Typer(help="Task central: Taskwarrior, reviews, metrics.")

TASKDOG_BIN = "taskdog"


def _run_taskdog(args: list[str]) -> dict[str, Any]:
    """Run taskdog CLI and return {ok, stdout, stderr, error?}.

    M83: Added as the canonical task creation/completion path now that
    taskdog-server (HTTP daemon, port 8000) is the project's task store
    (replaced Taskwarrior per user direction).
    """
    cfg = load_config()
    cmd = [TASKDOG_BIN] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout,
            "stderr": r.stderr,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "error": f"{TASKDOG_BIN} not found on PATH. Install with: pipx install taskdog",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.command()
def add(
    name: str = typer.Argument(..., help="Task title"),
    priority: Optional[int] = typer.Option(None, "-p", "--priority", help="1-10, higher = more urgent"),
    tag: list[str] = typer.Option([], "-t", "--tag", help="Tags (repeatable)"),
    estimate: Optional[float] = typer.Option(None, "-e", "--estimate", help="Estimated hours"),
    deadline: Optional[str] = typer.Option(None, "-D", "--deadline", help="YYYY-MM-DD HH:MM:SS"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Add a task to taskdog-server (M83: daily-use primary path)."""
    args = ["add", name]
    if priority is not None:
        args += ["--priority", str(priority)]
    if estimate is not None:
        args += ["--estimate", str(estimate)]
    if deadline:
        args += ["--deadline", deadline]
    for t in tag:
        args += ["--tag", t]
    out = _run_taskdog(args)
    if json_out:
        import json

        print(json.dumps(out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"].rstrip())
        if not out.get("ok"):
            if out.get("error"):
                typer.echo(out["error"], err=True)
            else:
                typer.echo(out.get("stderr", "taskdog add failed"), err=True)
            raise typer.Exit(1)


@app.command()
def start(
    task_id: int = typer.Argument(..., help="Task ID"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Start a task (PENDING → IN_PROGRESS)."""
    out = _run_taskdog(["start", str(task_id)])
    if json_out:
        import json

        print(json.dumps(out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"].rstrip())
        if not out.get("ok"):
            typer.echo(out.get("stderr") or out.get("error", "taskdog start failed"), err=True)
            raise typer.Exit(1)


@app.command()
def done(
    task_id: int = typer.Argument(..., help="Task ID"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Mark task as completed (requires IN_PROGRESS first)."""
    out = _run_taskdog(["done", str(task_id)])
    if json_out:
        import json

        print(json.dumps(out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"].rstrip())
        if not out.get("ok"):
            typer.echo(out.get("stderr") or out.get("error", "taskdog done failed"), err=True)
            raise typer.Exit(1)


@app.command()
def ls(
    json_out: bool = typer.Option(False, "--json"),
    q: Optional[str] = typer.Option(None, "--q", help="Filter query"),
):
    """List all tasks (from taskdog-server)."""
    args = ["list"]
    if q:
        args += ["--filter", q]
    out = _run_taskdog(args)
    if json_out:
        import json

        print(json.dumps(out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"].rstrip())
        if not out.get("ok"):
            typer.echo(out.get("stderr") or out.get("error", "taskdog list failed"), err=True)
            raise typer.Exit(1)


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
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "data": data,
        }
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
        # M66: Windows path → git-bash path; backslashes confuse bash.
        bash_script = str(script).replace("\\", "/")
        subprocess.run(["bash", bash_script], cwd=scripts, check=False)
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
        # M66: Windows path → git-bash path; backslashes confuse bash.
        bash_script = str(script).replace("\\", "/")
        subprocess.run(["bash", bash_script], cwd=scripts, check=False)
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

            print(
                json.dumps(
                    {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr}
                )
            )
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
