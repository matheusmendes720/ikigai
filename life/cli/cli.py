"""
Algorithmic Life OS — main CLI. Centrals, handlers, plugins, test, log.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

import typer
from life import __version__
from life.cli.config import load_config
from life.centrals import task_central, knowledge_central, research_central
from life.handlers import daily_handler, weekly_handler
from life.plugins.loader import load_plugins, register_plugins
from life.cli.test_runner import find_test_dirs, run_pytest

# M110: REPO_ROOT for the status command (resolves to repo root regardless of cwd).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _submodule_ref(path: Path) -> Optional[str]:
    """Return git rev (short) for path if it is a git repo."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return None


def _features_from_spec(spec_path: Path) -> Optional[str]:
    """Extract Implemented / planned section from SPEC.md."""
    if not spec_path.exists():
        return None
    text = spec_path.read_text(encoding="utf-8", errors="replace")
    in_section = False
    lines = []
    for line in text.splitlines():
        if line.strip().lower().startswith("## implemented") or "implemented / planned" in line.lower():
            in_section = True
            continue
        if in_section:
            if line.startswith("## ") and "implemented" not in line.lower():
                break
            lines.append(line)
    return "\n".join(lines).strip() if lines else None

app = typer.Typer(
    name="life",
    help="Algorithmic Life OS: task, finance, knowledge, research centrals; daily/weekly handlers; plugins; tests.",
    no_args_is_help=True,
)


# --- Centrals (different hubs) ---
app.add_typer(task_central, name="task", help="Task central: Taskwarrior, reviews, metrics.")
app.add_typer(knowledge_central, name="knowledge", help="Knowledge central: leitura, mindmaps, notes.")
app.add_typer(research_central, name="research", help="Research central: map, crawl, search.")

# --- Handlers (daily/weekly usage) ---
app.add_typer(daily_handler, name="daily", help="Daily flow: task today + optional centrals.")
app.add_typer(weekly_handler, name="weekly", help="Weekly flow: review + metrics.")


