"""v2 — Deep Agent / IKIGAI v2 Typer sub-app.

Three commands per plan §11.4:
  life v2 cycle       — invoke ikigai_maintainer_v2 LangGraph
  life v2 score      — call ikigai_score MCP observation wrapper
  life v2 regime     — call ikigai_regime MCP observation wrapper

Provenance: src/ikigai/src/agents/v2/graph.py  +  mcp_server/server.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console

# Ensure repo root is on sys.path so `from src.ikigai.src...` resolves.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

app = typer.Typer(help="IKIGAI v2 commands — cycle, score, regime")
console = Console()


# ---------------------------------------------------------------------------
# Helpers — import from ikigai source (resolved against repo root above)
# ---------------------------------------------------------------------------


def _load_handlers():
    """Lazily import handler functions + graph factory.

    Doing this at module level would cause ImportError if the repo root is not
    yet on sys.path (the CLI runner sets PYTHONPATH but conftest does it too).
    Splitting into a helper lets tests patch sys.path before first call.
    """
    # ikigai_score / ikigai_regime handlers (read vault, no math)
    from src.ikigai.src.mcp_server.server import (
        _handle_ikigai_score,
        _handle_ikigai_regime,
    )

    # ikigai_maintainer_v2 graph factory
    from src.ikigai.src.agents.v2.graph import make_v2_graph

    return _handle_ikigai_score, _handle_ikigai_regime, make_v2_graph


def _run_cycle() -> dict:
    """Compile and invoke ikigai_maintainer_v2 graph; return serialisable result."""
    _, _, make_v2_graph = _load_handlers()

    compiled = make_v2_graph()
    result = compiled.invoke({})
    # Return a serialisable slice (graph returns full IKIGAiStateDict)
    return {
        "graph": "ikigai_maintainer_v2",
        "entry_point": compiled._ikigai_entry_point,
        "nodes_visited": list(result.keys()) if isinstance(result, dict) else str(result),
        "error_type": result.get("error_type") if isinstance(result, dict) else None,
    }


def _run_score(date_str: str) -> dict:
    """Call ikigai_score handler; return parsed JSON dict."""
    _handle_ikigai_score, _, _ = _load_handlers()
    raw = _handle_ikigai_score({"date": date_str})
    return json.loads(raw)


def _run_regime(date_str: str) -> dict:
    """Call ikigai_regime handler; return parsed JSON dict."""
    _, _handle_ikigai_regime, _ = _load_handlers()
    raw = _handle_ikigai_regime({"date": date_str})
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command(name="cycle")
def cycle(
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
) -> None:
    """Invoke ikigai_maintainer_v2 LangGraph (observe → score → heuristics → … → commit)."""
    try:
        result = _run_cycle()
    except Exception as exc:
        console.print(f"[red]Graph error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        if result.get("error_type"):
            console.print(f"[yellow]Graph finished with error:[/yellow] {result['error_type']}")
        else:
            console.print("[green]Graph ikigai_maintainer_v2 invoked successfully.[/green]")
        console.print(f"[dim]Nodes visited:[/dim] {result.get('nodes_visited', [])}")


@app.command(name="score")
def score(
    date_arg: str = typer.Argument(
        "",
        help="Date to observe (YYYY-MM-DD). Defaults to today.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
) -> None:
    """Call ikigai_score MCP observation wrapper (reads vault/ikigai/meta/cycle_state/)."""
    date_str = date_arg or date.today().isoformat()
    try:
        result = _run_score(date_str)
    except Exception as exc:
        console.print(f"[red]Score observation error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        if "error" in result:
            console.print(f"[yellow]No cycle_state for {date_str}.[/yellow]")
            console.print(f"[dim]Hint: {result.get('hint', '')}[/dim]")
        else:
            console.print(f"[green]Score observation for {date_str}[/green]")
            scores = result.get("vector_scores", {})
            for vec, val in scores.items():
                if val:
                    console.print(f"  {vec:12s}: {val}")


@app.command(name="regime")
def regime(
    date_arg: str = typer.Argument(
        "",
        help="Date to observe (YYYY-MM-DD). Defaults to today.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
) -> None:
    """Call ikigai_regime MCP observation wrapper (reads vault/ikigai/meta/regime_state/)."""
    date_str = date_arg or date.today().isoformat()
    try:
        result = _run_regime(date_str)
    except Exception as exc:
        console.print(f"[red]Regime observation error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        if "error" in result:
            console.print(f"[yellow]No regime_state for {date_str}.[/yellow]")
            console.print(f"[dim]Hint: {result.get('hint', '')}[/dim]")
        else:
            console.print(f"[green]Regime observation for {date_str}[/green]")
            console.print(f"  regime_state: {result.get('regime_state', '?')}")
            console.print(f"  days_in_regime: {result.get('days_in_regime', '?')}")
            console.print(f"  q_he_score: {result.get('q_he_score', '?')}")


# Public alias so `from interfaces.cli.v2 import v2_app` matches __init__.py usage.
v2_app = app

if __name__ == "__main__":
    app()
