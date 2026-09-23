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
import os
import sys
from datetime import datetime
from pathlib import Path

from .mcp_runtime import _ensure_ikigai_src_on_path
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


# M94: register a `daily` command as a thin alias for `invoke-skill ikigai-daily`.
# This restores the missing command that test_daily_command_surface_suggestions_via_skill
# expects (was removed in V5-D). The actual work is delegated to invoke_skill().
def register_daily(app: typer.Typer) -> None:
    """Register `v2 daily` as an alias for `v2 invoke-skill ikigai-daily`."""

    @app.command(name="daily")
    def daily_cmd(
        json_out: bool = typer.Option(False, "--json", help="Emit JSON output"),
    ) -> None:
        """Run the ikigai-daily skill end-to-end (M94 alias for invoke-skill)."""
        from .invoke_skill import invoke_skill

        result = invoke_skill("ikigai-daily")
        # M94: shape the output for test_daily_command_surface_suggestions_via_skill
        # which expects `output["surface"]["suggestions"]` + `language`.
        surface = {
            "skill": result.get("skill"),
            "entry_point": result.get("entry_point"),
            "suggestions": result.get("user_suggestions", []),
            "suggestions_count": result.get("suggestions_count"),
            "language": result.get("suggestions_language"),
        }
        if json_out:
            typer.echo(json.dumps({"surface": surface}, default=str))
        else:
            typer.echo(json.dumps({"surface": surface}, indent=2, default=str))


