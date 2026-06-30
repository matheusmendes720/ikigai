"""Integration tests for PAE-Maintainer graph orchestration.

Validates:
  - Full graph execution end-to-end (observe -> plan -> reflect -> balance -> commit).
  - Checkpoint / restore roundtrip against a real SQLite database.
  - Conditional edge predicates (should_commit, should_terminate).
  - execute_pae_maintainer_once entry point.

Source: .omo/plans/agentic-markdown-system.md T12
Linked: T10 (graph orchestration), T11 (CLI entry point)
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
import sys
from pathlib import Path

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[2] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from agents.pae_maintainer.graph import (  # noqa: E402
    checkpoint_state,
    execute_pae_maintainer_once,
    restore_from_checkpoint,
    run_pae_cycle,
    run_pae_until_terminated,
    should_commit,
    should_overload_recovery,
    should_terminate,
)
from agents.pae_maintainer.state import (  # noqa: E402
    BalancerVerdict,
    PAEState,
)


def make_state(**overrides) -> PAEState:
    """Factory for valid PAEState kwargs (cycle-only defaults)."""
    base: dict = dict(
        cycle_id="integration-test",
        cycle_start=_dt.date(2026, 1, 1),
        cycle_end=_dt.date(2026, 3, 31),
    )
    base.update(overrides)
    return PAEState(**base)


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Pytest tmp_path fixture, scoped per-test (auto-cleaned)."""
    return tmp_path / "pae_state.db"


class TestGraphEnd2End:
    def test_happy_path_full_cycle(self) -> None:
        s = make_state(
            balancer={"workload_estimate": 4.0, "capacity_estimate": 8.0}
        )
        s = run_pae_cycle(s)
        assert s.last_step == "commit"
        assert s.terminated is False
        assert s.kill_switch_triggered is False
        assert s.iteration == 1

    def test_overload_terminates_cycle(self) -> None:
        s = make_state(
            balancer={"workload_estimate": 12.0, "capacity_estimate": 8.0}
        )
        s = run_pae_cycle(s)
        assert s.terminated is True
        assert s.kill_switch_triggered is True
        assert s.last_step == "commit_skipped_overload"

    def test_recover_skips_commit(self) -> None:
        # Q_HE below recover threshold -> RECOVER -> commit skipped.
        s = make_state(
            balancer={
                "workload_estimate": 4.0,
                "capacity_estimate": 8.0,
                "qhe_score": 0.20,
            }
        )
        s = run_pae_cycle(s)
        # RECOVER is rejected by should_commit guard -> commit skipped.
        assert s.terminated is True
        assert s.kill_switch_triggered is True
        assert s.last_step == "commit_skipped_overload"

    def test_underload_allows_commit(self) -> None:
        # UNDERLOAD is allowed through the commit edge.
        s = make_state(
            balancer={"workload_estimate": 1.0, "capacity_estimate": 8.0}
        )
        s = run_pae_cycle(s)
        assert s.balancer.state == BalancerVerdict.UNDERLOAD
        assert s.terminated is False
        assert s.kill_switch_triggered is False
        assert s.last_step == "commit"

    def test_execution_tracks_all_steps(self) -> None:
        s = make_state()
        s = run_pae_cycle(s)
        # Should have visited observe, plan, reflect, balance, commit.
        assert s.iteration == 1
        # last_step is final step (commit or commit_skipped_overload).
        assert s.last_step in ("commit", "commit_skipped_overload")

    def test_run_pae_until_terminated_caps_iterations(self) -> None:
        # With OK balancer, cycle never terminates naturally — must hit cap.
        s = make_state(
            balancer={"workload_estimate": 4.0, "capacity_estimate": 8.0}
        )
        s = run_pae_until_terminated(s, max_iterations=5)
        assert s.iteration == 5  # hit cap, no termination
        assert s.terminated is False

    def test_run_pae_until_terminated_terminates_on_overload(self) -> None:
        s = make_state(
            balancer={"workload_estimate": 12.0, "capacity_estimate": 8.0}
        )
        s = run_pae_until_terminated(s, max_iterations=10)
        # First cycle hits kill switch -> terminated=True.
        assert s.terminated is True
        assert s.iteration == 1


