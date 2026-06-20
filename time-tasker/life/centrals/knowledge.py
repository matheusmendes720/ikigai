"""Knowledge central: leitura, mindmaps, notes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from life.cli.config import LifeConfig, load_config
from life.centrals.base import BaseCentral

app = typer.Typer(help="Knowledge central: leitura, mindmaps, notes.")


def _run_sub(
    cfg: LifeConfig, name: str, module: str, args: list[str], json_out: bool = True
) -> dict:
    path = cfg.get_submodule_path(name)
    if not path or not path.exists():
        return {"ok": False, "error": f"Submodule {name} not found"}
    return BaseCentral(config=cfg).run_cli(path, module, args, json_out=json_out)


@app.command()
def read(
    path: str = typer.Argument(...),
    format: Optional[str] = typer.Option(None, "--format", "-f"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """Read file (leitura read)."""
    cfg = load_config()
    args = ["read", path]
    if format:
        args += ["--format", format]
    out = _run_sub(cfg, "leitura", "leitura.cli", args, json_out=json_out)
    if json_out:
        import json

        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command("list-sections")
def list_sections(
    path: str = typer.Argument(...),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """List sections (leitura list)."""
    cfg = load_config()
    out = _run_sub(cfg, "leitura", "leitura.cli", ["list", path], json_out=json_out)
    if json_out:
        import json

        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command()
def note_add(
    content: str = typer.Argument(...),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    tags: Optional[str] = typer.Option(None, "--tags"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """Add note (notes add)."""
    cfg = load_config()
    args = ["add", content]
    if title:
        args += ["--title", title]
    if tags:
        args += ["--tags", tags]
    out = _run_sub(cfg, "notes", "notes.cli", args, json_out=json_out)
    if json_out:
        import json

        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command()
def note_list(
    tags: Optional[str] = typer.Option(None, "--tags"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """List notes (notes list)."""
    cfg = load_config()
    args = ["list"]
    if tags:
        args += ["--tags", tags]
    out = _run_sub(cfg, "notes", "notes.cli", args, json_out=json_out)
    if json_out:
        import json

        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command()
def mindmap_phase0(
    source_path: str = typer.Argument(...),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """Inspect source for mindmap (mindmaps phase0)."""
    cfg = load_config()
    args = ["phase0", source_path]
    if output:
        args += ["--output", str(output)]
    out = _run_sub(cfg, "mindmaps", "mindmaps.cli", args, json_out=json_out)
    if json_out:
        import json

        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command()
def mindmap_phase1(
    index_or_source: str = typer.Argument(...),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """Build mindmap (mindmaps phase1)."""
    cfg = load_config()
    args = ["phase1", index_or_source]
    if output:
        args += ["--output", str(output)]
    out = _run_sub(cfg, "mindmaps", "mindmaps.cli", args, json_out=json_out)
    if json_out:
        import json

        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


knowledge_central = app
