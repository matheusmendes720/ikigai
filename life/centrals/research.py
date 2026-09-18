"""Research central: map, crawl, search."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from life.cli.config import load_config
from life.centrals.base import BaseCentral

app = typer.Typer(help="Research central: map URLs, crawl, search.")


def _run_research(module_args: list[str], json_out: bool = True) -> dict:
    cfg = load_config()
    path = cfg.get_submodule_path("research")
    if not path or not path.exists():
        return {"ok": False, "error": "research submodule not found"}
    return BaseCentral(config=cfg).run_cli(
        path, "research.cli", module_args, json_out=json_out
    )


@app.command("map")
def map_urls(
    url: str = typer.Argument(...),
    depth: int = typer.Option(2, "--depth", "-d"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """Map URL for crawling (research map)."""
    args = ["map", url, "--depth", str(depth)]
    if output:
        args += ["--output", str(output)]
    out = _run_research(args, json_out=json_out)
    if json_out:
        import json

        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command()
def crawl(
    sitemap_or_url: str = typer.Argument(...),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """Crawl from sitemap or URL (research crawl)."""
    args = ["crawl", sitemap_or_url]
    if output:
        args += ["--output", str(output)]
    out = _run_research(args, json_out=json_out)
    if json_out:
        import json

        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(...),
    backend: str = typer.Option("stub", "--backend", "-b"),
    json_out: bool = typer.Option(True, "--json/--no-json"),
):
    """Search research backend (research search)."""
    args = ["search", query, "--backend", backend]
    out = _run_research(args, json_out=json_out)
    if json_out:
        import json

        print(json.dumps(out.get("data") or out))
    else:
        if out.get("stdout"):
            typer.echo(out["stdout"])
        if not out.get("ok"):
            raise typer.Exit(1)


research_central = app
