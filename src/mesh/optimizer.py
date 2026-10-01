"""M167: Taskdog task optimizer — topological sort with priority weighting.

Three strategies (selectable via ``strategy=``):

  - ``critical_path``   topological order weighted by critical-path length
                        (a task that gates many downstream tasks floats up).
  - ``priority_weighted`` Kahn's algorithm + per-task weight
                          ``priority_score × (1 + blocker_count)``.
  - ``fifo``            plain FIFO over creation order, deps respected.

All strategies honor the dep graph as a hard constraint: a task never
appears before any of its dependencies. Cycles are detected and
reported — a cycle renders the result invalid (returned with
``has_cycle=True`` so the caller can surface it).

Inputs:
  - tasks: list[dict] (TaskdogAdapter.list_all() shape)
  - deps:  optional list[(src_ueid, dst_ueid)] pairs. When omitted,
           each task's ``deps`` field is used as its upstream set.

Outputs:
  - OptimizeResult: ordered tasks, per-task rationale, dep graph metadata.

Usage::

    from src.mesh.optimizer import Optimizer, OptimizeConfig, OptimizeStrategy

    cfg = OptimizeConfig(strategy=OptimizeStrategy.PRIORITY_WEIGHTED)
    result = Optimizer(tasks).optimize(cfg)
    for row in result.ordered:
        print(row.ueid, row.weight, row.rationale)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class OptimizeStrategy(str, Enum):
    """Strategy for the optimizer.

    Stored as ``str`` so it round-trips through ``argparse`` cleanly.
    """

    CRITICAL_PATH = "critical_path"
    PRIORITY_WEIGHTED = "priority_weighted"
    FIFO = "fifo"


# Priority score table: 1 (high) > 2 (medium) > 3 (low). Tasks with no
# priority get a neutral score of 2 (medium).
_PRIORITY_SCORE: dict[int, int] = {1: 3, 2: 2, 3: 1}
_DEFAULT_PRIORITY_SCORE = 2


@dataclass(frozen=True)
class OptimizeConfig:
    """Configuration for the optimizer."""

    strategy: OptimizeStrategy = OptimizeStrategy.PRIORITY_WEIGHTED
    # If True, ties are broken by created_at (older first). If False,
    # ties are broken by ueid (lexicographic) for determinism in tests.
    tie_break_by_created_at: bool = True


@dataclass(frozen=True)
class OptimizedTask:
    """One task in the optimizer output."""

    ueid: str
    name: str
    status: str
    priority: int | None
    weight: float
    position: int
    rationale: str
    deps: tuple[str, ...]
    blocks: tuple[str, ...]


@dataclass(frozen=True)
class OptimizeResult:
    """Result of an optimization run."""

    strategy: OptimizeStrategy
    ordered: tuple[OptimizedTask, ...]
    has_cycle: bool
    cycle_edges: tuple[tuple[str, str], ...]
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize as JSON."""
        import json

        payload = {
            "strategy": self.strategy.value,
            "has_cycle": self.has_cycle,
            "cycle_edges": [list(e) for e in self.cycle_edges],
            "metrics": self.metrics,
            "ordered": [
                {
                    "ueid": t.ueid,
                    "name": t.name,
                    "status": t.status,
                    "priority": t.priority,
                    "weight": t.weight,
                    "position": t.position,
                    "rationale": t.rationale,
                    "deps": list(t.deps),
                    "blocks": list(t.blocks),
                }
                for t in self.ordered
            ],
        }
        return json.dumps(payload, indent=2, sort_keys=True)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _priority_score(priority: Any) -> int:
    """Convert a priority integer (1=high, 2=medium, 3=low) → score."""
    if priority is None:
        return _DEFAULT_PRIORITY_SCORE
    try:
        return _PRIORITY_SCORE[int(priority)]
    except (KeyError, TypeError, ValueError):
        return _DEFAULT_PRIORITY_SCORE


def _build_dep_graph(
    tasks: list[dict[str, Any]],
    explicit_deps: Iterable[tuple[str, str]],
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, dict[str, Any]]]:
    """Build (down, up, by_ueid) maps from task slices + explicit edges.

    ``down[ueid]`` = set of UEIDs that this task is blocked by.
    ``up[ueid]``   = set of UEIDs that this task blocks.
    ``by_ueid``    = the task dict keyed by ueid (for back-references).

    Edges referencing unknown UEIDs are dropped silently (defensive —
    the dep subsystem already rejects bad writes, but the optimizer
    needs to survive partial fixtures).
    """
    by_ueid: dict[str, dict[str, Any]] = {}
    for t in tasks:
        u = str(t.get("ueid") or "")
        if u:
            by_ueid[u] = t

    down: dict[str, set[str]] = {u: set() for u in by_ueid}
    up: dict[str, set[str]] = {u: set() for u in by_ueid}

    for u, t in by_ueid.items():
        for d in t.get("deps") or []:
            sd = str(d or "")
            if sd and sd in by_ueid and sd != u:
                down[u].add(sd)
                up[sd].add(u)

    for src, dst in explicit_deps:
        if src in by_ueid and dst in by_ueid and src != dst:
            down[src].add(dst)
            up[dst].add(src)

    return down, up, by_ueid


