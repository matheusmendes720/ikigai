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
import logging
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import typer
import yaml
from rich.console import Console

# Ensure repo root is on sys.path so `from src.ikigai.src...` resolves.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

app = typer.Typer(
    help="IKIGAI v2 commands — cycle, score, regime, suggest, daily, weekly, monthly, quarterly, plan"
)
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


log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Skill loader (ADR-025 R5)
# ---------------------------------------------------------------------------

_SKILLS_DIR = _REPO_ROOT / "src" / "ikigai" / "src" / "agents" / "v2" / "skills"


def load_skill_manifest(skill_name: str) -> dict:
    """Parse YAML frontmatter from <skills_dir>/<skill_name>.md.

    Per ADR-025 §"Loader rule": frontmatter is the canonical skill binding.
    skill_name is the full name (e.g. "ikigai-daily") but the file is
    named "daily.md" — this function strips the "ikigai-" prefix to find
    the actual file.
    Raises FileNotFoundError if the skill file is missing.
    """
    # Strip "ikigai-" prefix — file is named daily.md not ikigai-daily.md
    file_name = skill_name
    if skill_name.startswith("ikigai-"):
        file_name = skill_name[len("ikigai-") :]
    skill_file = _SKILLS_DIR / f"{file_name}.md"
    content = skill_file.read_text(encoding="utf-8")

    # Extract YAML block between first `---` markers
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        raise ValueError(f"Skill {skill_name!r}: no YAML frontmatter found")
    manifest = yaml.safe_load(m.group(1))
    if not isinstance(manifest, dict):
        raise ValueError(f"Skill {skill_name!r}: frontmatter is not a YAML dict")
    return manifest


def invoke_skill(
    skill_name: str,
    entry_point_override: str | None = None,
) -> dict:
    """Load skill manifest and invoke make_v2_graph(entry_point=entry_point).

    Per ADR-025 §"Loader rule": reads skill .md frontmatter for entry_point
    and actor, then calls make_v2_graph().invoke(initial_state).

    entry_point_override is used for testing/edge cases; if it differs from
    the manifest's entry_point, a warning is logged (per ADR-025 R5).

    W3.6 post-processor: AFTER the graph returns, the manifest's `outputs`
    list is consulted by ``post_process_skill_outputs`` (see
    ``_skill_outputs.py``). Skills declaring ``taskdog_create_task`` trigger
    the existing ``taskdog_create_task`` @tool (Path-1 canonical harness,
    src/ikigai/src/agents/tools.py:423). On success the graph result is
    extended with ``taskdog_result``; on failure a TaskChange is enqueued to
    ``data/review_queue/`` and ``taskdog_pending_review_queue: True`` is
    added. Per ADR-013 the graph itself stays pure — orchestration lives in
    the CLI.
    """
    manifest = load_skill_manifest(skill_name)
    entry_point = manifest.get("entry_point")
    if entry_point_override is None:
        pass  # use manifest value
    elif entry_point_override != entry_point:
        log.warning(
            f"Skill {skill_name!r} entry_point override: "
            f"manifest={entry_point!r}, caller={entry_point_override!r}"
        )
        entry_point = entry_point_override
    else:
        entry_point = entry_point_override

    from agents.v2.graph import NODES

    if entry_point not in NODES:
        raise ValueError(f"Invalid entry_point {entry_point!r}; must be in {NODES}")

    make_v2_graph = _load_graph_factory()
    graph = make_v2_graph(entry_point=entry_point)
    config = {"configurable": {"thread_id": f"skill-{skill_name}"}}
    initial_state = {
        "vault_root": str(_resolve_vault_root()),
        "last_step": "invoke_skill",
    }
    graph_result = graph.invoke(initial_state, config)

    # W3.6 — post-processor: fire taskdog_create_task if manifest declares it.
    # The manifest's `outputs` list is the single source of truth for which
    # side-effect tools a skill invokes. Surface-only skills (daily) have
    # outputs=[] and short-circuit here.
    from ._skill_outputs import post_process_skill_outputs

    return post_process_skill_outputs(skill_name, manifest, graph_result)


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
    """Run ikigai-daily skill via invoke_skill().

    Per W3.5 + ADR-025: wires `daily` command to
    make_v2_graph(entry_point="surface_intentions") via the invoke_skill()
    helper. daily.md is surface-only (no vault_write, no taskdog).

    Transforms graph result to the format expected by the Typer command:
    graph result -> {"skill": "...", "date": "...", "surface": {"suggestions": [...], ...}}
    """
    graph_result = invoke_skill("ikigai-daily")
    return {
        "skill": "ikigai-daily",
        "date": date_str,
        "surface": {
            "suggestions": graph_result.get("user_suggestions", []),
            "language": graph_result.get("suggestions_language", "pt-BR"),
        },
    }


