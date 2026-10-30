"""``subagent`` node factory — LLM-C: dynamic node, one per task.

Per ``deep-dive-dynamic-workflows.md`` §6, the sub-agent is "largest
model for the actual research" — it's the worker, where the actual
work happens. In a real graph topology this is a **dynamic node**
where ``N`` copies are materialised by the harness builder at runtime;
the verifier loop wraps each one.

For MVP we use a **static fan-out** with ``N=3`` slots (one per task
emitted by the planner). The graph factory in ``graph.py`` registers
``subagent_1`` / ``subagent_2`` / ``subagent_3``; each binds to a
specific index via partial. If the planner emits more than 3 tasks,
extras are warned and dropped (per task spec: "use the first 3 tasks,
ignore extras with a warning").

Each sub-agent invocation is a **mock** LLM call — see
``mock_subagent_response``. Real LLM calls (heavy, large model) are
followup.

The returned state writes:

* ``subagent_results`` — keyed by task id, contains the worker output
  (a markdown blob, plus metadata: ``attempts``, ``role``)
* ``subagent_warnings`` — appended to (e.g. "task t4 dropped: only 3 slots")

Per-node contract:

* Inputs: ``subagent_tasks[index]``, ``user_query``, ``command``
* Output: ``{subagent_results: {task_id: result}, ...}``
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.ikigai.src.agents.paperclip_dynamic.state import DynamicWorkflowState


def mock_subagent_response(task: dict[str, Any]) -> dict[str, Any]:
    """Deterministic worker output for one sub-agent task.

    Returns a markdown blob + a small metadata dict. Uses the task id
    + role to vary the output text so downstream tests can assert
    which slot ran. MVP-only — no LLM call.
    """
    task_id = task.get("id") or "t?"
    role = task.get("role") or "synthesizer"
    prompt = task.get("prompt") or ""
    return {
        "task_id": task_id,
        "role": role,
        "markdown": (
            f"## {role} ({task_id})\n\n"
            f"**Prompt:** {prompt}\n\n"
            f"**Findings (mock):**\n\n"
            f"- stub finding 1 for {task_id}\n"
            f"- stub finding 2 for {task_id}\n"
            f"- stub finding 3 for {task_id}\n"
        ),
        "ok": True,
        "attempts": 1,
    }


def make_subagent_node(index: int) -> Callable[[DynamicWorkflowState], dict[str, Any]]:
    """Build a sub-agent node function bound to a single slot index.

    The factory returns a plain ``def(state) -> dict`` function that
    reads ``state["subagent_tasks"][index]``, runs the (mock) worker,
    and writes the result into ``state["subagent_results"]``.

    The factory is the M196 lesson: same code path, three different
    graph nodes. Per-node state isolation comes from LangGraph: each
    slot reads only its own index, not the full task list.
    """
    if index < 0:
        raise ValueError(f"subagent slot index must be >= 0, got {index}")

    def subagent_node(state: DynamicWorkflowState) -> dict[str, object]:
        tasks = list(state.get("subagent_tasks") or [])
        if index >= len(tasks):
            # No task at this slot — emit a warning, write nothing.
            warnings = list(state.get("subagent_warnings") or [])
            warnings.append(f"subagent slot {index} empty (only {len(tasks)} task(s) planned)")
            return {
                "subagent_warnings": warnings,
                "trace": [{"node": f"subagent_{index}", "task": None}],
                "last_step": f"subagent_{index}",
            }

        task = tasks[index]
        task_id = task.get("id") or f"slot_{index}"
        # Bounded retry tracking — increment per attempt at this slot.
        retries = dict(state.get("subagent_retries") or {})
        attempts = int(retries.get(task_id, 0)) + 1
        retries[task_id] = attempts

        response = mock_subagent_response(task)
        response["attempts"] = attempts

        results = dict(state.get("subagent_results") or {})
        results[task_id] = response

        return {
            "subagent_results": results,
            "subagent_retries": retries,
            "trace": [
                {
                    "node": f"subagent_{index}",
                    "task_id": task_id,
                    "role": response["role"],
                    "attempts": attempts,
                }
            ],
            "last_step": f"subagent_{index}",
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        f"subagent_{index} ({task_id}): {len(response['markdown'])} "
                        f"chars, attempt {attempts}/{task.get('max_attempts', 3)}"
                    ),
                }
            ],
        }

    subagent_node.__name__ = f"subagent_node_{index}"
    return subagent_node
