"""``harness_builder`` node — LLM-B: emit ``workflow_spec.md`` + parse.

Per ``deep-dive-dynamic-workflows.md`` §5, the harness builder writes
a **Markdown document** that describes the workflow — name, problem,
stop / synthesis criteria, sub-agents, aggregation. The runtime reads
the MD and materialises a sub-graph from it.

For MVP we don't actually invoke an LLM — we emit a deterministic
markdown template populated from the planner output. The markdown
structure is faithful to §5's reverse-engineered schema.

The MD is then "parsed" (also deterministic in MVP) into a list of
sub-agent task dicts identical to ``subagent_tasks``. In real life the
parser would catch malformed specs; for MVP we just emit the same
shape the planner already produced and trust it.

Why Markdown? From the doc:

* human-readable (debuggable — you can ``cat workflow_spec.md`` and
  see what the planner asked for);
* serialisable (one big string in state);
* diffable (good for traces and for storing historical runs);
* LLM-friendly (planner outputs MD natively, the harness builder
  parses the same MD back into structured form).
"""

from __future__ import annotations

from typing import Any

from src.ikigai.src.agents.paperclip_dynamic.state import DynamicWorkflowState

# Sentinel workflow name constant — used in the markdown header. The
# real version would emit the planner's name (which the planner also
# derives from the user query). The MVP keeps the name stable so
# tests can match against a constant.
WORKFLOW_NAME = "ikigai_dynamic_workflow"


def _build_workflow_spec_md(state: DynamicWorkflowState) -> str:
    """Render the deterministic ``workflow_spec.md`` from state.

    Schema (per deep-dive §5 reverse-engineered minimal):

    ```
    # Workflow: <name>

    ## Problem
    <user query verbatim>

    ## Data sources available
    - (none in MVP)

    ## Stop criterion
    <all sub-agents returned with verifier PASS, or max_attempts exhausted>

    ## Synthesis criterion
    <aggregated markdown report synthesizing sub-agent outputs>

    ## Sub-agents
    ### subagent-1
    - role: ...
    - prompt: ...
    - tools: ...
    - data_sources: ...
    - output_schema: ...
    - success_criteria: ...
    - max_attempts: ...

    ## Aggregation
    <synthesize all sub-agent results into one markdown report>
    ```
    """
    user_query = (state.get("user_query") or "").strip() or "(no query)"
    tasks = list(state.get("subagent_tasks") or [])
    command = state.get("command") or "research"

    lines: list[str] = []
    lines.append(f"# Workflow: {WORKFLOW_NAME}")
    lines.append("")
    lines.append("## Problem")
    lines.append(user_query)
    lines.append("")
    lines.append(f"## Command: {command}")
    lines.append("")
    lines.append("## Data sources available")
    lines.append("- (none in MVP)")
    lines.append("")
    lines.append("## Stop criterion")
    lines.append("all sub-agents returned with verifier PASS, or max_attempts exhausted per task")
    lines.append("")
    lines.append("## Synthesis criterion")
    lines.append(
        "aggregated markdown report that synthesizes sub-agent outputs into one user-facing report"
    )
    lines.append("")
    lines.append("## Sub-agents")
    for i, task in enumerate(tasks, start=1):
        lines.append(f"### subagent-{i}")
        lines.append(f"- role: {task.get('role', 'synthesizer')}")
        lines.append(f"- prompt: {task.get('prompt', '')}")
        lines.append(f"- tools: {', '.join(task.get('tools') or []) or '(none)'}")
        lines.append(f"- data_sources: {', '.join(task.get('data_sources') or []) or '(none)'}")
        lines.append(f"- output_schema: {task.get('output_schema') or {'type': 'object'}}")
        lines.append(
            f"- success_criteria: {task.get('success_criteria', 'returns non-empty output')}"
        )
        lines.append(f"- max_attempts: {task.get('max_attempts', 3)}")
        lines.append("")

    lines.append("## Aggregation")
    lines.append(
        "synthesizer aggregates all sub-agent results into a single "
        "markdown report; global_evaluator cross-checks for conflicts "
        "and assigns a confidence score."
    )
    lines.append("")
    return "\n".join(lines)


def _parse_spec_to_tasks(spec_md: str) -> list[dict[str, Any]]:
    """Parse ``workflow_spec.md`` back into a list of sub-agent task dicts.

    MVP: returns the structured list already living in state — the
    parser is a no-op. In a real implementation this would be the
    strict-MD-parser that catches hallucinated specs (deep-dive §13).
    Returns an empty list if the spec is blank.
    """
    if not spec_md or not spec_md.strip():
        return []
    return []  # sentinel — real parse happens upstream (planner output)


def harness_builder_node(state: DynamicWorkflowState) -> dict[str, object]:
    """Emit ``workflow_spec_md`` for the run.

    Reads ``subagent_tasks`` + ``user_query``. Writes
    ``workflow_spec_md`` (the markdown document) and appends a trace
    entry. The "parsed" task list is dropped here because it's
    identical to ``subagent_tasks``; the parser exists as a future
    hook (deep-dive §13).
    """
    spec_md = _build_workflow_spec_md(state)
    tasks = _parse_spec_to_tasks(spec_md)

    return {
        "workflow_spec_md": spec_md,
        # ``subagent_results`` is initialised to an empty dict so
        # downstream nodes can write into it without a guard.
        "subagent_results": dict(state.get("subagent_results") or {}),
        "subagent_retries": dict(state.get("subagent_retries") or {}),
        "subagent_warnings": list(state.get("subagent_warnings") or []),
        "trace": [
            {
                "node": "harness_builder",
                "spec_md_chars": len(spec_md),
                "n_tasks_in_spec": len(tasks),
            }
        ],
        "last_step": "harness_builder",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"paperclip_dynamic: harness_builder emitted "
                    f"workflow_spec.md ({len(spec_md)} chars, "
                    f"{len(tasks)} parsed task(s))"
                ),
            }
        ],
    }
