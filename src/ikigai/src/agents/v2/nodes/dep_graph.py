"""dep_graph node — propose adding dependencies between tasks in the
same project (UEID cluster prefix).

Per ADR-013: NEVER auto-execute writes. Produces a proposal that the
review queue handles.

Pure-Python graph reasoning (M256 gate):
  - groups tasks by UEID cluster prefix (`<CLUSTER>:<ENTITY>`)
  - for each task with no dependencies, proposes adding deps to
    every other task in the same cluster (skipping any already-linked
    pair)
  - validates no cycle via DFS (rejects any proposal that would
    introduce a cycle, returns empty proposal with reason)

Output schema (review-queue compatible):
    {
        "action": "add_deps",
        "from_ueid": "ts:prj:abcd:0001",
        "to_ueids": ["ts:prj:abcd:0002", ...],
        "reason": "...",
        "node": "dep_graph",
    }
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _detect_cycle(graph: dict[str, list[str]], start: str) -> bool:
    """Return True if start has any path to itself in graph."""
    stack = [start]
    seen: set[str] = set()
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in graph.get(cur, []):
            if nxt == start:
                return True
            if nxt not in seen:
                stack.append(nxt)
    return False


def dep_graph_node(state: dict[str, Any]) -> dict[str, Any]:
    """Propose dep additions among same-cluster tasks.

    Reads state['dep_graph_input']:
        project_prefix: str                — e.g. "ts:prj:abcd"
        tasks: dict[str, dict]             — ueid -> {priority, ...}
        existing_deps: dict[str, list[str]] — ueid -> [depends_on_ueids]

    Writes state['proposal'] with shape compatible with review queue.
    Validates no cycle via DFS; returns empty proposal if any candidate
    would introduce one.
    """
    state = dict(state)
    payload = state.get("dep_graph_input") or {}
    project_prefix = payload.get("project_prefix")
    tasks = payload.get("tasks") or {}
    existing_deps = payload.get("existing_deps") or {}

    if not project_prefix or not isinstance(tasks, dict):
        state["proposal"] = {
            "action": "add_deps",
            "from_ueid": None,
            "to_ueids": [],
            "reason": "missing project_prefix or tasks",
            "node": "dep_graph",
        }
        state["last_step"] = "dep_graph"
        return state

    # Filter to tasks in the requested project cluster.
    cluster_tasks = [u for u in tasks if u.startswith(project_prefix + ":")]
    cluster_set = set(cluster_tasks)

    proposals: list[dict[str, Any]] = []
    skipped_cycles: list[str] = []

    for src in sorted(cluster_tasks):
        existing = set(existing_deps.get(src, []))
        candidates = sorted(cluster_set - {src} - existing)
        if not candidates:
            continue
        # Cycle check: simulate adding all candidates at once and verify
        # no node can reach itself through the augmented graph.
        proposed_graph: dict[str, list[str]] = {
            u: list(existing_deps.get(u, [])) for u in cluster_set
        }
        proposed_graph[src] = candidates
        if _detect_cycle(proposed_graph, src):
            skipped_cycles.append(src)
            continue
        proposals.append(
            {
                "action": "add_deps",
                "from_ueid": src,
                "to_ueids": candidates,
                "reason": (f"sibling project tasks for {src} in cluster {project_prefix!r}"),
                "node": "dep_graph",
            }
        )

    if not proposals:
        state["proposal"] = {
            "action": "add_deps",
            "from_ueid": None,
            "to_ueids": [],
            "reason": (
                f"no safe additions in cluster {project_prefix!r} "
                f"(skipped cycles for {len(skipped_cycles)} node(s))"
            ),
            "node": "dep_graph",
        }
        state["last_step"] = "dep_graph"
        return state

    # Pick the first deterministic proposal (sorted) as primary;
    # alternatives live in state['proposals'] for the executor to choose.
    primary = proposals[0]
    state["proposal"] = primary
    state["proposals"] = proposals  # full list for executor
    state["last_step"] = "dep_graph"
    return state
