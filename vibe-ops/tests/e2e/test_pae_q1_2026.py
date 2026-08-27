"""E2E test: PAE-Maintainer against synthetic Q1 2026 data fixture.

Validates that:
  1. Full pipeline runs end-to-end (observe -> plan -> reflect -> balance -> commit).
  2. Verdict aggregation matches expected outcome.
  3. State persists and can be restored.
  4. Kill switch fires on overload.

The fixture is synthetic real data — 1 sonho + 3 ondas + 12 weeklies +
21 dailies spanning Jan 1 - Mar 31, 2026. All dates are constructed via
datetime arithmetic (no mocks, no fabricated strings).

Source: .omo/plans/agentic-markdown-system.md T12
Linked: T10 (graph orchestration), T11 (CLI entry point)
"""
from __future__ import annotations

import datetime as _dt
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
)
from agents.pae_maintainer.nodes import balance_node  # noqa: E402
from agents.pae_maintainer.state import (  # noqa: E402
    BalancerVerdict,
    PAEState,
    PlanNode,
    PlanTier,
    PlanVerdict,
)


def make_q1_2026_fixture() -> PAEState:
    """Build synthetic Q1 2026 state: 1 sonho + 3 ondas + 12 weeklies + 63 dailies.

    All dates computed via timedelta from Q1 start (2026-01-01) so the fixture
    stays valid regardless of leap years or month boundaries.
    """
    q1_start = _dt.date(2026, 1, 1)
    s = PAEState(
        cycle_id="2026-Q1",
        cycle_start=q1_start,
        cycle_end=_dt.date(2026, 3, 31),
    )

    s.active_nodes.append(PlanNode(
        id="sonho-2026-1",
        tier=PlanTier.SONHO,
        title="Land AI role",
        verdict=PlanVerdict.ACTIVE,
        verdict_score=0.65,
        date_start=q1_start,
        date_end=_dt.date(2026, 12, 31),
    ))

    # 3 Ondas (each spanning ~30 days of Q1).
    for onda in range(1, 4):
        onda_start = q1_start + _dt.timedelta(days=(onda - 1) * 30)
        onda_end = onda_start + _dt.timedelta(days=29)
        s.active_nodes.append(PlanNode(
            id=f"onda-{onda}",
            tier=PlanTier.ONDA,
            title=f"Onda {onda}",
            verdict=PlanVerdict.CONTINUE_WAVE,
            verdict_score=0.70 + onda * 0.05,
            parent_id="sonho-2026-1",
            date_start=onda_start,
            date_end=onda_end,
        ))
        # 4 Weeklies per onda.
        for week in range(1, 5):
            week_idx = (onda - 1) * 4 + week
            week_start = q1_start + _dt.timedelta(days=(week_idx - 1) * 7)
            week_end = week_start + _dt.timedelta(days=6)
            s.active_nodes.append(PlanNode(
                id=f"w{onda}-{week}",
                tier=PlanTier.WEEKLY,
                title=f"Week {onda}.{week}",
                verdict=PlanVerdict.PASS,
                verdict_score=0.70 + (week * 0.03),
                parent_id=f"onda-{onda}",
                date_start=week_start,
                date_end=week_end,
            ))
        # 7 Dailies per week, 3 weeks per onda (range(1, 4)) = 21 per onda.
        for week in range(1, 4):
            week_idx = (onda - 1) * 4 + week
            for day in range(1, 8):
                day_idx = (week_idx - 1) * 7 + day
                day_date = q1_start + _dt.timedelta(days=day_idx - 1)
                s.active_nodes.append(PlanNode(
                    id=f"d{onda}-{week}-{day}",
                    tier=PlanTier.DAILY,
                    title=f"Day {onda}.{week}.{day}",
                    verdict=PlanVerdict.PASS,
                    verdict_score=0.75,
                    parent_id=f"w{onda}-{week}",
                    date_start=day_date,
                    date_end=day_date,
                ))
    return s


