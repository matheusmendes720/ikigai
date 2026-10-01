"""M167: Three optimization strategies for taskdog task reordering.

Split out of ``optimizer.py`` to keep that module under the project's
500-line cap. Each strategy is a pure function of:

  - ``down``  : ``{ueid: {deps}}``    (upstream tasks)
  - ``up``    : ``{ueid: {downstream}}`` (tasks this one blocks)
  - ``by_ueid``: ``{ueid: task_dict}``
  - ``cfg``   : ``OptimizeConfig`` (strategy + tie-break policy)

…that returns a ``list[OptimizedTask]`` ordered by the strategy's
priority.

Kahn's topological-sort skeleton is shared across strategies; only
the ready-queue ordering + rationale string change. Strategies never
mutate their inputs.

Strategies:
  - fifo: tie-break by created_at (or ueid as fallback).
  - priority_weighted: weight = priority_score x (1 + blocker_count).
  - critical_path: longest-path-in-DAG via memoized DFS.
"""

from __future__ import annotations

from typing import Any

from src.mesh.optimizer import (
    OptimizeConfig,
    OptimizedTask,
    _coerce_priority,
    _priority_score,
    _safe_created_at,
)


def fifo_strategy(
    down: dict[str, set[str]],
    up: dict[str, set[str]],
    by_ueid: dict[str, dict[str, Any]],
    cfg: OptimizeConfig,
) -> list[OptimizedTask]:
    """FIFO: tie-break by created_at, then ueid."""
    in_deg: dict[str, int] = {u: len(down[u]) for u in by_ueid}
    adj = {u: sorted(up[u]) for u in by_ueid}
    ready: list[str] = sorted(
        [u for u in by_ueid if in_deg[u] == 0],
        key=lambda u: (_safe_created_at(by_ueid[u]), u),
    )
    out: list[OptimizedTask] = []
    position = 0
    while ready:
        u = ready.pop(0)
        out.append(
            OptimizedTask(
                ueid=u,
                name=str(by_ueid[u].get("name") or ""),
                status=str(by_ueid[u].get("status") or "planned"),
                priority=by_ueid[u].get("priority"),
                weight=0.0,
                position=position,
                rationale="fifo: earliest-created available task",
                deps=tuple(sorted(down[u])),
                blocks=tuple(sorted(up[u])),
            )
        )
        position += 1
        for v in adj[u]:
            in_deg[v] -= 1
            if in_deg[v] == 0:
                ready.append(v)
        ready.sort(key=lambda x: (_safe_created_at(by_ueid[x]), x))
    return out


def priority_weighted_strategy(
    down: dict[str, set[str]],
    up: dict[str, set[str]],
    by_ueid: dict[str, dict[str, Any]],
    cfg: OptimizeConfig,
) -> list[OptimizedTask]:
    """Priority-weighted topological order.

    Weight formula: ``score = priority_score x (1 + blocker_count)``.
    """
    in_deg: dict[str, int] = {u: len(down[u]) for u in by_ueid}
    adj: dict[str, list[str]] = {u: sorted(up[u]) for u in by_ueid}

    def weight(u: str) -> float:
        p_score = _priority_score(by_ueid[u].get("priority"))
        blocker_count = len(up[u])
        return float(p_score) * (1 + blocker_count)

    def rationale(u: str, w: float) -> str:
        p_label = {1: "high", 2: "medium", 3: "low"}.get(
            _coerce_priority(by_ueid[u].get("priority")), "medium"
        )
        blocker_count = len(up[u])
        bits = [f"{p_label} priority"]
        if blocker_count:
            bits.append(f"blocks {blocker_count} others")
        return " + ".join(bits) + f" (score={w:g})"

    ready: list[str] = sorted(
        [u for u in by_ueid if in_deg[u] == 0],
        key=lambda u: (-weight(u), _safe_created_at(by_ueid[u]), u),
    )
    out: list[OptimizedTask] = []
    position = 0
    while ready:
        u = ready.pop(0)
        w = weight(u)
        out.append(
            OptimizedTask(
                ueid=u,
                name=str(by_ueid[u].get("name") or ""),
                status=str(by_ueid[u].get("status") or "planned"),
                priority=by_ueid[u].get("priority"),
                weight=w,
                position=position,
                rationale=rationale(u, w),
                deps=tuple(sorted(down[u])),
                blocks=tuple(sorted(up[u])),
            )
        )
        position += 1
        for v in adj[u]:
            in_deg[v] -= 1
            if in_deg[v] == 0:
                ready.append(v)
        ready.sort(key=lambda x: (-weight(x), _safe_created_at(by_ueid[x]), x))
    return out


def critical_path_strategy(
    down: dict[str, set[str]],
    up: dict[str, set[str]],
    by_ueid: dict[str, dict[str, Any]],
    cfg: OptimizeConfig,
) -> list[OptimizedTask]:
    """Critical-path-first topological order.

    Each task is annotated with its critical-path length (longest
    path from any source in its dependency subgraph). Higher cp_len
    floats the task earlier — it's the bottleneck of the graph.
    """
    cp_len = _compute_critical_path_lengths(down, by_ueid)
    in_deg: dict[str, int] = {u: len(down[u]) for u in by_ueid}
    adj: dict[str, list[str]] = {u: sorted(up[u]) for u in by_ueid}

    def rationale(u: str) -> str:
        length = cp_len[u]
        base = f"critical path length {length}"
        if length == 0:
            base += " (source task, no upstream chain)"
        return base

    ready: list[str] = sorted(
        [u for u in by_ueid if in_deg[u] == 0],
        key=lambda u: (-cp_len[u], _safe_created_at(by_ueid[u]), u),
    )
    out: list[OptimizedTask] = []
    position = 0
    while ready:
        u = ready.pop(0)
        out.append(
            OptimizedTask(
                ueid=u,
                name=str(by_ueid[u].get("name") or ""),
                status=str(by_ueid[u].get("status") or "planned"),
                priority=by_ueid[u].get("priority"),
                weight=float(cp_len[u]),
                position=position,
                rationale=rationale(u),
                deps=tuple(sorted(down[u])),
                blocks=tuple(sorted(up[u])),
            )
        )
        position += 1
        for v in adj[u]:
            in_deg[v] -= 1
            if in_deg[v] == 0:
                ready.append(v)
        ready.sort(key=lambda x: (-cp_len[x], _safe_created_at(by_ueid[x]), x))
    return out


def _compute_critical_path_lengths(
    down: dict[str, set[str]],
    by_ueid: dict[str, dict[str, Any]],
) -> dict[str, int]:
    """Longest-path-in-DAG via memoized DFS (post-order).

    For each node u, cp_len[u] = 1 + max(cp_len[v] for v in down[u]).
    Nodes with no upstream get cp_len = 0.
    """
    memo: dict[str, int] = {}

    def visit(u: str) -> int:
        if u in memo:
            return memo[u]
        deps = down[u]
        if not deps:
            memo[u] = 0
            return 0
        best = 0
        for v in sorted(deps):
            if v in memo:
                best = max(best, memo[v])
            elif v in by_ueid:
                best = max(best, visit(v))
        memo[u] = best + 1
        return memo[u]

    for u in by_ueid:
        visit(u)
    return memo


__all__ = [
    "fifo_strategy",
    "priority_weighted_strategy",
    "critical_path_strategy",
    "_compute_critical_path_lengths",
]