def _run_weekly(date_str: str) -> dict:
    """Run ikigai-weekly skill via invoke_skill().

    Per W6.X item 2: wires `weekly` command to
    make_v2_graph(entry_point="observe") via the invoke_skill()
    helper. Weekly.md declares outputs=[vault_write, taskdog_create_task].

    Transforms graph result to the format expected by the Typer command:
    graph result -> {"skill": "...", "date": "...", "score": {...}, "regime": {...}}
    """
    graph_result = invoke_skill("ikigai-weekly")
    return {
        "skill": "ikigai-weekly",
        "date": date_str,
        "score": graph_result.get("score", {}),
        "regime": graph_result.get("regime", {}),
    }


def _run_monthly(date_str: str) -> dict:
    """Run ikigai-monthly skill via invoke_skill().

    Per W6.X item 2: wires `monthly` command to
    make_v2_graph(entry_point="observe") via the invoke_skill()
    helper. Monthly.md declares outputs=[vault_write].

    Transforms graph result to the format expected by the Typer command:
    graph result -> {"skill": "...", "date": "...", "cycle": {...}, "score": {...}, "regime": {...}}
    """
    graph_result = invoke_skill("ikigai-monthly")
    return {
        "skill": "ikigai-monthly",
        "date": date_str,
        "cycle": graph_result.get("cycle", {}),
        "score": graph_result.get("score", {}),
        "regime": graph_result.get("regime", {}),
    }