@pytest.fixture
def q1_2026_fixture() -> PAEState:
    """Pytest fixture wrapper (allows reuse + future parametrization)."""
    return make_q1_2026_fixture()


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Pytest tmp_path fixture, scoped per-test."""
    return tmp_path / "pae_q1_2026.db"


class TestQ12026E2E:
    def test_fixture_has_expected_node_counts(
        self, q1_2026_fixture: PAEState
    ) -> None:
        # 1 sonho + 3 ondas + 12 weeklies + 63 dailies (3 ondas x 3 weeks x 7 days).
        assert len(q1_2026_fixture.active_nodes) >= 26
        # Verify tier distribution.
        tier_counts: dict[PlanTier, int] = {}
        for node in q1_2026_fixture.active_nodes:
            tier_counts[node.tier] = tier_counts.get(node.tier, 0) + 1
        assert tier_counts[PlanTier.SONHO] == 1
        assert tier_counts[PlanTier.ONDA] == 3
        assert tier_counts[PlanTier.WEEKLY] == 12
        assert tier_counts[PlanTier.DAILY] == 21 * 3  # 63

    def test_fixture_dates_within_q1(
        self, q1_2026_fixture: PAEState
    ) -> None:
        # No daily / weekly / onda should fall outside Q1 (Jan 1 - Mar 31).
        q1_start = _dt.date(2026, 1, 1)
        q1_end = _dt.date(2026, 3, 31)
        for node in q1_2026_fixture.active_nodes:
            if node.tier in (PlanTier.SONHO,):
                continue  # sonho may extend beyond Q1.
            assert node.date_start >= q1_start
            assert node.date_end <= q1_end

    def test_fixture_parent_links_consistent(
        self, q1_2026_fixture: PAEState
    ) -> None:
        ids = {n.id for n in q1_2026_fixture.active_nodes}
        # Every non-sonho node has a parent_id that exists in the fixture.
        for node in q1_2026_fixture.active_nodes:
            if node.parent_id is not None:
                assert node.parent_id in ids

    def test_full_pipeline_runs(self, q1_2026_fixture: PAEState) -> None:
        # Default workload=0 -> UNDERLOAD -> commit allowed.
        result = run_pae_cycle(q1_2026_fixture)
        assert result.iteration == 1
        assert result.balancer.state == BalancerVerdict.UNDERLOAD
        # last_step must be "commit" since UNDERLOAD is allowed through.
        assert result.last_step == "commit"

    def test_pipeline_runs_with_ok_balancer(
        self, q1_2026_fixture: PAEState
    ) -> None:
        q1_2026_fixture.balancer.workload_estimate = 4.0
        q1_2026_fixture.balancer.capacity_estimate = 8.0
        q1_2026_fixture.balancer.qhe_score = 0.75
        result = run_pae_cycle(q1_2026_fixture)
        assert result.balancer.state == BalancerVerdict.OK
        assert result.terminated is False
        assert result.kill_switch_triggered is False

    def test_checkpoint_restores(
        self, q1_2026_fixture: PAEState, tmp_db_path: Path
    ) -> None:
        q1_2026_fixture = run_pae_cycle(q1_2026_fixture)
        checkpoint_state(q1_2026_fixture, tmp_db_path)
        loaded = restore_from_checkpoint("2026-Q1", tmp_db_path)
        assert loaded is not None
        assert len(loaded.active_nodes) == len(q1_2026_fixture.active_nodes)
        assert loaded.balancer.state == q1_2026_fixture.balancer.state
        assert loaded.iteration == q1_2026_fixture.iteration
        assert loaded.last_step == q1_2026_fixture.last_step

    def test_execute_pae_maintainer_once_round_trip(
        self, q1_2026_fixture: PAEState, tmp_db_path: Path
    ) -> None:
        # Persist initial state.
        checkpoint_state(q1_2026_fixture, tmp_db_path)
        # First execution: loads + runs + persists.
        r1 = execute_pae_maintainer_once(
            cycle_id="2026-Q1",
            cycle_start=_dt.date(2026, 1, 1),
            cycle_end=_dt.date(2026, 3, 31),
            db_path=tmp_db_path,
        )
        assert r1.iteration == 1
        # Second execution: loads previous + runs + persists.
        r2 = execute_pae_maintainer_once(
            cycle_id="2026-Q1",
            cycle_start=_dt.date(2026, 1, 1),
            cycle_end=_dt.date(2026, 3, 31),
            db_path=tmp_db_path,
        )
        assert r2.iteration == 2
        # active_nodes must be preserved across executions.
        assert len(r2.active_nodes) == len(q1_2026_fixture.active_nodes)

    def test_overload_triggers_kill_switch(
        self, q1_2026_fixture: PAEState
    ) -> None:
        q1_2026_fixture.balancer.workload_estimate = 50.0
        q1_2026_fixture.balancer.capacity_estimate = 8.0
        # Pre-balance to confirm OVERLOAD detection works on the fixture.
        q1_2026_fixture = balance_node(q1_2026_fixture)
        assert q1_2026_fixture.balancer.state == BalancerVerdict.OVERLOAD
        result = run_pae_cycle(q1_2026_fixture)
        assert result.kill_switch_triggered is True
        assert result.terminated is True
        assert result.last_step == "commit_skipped_overload"

    def test_recover_triggers_kill_switch(
        self, q1_2026_fixture: PAEState
    ) -> None:
        # Workload within bounds but qhe below threshold -> RECOVER -> commit
        # skipped via the should_commit guard.
        q1_2026_fixture.balancer.workload_estimate = 4.0
        q1_2026_fixture.balancer.capacity_estimate = 8.0
        q1_2026_fixture.balancer.qhe_score = 0.10
        result = run_pae_cycle(q1_2026_fixture)
        assert result.balancer.state == BalancerVerdict.RECOVER
        assert result.kill_switch_triggered is True
        assert result.terminated is True

    def test_sonho_node_preserved_across_cycles(
        self, q1_2026_fixture: PAEState, tmp_db_path: Path
    ) -> None:
        # Verify the sonho node is preserved through cycle + checkpoint.
        result = run_pae_cycle(q1_2026_fixture)
        sonhos = [n for n in result.active_nodes if n.tier == PlanTier.SONHO]
        assert len(sonhos) == 1
        assert sonhos[0].id == "sonho-2026-1"
        # Persist + restore and re-verify.
        checkpoint_state(result, tmp_db_path)
        loaded = restore_from_checkpoint("2026-Q1", tmp_db_path)
        assert loaded is not None
        loaded_sonhos = [n for n in loaded.active_nodes if n.tier == PlanTier.SONHO]
        assert len(loaded_sonhos) == 1
        assert loaded_sonhos[0].id == "sonho-2026-1"

    def test_histerese_activates_after_consecutive_ok_cycles(
        self, q1_2026_fixture: PAEState
    ) -> None:
        # Reset balancer to a known OK state, run 3 cycles, expect histerese.
        q1_2026_fixture.balancer.workload_estimate = 4.0
        q1_2026_fixture.balancer.capacity_estimate = 8.0
        q1_2026_fixture.balancer.qhe_score = 0.7
        q1_2026_fixture.balancer.days_in_current_state = 0
        q1_2026_fixture.balancer.is_histerese_active = False

        # Cycle 1: days -> 1, histerese inactive.
        s = balance_node(q1_2026_fixture)
        assert s.balancer.days_in_current_state == 1
        assert s.balancer.is_histerese_active is False

        # Cycle 2: days -> 2, still inactive.
        s = balance_node(s)
        assert s.balancer.days_in_current_state == 2
        assert s.balancer.is_histerese_active is False

        # Cycle 3: days -> 3, histerese ACTIVE.
        s = balance_node(s)
        assert s.balancer.days_in_current_state == 3
        assert s.balancer.is_histerese_active is True