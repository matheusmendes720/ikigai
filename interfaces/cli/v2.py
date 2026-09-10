"""v2 — IKIGAI v2 Typer sub-app (post V5-D + V5-F radical cleanup).

V5-D (2026-09-06): kept only `plan` (Plan D meta-planner); retired
daily/weekly/today. The previous file referenced `_v2_plan.py` for the
`plan` command body.

V5-F (2026-09-07 "Opção B-A — radical-máxima"): merged
`v2.py + _v2_plan.py` → deleted `_v2_plan.py`. The 3 fns
(`_run_plan`, `_format_proposal`, `register_plan`) now live directly
in this module.

Pattern preserved (NOT refactored):
  - `register_plan(app)` takes the Typer instance as a parameter
    rather than using `@app.command(...)` directly at module top-level.
    This breaks a circular import discovered in Plan D Task E.1
    (`agents.v2.subgraph` ↔ `agents.v2.nodes.proposal_executor` ↔
    `interfaces.cli.v2`).
  - Lazy imports of `Proposal`, `make_meta_plan_subgraph`,
    `execute_proposal` live INSIDE `_run_plan`'s body (not at module
    top-level) for the same reason. Defer to first invocation.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

# Ensure `life/` is on sys.path so `from src.X` and `from agents.X`
# resolve when this CLI is invoked via `python -m interfaces.cli.main`.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


app = typer.Typer(
    help="IKIGAI v2 commands — plan (Plan D meta-planner; only surviving command post V5-D)",
)


# ===========================================================================
# V5-F: inlined from former _v2_plan.py — see header docstring for rationale
# ===========================================================================


def _run_plan(
    request: str,
    *,
    approve: bool = False,
    reject_field: str | None = None,
) -> dict[str, Any]:
    """Execute meta-planner subgraph + optional approval flow (Plan D Tasks E.1 + E.2).

    Returns a JSON-serializable dict; prints the proposal to stdout for the
    non-JSON path. The lazy imports below MUST stay inside the function
    body — moving them to module level reintroduces the Plan D Task E.1
    circular import (agents.v2.subgraph ↔ agents.v2.nodes.proposal_executor
    ↔ interfaces.cli.v2).
    """
    # Lazy imports — preserve verbatim from former _v2_plan.py.
    from src.ikigai.contracts.proposal import Proposal
    from agents.v2.subgraph import make_meta_plan_subgraph

    compiled = make_meta_plan_subgraph()
    graph_result = compiled.invoke({"user_request": request})
    proposal: Proposal | None = graph_result.get("proposal")

    if proposal is None:
        return {
            "status": "no_proposal",
            "message": "Intent não detectado — refine your request and try again.",
        }

    display = _format_proposal(proposal)
    print(display)

    if approve:
        # Lazy import preserved for the same circular-import reason.
        from agents.v2.nodes.proposal_executor import execute_proposal

        approved = proposal.model_copy(
            update={
                "approval_state": "approved",
                "approval_timestamp": datetime.now(),
            }
        )
        try:
            report = execute_proposal(approved)
            return {
                "status": "executed",
                "report": report.model_dump(),
            }
        except Exception as exc:  # noqa: BLE001 — executor may raise anything
            return {
                "status": "failed",
                "error": str(exc),
            }

    if reject_field:
        return {
            "status": "rejected_field",
            "field": reject_field,
            "message": (
                f"Field {reject_field!r} rejected. Refine and re-submit, "
                "or omit --reject to see the full proposal."
            ),
        }

    return {
        "status": "pending_approval",
        "proposal_id": proposal.id,
    }


def _format_proposal(proposal: Any) -> str:
    """Pretty-print a Proposal for in-chat display.

    Body shape (preserved from former _v2_plan.py):
      - Proposta gerada (UEID: <id>)
      - Request: <source_request>
      - Created: <created_at>
      - Operations: numbered list
      - Review guidance line
    """
    lines = [
        "",
        f"Proposta gerada (UEID: {proposal.id})",
        f"Request: {proposal.source_request}",
        f"Created: {proposal.created_at}",
        "",
        "Operations:",
    ]
    for i, op in enumerate(proposal.operations, start=1):
        lines.append(f"  {i}. {op}")
    lines.extend(
        [
            "",
            "Review and approve with --approve, "
            "or reject a specific field with --reject <field>.",
        ]
    )
    return "\n".join(lines)


def register_plan(app: typer.Typer) -> None:
    """Register the `plan` command on a Typer sub-app.

    The parameter is named `app` to match the former `_v2_plan.py`
    signature — caller in this module passes the top-level `app`
    defined above. Pattern preserved: do NOT convert to a
    `@app.command(name="plan")` at module top-level, that reintroduces
    the Plan D Task E.1 circular import.
    """

    @app.command(name="plan")
    def plan_cmd(
        request: str = typer.Argument("", help="User planning request (PT-BR or EN)"),
        approve: bool = typer.Option(
            False,
            "--approve",
            help="Approve the proposal and execute writes",
        ),
        reject_field: str | None = typer.Option(
            None,
            "--reject",
            help="Reject a specific field of the proposal",
        ),
    ) -> None:
        """Run meta-planner on a user request (Plan D)."""
        result = _run_plan(
            request,
            approve=approve,
            reject_field=reject_field,
        )
        typer.echo(json.dumps(result, indent=2, default=str))


# Wire the single `plan` command into the Typer app.
register_plan(app)


def register_skill(app: typer.Typer) -> None:
    """Register `daily` and `weekly` commands that dispatch the v2 graph.

    Lazy-imports _v2_skills inside each command body to dodge the
    circular import (v2 ↔ agents.v2.subgraph ↔ agents.v2.nodes.proposal_executor).
    Mirrors the register_plan pattern (v2.py:149).

    Args:
        app: Typer instance to register commands on (passed from v2.py caller).
    """

    @app.command(name="daily")
    def daily_cmd(
        date: str | None = typer.Option(
            None,
            "--date",
            help="Date in YYYY-MM-DD format; defaults to today",
        ),
        json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    ) -> None:
        """Run IKIGAI v2 daily reflection cycle (surface_intentions entry point).

        Reads PAV-written state, emits pt-BR suggestions.
        Entry point: surface_intentions.
        """
        # Lazy import — break circular import with agents.v2.subgraph
        from interfaces.cli import _v2_skills

        _v2_skills.ensure_mcp_server_bound()
        result = _v2_skills.invoke_skill("daily", date_str=date)
        if json_output:
            typer.echo(json.dumps(result, indent=2, default=str))
        else:
            surface = result.get("surface_intentions", {})
            suggestions = surface.get("user_suggestions", [])
            if suggestions:
                typer.echo("Sugestoes PAV ({n}):".format(n=len(suggestions)))
                for i, s in enumerate(suggestions, 1):
                    typer.echo(f"  {i}. {s}")
            else:
                typer.echo("(no suggestions — skill returned empty surface_intentions)")

    @app.command(name="weekly")
    def weekly_cmd(
        date: str | None = typer.Option(
            None,
            "--date",
            help="Date in YYYY-MM-DD format; defaults to today",
        ),
        json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    ) -> None:
        """Run IKIGAI v2 weekly review — observe, score vectors, regime check.

        Entry point: observe (full pipeline).
        """
        # Lazy import — break circular import with agents.v2.subgraph
        from interfaces.cli import _v2_skills

        _v2_skills.ensure_mcp_server_bound()
        result = _v2_skills.invoke_skill("weekly", date_str=date)
        if json_output:
            typer.echo(json.dumps(result, indent=2, default=str))
        else:
            observe = result.get("observe", {})
            typer.echo(f"Skill: {result.get('skill')}")
            typer.echo(f"Date: {result.get('date')}")
            regime = observe.get("regime_state", "unknown")
            typer.echo(f"Regime: {regime}")

    @app.command(name="monthly")
    def monthly_cmd(
        date: str | None = typer.Option(
            None,
            "--date",
            help="Date in YYYY-MM-DD format; defaults to today",
        ),
        json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    ) -> None:
        """Run IKIGAI v2 monthly review — aggregate weekly reviews, Q_HE trend.

        Entry point: observe (full pipeline).
        """
        # Lazy import — break circular import with agents.v2.subgraph
        from interfaces.cli import _v2_skills

        _v2_skills.ensure_mcp_server_bound()
        result = _v2_skills.invoke_skill("monthly", date_str=date)
        if json_output:
            typer.echo(json.dumps(result, indent=2, default=str))
        else:
            observe = result.get("observe", {})
            typer.echo(f"Skill: {result.get('skill')}")
            typer.echo(f"Date: {result.get('date')}")
            regime = observe.get("regime_state", "unknown")
            typer.echo(f"Regime: {regime}")

    @app.command(name="quarterly")
    def quarterly_cmd(
        date: str | None = typer.Option(
            None,
            "--date",
            help="Date in YYYY-MM-DD format; defaults to today",
        ),
        json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    ) -> None:
        """Run IKIGAI v2 quarterly review — strategic realignment, wave planning.

        Entry point: observe (full pipeline).
        """
        # Lazy import — break circular import with agents.v2.subgraph
        from interfaces.cli import _v2_skills

        _v2_skills.ensure_mcp_server_bound()
        result = _v2_skills.invoke_skill("quarterly", date_str=date)
        if json_output:
            typer.echo(json.dumps(result, indent=2, default=str))
        else:
            observe = result.get("observe", {})
            typer.echo(f"Skill: {result.get('skill')}")
            typer.echo(f"Date: {result.get('date')}")
            regime = observe.get("regime_state", "unknown")
            typer.echo(f"Regime: {regime}")

    @app.command(name="chat")
    def chat_cmd(
        prompt: str = typer.Option(..., "--prompt", "-p", help="Single prompt to send through the v2 graph"),
        thread: str = typer.Option(
            "default", "--thread", "-t", help="Thread ID for LangGraph checkpointing"
        ),
        cycle_id: str = typer.Option(
            "cli-chat", "--cycle", help="Cycle ID for state routing"
        ),
        json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    ) -> None:
        """One-shot v2 graph invocation (B4 fix 2026-09-10).

        Compiles the v2 graph via make_v2_graph(), invokes it with a
        realistic initial state carrying the user's prompt, and prints
        the result. Unlike daily/weekly (scheduled skills), `chat` is
        an ad-hoc single-prompt path useful for testing and CLI scripting.

        Note: this is NOT the same as `dcode --chat` (the LangGraph
        deepagent REPL). For conversational mode use `dcode.exe --chat`.
        """
        # Lazy imports — break circular imports with agents.v2.subgraph
        from interfaces.cli import _v2_skills
        from datetime import date as _date

        _v2_skills.ensure_mcp_server_bound()

        try:
            from src.ikigai.src.agents.v2.graph import make_v2_graph

            graph = make_v2_graph(checkpoint_db="data/v2-chat-checkpoints.db")
        except Exception as e:
            typer.echo(f"ERROR: failed to compile v2 graph: {e}", err=True)
            raise typer.Exit(code=1)

        # Realistic initial state. Required keys per IKIGAiStateDict.
        state = {
            "cycle_id": cycle_id,
            "cycle_start": str(_date.today()),
            "cycle_end": str(_date.today()),
            "iteration": 1,
            "date": str(_date.today()),
            "user_input": prompt,
            "messages": [{"role": "user", "content": prompt}],
        }
        config = {"configurable": {"thread_id": thread}}

        try:
            result = graph.invoke(state, config=config)
        except Exception as e:
            typer.echo(f"ERROR: graph.invoke failed: {e}", err=True)
            raise typer.Exit(code=1)

        if json_output:
            typer.echo(json.dumps(result, indent=2, default=str))
        else:
            # Print key result fields if present
            last_step = result.get("last_step", "unknown")
            commit_summary = result.get("commit_summary", "")
            error_msg = result.get("error_message", "")
            typer.echo(f"last_step: {last_step}")
            if commit_summary:
                typer.echo(f"commit_summary: {commit_summary}")
            if error_msg:
                typer.echo(f"error: {error_msg}")
            suggestions = result.get("user_suggestions", [])
            if suggestions:
                typer.echo(f"\nsuggestions ({len(suggestions)}):")
                for i, s in enumerate(suggestions, 1):
                    typer.echo(f"  {i}. {s}")


# Wire the skill commands into the Typer app.
register_skill(app)

# Backward-compat alias — callers that imported `v2_app` keep working.
v2_app = app


__all__ = ["app", "v2_app", "register_plan", "_run_plan", "_format_proposal"]


if __name__ == "__main__":
    app()
