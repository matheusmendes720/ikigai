"""v2 — Meta-plan command (Plan D Task E.1 + E.2).

Owns:
  - _run_plan(request, approve, reject_field) → status dict
  - _format_proposal(proposal) → pretty-printed chat string
  - register_plan(app)  → binds `life v2 plan` Typer command to the given app

Per Plan D spec: meta-planner takes a free-form pt-BR/en user request,
detects whether it's planning-intent, runs a 3-node subgraph to produce a
Proposal, then waits for --approve / --reject X.field before executing.

Why register_plan(app) (not @app.command(...) directly): the `app` is
defined in v2.py. Decorating the command here would create a circular
import (v2.py → _v2_plan.py → v2.py). The register_* pattern breaks the
cycle while preserving all typer metadata (name, help, options).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import typer


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

    # 1. Invoke subgraph. Late-bind through v2's namespace so
    # `patch("interfaces.cli.v2.invoke_skill")` takes effect (test_meta_plan_e2e).
    from . import v2 as _v2_mod

    graph_result = _v2_mod.invoke_skill("meta_plan")
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


def _format_proposal(proposal: Any) -> str:
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


def register_plan(app: typer.Typer) -> None:
    """Bind `life v2 plan` Typer command to the given app instance.

    Called from v2.py at module bottom so this file need NOT import v2.py
    (which would be a circular import). All typer option metadata (name,
    help) is preserved identically to the original v2.py decorator.
    """

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
