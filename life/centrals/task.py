"""Task central: Taskwarrior, daily/weekly review scripts, metrics."""

from __future__ import annotations

import json as _json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

import typer
from life.cli.config import load_config

from .base import BaseCentral

app = typer.Typer(help="Task central: Taskwarrior, reviews, metrics.")

TASKDOG_BIN = "taskdog"
# M112: taskdog-server HTTP endpoint. Default port from M68 wiring.
TASKDOG_HTTP_URL = "http://127.0.0.1:8000"
# Env override (set to "0" or "false" to disable HTTP, force CLI subprocess).
ENABLE_HTTP = True


def _http_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON to taskdog-server and return parsed response."""
    req = urllib.request.Request(
        f"{TASKDOG_HTTP_URL}{path}",
        data=_json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return _json.loads(resp.read().decode("utf-8"))


def _http_get(path: str) -> dict[str, Any]:
    """GET JSON from taskdog-server."""
    req = urllib.request.Request(f"{TASKDOG_HTTP_URL}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return _json.loads(resp.read().decode("utf-8"))


def _http_patch(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """PATCH JSON to taskdog-server."""
    req = urllib.request.Request(
        f"{TASKDOG_HTTP_URL}{path}",
        data=_json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return _json.loads(resp.read().decode("utf-8"))


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


def _http_or_cli(
    http_fn: Any, cli_args: list[str]
) -> dict[str, Any]:
    """M112: Try HTTP first, fall back to CLI subprocess.

    Returns {"ok": bool, "stdout": str, "stderr": str, "error": str?, "transport": "http"|"cli"}.
    """
    if ENABLE_HTTP:
        try:
            result = http_fn()
            return {
                "ok": True,
                "stdout": _json.dumps(result),
                "stderr": "",
                "transport": "http",
            }
        except (urllib.error.URLError, ConnectionError, OSError) as e:
            # Server down — fall back to CLI subprocess.
            pass
        except Exception as e:
            return {"ok": False, "error": f"http_failed: {e}", "transport": "http"}
    # Fallback: subprocess CLI.
    return {**_run_taskdog(cli_args), "transport": "cli"}


@app.command()
def add(
    name: str = typer.Argument(..., help="Task title"),
    priority: Optional[int] = typer.Option(None, "-p", "--priority", help="1-10, higher = more urgent"),
    tag: list[str] = typer.Option([], "-t", "--tag", help="Tags (repeatable)"),
    estimate: Optional[float] = typer.Option(None, "-e", "--estimate", help="Estimated hours"),
    deadline: Optional[str] = typer.Option(None, "-D", "--deadline", help="YYYY-MM-DD HH:MM:SS"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Add a task to taskdog-server (M83: daily-use primary path).

    M112: Now uses HTTP to taskdog-server directly (faster than subprocess CLI).
    Falls back to `taskdog` CLI if HTTP server is unreachable.
    """
    payload: dict[str, Any] = {"name": name}
    if priority is not None:
        payload["priority"] = priority
    if estimate is not None:
        payload["estimate"] = estimate
    if deadline:
        payload["deadline"] = deadline
    if tag:
        payload["tags"] = tag

    def _http_add() -> dict[str, Any]:
        return _http_post("/api/v1/tasks", payload)

    cli_args = ["add", name]
    if priority is not None:
        cli_args += ["--priority", str(priority)]
    if estimate is not None:
        cli_args += ["--estimate", str(estimate)]
    if deadline:
        cli_args += ["--deadline", deadline]
    for t in tag:
        cli_args += ["--tag", t]
    out = _http_or_cli(_http_add, cli_args)
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
    """Start a task (PENDING → IN_PROGRESS).

    M112: HTTP-first, CLI-fallback.
    """
    def _http_start() -> dict[str, Any]:
        return _http_post(f"/api/v1/tasks/{task_id}/start", {})

    out = _http_or_cli(_http_start, ["start", str(task_id)])
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
    """Mark task as completed (requires IN_PROGRESS first).

    M112: HTTP-first, CLI-fallback.
    """
    def _http_done() -> dict[str, Any]:
        return _http_patch(f"/api/v1/tasks/{task_id}/complete", {})

    out = _http_or_cli(_http_done, ["done", str(task_id)])
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
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status (PENDING/IN_PROGRESS/COMPLETED)"),
    tags: list[str] = typer.Option([], "--tag", help="Filter by tag (repeatable)"),
):
    """List all tasks (from taskdog-server).

    M112: HTTP-first, CLI-fallback. Server supports `status` and `tags` filters.
    Free-text `q` is applied client-side after fetching.
    """
    def _http_ls() -> dict[str, Any]:
        from urllib.parse import quote, urlencode

        params: dict[str, str] = {}
        if status:
            params["status"] = status
        if tags:
            # taskdog-server accepts comma-separated tags OR repeated `tags` params.
            params["tags"] = ",".join(tags)
        path = "/api/v1/tasks"
        if params:
            path += "?" + urlencode(params)
        data = _http_get(path)
        # Client-side filter for free-text q (taskdog-server doesn't support it).
        if q and "tasks" in data:
            ql = q.lower()
            data["tasks"] = [
                t for t in data["tasks"]
                if ql in t.get("name", "").lower()
                or any(ql in tg.lower() for tg in t.get("tags", []))
            ]
        return data

    cli_args = ["list"]
    if q:
        cli_args += ["--filter", q]
    out = _http_or_cli(_http_ls, cli_args)
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
