"""gantt_suggest node — topological sort + priority weighting, propose
a reordering that maximizes parallel work.

Per ADR-013: NEVER auto-execute writes. Pure read-only computation;
no MCP writes.

Pure-Python Kahn's algorithm with priority weighting (M256 gate):
  - input: tasks keyed by ueid, each with {priority: int, deps: list[str]}
  - output: a proposal containing a deterministic topological order
  - among tasks with no remaining unsatisfied deps, the higher-priority
    task (numerically smaller value, like priority:1 > priority:5) is
    emitted first to surface urgent items earlier
  - lower-priority tasks come later — maximizes parallel work by
    deferring blockers' blockers into batches

Output schema (review-queue compatible):
    {
        "action": "reorder",
        "suggestion": ["ts:prj:abcd:0001", ...],   # topological order
        "batches": [["ueid", ...], ...],            # parallelizable groups
        "reason": "...",
        "node": "gantt_suggest",
    }
"""

from __future__ import annotations

import heapq
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


def gantt_suggest_node(state: dict[str, Any]) -> dict[str, Any]:
    """Propose a topological + priority-weighted task order.

    Reads state['gantt_input']:
        tasks: dict[str, dict]  — ueid -> {"priority": int, "deps": list[str]}

    Writes state['proposal'] with shape compatible with review queue.
    Falls back to empty proposal on missing/invalid input.
    """
    state = dict(state)
    payload = state.get("gantt_input") or {}
    tasks = payload.get("tasks") or {}

    if not isinstance(tasks, dict) or not tasks:
        state["proposal"] = {
            "action": "reorder",
            "suggestion": [],
            "batches": [],
            "reason": "missing or empty tasks dict",
            "node": "gantt_suggest",
        }
        state["last_step"] = "gantt_suggest"
        return state

    # Build adjacency + in-degree map (drop deps that aren't in scope).
    in_scope = set(tasks.keys())
    deps: dict[str, set[str]] = {u: set(tasks[u].get("deps") or []) & in_scope for u in in_scope}
    in_degree: dict[str, int] = {u: len(deps[u]) for u in in_scope}
    dependents: dict[str, list[str]] = defaultdict(list)
    for u in in_scope:
        for d in deps[u]:
            dependents[d].append(u)

    # Min-heap keyed by (priority, ueid) so lower priority value (= higher
    # importance) is popped first. Ties broken alphabetically.
    heap: list[tuple[int, str]] = []
    for u in in_scope:
        if in_degree[u] == 0:
            heapq.heappush(heap, (int(tasks[u].get("priority", 999)), u))

    order: list[str] = []
    batches: list[list[str]] = []
    while heap:
        batch: list[str] = []
        next_heap: list[tuple[int, str]] = []
        while heap:
            _, u = heapq.heappop(heap)
            batch.append(u)
            for d in dependents[u]:
                in_degree[d] -= 1
                if in_degree[d] == 0:
                    heapq.heappush(
                        next_heap,
                        (int(tasks[d].get("priority", 999)), d),
                    )
        # NOTE: do NOT re-sort the batch alphabetically here — heap pops
        # already yielded them in (priority, then alphabetical tiebreak)
        # order, which is the desired deterministic order. A pure
        # alphabetical sort would clobber the priority weighting.
        order.extend(batch)
        batches.append(batch)
        heap = next_heap

    # Cycle detection: if some nodes never made it onto the heap, they're
    # part of a cycle. Surface them in reason, exclude from order.
    unscheduled = sorted(in_scope - set(order))

    state["proposal"] = {
        "action": "reorder",
        "suggestion": order,
        "batches": batches,
        "unscheduled": unscheduled,
        "reason": (
            f"topological order of {len(order)} task(s) across "
            f"{len(batches)} parallel batch(es)"
            + (f"; {len(unscheduled)} task(s) in cycle (excluded)" if unscheduled else "")
        ),
        "node": "gantt_suggest",
    }
    state["last_step"] = "gantt_suggest"
    return state
