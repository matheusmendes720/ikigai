"""Channel classes for PAE-Maintainer.

Two channels run in parallel:
  - ProspectiveChannel: drafts forward (plan direction)
  - RetrospectiveChannel: aggregates backward (reflect direction)

Both share BalancerState (from state.py) for overload safety.

Source: .omo/plans/agentic-markdown-system.md T9
"""
from __future__ import annotations

from .state import (
    BalancerState,
    PAEState,
    PlanNode,
    PlanVerdict,
    ProspectiveNode,
    RetrospectiveNode,
)

# Re-export BalancerState for callers that import via channels only.
__all__ = ["ProspectiveChannel", "RetrospectiveChannel", "BalancerState"]


class ProspectiveChannel:
    """Forward-drafting channel: from existing nodes, generate next-tier candidates.

    Stateless side-effect object: holds default window length + helpers. Each
    call to ``evaluate`` returns a new ProspectiveNode snapshot without
    mutating PAEState. Persistence is the orchestrator's responsibility via
    commit_node.
    """

    PROMOTE_THRESHOLD: float = 0.80
    """Scores >= this are candidates for rolling up to parent tier."""

    FLAG_THRESHOLD: float = 0.50
    """Scores < this are flagged for refactor or kill."""

    def __init__(self, default_window_days: int = 7) -> None:
        self.default_window_days = default_window_days

    def evaluate(
        self,
        state: PAEState,
        parent: PlanNode | None = None,
    ) -> ProspectiveNode:
        """Compute the next prospective state from current PAE state.

        Pulls active_nodes filtered by the inferred current tier and bundles
        them as candidates. Does NOT mutate state.

        Args:
            state: Current PAEState snapshot (read-only here).
            parent: Optional parent PlanNode to inherit from.

        Returns:
            ProspectiveNode: Fresh snapshot with target_tier, window, candidates.
        """
        target_tier = state.current_tier()
        candidates: list[PlanNode] = [
            node
            for node in state.active_nodes
            if node.tier == target_tier
        ]
        return ProspectiveNode(
            target_tier=target_tier,
            target_window_days=self.default_window_days,
            candidates=candidates,
            next_action="REVIEW",
        )

    def next_action(self, node: PlanNode) -> str:
        """Decide next action for a single node based on its verdict_score.

        Args:
            node: PlanNode to inspect.

        Returns:
            One of "PROMOTE_TO_PARENT", "FLAGGED_FOR_REFACTOR", "MAINTAIN".
        """
        if node.verdict_score >= self.PROMOTE_THRESHOLD:
            return "PROMOTE_TO_PARENT"
        if node.verdict_score < self.FLAG_THRESHOLD:
            return "FLAGGED_FOR_REFACTOR"
        return "MAINTAIN"


class RetrospectiveChannel:
    """Backward-aggregating channel: from children, compute parent aggregate.

    Stateless side-effect object: holds window length and verdict cutoffs.
    Each call to ``aggregate`` returns a new RetrospectiveNode without
    mutating PAEState. ``rollback_signals`` emits correction strings to feed
    back into the ProspectiveChannel.
    """

    PASS_THRESHOLD: float = 0.70
    """Aggregate >= this is PASS."""

    PARTIAL_THRESHOLD: float = 0.50
    """Aggregate >= this (and < PASS_THRESHOLD) is PARTIAL."""

    def __init__(self, window_days: int = 30) -> None:
        self.window_days = window_days

    def aggregate(
        self,
        state: PAEState,
        children: list[PlanNode],
    ) -> RetrospectiveNode:
        """Compute aggregate metrics for a set of children.

        Args:
            state: Current PAEState (provides cycle_start/cycle_end).
            children: PlanNode list to aggregate over.

        Returns:
            RetrospectiveNode: New snapshot with aggregate_score, verdict, gaps.
        """
        scores: list[float] = [
            c.verdict_score
            for c in children
            if c.verdict_score is not None
        ]
        avg = sum(scores) / len(scores) if scores else 0.0
        if avg >= self.PASS_THRESHOLD:
            verdict = PlanVerdict.PASS
        elif avg >= self.PARTIAL_THRESHOLD:
            verdict = PlanVerdict.PARTIAL
        else:
            verdict = PlanVerdict.FAIL
        gaps: list[str] = []
        for c in children:
            if c.verdict_score is not None and c.verdict_score < self.PARTIAL_THRESHOLD:
                gap_msg = f"{c.id}: low score {c.verdict_score:.2f}"
                if gap_msg not in gaps:
                    gaps.append(gap_msg)
        return RetrospectiveNode(
            period_start=state.cycle_start,
            period_end=state.cycle_end,
            children_aggregated=list(children),
            aggregate_score=avg,
            aggregate_verdict=verdict,
            gaps=gaps,
        )

    def rollback_signals(self, agg: RetrospectiveNode) -> list[str]:
        """Return correction messages to feed back to prospective channel.

        Args:
            agg: RetrospectiveNode from ``aggregate``.

        Returns:
            List of human-readable correction strings. Empty if all clear.
        """
        signals: list[str] = []
        if agg.aggregate_verdict == PlanVerdict.FAIL:
            signals.append("CRITICAL: aggregate below 0.50 — kill or pivot")
        elif agg.aggregate_verdict == PlanVerdict.PARTIAL:
            signals.append("WARN: aggregate between 0.50-0.70 — correct trajectory")
        for gap in agg.gaps:
            signals.append(f"GAP: {gap}")
        return signals
