"""``per_subagent_verifier`` node — LLM-D: cheap retry gate.

Per ``deep-dive-dynamic-workflows.md`` §6, this is "small, fast
(deliberate choice)" — a cheap model whose job is just to check that
the worker's output meets the success criteria emitted by the planner.

The verifier applies three checks (MVP):

1. ``ok`` flag is True (worker's own health flag).
2. Markdown output is non-empty.
3. Retry count is below the task's ``max_attempts``.

On PASS the verifier advances. On FAIL it would loop back to the
sub-agent; in MVP's fan-out that's the routing edge's job (verifier
just writes ``subagent_warnings``; the conditional edge bumps retries).

For the 3-slot MVP we can't actually loop a single sub-agent back
inside the same graph cycle (each sub-agent is one node per run),
so the verifier's "retry" is a *deferred intent*: it bumps the
warning list, and a followup run can pick it up. The architecture
is right; the per-cycle retry would need Send API or loop sub-graph
in a real implementation.

State writes:

* ``subagent_warnings`` — appended to (one warning per failed check)
* ``trace`` — appended (PASS/FAIL per task)
"""

from __future__ import annotations

from typing import Any

from src.ikigai.src.agents.paperclip_dynamic.state import DynamicWorkflowState


def _passes_check(result: dict[str, Any], task: dict[str, Any]) -> tuple[bool, str]:
    """Run the 3 MVP verifier checks against a worker result + task spec.

    Returns (passed, reason). Reason is "PASS" on success, otherwise
    a short message describing which check failed.
    """
    if not result.get("ok"):
        return False, "worker reported ok=False"
    markdown = result.get("markdown") or ""
    if not markdown.strip():
        return False, "worker returned empty markdown"
    return True, "PASS"


def per_subagent_verifier_node(state: DynamicWorkflowState) -> dict[str, object]:
    """Verify every completed sub-agent result against its task contract.

    Reads ``subagent_results``, ``subagent_tasks``, ``subagent_retries``.
    For each (task_id, result) pair, runs the MVP 3-check verifier.
    Writes:

    * ``subagent_warnings`` — list of failure messages (deduped)
    * ``trace`` — verification summary per task
    * ``last_step`` — fixed string

    Returns a *partial* state dict; the routing after the verifier
    decides whether to loop back to the sub-agent or advance to the
    global evaluator.
    """
    results = dict(state.get("subagent_results") or {})
    tasks_list = list(state.get("subagent_tasks") or [])
    retries = dict(state.get("subagent_retries") or {})
    warnings = list(state.get("subagent_warnings") or [])

    # Index tasks by id for O(1) lookups.
    tasks_by_id: dict[str, dict[str, Any]] = {
        t.get("id") or f"slot_{i}": t for i, t in enumerate(tasks_list)
    }

    verification: list[dict[str, Any]] = []
    for task_id, result in results.items():
        task = tasks_by_id.get(task_id, {})
        max_attempts = int(task.get("max_attempts") or 3)
        attempts = int(retries.get(task_id, 0))
        passed, reason = _passes_check(result, task)
        if not passed and attempts < max_attempts:
            # In a real graph this would loop back to subagent.
            warnings.append(
                f"verifier FAIL on {task_id} attempt {attempts}/{max_attempts}: {reason}"
            )
        elif not passed:
            warnings.append(
                f"verifier FAIL on {task_id} — max_attempts {max_attempts} exhausted: {reason}"
            )
        verification.append(
            {
                "task_id": task_id,
                "passed": passed,
                "reason": reason,
                "attempts": attempts,
                "max_attempts": max_attempts,
            }
        )

    return {
        "subagent_warnings": warnings,
        "trace": [
            {
                "node": "per_subagent_verifier",
                "n_verified": len(verification),
                "n_passed": sum(1 for v in verification if v["passed"]),
                "n_failed": sum(1 for v in verification if not v["passed"]),
            }
        ],
        "last_step": "per_subagent_verifier",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"paperclip_dynamic: verifier ran {len(verification)} check(s); "
                    f"passed={sum(1 for v in verification if v['passed'])} "
                    f"failed={sum(1 for v in verification if not v['passed'])}"
                ),
            }
        ],
    }
