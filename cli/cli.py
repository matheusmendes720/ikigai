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
from life.config import load_config
from life.centrals import task_central, finance_central, knowledge_central, research_central
from life.handlers import daily_handler, weekly_handler
from life.plugins.loader import load_plugins, register_plugins
from life.test_runner import find_test_dirs, run_pytest


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
app.add_typer(finance_central, name="finance", help="Finance central: fin_ops.")
app.add_typer(knowledge_central, name="knowledge", help="Knowledge central: leitura, mindmaps, notes.")
app.add_typer(research_central, name="research", help="Research central: map, crawl, search.")

# --- Handlers (daily/weekly usage) ---
app.add_typer(daily_handler, name="daily", help="Daily flow: task today + finance report.")
app.add_typer(weekly_handler, name="weekly", help="Weekly flow: review + finance + metrics.")


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


# Register plugin-provided commands (e.g. health)
register_plugins(app)


def main():
    app()


if __name__ == "__main__":
    main()
