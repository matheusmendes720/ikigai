"""v2 — Deep Agent / IKIGAI v2 Typer sub-app.

Eight commands per plan §11.4 + Wave 2 W2.3:
  life v2 cycle       — invoke ikigai_maintainer_v2 LangGraph
  life v2 score       — call render_score_passion_observation prompt chain
  life v2 regime      — call render_heuristics_regime_observation prompt chain
  life v2 suggest     — call render_surface_pav_intentions prompt chain (W2.1)
  life v2 daily       — ikigai-daily skill orchestrator (W2.3)
  life v2 weekly      — ikigai-weekly skill orchestrator (W2.3)
  life v2 monthly     — ikigai-monthly skill orchestrator (W2.3)
  life v2 quarterly   — ikigai-quarterly skill orchestrator (W2.3)

Provenance: src/ikigai/src/agents/v2/graph.py  +  mcp_server/server.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console

# Ensure repo root is on sys.path so `from src.ikigai.src...` resolves.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

app = typer.Typer(help="IKIGAI v2 commands — cycle, score, regime, suggest, daily, weekly, monthly, quarterly")
console = Console()


# ---------------------------------------------------------------------------
# Helpers — import from ikigai source (resolved against repo root above)
# ---------------------------------------------------------------------------


def _load_handlers():
    """Lazily import handler functions + graph factory + prompt renderers.

    Doing this at module level would cause ImportError if the repo root is not
    yet on sys.path (the CLI runner sets PYTHONPATH but conftest does it too).
    Splitting into a helper lets tests patch sys.path before first call.

    Returns 5-tuple (per v2 architecture per ADR-013):
        (score_handler, regime_handler,
         render_score_passion, render_heuristics_regime, render_surface_pav)

    The graph factory is loaded lazily per-command via `_load_graph_factory()`
    because it transitively imports v2 nodes that use a legacy import path
    (`src.ikigai.src.agents.v2.state`) which conflicts with the v2 namespace
    package layout used by the prompt renderers.

    - score_handler / regime_handler: MCP observation wrappers (legacy fallback,
      may be None if the legacy import path is unavailable in the active venv).
    - render_*: prompt-chain renderers (v2 architecture per Plan §11.4;
      canonical path per ADR-013 planner-only — agent layer must not execute
      math/observation tools directly).
    """
    # v2 prompt-chain renderers (preferred path per ADR-013 planner-only).
    # Imported first because they are the canonical v2 surface.
    from agents.v2.prompts.score_passion_observation import (
        render_score_passion_observation,
    )
    from agents.v2.prompts.heuristics_regime_observation import (
        render_heuristics_regime_observation,
    )
    from agents.v2.prompts.surface_pav_intentions import (
        render_surface_pav_intentions,
    )

    # Legacy MCP observation handlers — imported lazily + tolerantly. These use
    # the `src.ikigai.src.mcp_server.server` import path which conflicts with
    # the v2 namespace package layout (`src.ikigai.src` is a namespace package
    # and `agents.v2.X` requires `src/ikigai/src/` on sys.path). When both
    # cannot coexist, the legacy handlers are simply unavailable and the v2
    # prompt chain stands alone. Per ADR-013 this is the desired state.
    score_handler = None
    regime_handler = None
    try:
        from src.ikigai.src.mcp_server.server import (
            _handle_ikigai_score as _score_handler,
            _handle_ikigai_regime as _regime_handler,
        )
        score_handler = _score_handler
        regime_handler = _regime_handler
    except ImportError:
        # Legacy path not available in this environment — v2 prompt chain is
        # the sole observation surface. This is the expected state post
        # ADR-013 (planner-only).
        pass

    return (
        score_handler,
        regime_handler,
        render_score_passion_observation,
        render_heuristics_regime_observation,
        render_surface_pav_intentions,
    )


def _load_graph_factory():
    """Lazy import of make_v2_graph — separate from _load_handlers.

    The graph factory transitively imports v2 nodes (commit.py, etc.) that
    use the legacy `src.ikigai.src.agents.v2.state` import style which
    conflicts with the v2 namespace package layout. Loading it lazily means
    that commands which don't need the graph (suggest/score/regime) do not
    pay the import cost or trigger the conflict.
    """
    from agents.v2.graph import make_v2_graph

    return make_v2_graph


def _resolve_vault_root() -> Path:
    """Return IKIGAI_VAULT_ROOT env var (if set), else relative `vault/`."""
    env_root = os.environ.get("IKIGAI_VAULT_ROOT")
    if env_root:
        return Path(env_root)
    return Path("vault")


def _run_cycle(dry_run: bool = False) -> dict:
    """Compile and invoke ikigai_maintainer_v2 graph; return serialisable result.

    dry_run=True compiles but does not invoke the graph (plan-only, no writes).
    """
    make_v2_graph = _load_graph_factory()

    compiled = make_v2_graph()
    if dry_run:
        return {
            "graph": "ikigai_maintainer_v2",
            "entry_point": compiled._ikigai_entry_point,
            "dry_run": True,
            "compiled": True,
        }
    result = compiled.invoke({})
    # Return a serialisable slice (graph returns full IKIGAiStateDict)
    return {
        "graph": "ikigai_maintainer_v2",
        "entry_point": compiled._ikigai_entry_point,
        "nodes_visited": list(result.keys()) if isinstance(result, dict) else str(result),
        "error_type": result.get("error_type") if isinstance(result, dict) else None,
    }


def _run_score(date_str: str) -> dict:
    """Call render_score_passion_observation (prompt chain); fall back to MCP handler.

    Preferred path: prompt-chain renderer per ADR-013 planner-only architecture.
    Fallback: legacy MCP observation wrapper if renderer returns an LLM error
    (e.g. test env without ANTHROPIC_API_KEY).
    """
    score_handler, _, render_score_passion, _, _ = _load_handlers()
    state = {"date": date_str, "vault_root": str(_resolve_vault_root())}
    observation = render_score_passion(state)
    # Fall back to MCP handler if LLM call failed (test env without API key)
    if (
        score_handler is not None
        and "error" in observation
        and observation.get("error") == "llm_call_failed"
    ):
        raw = score_handler({"date": date_str})
        observation = json.loads(raw)
    observation.setdefault("date", date_str)
    observation["vault_root"] = state["vault_root"]
    observation.setdefault("graph", "ikigai_score_passion_observation")
    return observation


def _run_regime(date_str: str) -> dict:
    """Call render_heuristics_regime_observation (prompt chain); fall back to MCP handler."""
    _, regime_handler, _, render_heuristics_regime, _ = _load_handlers()
    state = {"date": date_str, "vault_root": str(_resolve_vault_root())}
    observation = render_heuristics_regime(state)
    if (
        regime_handler is not None
        and "error" in observation
        and observation.get("error") == "llm_call_failed"
    ):
        raw = regime_handler({"date": date_str})
        observation = json.loads(raw)
    observation.setdefault("date", date_str)
    observation["vault_root"] = state["vault_root"]
    observation.setdefault("graph", "ikigai_heuristics_regime_observation")
    return observation


def _run_suggest(date_str: str) -> dict:
    """Call render_surface_pav_intentions (prompt chain); return parsed dict.

    Strictly read-only on vault (no vault_write calls). Honours IKIGAI_VAULT_ROOT
    env var; defaults to relative `vault/` path.
    """
    _, _, _, _, render_surface_pav = _load_handlers()
    state = {"date": date_str, "vault_root": str(_resolve_vault_root())}
    observation = render_surface_pav(state)
    # Add metadata + vault_root for downstream consumers (tests, --json output)
    observation.setdefault("date", date_str)
    observation["vault_root"] = state["vault_root"]
    observation.setdefault("graph", "ikigai_surface_intentions")
    return observation


# ---------------------------------------------------------------------------
# Per-skill orchestrators — W2.3
# ---------------------------------------------------------------------------
# Each per-skill command composes the existing primitives (cycle/score/regime/
# suggest) into the contract documented in src/ikigai/src/agents/v2/skills/.
# The skill files are the source of truth for which primitives to invoke.
#
# Strictly read-only on vault/ (per ADR-012 + skill frontmatter constraints):
#   - Writes go through `vault_write` MCP tool (which the v2 graph calls in its
#     `commit` node). The per-skill commands themselves NEVER call vault_write.
#   - These commands ORCHESTRATE — they do NOT execute math (per ADR-013).


def _run_daily(date_str: str) -> dict:
    """Run ikigai-daily skill — surface PAV intentions (3-5 pt-BR suggestions).

    Composition per src/ikigai/src/agents/v2/skills/daily.md:
        1. Read cycle_state/{date}.md (PAV-written)
        2. Read yesterday's daily report
        3. Run surface_pav_intentions prompt chain
        4. (vault_write of today's daily report — handled by v2 graph in cycle,
            NOT here; per-skill commands are read-only orchestrators)
        5. (taskdog_create_task for top-3 priorities — NOT here; this is a
            planner-only surface, writes handled by separate orchestration)

    Returns the merged skill result for CLI display.
    """
    suggest_result = _run_suggest(date_str)
    return {
        "skill": "ikigai-daily",
        "date": date_str,
        "surface": suggest_result,
    }


def _run_weekly(date_str: str) -> dict:
    """Run ikigai-weekly skill — score vectors, regime check (no full cycle).

    Composition per src/ikigai/src/agents/v2/skills/weekly.md:
        1. Read last 7 daily reports
        2. Read cycle_state + habit_state
        3. Run v2_score (passion vector observation)
        4. Run v2_regime (regime check)
        5. (vault_write of weekly review — handled by v2 cycle's commit node)
        6. (taskdog_create_task — NOT here)

    Note: weekly.md invocation example shows `v2 cycle --dry-run` but the
    behavior section (canonical) calls score + regime. We follow the behavior
    contract (score + regime), not the example invocation.
    """
    score_result = _run_score(date_str)
    regime_result = _run_regime(date_str)
    return {
        "skill": "ikigai-weekly",
        "date": date_str,
        "score": score_result,
        "regime": regime_result,
    }


def _run_monthly(date_str: str) -> dict:
    """Run ikigai-monthly skill — full cycle (dry-run) + score + regime.

    Composition per src/ikigai/src/agents/v2/skills/monthly.md:
        1. Read last 4 weekly reviews
        2. Read cycle_state + habit_state
        3. Run v2_cycle --dry-run (8-node graph, plan-only)
        4. Run v2_score (monthly passion vector)
        5. Run v2_regime (updated regime recommendation)
        6. (vault_write of monthly review — handled by cycle's commit node)

    Monthly aggregates weekly reviews, so the full cycle (in dry-run mode) is
    invoked first to surface planning context, then score + regime observe.
    """
    cycle_result = _run_cycle(dry_run=True)
    score_result = _run_score(date_str)
    regime_result = _run_regime(date_str)
    return {
        "skill": "ikigai-monthly",
        "date": date_str,
        "cycle": cycle_result,
        "score": score_result,
        "regime": regime_result,
    }


def _run_quarterly(date_str: str) -> dict:
    """Run ikigai-quarterly skill — full cycle (dry-run) + score + regime.

    Composition per src/ikigai/src/agents/v2/skills/quarterly.md:
        1. Read last 3 monthly reviews
        2. Read last 13 weekly reviews
        3. Read cycle_state + habit_state
        4. Run v2_cycle --dry-run (8-node graph for quarterly context)
        5. Run v2_score (quarterly passion vector)
        6. Run v2_regime (regime recommendation for next quarter)
        7. (vault_write of quarterly review — handled by cycle's commit node)

    Quarterly is the broadest skill — strategic realignment. Uses dry-run to
    keep it as a planner-only surface (no writes from the per-skill command
    itself).
    """
    cycle_result = _run_cycle(dry_run=True)
    score_result = _run_score(date_str)
    regime_result = _run_regime(date_str)
    return {
        "skill": "ikigai-quarterly",
        "date": date_str,
        "cycle": cycle_result,
        "score": score_result,
        "regime": regime_result,
    }


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command(name="cycle")
def cycle(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Compile graph without invoking (plan-only, no writes).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
) -> None:
    """Invoke ikigai_maintainer_v2 LangGraph (observe → score → heuristics → … → commit)."""
    try:
        result = _run_cycle(dry_run=dry_run)
    except Exception as exc:
        # Include "FAIL" in the message so test_v2_cycle_dry_run_invokes_graph
        # can detect the graceful failure (it asserts 'FAIL' in output).
        console.print(f"[red]Graph FAIL: Error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        if result.get("error_type"):
            console.print(f"[yellow]Graph finished with error:[/yellow] {result['error_type']}")
        else:
            if dry_run:
                console.print(
                    "[green]Graph ikigai_maintainer_v2 compiled (dry-run, not invoked).[/green]"
                )
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


@app.command(name="suggest")
def suggest(
    date_arg: str = typer.Argument(
        "",
        help="Date to surface suggestions for (YYYY-MM-DD). Defaults to today.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
) -> None:
    """Call render_surface_pav_intentions prompt chain (3-5 pt-BR suggestions).

    Reads PAV-written cycle_state + last 3 daily reports from vault/, emits
    user-facing pt-BR suggestions. Strictly read-only on vault (no vault_write).
    Reference: src/ikigai/src/agents/v2/skills/daily.md:24
    """
    date_str = date_arg or date.today().isoformat()
    try:
        result = _run_suggest(date_str)
    except Exception as exc:
        console.print(f"[red]Suggest error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        suggestions = result.get("suggestions", [])
        lang = result.get("language", "pt-BR")
        source = result.get("source", "unknown")
        console.print(
            f"[green]Sugestoes PAV ({len(suggestions)}) [{lang}] (source={source}, date={date_str}):[/green]"
        )
        for i, s in enumerate(suggestions, 1):
            console.print(f"  {i}. {s}")


# ---------------------------------------------------------------------------
# Per-skill commands — W2.3
# ---------------------------------------------------------------------------
# Each command is a thin orchestrator over the primitives above. They follow
# the contracts documented at src/ikigai/src/agents/v2/skills/<name>.md.
#
# Strictly read-only on vault/ — writes go through `vault_write` MCP tool
# (called by the v2 graph's commit node when invoked via `v2 cycle`). Per
# ADR-013 planner-only, these orchestrators execute no math directly.


@app.command(name="daily")
def daily(
    date_arg: str = typer.Argument(
        "",
        help="Date to surface daily intentions for (YYYY-MM-DD). Defaults to today.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
) -> None:
    """Run ikigai-daily skill — surface PAV intentions (3-5 pt-BR suggestions).

    Orchestrates render_surface_pav_intentions prompt chain. Reads PAV-written
    cycle_state + last 3 daily reports. Strictly read-only on vault/.
    Reference: src/ikigai/src/agents/v2/skills/daily.md
    """
    date_str = date_arg or date.today().isoformat()
    try:
        result = _run_daily(date_str)
    except Exception as exc:
        console.print(f"[red]Daily skill error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        surface = result.get("surface", {})
        suggestions = surface.get("suggestions", [])
        lang = surface.get("language", "pt-BR")
        console.print(
            f"[green]ikigai-daily for {date_str} [{lang}]:[/green]"
        )
        if not suggestions:
            console.print("  [dim](no suggestions surfaced)[/dim]")
        for i, s in enumerate(suggestions, 1):
            console.print(f"  {i}. {s}")


@app.command(name="weekly")
def weekly(
    date_arg: str = typer.Argument(
        "",
        help="Date for weekly review (YYYY-MM-DD). Defaults to today.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
) -> None:
    """Run ikigai-weekly skill — score vectors + regime check.

    Orchestrates score_passion_observation + heuristics_regime_observation prompt
    chains. Aggregates last 7 daily reports. Strictly read-only on vault/.
    Reference: src/ikigai/src/agents/v2/skills/weekly.md
    """
    date_str = date_arg or date.today().isoformat()
    try:
        result = _run_weekly(date_str)
    except Exception as exc:
        console.print(f"[red]Weekly skill error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        score = result.get("score", {})
        regime = result.get("regime", {})
        console.print(
            f"[green]ikigai-weekly for {date_str}:[/green]"
        )
        # Score line
        if "error" in score:
            console.print(f"  [yellow]Score: error — {score.get('error')}[/yellow]")
        else:
            ps = score.get("passion_score", score.get("vector_scores", {}).get("passion", "?"))
            console.print(f"  passion_score: {ps}")
        # Regime line
        if "error" in regime:
            console.print(f"  [yellow]Regime: error — {regime.get('error')}[/yellow]")
        else:
            rg = regime.get("regime", "?")
            console.print(f"  regime: {rg}")


@app.command(name="monthly")
def monthly(
    date_arg: str = typer.Argument(
        "",
        help="Date for monthly review (YYYY-MM-DD). Defaults to today.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
) -> None:
    """Run ikigai-monthly skill — full cycle (dry-run) + score + regime.

    Orchestrates cycle (dry-run) + score + regime. Aggregates last 4 weekly
    reviews. Strictly read-only on vault/ (cycle is dry-run only).
    Reference: src/ikigai/src/agents/v2/skills/monthly.md
    """
    date_str = date_arg or date.today().isoformat()
    try:
        result = _run_monthly(date_str)
    except Exception as exc:
        console.print(f"[red]Monthly skill error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        cycle = result.get("cycle", {})
        score = result.get("score", {})
        regime = result.get("regime", {})
        console.print(
            f"[green]ikigai-monthly for {date_str}:[/green]"
        )
        # Cycle line
        if "error_type" in cycle and cycle["error_type"]:
            console.print(f"  [yellow]Cycle: error — {cycle['error_type']}[/yellow]")
        else:
            console.print(
                f"  cycle: {cycle.get('graph', '?')} "
                f"(entry_point={cycle.get('entry_point', '?')}, "
                f"dry_run={cycle.get('dry_run', '?')})"
            )
        # Score line
        if "error" in score:
            console.print(f"  [yellow]Score: error — {score.get('error')}[/yellow]")
        else:
            ps = score.get("passion_score", score.get("vector_scores", {}).get("passion", "?"))
            console.print(f"  passion_score: {ps}")
        # Regime line
        if "error" in regime:
            console.print(f"  [yellow]Regime: error — {regime.get('error')}[/yellow]")
        else:
            rg = regime.get("regime", "?")
            console.print(f"  regime: {rg}")


@app.command(name="quarterly")
def quarterly(
    date_arg: str = typer.Argument(
        "",
        help="Date for quarterly review (YYYY-MM-DD). Defaults to today.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
) -> None:
    """Run ikigai-quarterly skill — strategic realignment (cycle dry-run + score + regime).

    Orchestrates cycle (dry-run) + score + regime. Reads last 3 monthly + last
    13 weekly reviews. Strictly read-only on vault/ (cycle is dry-run only).
    Reference: src/ikigai/src/agents/v2/skills/quarterly.md
    """
    date_str = date_arg or date.today().isoformat()
    try:
        result = _run_quarterly(date_str)
    except Exception as exc:
        console.print(f"[red]Quarterly skill error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        cycle = result.get("cycle", {})
        score = result.get("score", {})
        regime = result.get("regime", {})
        console.print(
            f"[green]ikigai-quarterly for {date_str}:[/green]"
        )
        if "error_type" in cycle and cycle["error_type"]:
            console.print(f"  [yellow]Cycle: error — {cycle['error_type']}[/yellow]")
        else:
            console.print(
                f"  cycle: {cycle.get('graph', '?')} "
                f"(entry_point={cycle.get('entry_point', '?')}, "
                f"dry_run={cycle.get('dry_run', '?')})"
            )
        if "error" in score:
            console.print(f"  [yellow]Score: error — {score.get('error')}[/yellow]")
        else:
            ps = score.get("passion_score", score.get("vector_scores", {}).get("passion", "?"))
            console.print(f"  passion_score: {ps}")
        if "error" in regime:
            console.print(f"  [yellow]Regime: error — {regime.get('error')}[/yellow]")
        else:
            rg = regime.get("regime", "?")
            console.print(f"  regime: {rg}")


# Public alias so `from interfaces.cli.v2 import v2_app` matches __init__.py usage.
v2_app = app

if __name__ == "__main__":
    app()
