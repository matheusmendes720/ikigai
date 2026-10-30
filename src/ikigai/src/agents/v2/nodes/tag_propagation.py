"""tag_propagation node — propose applying tags from a source task to
related tasks reachable through the dep graph.

Per ADR-013: NEVER auto-execute writes. This node computes a proposal
and writes it to the review queue; the user (or human-in-the-loop)
adjudicates whether to apply.

Pure-Python BFS over the dep graph (M256 gate). Reads graph from
state['tag_propagation_input'] which is populated upstream from
taskdog_list + taskdog_read + dependency walking. Does NOT call MCP
tools itself — that is the upstream node's responsibility.

Output schema (review-queue compatible):
    {
        "action": "tag_propagate",
        "tags": ["weekly", "p0"],
        "target_ueids": ["ts:prj:abcd:0001", ...],
        "source_ueid": "ts:prj:abcd:0001",
        "reason": "...",
        "node": "tag_propagation",
    }

Reference: src/contracts/task_change.py TaskAction enum for the
review-queue payload shape. This node writes to
state['proposal'] which proposal_executor.ts forwards into the queue.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

# Cap the BFS so a runaway dep graph cannot freeze the node.
_MAX_BFS_NODES = 500


def tag_propagation_node(state: dict[str, Any]) -> dict[str, Any]:
    """Propose tag propagation across dep-chain siblings.

    Reads state['tag_propagation_input']:
        source_ueid: str  — task whose tags should be propagated
        tags: list[str]   — tags to apply
        graph: dict[str, list[str]] — ueid -> [child_ueids] (forward deps)

    Writes state['proposal'] with shape compatible with the review queue.
    Falls back to empty proposal on missing/invalid input (graceful).
    """
    state = dict(state)
    payload = state.get("tag_propagation_input") or {}
    source_ueid = payload.get("source_ueid")
    tags = payload.get("tags") or []
    graph = payload.get("graph") or {}

    if not source_ueid or not tags or not isinstance(graph, dict):
        state["proposal"] = {
            "action": "tag_propagate",
            "tags": [],
            "target_ueids": [],
            "source_ueid": source_ueid,
            "reason": "missing source_ueid, tags, or graph",
            "node": "tag_propagation",
        }
        state["last_step"] = "tag_propagation"
        return state

    # BFS from source, collect reachable nodes (excluding source itself).
    visited: set[str] = set()
    queue: deque[str] = deque([source_ueid])
    target_ueids: list[str] = []
    while queue and len(visited) < _MAX_BFS_NODES:
        cur = queue.popleft()
        if cur in visited:
            continue
        visited.add(cur)
        if cur != source_ueid:
            target_ueids.append(cur)
        for child in graph.get(cur, []):
            if child not in visited:
                queue.append(child)

    # Deterministic ordering so tests don't flake.
    target_ueids.sort()

    state["proposal"] = {
        "action": "tag_propagate",
        "tags": sorted(set(tags)),
        "target_ueids": target_ueids,
        "source_ueid": source_ueid,
        "reason": (
            f"BFS-walked {len(target_ueids)} reachable task(s) from "
            f"{source_ueid}; proposing tag set {sorted(set(tags))}"
        ),
        "node": "tag_propagation",
    }
    state["last_step"] = "tag_propagation"
    return state
