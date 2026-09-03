"""IKIGAI v2 graph commands (Phase 8.2+) — surface PAV intentions as pt-BR suggestions.

Registered as a Typer sub-app of the main `app` in interfaces.cli.__init__.
Uses IKIGAI_FAKE_LLM=1 so no real LLM calls are made from the CLI.

Commands
--------
suggest : Display PAV intention suggestions (3-5 pt-BR recommendations)
cycle   : Run IKIGAI v2 graph end-to-end (8-node LangGraph)
score   : Read PAV-written cycle_state and emit passion-score observation
regime  : Read PAV-written regime_state and emit regime observation

Architecture invariants
-----------------------
- Interfaces READ vault only — never write to vault/
- vault_write is the SOLE vault writer (MCP tool)
- No PAV math execution in interface code
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date as _date
from pathlib import Path

import typer

v2_app = typer.Typer(help="IKIGAI v2 graph commands (Phase 8.2+)")


def _get_v2_src() -> Path:
    """Locate ikigai/src under the repo root."""
    cli_root = Path(__file__).parent.parent.parent  # interfaces/cli/ → life/
    return cli_root / "src" / "ikigai" / "src"


def _vault_root() -> Path:
    """Resolve vault root: env override or default 'vault'."""
    repo_root = Path(__file__).parent.parent.parent
    return Path(os.environ.get("IKIGAI_VAULT_ROOT", str(repo_root / "vault")))


def _ensure_fake_llm() -> None:
    """CLI defaults to fake-LLM mode unless user explicitly opts in to real LLM."""
    os.environ.setdefault("IKIGAI_FAKE_LLM", "1")


@v2_app.command("suggest")
def v2_suggest(
    date: str = typer.Option("", help="Date (YYYY-MM-DD); default = today"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Display user-facing PAV intention suggestions (3-5 pt-BR recommendations)."""
    _ensure_fake_llm()

    v2_src = _get_v2_src()
    if str(v2_src) not in sys.path:
        sys.path.insert(0, str(v2_src))

    from ikigai.src.agents.v2.prompts.surface_pav_intentions import (
        render_surface_pav_intentions,
    )

    state: dict[str, str] = {"vault_root": str(_vault_root())}
    if date:
        state["date"] = date

    result = render_surface_pav_intentions(state)
    suggestions = result.get("suggestions", [])

    if json_output:
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if not suggestions:
        typer.echo("Nenhuma sugestao disponivel para esta data.")
        return

    typer.echo(f"Sugestoes PAV ({len(suggestions)}):")
    for i, s in enumerate(suggestions, 1):
        typer.echo(f"  {i}. {s}")


@v2_app.command("cycle")
def v2_cycle(
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run", help="Run graph in stub mode (default: dry run)"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output full graph state as JSON"
    ),
) -> None:
    """Run IKIGAI v2 graph end-to-end (8-node LangGraph).

    Defaults to dry-run mode (IKIGAI_FAKE_LLM=1). Use --no-dry-run for a
    real cycle (requires live LLM and MCP gateway).
    """
    _ensure_fake_llm()

    v2_src = _get_v2_src()
    if str(v2_src) not in sys.path:
        sys.path.insert(0, str(v2_src))

    try:
        from agents.v2.graph import make_v2_graph

        graph = make_v2_graph()
        initial_state = {
            "cycle_id": "cli-dry-run",
            "last_step": "init",
            "vault_root": str(_vault_root()),
        }
        result = graph.invoke(initial_state)

        if json_output:
            typer.echo(
                json.dumps(dict(result), indent=2, default=str, ensure_ascii=False)
            )
        else:
            typer.echo(
                f"OK Cycle dry-run complete (last_step={result.get('last_step', '?')})"
            )
            commit = result.get("commit_summary", "(none)")
            typer.echo(f"  commit_summary: {commit}")
    except Exception as exc:
        typer.echo(f"FAIL Cycle failed: {type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(code=1)


@v2_app.command("score")
def v2_score(
    date: str = typer.Option("", help="Date (YYYY-MM-DD); default = today"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Read PAV-written cycle_state and emit passion-score observation.

    Reads vault/ikigai/meta/cycle_state/{date}.md (PAV-written).
    Emits passion_score (0-100) + rationale via prompt chain.
    """
    _ensure_fake_llm()

    if not date:
        date = _date.today().isoformat()

    v2_src = _get_v2_src()
    if str(v2_src) not in sys.path:
        sys.path.insert(0, str(v2_src))

    try:
        from agents.v2.prompts.score_passion_observation import (
            render_score_passion_observation,
        )

        state = {"date": date, "vault_root": str(_vault_root())}
        result = render_score_passion_observation(state)

        if json_output:
            typer.echo(
                json.dumps({"date": date, **result}, indent=2, ensure_ascii=False)
            )
        else:
            typer.echo(f"[PAV passion observation for {date}]")
            for key, val in result.items():
                if key != "rationale":
                    typer.echo(f"  {key}: {val}")
            if "rationale" in result:
                typer.echo(f"  rationale: {result['rationale']}")
    except Exception as exc:
        typer.echo(f"FAIL Score failed: {type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(code=1)


@v2_app.command("regime")
def v2_regime(
    date: str = typer.Option("", help="Date (YYYY-MM-DD); default = today"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Read PAV-written regime_state and emit regime observation.

    Reads vault/ikigai/meta/cycle_state/{date}.md (PAV-written).
    Emits regime (PUSH|MAINTAIN|REDUCE|RECOVER) + rationale via prompt chain.
    """
    _ensure_fake_llm()

    if not date:
        date = _date.today().isoformat()

    v2_src = _get_v2_src()
    if str(v2_src) not in sys.path:
        sys.path.insert(0, str(v2_src))

    try:
        from agents.v2.prompts.heuristics_regime_observation import (
            render_heuristics_regime_observation,
        )

        state = {"date": date, "vault_root": str(_vault_root())}
        result = render_heuristics_regime_observation(state)

        if json_output:
            typer.echo(
                json.dumps({"date": date, **result}, indent=2, ensure_ascii=False)
            )
        else:
            typer.echo(f"[PAV regime observation for {date}]")
            for key, val in result.items():
                typer.echo(f"  {key}: {val}")
    except Exception as exc:
        typer.echo(f"FAIL Regime failed: {type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(code=1)
