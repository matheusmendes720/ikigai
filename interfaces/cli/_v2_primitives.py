"""v2 — Primitive observation runners (cycle / score / regime / suggest)
PLUS the 4 observation Typer commands (registered via register_observation).

These are the v2 architecture's prompt-chain renderers + LangGraph cycle
runner. Each `_run_*` returns a serialisable dict that the Typer command
consumers decorate with `--json` output or pretty-printing.

Per ADR-013 (planner-only), this layer:
  - executes no math directly
  - reads from `data/observations/` (PAV-written) and `vault/ikigai/meta/`
  - returns dicts, not state mutations
  - honours IKIGAI_VAULT_ROOT env var via _resolve_vault_root()

Note on monkey-patching: tests use `monkeypatch.setattr(v2, "_load_graph_factory", ...)`
and `monkeypatch.setattr(v2, "_load_handlers", ...)`. Inside these functions
we must look up `_load_handlers` / `_load_graph_factory` via the v2 module's
namespace at call time so the patches take effect.
"""

from __future__ import annotations

import json
from datetime import date

import typer

# Lazy module-level imports kept inside functions to:
#   1) break the circular module load (v2 → _v2_primitives → v2)
#   2) make monkeypatch.setattr(v2, "_load_handlers", ...) / _load_graph_factory
#      actually take effect (late binding through v2's namespace).


def _run_cycle(dry_run: bool = False) -> dict:
    """Compile and invoke ikigai_maintainer_v2 graph; return serialisable result.

    dry_run=True compiles but does not invoke the graph (plan-only, no writes).
    """
    from . import v2 as _v2_mod

    make_v2_graph = _v2_mod._load_graph_factory()

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
        "nodes_visited": list(result.keys())
        if isinstance(result, dict)
        else str(result),
        "error_type": result.get("error_type") if isinstance(result, dict) else None,
    }


def _run_score(date_str: str) -> dict:
    """Call render_score_passion_observation (prompt chain); fall back to MCP handler.

    Preferred path: prompt-chain renderer per ADR-013 planner-only architecture.
    Fallback: legacy MCP observation wrapper if renderer returns an LLM error
    (e.g. test env without ANTHROPIC_API_KEY).
    """
    from . import v2 as _v2_mod

    score_handler, _, render_score_passion, _, _ = _v2_mod._load_handlers()
    state = {"date": date_str, "vault_root": str(_v2_mod._resolve_vault_root())}
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
    from . import v2 as _v2_mod

    _, regime_handler, _, render_heuristics_regime, _ = _v2_mod._load_handlers()
    state = {"date": date_str, "vault_root": str(_v2_mod._resolve_vault_root())}
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
    from . import v2 as _v2_mod

    _, _, _, _, render_surface_pav = _v2_mod._load_handlers()
    state = {"date": date_str, "vault_root": str(_v2_mod._resolve_vault_root())}
    observation = render_surface_pav(state)
    # Add metadata + vault_root for downstream consumers (tests, --json output)
    observation.setdefault("date", date_str)
    observation["vault_root"] = state["vault_root"]
    observation.setdefault("graph", "ikigai_surface_intentions")
    return observation


# ---------------------------------------------------------------------------
# Observation Typer commands — registered onto v2.app via register_observation
# ---------------------------------------------------------------------------


def register_observation(app: typer.Typer, console) -> None:
    """Bind 4 observation typer commands to `app`:
      cycle  — invoke ikigai_maintainer_v2 LangGraph
      score  — ikigai_score MCP observation wrapper (reads cycle_state/)
      regime — ikigai_regime MCP observation wrapper (reads regime_state/)
      suggest — render_surface_pav_intentions prompt chain (W2.1)

    The ``console`` Rich console is injected so this module does not need to
    import v2.py's console (which would create a circular import). v2.py
    owns app + console and passes both into register_observation().
    """

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
                console.print(
                    f"[yellow]Graph finished with error:[/yellow] {result['error_type']}"
                )
            else:
                if dry_run:
                    console.print(
                        "[green]Graph ikigai_maintainer_v2 compiled (dry-run, not invoked).[/green]"
                    )
                else:
                    console.print(
                        "[green]Graph ikigai_maintainer_v2 invoked successfully.[/green]"
                    )
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