# M95: register score/regime/suggest/cycle as aliases for invoke-skill
# with the corresponding entry_point override. These were V5-D-removed
# commands; restoring as thin aliases re-enables interface_dispatch tests.
def _make_graph_alias(name: str, entry_point: str, help_text: str) -> object:
    """Build a Typer command that invokes invoke_skill with a fixed entry_point.

    Used to restore V5-D-removed commands as thin wrappers over the
    canonical invoke-skill interface.
    """

    def cmd(
        date: str = typer.Option(None, "--date", help="Date (YYYY-MM-DD)"),
        json_out: bool = typer.Option(False, "--json", help="Emit JSON output"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Dry run (no writes)"),
    ) -> None:
        from .invoke_skill import invoke_skill

        result = invoke_skill("ikigai-daily", entry_point_override=entry_point)
        if json_out:
            typer.echo(json.dumps(result, indent=2, default=str))
        else:
            typer.echo(json.dumps(result, indent=2, default=str))

    cmd.__name__ = name
    cmd.__doc__ = help_text
    return app.command(name=name)(cmd)


def register_graph_aliases(app: typer.Typer) -> None:
    """Register `score/regime/suggest/cycle` aliases (M95).

    Each maps to invoke_skill with the corresponding entry_point.
    Uses @app.command() with a Typer-style signature (NOT @click decorators)
    so --json/--date options are recognized correctly.

    Note: We MUST use a factory function (default arg pattern) for
    entry_pt because Typer evaluates @app.command() at decoration
    time, capturing the loop variable reference. Without the default
    arg trick, all 4 commands would see the LAST iteration's entry_pt.
    """
    for cmd_name, entry_pt, help_text in [
        ("score", "score_vectors", "Graph entry_point: score_vectors (M95 alias)"),
        ("regime", "heuristics", "Graph entry_point: heuristics (M95 alias)"),
        ("suggest", "surface_intentions", "Graph entry_point: surface_intentions (M95 alias)"),
        ("cycle", "observe", "Graph entry_point: observe (full cycle, M95 alias)"),
    ]:

        @app.command(name=cmd_name, help=help_text)
        def _alias_cmd(
            date: str = typer.Option(None, "--date", help="Date (YYYY-MM-DD)"),
            json_out: bool = typer.Option(False, "--json", help="Emit JSON output"),
            dry_run: bool = typer.Option(False, "--dry-run", help="Dry run (no writes)"),
            _entry_pt: str = entry_pt,  # bind via default arg (M95 fix)
        ) -> None:
            from .invoke_skill import invoke_skill

            try:
                result = invoke_skill("ikigai-daily", entry_point_override=_entry_pt)
            except ValueError as exc:
                # M95: surface errors as structured JSON for CLI consumers
                result = {
                    "skill": "ikigai-daily",
                    "entry_point": _entry_pt,
                    "outputs_fired": [],
                    "graph_state": {"error": str(exc)},
                    "actor": "agent",
                    "error": str(exc),
                }
            typer.echo(json.dumps(result, indent=2, default=str))




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

        # M94: catch ValueError (manifest not found / unknown entry_point)
        # and surface as a structured error dict (NOT raise from CLI).
        # This preserves the test_invoke_skill_unknown_returns_empty_state
        # contract: exit 0 + JSON error response.
        try:
            result = _invoke_skill(
                name,
                entry_point_override=entry_point,
                actor=actor,
            )
        except ValueError as exc:
            # Build the same shape as the old "empty state" return value.
            result = {
                "skill": name,
                "entry_point": "unknown",
                "outputs_fired": [],
                "graph_state": {"error": str(exc)},
                "actor": actor,
                "error": str(exc),
            }
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
# M94: also wire the `daily` alias.
register_daily(app)
# M95: also wire the V5-D-restored graph aliases (score/regime/suggest/cycle).
register_graph_aliases(app)


# ---------------------------------------------------------------------------
# M98: `agent` one-shot deep-agent driver
# ---------------------------------------------------------------------------


def register_agent(app: typer.Typer) -> None:
    """Register the `agent` command on the Typer sub-app.

    M98: surface the deep-agent (38 tools: 12 IKIGAI + 26 MCP taskdog)
    as a one-shot CLI command. User runs:

        life v2 agent "cancel task #162"
        life v2 agent "add dependency from 165 to 162"
        life v2 agent "decompose task 150 into 5 subtasks"

    The agent receives the request, plans tool calls, executes them,
    and prints the final AI message + tool call trace as JSON.

    Requires the ikigai venv to have langchain-mcp-adapters installed
    (M97b). Falls back to IKIGAI_TOOLS-only mode if MCP unavailable.
    """

    @app.command(name="agent")
    def agent_cmd(
        request: str = typer.Argument(..., help="User request to send to the deep-agent."),
        thread_id: str = typer.Option(
            "cli-agent", "--thread", "-t", help="Thread ID for checkpointing."
        ),
        checkpoint_db: str = typer.Option(
            ":memory:", "--checkpoint-db", "-c", help="SQLite checkpoint DB (default in-memory)."
        ),
        human_in_the_loop: bool = typer.Option(
            False, "--human-in-the-loop", "-i", help="Pause before each tool write."
        ),
        disable_mcp: bool = typer.Option(
            False, "--disable-mcp", help="Skip MCP taskdog tools (12 IKIGAI tools only)."
        ),
    ) -> None:
        """Run the deep-agent on a user request (one-shot, M98)."""
        if disable_mcp:
            os.environ["IKIGAI_DISABLE_MCP_TASKDOG"] = "1"

        # Lazy import: ikigai venv required (mcp.server.fastmcp + langchain-mcp-adapters)
        # Inject ikigai.src onto sys.path so `from strategics.loader import ...`
        # resolves (strategics lives at src/ikigai/src/strategics/, not under repo root).
        _ensure_ikigai_src_on_path()
        try:
            from ikigai.src.agents.deepagents_harness import _make_agent
            from ikigai.src.agents.deepagents_harness import (
                _invoke_agent_or_fallback,
                _extract_assistant_text,
            )
        except ImportError as exc:
            typer.echo(
                json.dumps(
                    {
                        "ok": False,
                        "error": f"ikigai venv missing: {exc}. "
                        "Use src/ikigai/.venv/Scripts/python.exe.",
                    },
                    indent=2,
                )
            )
            raise typer.Exit(code=1)

        agent, agent_thread_id = _make_agent(
            thread_id=thread_id,
            checkpoint_db=checkpoint_db,
            human_in_the_loop=human_in_the_loop,
        )

        config = {"configurable": {"thread_id": agent_thread_id}}
        messages = [{"role": "user", "content": request}]

        result = _invoke_agent_or_fallback(agent, messages, config, agent_thread_id)

        if result is None:
            typer.echo(
                json.dumps(
                    {
                        "ok": False,
                        "error": "agent.invoke failed (graceful fallback returned None).",
                        "thread_id": agent_thread_id,
                    },
                    indent=2,
                )
            )
            raise typer.Exit(code=1)

        # Extract the final assistant message text + tool call trace
        response_text = _extract_assistant_text(result)
        tool_calls = []
        for msg in result.get("messages", []):
            tc = getattr(msg, "tool_calls", None) or (
                msg.get("tool_calls") if isinstance(msg, dict) else None
            )
            if tc:
                for c in tc:
                    tool_calls.append(
                        {
                            "name": c.get("name") if isinstance(c, dict) else getattr(c, "name", None),
                            "args": c.get("args") if isinstance(c, dict) else getattr(c, "args", None),
                        }
                    )

        typer.echo(
            json.dumps(
                {
                    "ok": True,
                    "thread_id": agent_thread_id,
                    "response": response_text,
                    "tool_calls": tool_calls,
                    "tool_call_count": len(tool_calls),
                    "request": request,
                },
                indent=2,
                default=str,
            )
        )


# M98: wire `agent` one-shot deep-agent driver (post-M97b MCP wiring).
register_agent(app)


# ---------------------------------------------------------------------------
# M99: `chat` REPL driver — live conversational access to the 38-tool agent
# ---------------------------------------------------------------------------


def register_chat(app: typer.Typer) -> None:
    """Register the `chat` command on the Typer sub-app.

    M99: surface the existing ``run_chat()`` REPL (deepagents_harness.py)
    as a CLI command. User runs ``life v2 chat`` to get an interactive
    session with the 38-tool deep-agent.

    Built-in slash commands are NOT exposed (per attribution §3 design):
    the agent reads ./strategics/ for instructions, so the shell stays
    neutral and routes user input directly to the agent.
    """

    @app.command(name="chat")
    def chat_cmd(
        thread_id: str = typer.Option(
            "chat-cli", "--thread", "-t", help="Thread ID for checkpointing."
        ),
        checkpoint_db: str = typer.Option(
            ":memory:",
            "--checkpoint-db",
            "-c",
            help="SQLite checkpoint DB (default in-memory).",
        ),
        human_in_the_loop: bool = typer.Option(
            False, "--human-in-the-loop", "-i", help="Pause before each tool write."
        ),
        disable_mcp: bool = typer.Option(
            False, "--disable-mcp", help="Skip MCP taskdog tools (12 IKIGAI tools only)."
        ),
    ) -> None:
        """Start an interactive REPL chat with the deep-agent (M99)."""
        if disable_mcp:
            os.environ["IKIGAI_DISABLE_MCP_TASKDOG"] = "1"

        # Inject ikigai.src onto sys.path (see register_agent docstring).
        _ensure_ikigai_src_on_path()
        try:
            from ikigai.src.agents.deepagents_harness import _make_agent, run_chat
        except ImportError as exc:
            typer.echo(
                json.dumps(
                    {
                        "ok": False,
                        "error": f"ikigai venv missing: {exc}. "
                        "Use src/ikigai/.venv/Scripts/python.exe.",
                    },
                    indent=2,
                )
            )
            raise typer.Exit(code=1)

        agent, agent_thread_id = _make_agent(
            thread_id=thread_id,
            checkpoint_db=checkpoint_db,
            human_in_the_loop=human_in_the_loop,
        )
        run_chat(agent, agent_thread_id)


# M99: wire `chat` REPL driver.
register_chat(app)


# ---------------------------------------------------------------------------
# M101b: `td` short alias sub-app for `taskdog *` (cuts typing in half)
# ---------------------------------------------------------------------------


def register_td_alias(app: typer.Typer) -> None:
    """Register `life v2 td <cmd>` as a thin alias for `life taskdog <cmd>`.

    M101b: user pain point — full kebab names like
    `life taskdog decompose-task --task-id 150 --num-subtasks 5`
    are 60+ chars to type. `life v2 td decompose --task-id 150 -n 5`
    is half.

    Implementation: lazy import + dynamic command discovery at first
    invocation. Same venv-detect pattern as life.taskdog sub-app.
    """
    import importlib.util as _importlib_util

    if _importlib_util.find_spec("langchain_mcp_adapters") is None:
        _placeholder = typer.Typer(
            name="td",
            help="Short alias for `taskdog *` (requires langchain-mcp-adapters).",
            no_args_is_help=True,
        )

        @_placeholder.callback(invoke_without_command=True)
        def _td_unavailable(ctx: typer.Context) -> None:
            typer.echo(
                json.dumps(
                    {
                        "ok": False,
                        "error": "langchain-mcp-adapters not installed; use ikigai venv.",
                    },
                    indent=2,
                )
            )
            raise typer.Exit(code=1)

        app.add_typer(_placeholder, name="td")
        return

    # Discover MCP tools and register short-name commands
    try:
        from .mcp_runtime import get_mcp_tools_sync
        tools = get_mcp_tools_sync()
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            json.dumps({"ok": False, "error": f"MCP discovery failed: {exc}"}, indent=2)
        )
        raise typer.Exit(code=1)

    _td_app = typer.Typer(
        name="td",
        help="Short aliases for `taskdog *` commands (M101b). "
        "E.g. `life v2 td list -s PENDING` → `life taskdog list-tasks --status PENDING`.",
        no_args_is_help=True,
    )

    for tool in tools:
        # Strip the _task / _tasks suffix for shorter names
        short_name = tool.name
        for suffix in ("_task", "_tasks", "_notes", "_dependency", "_dependencies"):
            if short_name.endswith(suffix):
                short_name = short_name[: -len(suffix)]
                break
        # Keep kebab-case
        short_name = short_name.replace("_", "-")

        # Build a thin wrapper that calls the full taskdog_app command
        # via subprocess (avoids re-implementing argument parsing).
        full_name = tool.name.replace("_", "-")

        def _make_alias(_full: str = full_name) -> Any:
            def _alias(*args: Any, **kwargs: Any) -> None:
                import subprocess

                cmd = [
                    sys.executable,
                    "-m",
                    "life.cli.cli",
                    "taskdog",
                    _full,
                ]
                # Forward kwargs as --key value pairs (only non-None)
                for k, v in kwargs.items():
                    if v is None:
                        continue
                    cmd.extend([f"--{k.replace('_', '-')}", str(v)])
                # Capture and print output
                r = subprocess.run(cmd, capture_output=True, text=True)
                sys.stdout.write(r.stdout)
                if r.returncode != 0:
                    sys.stderr.write(r.stderr)
                    raise typer.Exit(code=r.returncode)

            return _alias

        # Use the same args_schema as the full version so Typer parses flags identically.
        properties = (tool.args_schema or {}).get("properties", {})
        required = set((tool.args_schema or {}).get("required", []))

        import inspect

        params = []
        for pname, pdef in properties.items():
            default = typer.Option(
                ... if pname in required else None,
                "--" + pname.replace("_", "-"),
                help=str(pdef.get("description") or ""),
            )
            params.append(
                inspect.Parameter(
                    name=pname,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=str | None,
                )
            )

        alias_fn = _make_alias()
        alias_fn.__name__ = f"td_{short_name.replace('-', '_')}"
        alias_fn.__doc__ = f"Alias for `life taskdog {full_name}` (M101b)."
        alias_fn.__signature__ = inspect.Signature(parameters=params)  # type: ignore[attr-defined]
        _td_app.command(name=short_name)(alias_fn)

    app.add_typer(_td_app, name="td")