class TestCheckpointRoundtrip:
    def test_persist_and_load(self, tmp_db_path: Path) -> None:
        s = make_state()
        s = run_pae_cycle(s)
        checkpoint_state(s, tmp_db_path)
        loaded = restore_from_checkpoint(s.cycle_id, tmp_db_path)
        assert loaded is not None
        assert loaded.cycle_id == s.cycle_id
        assert loaded.iteration == s.iteration
        assert loaded.last_step == s.last_step

    def test_load_nonexistent_returns_none(self, tmp_db_path: Path) -> None:
        # Database file doesn't exist yet.
        assert not tmp_db_path.exists()
        loaded = restore_from_checkpoint("nonexistent-cycle", tmp_db_path)
        assert loaded is None

    def test_load_empty_db_returns_none(self, tmp_db_path: Path) -> None:
        # Create empty DB, no rows inserted.
        tmp_db_path.touch()
        loaded = restore_from_checkpoint("nonexistent-cycle", tmp_db_path)
        assert loaded is None

    def test_execute_pae_maintainer_once_creates_and_persists(
        self, tmp_db_path: Path
    ) -> None:
        # First call: no checkpoint exists -> creates fresh state, runs, persists.
        result = execute_pae_maintainer_once(
            cycle_id="first-call",
            cycle_start=_dt.date(2026, 1, 1),
            cycle_end=_dt.date(2026, 3, 31),
            db_path=tmp_db_path,
        )
        assert result.iteration == 1

        # Second call: loads checkpoint, increments iteration, persists.
        result2 = execute_pae_maintainer_once(
            cycle_id="first-call",
            cycle_start=_dt.date(2026, 1, 1),
            cycle_end=_dt.date(2026, 3, 31),
            db_path=tmp_db_path,
        )
        assert result2.iteration == 2
        assert tmp_db_path.exists()

    def test_paestate_table_created_lazily(self, tmp_db_path: Path) -> None:
        s = make_state(cycle_id="lazy-create")
        checkpoint_state(s, tmp_db_path)
        with sqlite3.connect(str(tmp_db_path)) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pae_state'"
            ).fetchone()
        assert row is not None


class TestConditionalEdges:
    def test_should_commit_true_for_ok(self) -> None:
        s = make_state()
        s.balancer.state = BalancerVerdict.OK
        assert should_commit(s) is True

    def test_should_commit_true_for_underload(self) -> None:
        s = make_state()
        s.balancer.state = BalancerVerdict.UNDERLOAD
        assert should_commit(s) is True

    def test_should_commit_false_for_overload(self) -> None:
        s = make_state()
        s.balancer.state = BalancerVerdict.OVERLOAD
        assert should_commit(s) is False

    def test_should_commit_false_for_recover(self) -> None:
        s = make_state()
        s.balancer.state = BalancerVerdict.RECOVER
        assert should_commit(s) is False

    def test_should_terminate_on_kill_switch(self) -> None:
        s = make_state()
        s.kill_switch_triggered = True
        assert should_terminate(s) is True
        s.kill_switch_triggered = False
        s.terminated = True
        assert should_terminate(s) is True

    def test_should_terminate_false_when_running(self) -> None:
        s = make_state()
        assert s.kill_switch_triggered is False
        assert s.terminated is False
        assert should_terminate(s) is False

    def test_should_overload_recovery_requires_two_days(self) -> None:
        # Single day in OVERLOAD -> False.
        s = make_state()
        s.balancer.state = BalancerVerdict.OVERLOAD
        s.balancer.days_in_current_state = 1
        assert should_overload_recovery(s) is False

        s.balancer.days_in_current_state = 2
        assert should_overload_recovery(s) is True

        s.balancer.days_in_current_state = 5
        assert should_overload_recovery(s) is True

    def test_should_overload_recovery_false_for_other_states(self) -> None:
        s = make_state()
        s.balancer.days_in_current_state = 5
        for verdict in (BalancerVerdict.OK, BalancerVerdict.UNDERLOAD, BalancerVerdict.RECOVER):
            s.balancer.state = verdict
            assert should_overload_recovery(s) is False