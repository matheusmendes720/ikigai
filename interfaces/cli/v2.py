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
    from src.ikigai.src.agents.v2.subgraph import make_meta_plan_subgraph

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
        from src.ikigai.src.agents.v2.nodes.proposal_executor import execute_proposal

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

# Backward-compat alias — callers that imported `v2_app` keep working.
v2_app = app




def register_invoke_skill(app: typer.Typer) -> None:
    """Register the `invoke-skill` command on a Typer sub-app.

    M78: wraps invoke_skill() for the CLI surface. Lets users run
    `life invoke-skill ikigai-daily` to fire the daily cycle's
    post-processors (vault_write, taskdog_create_task).

    Pattern matches register_plan(): parameter-based to defer the
    invoke_skill import and avoid circular imports from v2 subgraphs.
    """

    @app.command(name="invoke-skill")
    def invoke_skill_cmd(
        name: str = typer.Argument(..., help="Skill name (e.g. ikigai-daily, ikigai-quarterly)."),
        entry_point: str = typer.Option(
            None,
            "--entry-point",
            "-e",
            help="Override the manifest's entry_point (default: from manifest).",
        ),
        actor: str = typer.Option(
            "agent",
            "--actor",
            "-a",
            help="Actor performing the skill (user | agent | system).",
        ),
    ) -> None:
        """Run a skill manifest end-to-end (W3.5/W3.6).

        Loads the skill from src/ikigai/src/agents/v2/skills/<name>.md,
        dispatches via IKIGAI_FAKE_LLM=1 (set env var to bypass LLM API),
        then runs the manifest-declared post-processors (vault_write,
        taskdog_create_task).
        """
        # Lazy import to avoid circular (per Plan D Task E.1 lesson)
        from .invoke_skill import invoke_skill as _invoke_skill

        result = _invoke_skill(
            name,
            entry_point_override=entry_point,
            actor=actor,
        )
        typer.echo(json.dumps(result, indent=2, default=str))


def register_skill_list(app: typer.Typer) -> None:
    """Register the `skill list` introspection command.

    Lists all available skill manifests under the canonical skills dir,
    showing name, description, entry_point, actor, and whether the
    manifest declares a taskdog output.
    """

    @app.command(name="skill-list")
    def skill_list_cmd() -> None:
        """List available skill manifests (W3.5)."""
        from .invoke_skill import _resolve_skills_dir, load_skill_manifest
        from ._skill_outputs import _manifest_declares_taskdog

        skills_dir = _resolve_skills_dir()
        rows: list[dict[str, object]] = []
        for md_path in sorted(skills_dir.glob("*.md")):
            manifest = load_skill_manifest(md_path.stem)
            outputs = manifest.get("outputs") or []
            has_taskdog = _manifest_declares_taskdog(outputs) is not None
            rows.append(
                {
                    "name": manifest.get("name", md_path.stem),
                    "description": manifest.get("description", ""),
                    "entry_point": manifest.get("entry_point", ""),
                    "actor": manifest.get("actor", ""),
                    "outputs_count": len(outputs) if isinstance(outputs, list) else 0,
                    "fires_taskdog": has_taskdog,
                }
            )
        typer.echo(json.dumps({"count": len(rows), "skills": rows}, indent=2))


def register_skill_show(app: typer.Typer) -> None:
    """Register the `skill show` introspection command (M84).

    Shows full manifest details for a single skill: name, description,
    entry_point, actor, inputs, outputs (with target tools), and
    helpful metadata like cron cadence (if declared) and tags.
    """

    @app.command(name="skill-show")
    def skill_show_cmd(
        name: str = typer.Argument(..., help="Skill name (e.g. ikigai-daily)."),
        json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of pretty-print."),
    ) -> None:
        """Show details for a single skill manifest."""
        from .invoke_skill import load_skill_manifest
        from ._skill_outputs import _manifest_declares_taskdog

        manifest = load_skill_manifest(name)
        if not manifest:
            error = {"ok": False, "error": f"skill {name!r} not found"}
            typer.echo(json.dumps(error))
            raise typer.Exit(1)

        outputs = manifest.get("outputs") or []
        taskdog_target = _manifest_declares_taskdog(outputs)

        detail: dict[str, object] = {
            "ok": True,
            "name": manifest.get("name", name),
            "description": manifest.get("description", ""),
            "entry_point": manifest.get("entry_point", ""),
            "actor": manifest.get("actor", ""),
            "inputs": manifest.get("inputs", []),
            "outputs": outputs,
            "fires_taskdog": taskdog_target is not None,
            "taskdog_target": taskdog_target if taskdog_target else None,
            "metadata": manifest.get("metadata", {}),
        }

        if json_out:
            typer.echo(json.dumps(detail, indent=2, default=str))
        else:
            _print_skill_human(detail)


def _print_skill_human(detail: dict[str, object]) -> None:
    """Pretty-print a single skill manifest in human-friendly form."""
    name = detail.get("name", "<unknown>")
    typer.echo(f"\n=== {name} ===")
    if detail.get("description"):
        typer.echo(f"\n  {detail['description']}\n")
    typer.echo(f"  entry_point: {detail.get('entry_point', '?')}")
    typer.echo(f"  actor:       {detail.get('actor', '?')}")
    typer.echo(f"  fires taskdog: {detail.get('fires_taskdog')}")
    if detail.get("taskdog_target"):
        typer.echo(f"  taskdog action: {detail['taskdog_target']}")

    inputs = detail.get("inputs") or []
    if inputs:
        typer.echo("\n  inputs:")
        if isinstance(inputs, list):
            for inp in inputs:
                typer.echo(f"    - {inp}")
        else:
            typer.echo(f"    {inputs}")

    outputs = detail.get("outputs") or []
    if outputs:
        typer.echo("\n  outputs (post-processors):")
        if isinstance(outputs, list):
            for out in outputs:
                typer.echo(f"    - {out}")

    metadata = detail.get("metadata")
    if metadata and isinstance(metadata, dict) and metadata:
        typer.echo("\n  metadata:")
        for k, v in metadata.items():
            typer.echo(f"    {k}: {v}")

    typer.echo("")


# Wire invoke-skill + skill-list + skill-show commands into the Typer app.
register_invoke_skill(app)
register_skill_list(app)
register_skill_show(app)


# Re-export invoke_skill so ``from interfaces.cli.v2 import invoke_skill``
# works (W3.5/W3.6 skill manifest loader + taskdog post-processor).
from .invoke_skill import invoke_skill, load_skill_manifest  # noqa: E402,F401


__all__ = [
    "app",
    "v2_app",
    "register_plan",
    "_run_plan",
    "_format_proposal",
    "invoke_skill",
    "load_skill_manifest",
]


if __name__ == "__main__":
    app()