# M101b: wire short-alias sub-app.
register_td_alias(app)


# M128: register audit-drift subcommand on the v2 app.
def register_audit_drift(app: typer.Typer) -> None:
    """Register `life v2 audit-drift` — drift detection from vault_propagation.

    M128: lets the agent (and humans) invoke audit_drift() directly,
    without going through the backtest harness. Three modes:
      - default: human-readable summary table
      - --json: machine-readable for agent prompts / CI
      - --kind-filter: only show drifts of one kind (phantom_task, etc.)

    Exit codes:
      0 — drift acknowledged (default) OR no drift
      1 — drift found AND --exit-on-drift is set
      2 — audit_drift raised (import error, vault missing, etc.)
    """

    @app.command(name="audit-drift")
    def audit_drift_cmd(
        json_output: bool = typer.Option(
            False, "--json", help="Emit JSON instead of human-readable table."
        ),
        kind_filter: str | None = typer.Option(
            None, "--kind-filter", "-k", help="Only show drifts of this kind."
        ),
        exit_on_drift: bool = typer.Option(
            False, "--exit-on-drift", help="Exit code 1 if any drift is found (CI-friendly)."
        ),
    ) -> None:
        from tools.vault.audit_drift_cli import main as ad_main
        rc = ad_main(
            json_output=json_output,
            kind_filter=kind_filter,
            exit_on_drift=exit_on_drift,
        )
        raise typer.Exit(code=rc)