def _detect_cycle(
    down: dict[str, set[str]],
    up: dict[str, set[str]],
) -> tuple[bool, tuple[tuple[str, str], ...]]:
    """Iterative DFS cycle detector.

    Returns ``(has_cycle, cycle_edges)`` where ``cycle_edges`` is the
    set of edges that close a back-edge (best-effort — at least one
    edge from each detected cycle is reported).
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {u: WHITE for u in down}
    cycle_edges: list[tuple[str, str]] = []
    found = False

    for start in list(down.keys()):
        if color[start] != WHITE:
            continue
        stack: list[tuple[str, list[str]]] = [(start, sorted(down[start]))]
        color[start] = GRAY
        while stack:
            node, children = stack[-1]
            if not children:
                color[node] = BLACK
                stack.pop()
                continue
            nxt = children.pop(0)
            if nxt not in color:
                # Reference to unknown node — skip defensively.
                continue
            if color[nxt] == GRAY:
                # Back-edge → cycle.
                found = True
                cycle_edges.append((node, nxt))
                # Don't traverse further on this branch.
                continue
            if color[nxt] == WHITE:
                color[nxt] = GRAY
                stack.append((nxt, sorted(down[nxt])))
        # Continue the outer for-loop if no cycle on this DFS tree.

    # Deduplicate while preserving order.
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []
    for e in cycle_edges:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return found, tuple(unique)


def _safe_created_at(task: dict[str, Any]) -> str:
    """Lex-sortable created_at key (empty string sorts last)."""
    val = task.get("created_at")
    if not val:
        return "9999"
    return str(val)


# ─────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────


class Optimizer:
    """Pure optimizer over taskdog task slices.

    Inputs:
      - tasks: list of dicts from ``TaskdogAdapter.list_all()``.
      - deps:  optional list of explicit dep edges (src, dst) tuples.

    Public API:
      - ``optimize(cfg)`` → ``OptimizeResult``.
    """

    def __init__(
        self,
        tasks: list[dict[str, Any]],
        deps: Iterable[tuple[str, str]] | None = None,
    ) -> None:
        self._tasks = list(tasks)
        self._explicit_deps: list[tuple[str, str]] = list(deps or [])

    def optimize(self, cfg: OptimizeConfig) -> OptimizeResult:
        """Run the chosen strategy."""
        down, up, by_ueid = _build_dep_graph(self._tasks, self._explicit_deps)
        has_cycle, cycle_edges = _detect_cycle(down, up)
        if has_cycle:
            return OptimizeResult(
                strategy=cfg.strategy,
                ordered=(),
                has_cycle=True,
                cycle_edges=cycle_edges,
                metrics={"task_count": len(by_ueid)},
            )

        # Lazy import to keep strategy implementations in a separate
        # module under the project's 500-line cap.
        from src.mesh.optimizer_strategies import (
            critical_path_strategy,
            fifo_strategy,
            priority_weighted_strategy,
        )

        if cfg.strategy == OptimizeStrategy.FIFO:
            ordered = fifo_strategy(down, up, by_ueid, cfg)
        elif cfg.strategy == OptimizeStrategy.PRIORITY_WEIGHTED:
            ordered = priority_weighted_strategy(down, up, by_ueid, cfg)
        elif cfg.strategy == OptimizeStrategy.CRITICAL_PATH:
            ordered = critical_path_strategy(down, up, by_ueid, cfg)
        else:  # pragma: no cover — defensive
            raise ValueError(f"unknown strategy: {cfg.strategy!r}")

        return OptimizeResult(
            strategy=cfg.strategy,
            ordered=tuple(ordered),
            has_cycle=False,
            cycle_edges=(),
            metrics={
                "task_count": len(by_ueid),
                "dep_edge_count": sum(len(s) for s in down.values()),
            },
        )


# Strategy implementations live in ``optimizer_strategies.py`` to keep
# this module under the project's 500-line cap.


def _coerce_priority(p: Any) -> int:
    """Defensive priority coercion for rationale labels."""
    if p is None:
        return 2
    try:
        return int(p)
    except (TypeError, ValueError):
        return 2


__all__ = [
    "OptimizeConfig",
    "OptimizeResult",
    "OptimizeStrategy",
    "OptimizedTask",
    "Optimizer",
]
