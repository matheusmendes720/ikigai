"""Built-in plugin: health check for submodules and scripts."""

from pathlib import Path
from typing import Any

import typer
from life.cli.config import load_config
from life.plugins.protocol import PluginProtocol

app = typer.Typer(help="Health: check submodules and paths.")


def _check() -> dict[str, Any]:
    cfg = load_config()
    out = {"submodules": {}, "task_scripts": None, "ok": True}
    for name, path in cfg.submodules.items():
        p = Path(path)
        exists = p.exists()
        out["submodules"][name] = {"path": str(p), "exists": exists}
        if not exists:
            out["ok"] = False
    out["task_scripts"] = {"path": str(cfg.task_scripts), "exists": cfg.task_scripts.exists()}
    if not out["task_scripts"]["exists"]:
        out["ok"] = False
    return out


class HealthCheckPlugin(PluginProtocol):
    name = "health_check"

    def register(self, app: typer.Typer) -> None:
        @app.command("health")
        def health(
            json_out: bool = typer.Option(False, "--json"),
        ):
            """Check submodule paths and task scripts."""
            data = _check()
            if json_out:
                import json
                print(json.dumps(data))
            else:
                for name, info in data["submodules"].items():
                    status = "ok" if info["exists"] else "MISSING"
                    typer.echo(f"  {name}: {status} ({info['path']})")
                ts = data["task_scripts"]
                status = "ok" if ts["exists"] else "MISSING"
                typer.echo(f"  task_scripts: {status} ({ts['path']})")
                if not data["ok"]:
                    raise typer.Exit(1)


PLUGIN = HealthCheckPlugin()