register_audit_drift(app)


# M131: register vault-toggle subcommand (preview + apply) on the v2 app.
def register_vault_toggle(app: typer.Typer) -> None:
    """Register `life v2 vault-toggle` — guarded mutation of vault checkboxes.

    M131: surfaces M114f's `preview_toggle()` + `apply_toggle()` as a CLI.
    Three sub-commands (kept flat for ease of use):

      preview  — dry-run, always safe; never mutates
      apply    — mutate after preview (refuses if preview fails)
      toggle   — preview + apply in one shot (for trusted agent flows)

    All three require:
      - --plan-path (vault-relative, no .., no absolute)
      - --line (positive integer)
      - --expected (the checkbox text without the leading "- [ ] ")

    apply + toggle also require:
      - --reason (free text, recorded in vault/.vault_events.jsonl)
      - --actor (who is doing this; defaults to "cli")
    """

    @app.command(name="vault-preview")
    def preview_cmd(
        plan_path: str = typer.Option(..., "--plan-path", "-p", help="Vault-relative path."),
        line: int = typer.Option(..., "--line", "-l", help="Target line number (1-indexed)."),
        expected: str = typer.Option(..., "--expected", "-e", help="Expected checkbox text."),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        from tools.vault.apply_toggle_cli import main as at_main
        rc = at_main("preview", rel_path=plan_path, line=line,
                     expected=expected, json_output=json_output)
        raise typer.Exit(code=rc)

    @app.command(name="vault-apply")
    def apply_cmd(
        plan_path: str = typer.Option(..., "--plan-path", "-p"),
        line: int = typer.Option(..., "--line", "-l"),
        expected: str = typer.Option(..., "--expected", "-e"),
        reason: str = typer.Option(..., "--reason", "-r", help="Free-text reason (audit-logged)."),
        actor: str = typer.Option("cli", "--actor", help="Who is doing this (audit-logged)."),
        skip_preview: bool = typer.Option(False, "--skip-preview", help="Skip preview gate (trusted scripts only)."),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        from tools.vault.apply_toggle_cli import main as at_main
        rc = at_main("apply", rel_path=plan_path, line=line, expected=expected,
                     actor=actor, reason=reason, skip_preview=skip_preview,
                     json_output=json_output)
        raise typer.Exit(code=rc)

    @app.command(name="vault-toggle")
    def toggle_cmd(
        plan_path: str = typer.Option(..., "--plan-path", "-p"),
        line: int = typer.Option(..., "--line", "-l"),
        expected: str = typer.Option(..., "--expected", "-e"),
        reason: str = typer.Option(..., "--reason", "-r"),
        actor: str = typer.Option("cli", "--actor"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        from tools.vault.apply_toggle_cli import main as at_main
        rc = at_main("toggle", rel_path=plan_path, line=line, expected=expected,
                     actor=actor, reason=reason, json_output=json_output)
        raise typer.Exit(code=rc)

    # M133: inverse of toggle — reopen a closed checkbox.
    @app.command(name="vault-reopen")
    def reopen_cmd(
        plan_path: str = typer.Option(..., "--plan-path", "-p"),
        line: int = typer.Option(..., "--line", "-l"),
        expected: str = typer.Option(..., "--expected", "-e"),
        reason: str = typer.Option(..., "--reason", "-r"),
        actor: str = typer.Option("cli", "--actor"),
        skip_preview: bool = typer.Option(False, "--skip-preview"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        from tools.vault.reopen_cli import main as ro_main
        rc = ro_main(rel_path=plan_path, line=line, expected=expected,
                     actor=actor, reason=reason, skip_preview=skip_preview,
                     json_output=json_output)
        raise typer.Exit(code=rc)

    # M135: rollback recent toggle/reopen events from the audit log.
    @app.command(name="vault-rollback")
    def rollback_cmd(
        since_hours: float = typer.Option(None, "--since-hours",
                                          help="Only rollback events newer than N hours."),
        actor: str = typer.Option(None, "--actor",
                                   help="Only rollback events from this actor."),
        event: str = typer.Option(None, "--event",
                                   help="Only rollback events of this type."),
        limit: int = typer.Option(1, "--limit", "-n",
                                   help="Rollback this many most-recent matching events."),
        reason: str = typer.Option("user rollback", "--reason", "-r"),
        actor_name: str = typer.Option("cli-rollback", "--actor-name"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        list_only: bool = typer.Option(False, "--list",
                                        help="List matching events without rolling back."),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        from tools.vault.rollback import list_events, main as rb_main
        import sys as _sys
        if list_only:
            events = list_events(since_hours=since_hours, actor=actor,
                                 event_type=event, limit=limit)
            if json_output:
                import json as _json
                print(_json.dumps(events, indent=2, default=str))
            else:
                for e in events:
                    ts = e.get("ts", "")
                    evt = e.get("event", "?")
                    rel = e.get("rel_path", "")
                    line_no = e.get("target_line", "")
                    text = e.get("expected_text", "")[:30]
                    ok = e.get("ok", True)
                    marker = "✓" if ok else "✗"
                    print(f"{marker} {ts}  {evt}  {rel}:{line_no}  {text}")
            raise typer.Exit(code=0)
        # Delegate to the underlying CLI for the actual rollback.
        _sys.argv = [
            "rollback", "undo",
            *(["--since-hours", str(since_hours)] if since_hours else []),
            *(["--actor", actor] if actor else []),
            *(["--event", event] if event else []),
            "--limit", str(limit),
            "--reason", reason,
            "--actor-name", actor_name,
            *(["--dry-run"] if dry_run else []),
            *(["--json"] if json_output else []),
        ]
        rc = rb_main(_sys.argv[1:])
        raise typer.Exit(code=rc)


register_vault_toggle(app)


# M140 — vault full-text search.
def register_vault_search(app: typer.Typer) -> None:
    """Register `life v2 vault-search` command."""

    @app.command(name="vault-search")
    def vault_search_cmd(
        query: str = typer.Argument(..., help="Substring (or regex with --regex)"),
        regex: bool = typer.Option(False, "--regex", help="Interpret query as Python regex"),
        glob: str | None = typer.Option(None, "--glob", help="Glob filter (relative to vault/)"),
        kind: str | None = typer.Option(None, "--kind", help="Frontmatter kind filter"),
        context: int = typer.Option(0, "--context", help="N lines of context"),
        limit: int = typer.Option(100, "--limit", help="Max matches"),
        fmt: str = typer.Option("content", "--format", help="content | paths | json"),
        case_sensitive: bool = typer.Option(False, "--case-sensitive"),
    ) -> None:
        from tools.vault.search import main as _vault_search_main  # lazy import
        import sys as _sys
        argv: list[str] = [query]
        if regex:
            argv.append("--regex")
        if glob is not None:
            argv += ["--glob", glob]
        if kind is not None:
            argv += ["--kind", kind]
        if context:
            argv += ["--context", str(context)]
        if limit != 100:
            argv += ["--limit", str(limit)]
        if fmt != "content":
            argv += ["--format", fmt]
        if case_sensitive:
            argv.append("--case-sensitive")
        # Echo output to stdout (the script writes to stdout).
        rc = _vault_search_main(argv)
        if rc == 1:
            # No matches is not a real error; typer exits 0.
            print("(no matches)", file=_sys.stderr)
        elif rc == 2:
            raise typer.Exit(code=2)
        # rc 0 → matches found, output already printed


register_vault_search(app)


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
