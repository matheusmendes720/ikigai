"""5 nodes of the PAE-Maintainer graph.

Nodes: observe -> plan/reflect (parallel) -> balance -> commit (guarded)

Each node is a pure function (state_in, deps) -> (state_out, side_effects).
Custom Python graph orchestration (NOT langgraph SDK).

Source: .omo/plans/agentic-markdown-system.md T9
"""
from __future__ import annotations

import datetime as _dt

from .state import (
    BalancerVerdict,
    PAEState,
    PlanVerdict,
)


def observe_node(state: PAEState) -> PAEState:
    """Pull latest metrics from period_reports table.

    Read-only: increments iteration, infers current tier, no DB mutation.
    In production: query vibe_ops.db period_reports via period-sync and
    populate state.active_nodes from active rows.
    """
    state.iteration += 1
    state.last_step = "observe"
    # Tier inference is the observable signal at this stage.
    _ = state.current_tier()
    return state


def plan_node(state: PAEState) -> PAEState:
    """Prospective channel: draft forward for current tier.

    Reads existing children, decides next action (REDUCE_LOAD / EXPAND / MAINTAIN)
    based on the candidate set's average verdict_score. No LLM — deterministic
    decision rule using the 5x3x3 proportionality constants.
    """
    state.last_step = "plan"
    if state.prospective is not None:
        state.prospective.drafted_at = _dt.datetime.utcnow()
        # Decision rule from PAVConstants (no LLM).
        candidates = state.prospective.candidates
        if candidates:
            scores = [c.verdict_score for c in candidates if c.verdict_score is not None]
            avg = sum(scores) / len(scores) if scores else 0.5
        else:
            avg = 0.5
        if avg < 0.50:
            state.prospective.next_action = "REDUCE_LOAD"
        elif avg > 0.80:
            state.prospective.next_action = "EXPAND"
        else:
            state.prospective.next_action = "MAINTAIN"
    return state


def reflect_node(state: PAEState) -> PAEState:
    """Retrospective channel: aggregate completed work backward.

    Compares aggregate_score against thresholds, populates gaps[] for any
    child below 0.50. The aggregate_verdict translates the numeric mean into
    PASS / PARTIAL / FAIL using 0.70 / 0.50 cutoffs.
    """
    state.last_step = "reflect"
    if state.retrospective is not None:
        scores = [c.verdict_score for c in state.retrospective.children_aggregated]
        if scores:
            state.retrospective.aggregate_score = sum(scores) / len(scores)
        # Pick verdict from score bucket.
        avg = state.retrospective.aggregate_score
        if avg >= 0.70:
            state.retrospective.aggregate_verdict = PlanVerdict.PASS
        elif avg >= 0.50:
            state.retrospective.aggregate_verdict = PlanVerdict.PARTIAL
        else:
            state.retrospective.aggregate_verdict = PlanVerdict.FAIL
        # Gap detection: find any child below 0.50.
        for child in state.retrospective.children_aggregated:
            if child.verdict_score < 0.50:
                gap_msg = (
                    f"{child.id}: score {child.verdict_score:.2f} below 0.50"
                )
                if gap_msg not in state.retrospective.gaps:
                    state.retrospective.gaps.append(gap_msg)
    return state


def balance_node(state: PAEState) -> PAEState:
    """Workload vs capacity check + Q_HE histerese enforcement.

    Sets state.balancer.state (BalancerVerdict) based on:
      - workload_estimate vs capacity_estimate (5x3x3 proportionality)
      - Q_HE score vs recover threshold (PAVConstants.QHE_RECOVER_THRESHOLD)
    Updates histerese days counter; activates is_histerese_active after N OK days.
    """
    state.last_step = "balance"
    bal = state.balancer

    # 5x3x3 proportionality: workload should not exceed overload_factor * capacity.
    if bal.workload_estimate > bal.capacity_estimate * bal.overload_factor:
        bal.state = BalancerVerdict.OVERLOAD
        bal.reason = (
            f"workload {bal.workload_estimate:.2f}h > "
            f"{bal.overload_factor}x capacity {bal.capacity_estimate:.2f}h"
        )
    elif bal.workload_estimate < bal.capacity_estimate * bal.underload_factor:
        bal.state = BalancerVerdict.UNDERLOAD
        bal.reason = (
            f"workload {bal.workload_estimate:.2f}h < "
            f"{bal.underload_factor}x capacity {bal.capacity_estimate:.2f}h"
        )
    elif bal.qhe_score < bal.qhe_recover_threshold:
        bal.state = BalancerVerdict.RECOVER
        bal.reason = (
            f"Q_HE={bal.qhe_score:.2f} < threshold {bal.qhe_recover_threshold:.2f}"
        )
    else:
        bal.state = BalancerVerdict.OK
        bal.reason = "within bounds"

    # Histerese: count consecutive OK days (PAVConstants.POLICY_UPGRADE_DAYS).
    if bal.state == BalancerVerdict.OK:
        bal.days_in_current_state += 1
    else:
        bal.days_in_current_state = 1
    bal.is_histerese_active = bal.days_in_current_state >= bal.histerese_upgrade_days

    return state


def commit_node(state: PAEState) -> PAEState:
    """Persist state to pae_state table in vibe_ops.db.

    Guarded by balancer: if OVERLOAD, skip commit and mark kill_switch_triggered
    so the orchestrator can halt the cycle. In production: actually
    INSERT/UPDATE pae_state row + sync to vault via PeriodReportSync.
    Here (scaffold): just update meta fields.
    """
    state.last_step = "commit"
    if state.balancer.state == BalancerVerdict.OVERLOAD:
        state.kill_switch_triggered = True
        state.terminated = True
    return state


__all__ = [
    "observe_node",
    "plan_node",
    "reflect_node",
    "balance_node",
    "commit_node",
]
