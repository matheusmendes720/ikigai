"""Graph orchestration for PAE-Maintainer.

Custom Python graph (NOT langgraph SDK) — matches qa_swarm.yaml pattern.
Dual-channel execution: observe -> (plan || reflect) -> balance -> commit (guarded).

Public API:
- run_pae_cycle(state) -> state: run one full cycle.
- run_pae_until_terminated(state, max_iterations): drive until terminated.
- checkpoint_state(state, db_path): persist to pae_state table.
- restore_from_checkpoint(cycle_id, db_path) -> Optional[PAEState].
- execute_pae_maintainer_once(cycle_id, cycle_start, cycle_end, db_path): one-shot.

Source: .omo/plans/agentic-markdown-system.md T10
Linked: ADR-006 (period schema), operational constants (Q_HE + 5x3x3).
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
from pathlib import Path

from .nodes import (
    balance_node,
    commit_node,
    observe_node,
    plan_node,
    reflect_node,
)
from .state import (
    BalancerVerdict,
    PAEState,
)


# ---------------------------------------------------------------------------
# Conditional edge predicates
# ---------------------------------------------------------------------------


def should_terminate(state: PAEState) -> bool:
    """Kill switch: if OVERLOAD + kill_switch_triggered, end cycle."""
    return bool(state.kill_switch_triggered or state.terminated)


def should_commit(state: PAEState) -> bool:
    """Commit edge guard: only commit if balancer is OK or UNDERLOAD.

    OVERLOAD and RECOVER both block commit. UNDERLOAD is allowed through
    because it indicates capacity available for expansion.
    """
    return state.balancer.state in (BalancerVerdict.OK, BalancerVerdict.UNDERLOAD)


def should_overload_recovery(state: PAEState) -> bool:
    """Detect persistent OVERLOAD for histeresis escalation.

    Two or more consecutive days in OVERLOAD triggers an upgrade path
    (e.g., RECOVER transition) without bouncing on a single noisy reading.
    """
    return (
        state.balancer.state == BalancerVerdict.OVERLOAD
        and state.balancer.days_in_current_state >= 2
    )


# ---------------------------------------------------------------------------
# Node execution pipeline
# ---------------------------------------------------------------------------


def run_pae_cycle(state: PAEState) -> PAEState:
    """Execute one full PAE cycle through the graph.

    Channel execution order:
        1. observe (read latest metrics).
        2. plan + reflect (parallel via channels; sequential here for
           determinism; async in production).
        3. balance (workload vs capacity + Q_HE histerese).
        4. commit (guarded by balance; skipped on OVERLOAD/RECOVER).
        5. TERMINATE if kill_switch OR commit completes.

    Returns updated state (mutated in-place, Pydantic v2 without frozen).
    """
    # Step 1: observe
    state = observe_node(state)

    # Step 2: parallel channels (plan + reflect). Production runs these
    # async; here they execute sequentially for determinism + testability.
    state = plan_node(state)
    state = reflect_node(state)

    # Step 3: balance
    state = balance_node(state)

    # Early termination guard (kill switch propagation).
    if should_terminate(state):
        state.terminated = True
        return state

    # Conditional edge: only commit if NOT overloaded or in recover.
    if should_commit(state):
        state = commit_node(state)
    else:
        # OVERLOAD or RECOVER: skip commit, trigger kill switch.
        state.kill_switch_triggered = True
        state.terminated = True
        state.last_step = "commit_skipped_overload"

    return state


def run_pae_until_terminated(
    state: PAEState,
    max_iterations: int = 100,
) -> PAEState:
    """Run cycles until terminated or max_iterations reached.

    Safety cap prevents infinite loops when downstream consumers mutate
    state in unexpected ways (e.g., external rollback).
    """
    for _ in range(max_iterations):
        if state.terminated:
            break
        state = run_pae_cycle(state)
    return state


# ---------------------------------------------------------------------------
# State persistence (scaffolded — full SQLite schema lands in migration 005).
# ---------------------------------------------------------------------------


# Migration 005 DDL (pae_state table). Inlined as fallback when the file is
# not present so that the graph can run in isolation during early T11 wiring.
_PAESTATE_DDL = """
CREATE TABLE IF NOT EXISTS pae_state (
    cycle_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def checkpoint_state(state: PAEState, db_path: Path) -> None:
    """Persist PAEState to pae_state table in vibe_ops.db.

    Idempotent upsert keyed on cycle_id. Caller is responsible for
    serializing the state via Pydantic's model_dump_json (no computed
    fields; the entire snapshot is stored verbatim).

    Schema (created in migration 005):
        CREATE TABLE pae_state (
            cycle_id TEXT PRIMARY KEY,
            state_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    payload = state.model_dump_json()
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(_PAESTATE_DDL)
        conn.execute(
            """
            INSERT INTO pae_state (cycle_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(cycle_id) DO UPDATE SET
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (
                state.cycle_id,
                payload,
                _dt.datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()


def restore_from_checkpoint(cycle_id: str, db_path: Path) -> PAEState | None:
    """Load PAEState from pae_state table.

    Returns None if the database file does not exist or no row matches.
    Schema is created lazily via CREATE TABLE IF NOT EXISTS so the
    function is safe to call before migration 005 has been applied.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        return None
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(_PAESTATE_DDL)
        row = conn.execute(
            "SELECT state_json FROM pae_state WHERE cycle_id = ?",
            (cycle_id,),
        ).fetchone()
    if row is None:
        return None
    return PAEState.model_validate_json(row[0])


# ---------------------------------------------------------------------------
# Public entry function (T11 daemon loop will wrap this).
# ---------------------------------------------------------------------------


def execute_pae_maintainer_once(
    cycle_id: str,
    cycle_start: _dt.date,
    cycle_end: _dt.date,
    db_path: Path,
) -> PAEState:
    """One full execution: load state (or create), run cycle, save state.

    Entry point used by the daemon loop in T11. Performs a checkpoint
    after the cycle so the next invocation can resume from this exact
    state — even mid-cycle if the daemon is killed.
    """
    state = restore_from_checkpoint(cycle_id, db_path)
    if state is None:
        state = PAEState(
            cycle_id=cycle_id,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
        )
    state = run_pae_cycle(state)
    checkpoint_state(state, db_path)
    return state


__all__ = [
    "run_pae_cycle",
    "run_pae_until_terminated",
    "checkpoint_state",
    "restore_from_checkpoint",
    "execute_pae_maintainer_once",
    "should_terminate",
    "should_commit",
    "should_overload_recovery",
]