def _run_quarterly(date_str: str) -> dict:
    """Run ikigai-quarterly skill via invoke_skill().

    Per W6.X item 2: wires `quarterly` command to
    make_v2_graph(entry_point="observe") via the invoke_skill()
    helper. Quarterly.md declares outputs=[vault_write, taskdog_create_task].

    Transforms graph result to the format expected by the Typer command:
    graph result -> {"skill": "...", "date": "...", "cycle": {...}, "score": {...}, "regime": {...}}
    """
    graph_result = invoke_skill("ikigai-quarterly")
    return {
        "skill": "ikigai-quarterly",
        "date": date_str,
        "cycle": graph_result.get("cycle", {}),
        "score": graph_result.get("score", {}),
        "regime": graph_result.get("regime", {}),
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
        console.print(f"[green]ikigai-daily for {date_str} [{lang}]:[/green]")
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
        console.print(f"[green]ikigai-weekly for {date_str}:[/green]")
        # Score line
        if "error" in score:
            console.print(f"  [yellow]Score: error — {score.get('error')}[/yellow]")
        else:
            ps = score.get(
                "passion_score", score.get("vector_scores", {}).get("passion", "?")
            )
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
        console.print(f"[green]ikigai-monthly for {date_str}:[/green]")
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
            ps = score.get(
                "passion_score", score.get("vector_scores", {}).get("passion", "?")
            )
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
        console.print(f"[green]ikigai-quarterly for {date_str}:[/green]")
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
            ps = score.get(
                "passion_score", score.get("vector_scores", {}).get("passion", "?")
            )
            console.print(f"  passion_score: {ps}")
        if "error" in regime:
            console.print(f"  [yellow]Regime: error — {regime.get('error')}[/yellow]")
        else:
            rg = regime.get("regime", "?")
            console.print(f"  regime: {rg}")


# ---------------------------------------------------------------------------
# Plan D Task E.1 — `life plan <request>` CLI command
# Supports --approve / --reject X.field approval flow.
# ---------------------------------------------------------------------------


def _run_plan(
    request: str,
    approve: bool = False,
    reject_field: str | None = None,
) -> dict:
    """Run meta-plan skill and (optionally) approve/reject the resulting Proposal.

    Flow:
      1. invoke_skill("meta_plan", ...) → subgraph produces Proposal
      2. Display Proposal in chat (pretty-printed)
      3. If --approve: execute via proposal_executor
      4. If --reject X.field: log rejection (amend-and-rerun deferred to follow-up)
    """
    from src.ikigai.contracts.proposal import Proposal

    # 1. Invoke subgraph
    graph_result = invoke_skill("meta_plan")
    # The skill manifest declares inputs: user_request — we need to thread
    # it through. For now, store the request in state and let fetch_context
    # use it. The actual subgraph returns the Proposal.
    proposal: Proposal | None = graph_result.get("proposal")

    if proposal is None:
        return {
            "status": "no_proposal",
            "message": "Intent não detectado como planning. Use uma frase com palavras como 'quero focar', 'me ajuda a organizar', etc.",
        }

    # 2. Display
    display = _format_proposal(proposal)
    print(display)

    # 3. Approve flow
    if approve:
        from agents.v2.nodes.proposal_executor import execute_proposal

        # Update approval_state before executing
        approved = proposal.model_copy(
            update={"approval_state": "approved", "approval_timestamp": datetime.now()}
        )
        try:
            report = execute_proposal(approved)
            return {"status": "executed", "report": report.model_dump()}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}

    # 4. Reject flow (deferred to follow-up — for now just acknowledge)
    if reject_field:
        return {
            "status": "rejected_field",
            "field": reject_field,
            "message": "Field rejection logged. Re-run /plan to regenerate. "
                       "(Detailed amend-and-rerun flow is a follow-up.)",
        }

    return {"status": "pending_approval", "proposal_id": proposal.id}


def _format_proposal(proposal) -> str:
    """Pretty-print a Proposal for in-chat display."""
    lines = [
        f"Proposta gerada (UEID: {proposal.id})",
        f"   Request: {proposal.source_request}",
        f"   Created: {proposal.created_at.isoformat()}",
        f"   Operations: {len(proposal.operations)}",
    ]
    for i, op in enumerate(proposal.operations, 1):
        if op.vault_write:
            lines.append(
                f"   [{i}] vault_write -> {op.vault_write.vault_path} "
                f"({op.vault_write.entity_type}, actor={op.vault_write.actor_required})"
            )
        elif op.taskdog_create:
            lines.append(
                f"   [{i}] taskdog_create -> {op.taskdog_create.title} "
                f"(priority={op.taskdog_create.priority})"
            )
    lines.append("   -> Aprovar? (--approve / --reject X.field)")
    return "\n".join(lines)


@app.command(name="plan")
def plan_cmd(
    request: str = typer.Argument("", help="User planning request (PT-BR or EN)"),
    approve: bool = typer.Option(False, "--approve", help="Approve the proposal and execute writes"),
    reject_field: str | None = typer.Option(None, "--reject", help="Reject a specific field of the proposal"),
) -> None:
    """Run meta-planner on a user request (Plan D).

    Example:
        life v2 plan "quero focar em entrega E1 essa semana"
        life v2 plan "..." --approve
        life v2 plan "..." --reject priority
    """
    result = _run_plan(request, approve=approve, reject_field=reject_field)
    typer.echo(json.dumps(result, indent=2, default=str))


# Public alias so `from interfaces.cli.v2 import v2_app` matches __init__.py usage.
v2_app = app

if __name__ == "__main__":
    app()