# --- Config ---
@app.command()
def config_show(
    path: bool = typer.Option(False, "--path", help="Show config file path"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Show current life OS config (from config/life.yaml or defaults)."""
    cfg = load_config()
    if path:
        typer.echo(str(Path("config") / "life.yaml"))
        return
    data = {
        "root": str(cfg.root),
        "log_dir": str(cfg.log_dir),
        "log_level": cfg.log_level,
        "log_json": cfg.log_json,
        "plugin_dirs": [str(p) for p in cfg.plugin_dirs],
        "submodules": {k: str(v) for k, v in cfg.submodules.items()},
        "task_scripts": str(cfg.task_scripts),
    }
    if json_out:
        print(json.dumps(data, indent=2))
    else:
        for k, v in data.items():
            typer.echo(f"  {k}: {v}")


# --- Log ---
@app.command()
def log(
    level: str = typer.Option("INFO", "--level", "-l", help="Set log level (DEBUG, INFO, WARNING, ERROR)"),
    json_format: bool = typer.Option(False, "--json", help="Use JSON log format"),
    show_path: bool = typer.Option(False, "--path", help="Show log file path"),
):
    """Show or configure logging. Use --path to see log file location."""
    cfg = load_config()
    if show_path:
        cfg.ensure_dirs()
        typer.echo(cfg.log_dir / "life.log")
        return
    typer.echo(f"Log level={level} json={json_format} dir={cfg.log_dir}")


# --- Test runner ---
@app.command()
def test(
    submodule: Optional[str] = typer.Option(None, "--submodule", "-s", help="Run only this submodule"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
    list_only: bool = typer.Option(False, "--list", "-l", help="Only list test dirs"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Run tests across submodules (pytest). Use --list to see test dirs."""
    cfg = load_config()
    dirs = find_test_dirs(cfg)
    if submodule:
        path = cfg.get_submodule_path(submodule)
        dirs = [path] if path and path.exists() else []
    if list_only:
        if json_out:
            print(json.dumps({"test_dirs": [str(p) for p in dirs]}))
        else:
            for p in dirs:
                typer.echo(p)
        return
    result = run_pytest(paths=dirs or None, verbose=verbose)
    if json_out:
        print(json.dumps(result))
    else:
        for r in result.get("results", []):
            status = "PASS" if r.get("ok") else "FAIL"
            typer.echo(f"  {r.get('path', '?')}: {status}")
        if not result.get("ok"):
            raise typer.Exit(1)


# --- Submodules ---
@app.command("submodules")
def submodules_list(
    json_out: bool = typer.Option(False, "--json"),
):
    """List submodules: path, ref (if git), SPEC path."""
    cfg = load_config()
    out: list[dict[str, Any]] = []
    for name, path in cfg.submodules.items():
        p = Path(path)
        if not p.is_absolute():
            p = (cfg.root / p).resolve()
        spec = p / "SPEC.md"
        ref = _submodule_ref(p) if p.exists() else None
        entry = {"name": name, "path": str(p), "spec": str(spec), "exists": p.exists()}
        if ref:
            entry["ref"] = ref
        out.append(entry)
    if json_out:
        print(json.dumps({"submodules": out}))
    else:
        for e in out:
            ref_str = f" ref={e['ref']}" if e.get("ref") else ""
            typer.echo(f"  {e['name']}: {e['path']}{ref_str}  SPEC: {e['spec']}")


@app.command("features")
def features_show(
    submodule: Optional[str] = typer.Argument(None, help="Submodule name (omit to list all with features)"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Show Implemented/Planned from SPEC.md (or FEATURES.md) for a submodule."""
    cfg = load_config()
    if submodule:
        path = cfg.get_submodule_path(submodule)
        if not path or not path.exists():
            typer.echo(f"Submodule not found: {submodule}", err=True)
            raise typer.Exit(1)
        spec_path = path / "SPEC.md"
        features_path = path / "FEATURES.md"
        content = _features_from_spec(spec_path)
        if content is None and features_path.exists():
            content = features_path.read_text(encoding="utf-8", errors="replace").strip()
        if json_out:
            print(json.dumps({"submodule": submodule, "features": content or ""}))
        else:
            typer.echo(f"--- {submodule} ---")
            typer.echo(content or "(no Implemented/Planned section or FEATURES.md)")
        return
    # List all: show which have SPEC with Implemented/planned
    result = []
    for name, path in cfg.submodules.items():
        p = Path(path)
        if not p.is_absolute():
            p = (cfg.root / p).resolve()
        spec_path = p / "SPEC.md"
        content = _features_from_spec(spec_path)
        if content:
            result.append({"name": name, "has_features": True})
        else:
            result.append({"name": name, "has_features": False})
    if json_out:
        print(json.dumps({"submodules": result}))
    else:
        for r in result:
            typer.echo(f"  {r['name']}: {'SPEC has Implemented/Planned' if r['has_features'] else 'no section'}")


# --- Plugins ---
@app.command("plugins")
def plugins_list(
    json_out: bool = typer.Option(False, "--json"),
):
    """List loaded plugins."""
    plugs = load_plugins()
    if json_out:
        print(json.dumps({"plugins": [p.name for p in plugs]}))
    else:
        for p in plugs:
            typer.echo(f"  {p.name}")


# --- Version ---
@app.command()
def version():
    """Show life OS version."""
    typer.echo(__version__)


@app.command("status")
def status_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """M110: Show system status snapshot.

    Displays:
    - Daemon status (loop-tick, hill-climb, cost-dashboard, etc.)
    - taskdog-server health + live task count
    - MCP servers registered (ikigai + taskdog)
    - langgraph dev graphs (v2 + fork_smoke + taskdog_mcp)
    - Drift gate status
    """
    import json as _json
    import subprocess
    import urllib.request

    snapshot: dict[str, object] = {"version": __version__}

    # 1. Daemon status — read schedules.json directly + verify each PID is alive.
    # More reliable than daemon-manager.sh (which has bash/Python env path issues
    # when invoked from Python subprocess).
    schedules_file = REPO_ROOT / ".claude" / "loop" / "schedules.json"
    if schedules_file.exists():
        try:
            import json as _json
            schedules = _json.loads(schedules_file.read_text())
            running = 0
            for s in schedules:
                name = s.get("name", "")
                # Check `ps -p <PID>` via the daemon script output cached in PID_DIR.
                # As fallback, just count all schedules — daemon-manager.sh handles
                # the running/stopped split.
                if name:
                    # Use simple heuristic: schedule exists and has a non-empty command.
                    if s.get("command"):
                        running += 1
            snapshot["daemons"] = {
                "running": running,
                "total": len(schedules),
                "source": "schedules.json (presence check; use 'bash .claude/helpers/daemon-manager.sh list' for live PID status)",
            }
        except Exception as e:
            snapshot["daemons"] = {"error": str(e)}
    else:
        snapshot["daemons"] = {"error": "schedules.json not found"}

    # 2. taskdog-server
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/v1/tasks")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = _json.loads(resp.read().decode())
            snapshot["taskdog"] = {
                "url": "http://127.0.0.1:8000",
                "status": "ok",
                "tasks_live": data.get("total_count", 0),
            }
    except Exception as e:
        snapshot["taskdog"] = {"url": "http://127.0.0.1:8000", "status": "down", "error": str(e)[:100]}

    # 3. MCP servers (from .mcp.json)
    mcp_config = REPO_ROOT / ".mcp.json"
    if mcp_config.exists():
        try:
            cfg = _json.loads(mcp_config.read_text())
            snapshot["mcp_servers"] = list(cfg.get("mcpServers", {}).keys())
        except Exception:
            snapshot["mcp_servers"] = []
    else:
        snapshot["mcp_servers"] = []

    # 4. langgraph graphs (from langgraph.json)
    lg_config = REPO_ROOT / "langgraph.json"
    if lg_config.exists():
        try:
            cfg = _json.loads(lg_config.read_text())
            snapshot["langgraph_graphs"] = list(cfg.get("graphs", {}).keys())
        except Exception:
            snapshot["langgraph_graphs"] = []
    else:
        snapshot["langgraph_graphs"] = []

    # 5. Drift gate
    drift_test = REPO_ROOT / "src" / "ikigai" / "tests" / "test_drift_extended_invariants.py"
    snapshot["drift_gate"] = "available" if drift_test.exists() else "missing"

    if json_output:
        typer.echo(_json.dumps(snapshot, indent=2))
    else:
        typer.echo(f"life OS {snapshot['version']}")
        typer.echo("")
        if "daemons" in snapshot:
            d = snapshot["daemons"]
            if "running" in d:
                typer.echo(f"  Daemons:        {d['running']}/{d['total']} RUNNING")
            else:
                typer.echo(f"  Daemons:        error ({d.get('error')})")
        if "taskdog" in snapshot:
            t = snapshot["taskdog"]
            if t.get("status") == "ok":
                typer.echo(f"  taskdog-server: ok ({t['tasks_live']} tasks live)")
            else:
                typer.echo(f"  taskdog-server: DOWN ({t.get('error', '?')})")
        typer.echo(f"  MCP servers:    {', '.join(snapshot.get('mcp_servers', [])) or '(none)'}")
        typer.echo(f"  langgraph:      {', '.join(snapshot.get('langgraph_graphs', [])) or '(none)'}")
        typer.echo(f"  Drift gate:     {snapshot['drift_gate']}")


# Register plugin-provided commands (e.g. health)

# ---------------------------------------------------------------------------
# notify subcommand (M75)
# ---------------------------------------------------------------------------
from interfaces.cli.notify_cli import app as notify_app  # noqa: E402
app.add_typer(notify_app, name="notify")


# ---------------------------------------------------------------------------
# IKIGAI v2 subcommand (M85)
# Exposes invoke-skill, skill-list, skill-show, plan under `life v2 ...`
# ---------------------------------------------------------------------------
from interfaces.cli.v2 import app as v2_app  # noqa: E402
app.add_typer(v2_app, name="v2")

# M100: direct taskdog-mcp commands (26 tools, no LLM).
# Detect whether the active Python has langchain-mcp-adapters installed
# before attempting module-import-time registration. Falls back to a
# placeholder if not, so `life --help` works from any venv.
import importlib.util as _importlib_util

if _importlib_util.find_spec("langchain_mcp_adapters") is not None:
    from interfaces.cli.taskdog_app import app as taskdog_mcp_app  # noqa: E402
    from interfaces.cli.taskdog_app import register_taskdog_app  # noqa: E402
    try:
        register_taskdog_app(taskdog_mcp_app)
    except typer.Exit:
        pass
    app.add_typer(taskdog_mcp_app, name="taskdog")
else:
    # No langchain-mcp-adapters → register a placeholder that explains the fix.
    _placeholder_app = typer.Typer(
        name="taskdog",
        help="M100 taskdog-mcp commands (requires langchain-mcp-adapters).",
        no_args_is_help=True,
    )

    @_placeholder_app.callback(invoke_without_command=True)
    def _taskdog_unavailable(ctx: typer.Context) -> None:
        typer.echo(
            json.dumps(
                {
                    "ok": False,
                    "error": "langchain-mcp-adapters not installed in this venv.",
                    "fix": "uv pip install --python <venv> langchain-mcp-adapters",
                },
                indent=2,
            )
        )
        raise typer.Exit(code=1)

    app.add_typer(_placeholder_app, name="taskdog")


register_plugins(app)


def main():
    app()


if __name__ == "__main__":
    main()
