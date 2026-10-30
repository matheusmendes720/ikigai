"""``planner`` node — LLM-A: emit a sub-agent task list.

Per ``deep-dive-dynamic-workflows.md`` §6, this node is "mid-size,
instruction-tuned" with a "structured-output capable" prompt. It
decomposes the user query into an ordered list of sub-agent tasks, each
with a role, prompt template, success criteria, and bounded retry count.

For MVP we don't actually invoke an LLM — see ``_mock_planner_response``
for the deterministic shape. The MVP planner always emits 3 sub-agent
tasks (the static fan-out count we use in the skeleton), so the graph
topology stays a fixed 7-node skeleton with a 3-slot fan-out.

Per Ronald's capstone number: ``max_subagents = 160`` is a deliberate
arbitrary cost ceiling. For MVP we hardcode 3 (the static fan-out)
but we still emit a ``max_attempts`` per task so the planner contract
is in place.

The state fields written here mirror §4 of the deep-dive doc:

* ``plan`` — the structured ``{goal, tasks[]}`` document
* ``subagent_tasks`` — flat ordered list (same data, redundant for
  LangGraph serialisation)
* ``max_attempts`` — default ceiling (3)
"""

from __future__ import annotations

import json
from typing import Any

from src.ikigai.src.agents.paperclip_dynamic.state import DynamicWorkflowState

# Static fan-out count in MVP. Real dynamic graphs emit N from the
# planner; we pre-cap here so the topology stays a fixed skeleton.
DEFAULT_MAX_SUBAGENTS = 3
DEFAULT_MAX_ATTEMPTS = 3


def _mock_planner_response(state: DynamicWorkflowState) -> dict[str, Any]:
    """Deterministic planner output for MVP.

    Always emits 3 sub-agent tasks, each with a distinct role that
    matches the bucket (research / audit / fix) the classifier routed
    to. Same three roles across all commands — the prompt template
    tailors the task to the command.
    """
    user_query = (state.get("user_query") or "").strip()
    command = state.get("command") or "research"
    return {
        "goal": f"Address user request via {command} workflow",
        "tasks": [
            {
                "id": "t1",
                "role": "researcher",
                "prompt": f"Research: {user_query}",
                "tools": [],
                "data_sources": [],
                "output_schema": {"type": "object"},
                "success_criteria": "returns a markdown summary of findings",
                "max_attempts": DEFAULT_MAX_ATTEMPTS,
            },
            {
                "id": "t2",
                "role": "auditor",
                "prompt": f"Audit: {user_query}",
                "tools": [],
                "data_sources": [],
                "output_schema": {"type": "object"},
                "success_criteria": "returns a list of findings with severity",
                "max_attempts": DEFAULT_MAX_ATTEMPTS,
            },
            {
                "id": "t3",
                "role": "synthesizer",
                "prompt": f"Synthesize: {user_query}",
                "tools": [],
                "data_sources": [],
                "output_schema": {"type": "object"},
                "success_criteria": "returns aggregated report markdown",
                "max_attempts": 2,
            },
        ],
        "command": command,
        "n_planned": DEFAULT_MAX_SUBAGENTS,
    }


def planner_node(state: DynamicWorkflowState) -> dict[str, object]:
    """Decompose the user query into a sub-agent task list.

    Reads ``user_query``, ``command``. Writes ``plan`` (the full
    structured document), ``subagent_tasks`` (the flat list), and
    ``max_attempts`` (default ceiling). Always returns a non-empty
    ``subagent_tasks`` list so downstream fan-out never sees zero tasks.
    """
    user_query = (state.get("user_query") or "").strip()
    command = state.get("command") or "research"

    mock = _mock_planner_response(state={"user_query": user_query, "command": command})
    plan = {
        "goal": mock["goal"],
        "tasks": mock["tasks"],
        "command": command,
        "n_planned": mock["n_planned"],
    }
    subagent_tasks = list(mock["tasks"])
    if not subagent_tasks:
        # Defensive: every planner invocation must emit at least one
        # task. Emit a single degenerate task so the fan-out edge has
        # something to dispatch.
        subagent_tasks = [
            {
                "id": "t1",
                "role": "synthesizer",
                "prompt": f"Handle empty plan: {user_query}",
                "success_criteria": "returns non-empty output",
                "max_attempts": 1,
            }
        ]

    return {
        "plan": plan,
        "subagent_tasks": subagent_tasks,
        "max_attempts": DEFAULT_MAX_ATTEMPTS,
        "trace": [
            {
                "node": "planner",
                "n_tasks": len(subagent_tasks),
                "command": command,
            }
        ],
        "last_step": "planner",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"paperclip_dynamic: planner emitted "
                    f"{len(subagent_tasks)} task(s) for command={command!r}; "
                    f"plan={json.dumps({'goal': plan['goal'], 'n': plan['n_planned']})}"
                ),
            }
        ],
    }


def get_default_subagent_count() -> int:
    """Return the static fan-out count for the MVP skeleton.

    Exposed so callers (graph builder, tests) can confirm the fan-out
    math without importing the mock dict.
    """
    return DEFAULT_MAX_SUBAGENTS
