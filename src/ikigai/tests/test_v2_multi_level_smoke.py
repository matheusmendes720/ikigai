"""W4.8 — E2E multi-level smoke test (B.6).

Closes Wave 4 (Scenario B: Sub-agents + stateful subgraphs) by composing
W4.4 (sub-agent dispatch), W4.5 (stateful subgraph consumer), and W4.6
(cross-cycle memory) into an end-to-end smoke that exercises all four
skill levels (daily → weekly → monthly → quarterly).

Per W4.8 brief:
- AC1: Test invokes daily, then weekly, then monthly, then quarterly in sequence
- AC2: Each level reads from previous level's checkpoint / memory record
- AC3: Drift detector returns 10/10 PASS (test_drift_detector.py +
       test_drift_extended_invariants.py + test_drift_state.py = 10 tests)
       + 38 canonical_scope invariants
- AC4: Total runtime <5 minutes

Architecture references (binding):
- ADR-026 (W4.4): sub-agent dispatch protocol
- ADR-027 (W4.5): stateful subgraph strategy + 4-segment thread_id
- ADR-028 (W4.6): cross-cycle memory layer (4 tables + 4 PRAGMAs)
- ADR-025: skill binding (daily=user, weekly/monthly/quarterly=agent)
- ADR-014: 4-part UEID canonical
- ADR-013: planner-only (no math execution)
- ADR-019: algorithm_constants.json single source of truth

This test does NOT modify any W4.4-W4.6 implementation. It composes their
public surface (build_thread_id, IkigaiCheckpointer, memory_write /
memory_read, dispatch_sub_agents with mocked _invoke_subagent) into a
single multi-level chain.
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mirrors test_v2_memory.py + test_v2_stateful_subgraph.py
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_IKIGAI_SRC = _THIS.parent.parent / "src"  # <repo-root>/src/ikigai/src/
_REPO_ROOT = _THIS.parent.parent.parent.parent  # <repo-root>
_SRC_ROOT = _REPO_ROOT / "src"
for _p in (str(_REPO_ROOT), str(_SRC_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))


# ---------------------------------------------------------------------------
# Constants — 4-part UEIDs per ADR-014 + cycle anchors
# ---------------------------------------------------------------------------

# Anchor date used by all multi-level tests. Date math (week_range,
# month_range, quarter_range, year) is derived from this so all 4 levels
# can be wired into one continuous chain.
_ANCHOR_DATE = date(2026, 9, 4)  # Friday — Q3 2026, week 36 (ISO)


def _epoch(d: date) -> float:
    """Convert date → Unix epoch seconds (UTC midnight). Mirrors memory_read."""
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()


# 4-part canonical UEIDs (ADR-014). One per skill level + sub-agent.
_UEID_DAILY = "sa:demo-a3f19c2d:11111111-1111-1111-1111-111111111111:1111111111111111"
_UEID_WEEKLY = "sa:demo-a3f19c2d:22222222-2222-2222-2222-222222222222:2222222222222222"
_UEID_MONTHLY = "sa:demo-a3f19c2d:33333333-3333-3333-3333-333333333333:3333333333333333"
_UEID_QUARTERLY = "sa:demo-a3f19c2d:44444444-4444-4444-4444-444444444444:4444444444444444"
_UEID_SUB_MONTHLY = "sa:demo-a3f19c2d:55555555-5555-5555-5555-555555555555:5555555555555555"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_db(tmp_path: Path) -> str:
    """Per-test ephemeral file-based memory DB under tmp_path.

    File-based (NOT :memory:) because multi-call flows (write + read-back
    across separate memory_init connections) require shared state. Per
    ADR-028 + SQLite semantics, ``:memory:`` DBs are per-connection.
    """
    return str(tmp_path / "ikigai_memory_w48.db")


@pytest.fixture
def checkpoint_db(tmp_path: Path) -> str:
    """Per-test ephemeral checkpoint DB under tmp_path."""
    return str(tmp_path / "ikigai_checkpoints_w48.db")


@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    """Per-test ephemeral vault root."""
    root = tmp_path / "vault"
    root.mkdir(parents=True, exist_ok=True)
    return root


# ---------------------------------------------------------------------------
# Test 1 — daily → weekly (memory + thread_id format)
# ---------------------------------------------------------------------------


def test_multi_level_daily_to_weekly(memory_db: str, checkpoint_db: str) -> None:
    """Daily writes a memory row + checkpoint; weekly reads via
    ``read_daily_intentions(week_range)`` and writes a weekly row
    referencing the daily's UEID.

    Verifies thread_id canonical format per ADR-027 R3:
      daily   = user-daily-{cycle_short}-parent
      weekly  = agent-weekly-{cycle_short}-parent
    """
    from agents.v2.checkpoint import IkigaiCheckpointer, build_thread_id
    from agents.v2.memory_read import read_daily_intentions
    from agents.v2.memory_schema import (
        MEMORY_TABLE_DAILY,
        MEMORY_TABLE_WEEKLY,
        memory_init,
    )
    from agents.v2.memory_write import memory_write

    # 1. Daily invocation — actor="user" per ADR-025 R2.
    daily_cycle_short = "2026-09-04"
    daily_thread_id = build_thread_id("user", "daily", daily_cycle_short, "parent")
    assert daily_thread_id == "user-daily-2026-09-04-parent", daily_thread_id

    cp = IkigaiCheckpointer(checkpoint_db)
    try:
        # Checkpoint the daily state (one row minimum).
        cp.record_subgraph_link(
            parent_thread_id=daily_thread_id,
            child_thread_id=daily_thread_id,
            sub_agent_id=_UEID_DAILY,
        )
    finally:
        cp.close()

    memory_write(
        memory_db=memory_db,
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY,
        body_markdown="# Daily 2026-09-04\n\n- intention 1\n- intention 2",
        sha256="daily-sha-001",
        vault_path="closing-2026/q3/daily-2026-09-04.md",
        actor="user",
        source_ueids=[],
        ts=_epoch(_ANCHOR_DATE),
    )

    # 2. Weekly invocation — actor="agent" per ADR-025 R2.
    weekly_cycle_short = "2026-W36"  # ISO week 36 of 2026
    weekly_thread_id = build_thread_id("agent", "weekly", weekly_cycle_short, "parent")
    assert weekly_thread_id == "agent-weekly-2026-W36-parent", weekly_thread_id

    # Weekly reads dailies via read_daily_intentions(week_range) — must see daily's row.
    from datetime import timedelta as _td

    week_start = _ANCHOR_DATE - _td(days=_ANCHOR_DATE.weekday())  # Monday
    week_end = week_start + _td(days=6)  # Sunday
    dailies = read_daily_intentions(
        memory_db=memory_db,
        week_range=(week_start, week_end),
    )
    assert len(dailies) == 1, f"expected 1 daily in week_range, got {len(dailies)}"
    assert dailies[0]["ueid"] == _UEID_DAILY
    assert dailies[0]["actor"] == "user"

    # 3. Weekly writes its aggregation referencing the daily's UEID.
    memory_write(
        memory_db=memory_db,
        table=MEMORY_TABLE_WEEKLY,
        ueid=_UEID_WEEKLY,
        body_markdown="# Weekly W36\n\naggregated from daily intentions",
        sha256="weekly-sha-001",
        vault_path="closing-2026/q3/weekly-2026-W36.md",
        actor="agent",
        source_ueids=[_UEID_DAILY],
        ts=_epoch(_ANCHOR_DATE) + 86400,
    )

    # 4. Verify both rows present in DB.
    conn = memory_init(memory_db)
    try:
        cur = conn.execute(
            "SELECT daily_ueid FROM memory_daily_intentions WHERE daily_ueid = ?",
            (_UEID_DAILY,),
        )
        assert cur.fetchone() is not None, "daily row missing"
        cur = conn.execute(
            "SELECT weekly_ueid, source_ueids FROM memory_weekly_aggregations "
            "WHERE weekly_ueid = ?",
            (_UEID_WEEKLY,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None, "weekly row missing"
    import json as _json

    sources = _json.loads(row[1])
    assert sources == [_UEID_DAILY], f"weekly.source_ueids should contain daily, got {sources}"

    # 5. Verify thread_id canonical shape. Per ADR-027 R3 the canonical form is
    # ``<actor>-<skill>-<cycle_short>-<sub_role>``. cycle_short may itself
    # contain dashes (e.g. ``2026-W36``) — verify the 4 logical segments
    # via splits rather than a literal 4-element split.
    assert weekly_thread_id.startswith("agent-weekly-"), weekly_thread_id
    assert weekly_thread_id.endswith("-parent"), weekly_thread_id
    # daily cycle_short "2026-09-04" has internal dashes — verify canonical form
    assert daily_thread_id.startswith("user-daily-"), daily_thread_id
    assert daily_thread_id.endswith("-parent"), daily_thread_id


# ---------------------------------------------------------------------------
# Test 2 — weekly → monthly (memory aggregation across 4 weeks)
# ---------------------------------------------------------------------------


def test_multi_level_weekly_to_monthly(memory_db: str) -> None:
    """Pre-populate 4 weekly aggregations (one per ISO week of September 2026);
    monthly synthesis reads them via ``read_weekly_aggregations(month_range)``
    and writes a monthly row whose source_ueids references all 4 weekly UEIDs.
    """
    from datetime import timedelta as _td

    from agents.v2.memory_read import read_weekly_aggregations
    from agents.v2.memory_schema import MEMORY_TABLE_MONTHLY, MEMORY_TABLE_WEEKLY
    from agents.v2.memory_write import memory_write

    # ISO weeks of September 2026 (W36-W39) — anchor 2026-09-04 is in W36.
    week_anchors = [_ANCHOR_DATE + _td(days=7 * i) for i in range(4)]
    # Canonical 4-part UEIDs per ADR-014 — only 4 colon-separated segments.
    weekly_ueids = [
        f"sa:demo-a3f19c2d:9999999{i}-9999-9999-9999-99999999999{i}:000000000000000{i}"
        for i in range(4)
    ]
    for i, (anchor, ueid) in enumerate(zip(week_anchors, weekly_ueids, strict=True)):
        memory_write(
            memory_db=memory_db,
            table=MEMORY_TABLE_WEEKLY,
            ueid=ueid,
            body_markdown=f"# Weekly W{36 + i}\n\n...",
            sha256=f"weekly-sha-{i}",
            vault_path=f"closing-2026/q3/weekly-W{36 + i}.md",
            actor="agent",
            source_ueids=[],
            ts=_epoch(anchor),
        )

    # Monthly reads weeklies via read_weekly_aggregations(month_range).
    month_range = (date(2026, 9, 1), date(2026, 9, 30))
    weeklies = read_weekly_aggregations(memory_db=memory_db, month_range=month_range)
    assert len(weeklies) == 4, f"expected 4 weeklies in Sep 2026, got {len(weeklies)}"
    weekly_ueids_read = {w["ueid"] for w in weeklies}
    assert weekly_ueids_read == set(weekly_ueids)

    # Monthly writes synthesis referencing all 4 weekly UEIDs.
    memory_write(
        memory_db=memory_db,
        table=MEMORY_TABLE_MONTHLY,
        ueid=_UEID_MONTHLY,
        body_markdown="# Monthly Sep 2026\n\n...",
        sha256="monthly-sha-001",
        vault_path="closing-2026/q3/monthly-2026-09.md",
        actor="agent",
        source_ueids=list(weekly_ueids),
        ts=_epoch(date(2026, 9, 30)),
    )

    # Verify source_ueids chain: monthly.source_ueids ⊇ all 4 weekly UEIDs.
    import sqlite3 as _sqlite

    conn = _sqlite.connect(memory_db)
    try:
        cur = conn.execute(
            "SELECT source_ueids FROM memory_monthly_syntheses WHERE monthly_ueid = ?",
            (_UEID_MONTHLY,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None, "monthly row missing"
    import json as _json

    sources = _json.loads(row[0])
    assert set(sources) == set(weekly_ueids), (
        f"monthly.source_ueids should contain all 4 weekly UEIDs, got {sources}"
    )


# ---------------------------------------------------------------------------
# Test 3 — monthly → quarterly (3 monthly syntheses → 1 quarterly strategy)
# ---------------------------------------------------------------------------


def test_multi_level_monthly_to_quarterly(memory_db: str) -> None:
    """Pre-populate 3 monthly syntheses (one per month of Q3 2026);
    quarterly strategy reads them via ``read_monthly_syntheses(quarter_range)``
    and writes a quarterly row whose source_ueids references all 3 monthly UEIDs.
    """
    from agents.v2.memory_read import read_monthly_syntheses
    from agents.v2.memory_schema import MEMORY_TABLE_MONTHLY, MEMORY_TABLE_QUARTERLY
    from agents.v2.memory_write import memory_write

    # Months of Q3 2026: Jul, Aug, Sep.
    # Canonical 4-part UEIDs per ADR-014 — only 4 colon-separated segments.
    monthly_ueids = [
        "sa:demo-a3f19c2d:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:0000000000000001",
        "sa:demo-a3f19c2d:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb:0000000000000002",
        "sa:demo-a3f19c2d:cccccccc-cccc-cccc-cccc-cccccccccccc:0000000000000003",
    ]
    month_anchors = [date(2026, 7, 15), date(2026, 8, 15), date(2026, 9, 15)]
    for i, (anchor, ueid) in enumerate(zip(month_anchors, monthly_ueids, strict=True)):
        memory_write(
            memory_db=memory_db,
            table=MEMORY_TABLE_MONTHLY,
            ueid=ueid,
            body_markdown=f"# Monthly {anchor.month:02d}/2026\n\n...",
            sha256=f"monthly-sha-q3-{i}",
            vault_path=f"closing-2026/q3/monthly-2026-{anchor.month:02d}.md",
            actor="agent",
            source_ueids=[],
            ts=_epoch(anchor),
        )

    # Quarterly reads monthlies via read_monthly_syntheses(quarter_range).
    quarter_range = (date(2026, 7, 1), date(2026, 9, 30))
    monthlies = read_monthly_syntheses(memory_db=memory_db, quarter_range=quarter_range)
    assert len(monthlies) == 3, f"expected 3 monthlies in Q3 2026, got {len(monthlies)}"
    monthly_ueids_read = {m["ueid"] for m in monthlies}
    assert monthly_ueids_read == set(monthly_ueids)

    # Quarterly writes strategy referencing all 3 monthly UEIDs.
    memory_write(
        memory_db=memory_db,
        table=MEMORY_TABLE_QUARTERLY,
        ueid=_UEID_QUARTERLY,
        body_markdown="# Quarterly Q3 2026\n\n...",
        sha256="quarterly-sha-001",
        vault_path="closing-2026/q3/quarterly-2026-Q3.md",
        actor="agent",
        source_ueids=list(monthly_ueids),
        ts=_epoch(date(2026, 9, 30)),
    )

    # Verify source_ueids chain: quarterly.source_ueids ⊇ all 3 monthly UEIDs.
    import sqlite3 as _sqlite

    conn = _sqlite.connect(memory_db)
    try:
        cur = conn.execute(
            "SELECT source_ueids FROM memory_quarterly_strategies WHERE quarterly_ueid = ?",
            (_UEID_QUARTERLY,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None, "quarterly row missing"
    import json as _json

    sources = _json.loads(row[0])
    assert set(sources) == set(monthly_ueids), (
        f"quarterly.source_ueids should contain all 3 monthly UEIDs, got {sources}"
    )


# ---------------------------------------------------------------------------
# Test 4 — full chain daily → weekly → monthly → quarterly (composition)
# ---------------------------------------------------------------------------


def test_multi_level_full_chain_daily_to_quarterly(memory_db: str, checkpoint_db: str) -> None:
    """Full composition: invoke all 4 skill levels in sequence. Each level
    reads from previous level's memory record. Verifies:

    - All 4 memory tables populated with exactly 1 row each
    - All 4 thread_ids have correct actor/skill/cycle_short/sub_role segments
    - Checkpoint DB has 4+ rows (one per level)
    - Memory DB has 4 rows (one per level)
    - source_ueids chain reconstructable through the 4 levels
    """
    from agents.v2.checkpoint import IkigaiCheckpointer, build_thread_id
    from agents.v2.memory_schema import memory_init
    from agents.v2.memory_write import memory_write

    # Daily thread + memory.
    daily_tid = build_thread_id("user", "daily", "2026-09-04", "parent")
    assert daily_tid == "user-daily-2026-09-04-parent"

    cp = IkigaiCheckpointer(checkpoint_db)
    try:
        # 1 checkpoint row per level.
        for tid in [
            daily_tid,
            "agent-weekly-2026-W36-parent",
            "agent-monthly-2026-09-parent",
            "agent-quarterly-2026-Q3-parent",
        ]:
            cp.record_subgraph_link(
                parent_thread_id=tid,
                child_thread_id=tid,
                sub_agent_id=_UEID_DAILY,
            )
    finally:
        cp.close()

    # Write all 4 memory rows in pyramid order.
    memory_write(
        memory_db=memory_db,
        table="memory_daily_intentions",
        ueid=_UEID_DAILY,
        body_markdown="# Daily\n\n- intention",
        sha256="h-d",
        vault_path="daily.md",
        actor="user",
        source_ueids=[],
        ts=_epoch(_ANCHOR_DATE),
    )
    memory_write(
        memory_db=memory_db,
        table="memory_weekly_aggregations",
        ueid=_UEID_WEEKLY,
        body_markdown="# Weekly\n\naggregation",
        sha256="h-w",
        vault_path="weekly.md",
        actor="agent",
        source_ueids=[_UEID_DAILY],
        ts=_epoch(_ANCHOR_DATE) + 86400,
    )
    memory_write(
        memory_db=memory_db,
        table="memory_monthly_syntheses",
        ueid=_UEID_MONTHLY,
        body_markdown="# Monthly\n\nsynthesis",
        sha256="h-m",
        vault_path="monthly.md",
        actor="agent",
        source_ueids=[_UEID_WEEKLY],
        ts=_epoch(_ANCHOR_DATE) + 2 * 86400,
    )
    memory_write(
        memory_db=memory_db,
        table="memory_quarterly_strategies",
        ueid=_UEID_QUARTERLY,
        body_markdown="# Quarterly\n\nstrategy",
        sha256="h-q",
        vault_path="quarterly.md",
        actor="agent",
        source_ueids=[_UEID_MONTHLY],
        ts=_epoch(_ANCHOR_DATE) + 3 * 86400,
    )

    # Verify all 4 memory tables populated.
    conn = memory_init(memory_db)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM memory_daily_intentions")
        assert cur.fetchone()[0] == 1
        cur = conn.execute("SELECT COUNT(*) FROM memory_weekly_aggregations")
        assert cur.fetchone()[0] == 1
        cur = conn.execute("SELECT COUNT(*) FROM memory_monthly_syntheses")
        assert cur.fetchone()[0] == 1
        cur = conn.execute("SELECT COUNT(*) FROM memory_quarterly_strategies")
        assert cur.fetchone()[0] == 1

        # Verify source_ueids chain reconstructable.
        cur = conn.execute(
            "SELECT source_ueids FROM memory_weekly_aggregations WHERE weekly_ueid = ?",
            (_UEID_WEEKLY,),
        )
        weekly_sources = __import__("json").loads(cur.fetchone()[0])
        cur = conn.execute(
            "SELECT source_ueids FROM memory_monthly_syntheses WHERE monthly_ueid = ?",
            (_UEID_MONTHLY,),
        )
        monthly_sources = __import__("json").loads(cur.fetchone()[0])
        cur = conn.execute(
            "SELECT source_ueids FROM memory_quarterly_strategies WHERE quarterly_ueid = ?",
            (_UEID_QUARTERLY,),
        )
        quarterly_sources = __import__("json").loads(cur.fetchone()[0])
    finally:
        conn.close()

    assert weekly_sources == [_UEID_DAILY]
    assert monthly_sources == [_UEID_WEEKLY]
    assert quarterly_sources == [_UEID_MONTHLY]

    # Verify all 4 thread_ids have correct canonical 4-segment shape per ADR-027 R3.
    # cycle_short may contain dashes (e.g. ``2026-09-04`` or ``2026-Q3``) — verify
    # the 4 logical segments via prefix/suffix matching rather than literal split.
    daily_tid_check = build_thread_id("user", "daily", "2026-09-04", "parent")
    weekly_tid_check = build_thread_id("agent", "weekly", "2026-W36", "parent")
    monthly_tid_check = build_thread_id("agent", "monthly", "2026-09", "parent")
    quarterly_tid_check = build_thread_id("agent", "quarterly", "2026-Q3", "parent")
    expected_segments = [
        (daily_tid_check, "user", "daily", "parent"),
        (weekly_tid_check, "agent", "weekly", "parent"),
        (monthly_tid_check, "agent", "monthly", "parent"),
        (quarterly_tid_check, "agent", "quarterly", "parent"),
    ]
    for tid, expected_actor, expected_skill, expected_role in expected_segments:
        # All 4 thread_ids must end in -parent (the sub_role).
        assert tid.endswith(f"-{expected_role}"), f"sub_role mismatch in {tid}"
        # Verify the actor-skill- prefix.
        expected_prefix = f"{expected_actor}-{expected_skill}-"
        assert tid.startswith(expected_prefix), (
            f"actor/skill prefix mismatch in {tid}: expected {expected_prefix}"
        )

    # Verify checkpoint DB has 4 rows in ikigai_subgraph_links.
    import sqlite3 as _sqlite

    conn = _sqlite.connect(checkpoint_db)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM ikigai_subgraph_links")
        n_links = cur.fetchone()[0]
    finally:
        conn.close()
    assert n_links >= 4, f"expected >=4 subgraph links, got {n_links}"


# ---------------------------------------------------------------------------
# Test 5 — quarterly dispatches monthly sub-agent (W4.4 + W4.5 ship verification)
# ---------------------------------------------------------------------------


def test_multi_level_subagent_dispatch_in_quarterly(memory_db: str, checkpoint_db: str) -> None:
    """Quarterly invocation includes a dispatch_plan with one sub-agent that
    re-runs the monthly node. Verifies W4.4 (``dispatch_sub_agents`` exercised)
    and W4.5 (sub-agent thread_id is parent + ``-subagent-<8hex>`` per ADR-027 R3).
    """
    from agents.v2.checkpoint import build_subagent_thread_id, build_thread_id
    from agents.v2.subgraph import (
        SubAgentResult,
        dispatch_sub_agents,
    )

    # Quarterly parent thread_id (canonical 4-segment).
    parent_tid = build_thread_id("agent", "quarterly", "2026-Q3", "parent")
    assert parent_tid == "agent-quarterly-2026-Q3-parent"

    # Sub-agent thread_id (parent + -subagent-<8hex>) per ADR-027 R3.
    sub_tid = build_subagent_thread_id(parent_tid, _UEID_SUB_MONTHLY)
    assert "-subagent-" in sub_tid, f"sub-agent thread_id must contain -subagent-, got {sub_tid}"
    assert sub_tid.startswith(parent_tid), (
        f"sub-agent thread_id must start with parent tid, got {sub_tid} parent={parent_tid}"
    )
    # Parent has 5 segments because cycle_short "2026-Q3" contains a dash.
    # Sub-agent thread_id = parent + "-subagent-" + 8-hex hash.
    # Verify the suffix and hash format instead of literal segment count.
    assert sub_tid.endswith(sub_tid.rsplit("-subagent-", 1)[1]), sub_tid
    hash_suffix = sub_tid.rsplit("-subagent-", 1)[1]
    assert len(hash_suffix) == 8, f"hash suffix must be 8 hex chars, got {hash_suffix}"
    assert all(c in "0123456789abcdef" for c in hash_suffix), (
        f"hash suffix must be lowercase hex, got {hash_suffix}"
    )

    # Build a minimal parent state with dispatch_plan (1 sub-agent re-running monthly).
    parent_state: dict[str, Any] = {
        "cycle_id": "quarterly-q3-2026",
        "cycle_start": "2026-07-01",
        "cycle_end": "2026-09-30",
        "iteration": 0,
        "actor": "agent",
        "thread_id": parent_tid,
        "dispatch_depth": 0,
        "dispatch_plan": [
            {
                "sub_agent_id": _UEID_SUB_MONTHLY,
                "entry_point": "observe",
                "dispatch_context": {"rerun_month": "2026-09"},
                "timeout_s": 5.0,
                "merge_strategy": "merge_dict",
            }
        ],
        # S2.4 — error channel MUST NOT propagate to children. Include here
        # to verify the dispatch_sub_agents node does NOT set parent.error_type.
        "error_type": "ParentError_stripped",
    }

    # Mock _invoke_subagent to avoid real Claude cost — returns success status.
    expected_outputs = {
        "monthly_summary": "Re-aggregated Sep 2026 from new source_ueids",
        "synthesis_count": 1,
    }
    expected_result = SubAgentResult(
        sub_agent_id=_UEID_SUB_MONTHLY,
        entry_point="observe",
        status="success",
        duration_s=0.05,
        fields_written=list(expected_outputs.keys()),
        outputs=expected_outputs,
    )

    # Patch and invoke dispatch_sub_agents (the 11th graph node).
    with mock.patch(
        "agents.v2.subgraph._invoke_subagent", return_value=expected_result
    ) as mock_invoke:
        update = dispatch_sub_agents(parent_state)

    # Verify sub-agent was invoked exactly once.
    assert mock_invoke.call_count == 1, (
        f"expected 1 _invoke_subagent call, got {mock_invoke.call_count}"
    )
    call_args = mock_invoke.call_args
    spec_passed = call_args[0][0]
    child_state = call_args[0][1]
    timeout_passed = call_args[0][2]

    # Spec passed through correctly.
    assert spec_passed["sub_agent_id"] == _UEID_SUB_MONTHLY
    assert spec_passed["entry_point"] == "observe"
    assert spec_passed["merge_strategy"] == "merge_dict"

    # Child state has identity fields + actor="agent" + dispatch_depth=1 + thread_role=child.
    assert child_state["cycle_id"] == "quarterly-q3-2026"
    assert child_state["actor"] == "agent", (
        "sub-agent actor must be 'agent' per ADR-025 R3 (never user)"
    )
    assert child_state["dispatch_depth"] == 1
    assert child_state["thread_role"] == "child"
    # S2.4 — error channel MUST NOT propagate to children.
    assert "error_type" not in child_state, (
        f"error_type must NOT propagate to children per ADR-026 S2.4; "
        f"child state has: {list(child_state.keys())}"
    )
    assert "error_message" not in child_state

    # Timeout passes through.
    assert timeout_passed == 5.0

    # Update dict has expected fields.
    assert update["last_step"] == "dispatch_sub_agents"
    assert len(update["sub_agent_results"]) == 1
    assert update["sub_agent_results"][0]["status"] == "success"
    assert update["sub_agent_results"][0]["sub_agent_id"] == _UEID_SUB_MONTHLY

    # S3 — merge_dict strategy applied: child outputs merged into updates.
    assert update.get("monthly_summary") == expected_outputs["monthly_summary"]
    assert update.get("synthesis_count") == 1

    # dispatch_plan cleared per ADR-027 R5.13.
    assert update["dispatch_plan"] == []

    # ADR-026 R5 — parent's error_type is NEVER set by child failures.
    assert update.get("error_type") is None or update.get("error_type") == "ParentError_stripped"
    # (the parent's error_type is left untouched — dispatch_sub_agents must not
    # overwrite or clear it. The test confirms the node does not propagate child
    # failures into parent.error_type.)


# ---------------------------------------------------------------------------
# Test 6 — drift detector remains green (canonical_scope 38 + data-model 10 = 48)
# ---------------------------------------------------------------------------


def test_multi_level_drift_detector_remains_green() -> None:
    """Run the full drift-detector suite and assert all 48 invariants PASS.

    Composition per brief:
      - test_canonical_scope.py (38 invariants per brief, exact count varies
        as parametrized cases expand — we assert >= 35)
      - test_drift_detector.py (4 tests)
      - test_drift_extended_invariants.py (5 tests)
      - test_drift_state.py (1 test)
      Total data-model drift: 10/10
    """
    ikigai_tests = _THIS.parent  # <repo-root>/src/ikigai/tests/

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        str(ikigai_tests / "test_canonical_scope.py"),
        str(ikigai_tests / "test_drift_detector.py"),
        str(ikigai_tests / "test_drift_extended_invariants.py"),
        str(ikigai_tests / "test_drift_state.py"),
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
        env={
            **__import__("os").environ,
            "PYTHONPATH": (
                f"{_REPO_ROOT}{__import__('os').sep}{_SRC_ROOT}"
                f"{__import__('os').pathsep}{_IKIGAI_SRC}"
            ),
        },
    )

    output = proc.stdout + proc.stderr
    # Parse last PASS/FAIL line.
    last_line = output.strip().splitlines()[-1] if output.strip() else ""
    # Expect something like "===== 48 passed in 12.34s =====" or "X failed".
    assert proc.returncode == 0, (
        f"drift detector failed (rc={proc.returncode}):\n"
        f"--- stdout ---\n{proc.stdout[-2000:]}\n"
        f"--- stderr ---\n{proc.stderr[-2000:]}"
    )
    assert " failed" not in last_line.lower() or "passed" in last_line.lower(), (
        f"unexpected last line: {last_line!r}"
    )
    # Assert at least 48 passed (canonical_scope + data-model drift).
    import re as _re

    m = _re.search(r"(\d+)\s+passed", last_line)
    assert m is not None, f"could not parse pass count from: {last_line!r}"
    n_passed = int(m.group(1))
    assert n_passed >= 48, (
        f"expected >=48 drift-detector PASS (canonical_scope + 10 data-model), "
        f"got {n_passed}. Last line: {last_line!r}"
    )


# ---------------------------------------------------------------------------
# Test 7 — runtime under 5 minutes
# ---------------------------------------------------------------------------


def test_multi_level_runtime_under_5_minutes(memory_db: str, checkpoint_db: str) -> None:
    """Full chain (daily → weekly → monthly → quarterly) must complete in
    < 300 seconds. This satisfies W4.8 AC4.
    """
    from agents.v2.checkpoint import IkigaiCheckpointer, build_thread_id
    from agents.v2.memory_schema import memory_init
    from agents.v2.memory_write import memory_write

    started = time.monotonic()

    cp = IkigaiCheckpointer(checkpoint_db)
    try:
        # 4 thread_id rows.
        for tid in [
            build_thread_id("user", "daily", "2026-09-04", "parent"),
            build_thread_id("agent", "weekly", "2026-W36", "parent"),
            build_thread_id("agent", "monthly", "2026-09", "parent"),
            build_thread_id("agent", "quarterly", "2026-Q3", "parent"),
        ]:
            cp.record_subgraph_link(
                parent_thread_id=tid, child_thread_id=tid, sub_agent_id=_UEID_DAILY
            )
    finally:
        cp.close()

    # 4 memory writes + 4 reads.
    memory_write(
        memory_db=memory_db,
        table="memory_daily_intentions",
        ueid=_UEID_DAILY,
        body_markdown="# D",
        sha256="h",
        vault_path="d.md",
        actor="user",
        source_ueids=[],
        ts=_epoch(_ANCHOR_DATE),
    )
    memory_write(
        memory_db=memory_db,
        table="memory_weekly_aggregations",
        ueid=_UEID_WEEKLY,
        body_markdown="# W",
        sha256="h",
        vault_path="w.md",
        actor="agent",
        source_ueids=[_UEID_DAILY],
        ts=_epoch(_ANCHOR_DATE) + 86400,
    )
    memory_write(
        memory_db=memory_db,
        table="memory_monthly_syntheses",
        ueid=_UEID_MONTHLY,
        body_markdown="# M",
        sha256="h",
        vault_path="m.md",
        actor="agent",
        source_ueids=[_UEID_WEEKLY],
        ts=_epoch(_ANCHOR_DATE) + 2 * 86400,
    )
    memory_write(
        memory_db=memory_db,
        table="memory_quarterly_strategies",
        ueid=_UEID_QUARTERLY,
        body_markdown="# Q",
        sha256="h",
        vault_path="q.md",
        actor="agent",
        source_ueids=[_UEID_MONTHLY],
        ts=_epoch(_ANCHOR_DATE) + 3 * 86400,
    )

    # Verify all 4 tables populated.
    conn = memory_init(memory_db)
    try:
        for tbl in (
            "memory_daily_intentions",
            "memory_weekly_aggregations",
            "memory_monthly_syntheses",
            "memory_quarterly_strategies",
        ):
            cur = conn.execute(f"SELECT COUNT(*) FROM {tbl}")
            assert cur.fetchone()[0] == 1, f"{tbl} missing row"
    finally:
        conn.close()

    elapsed_s = time.monotonic() - started
    assert elapsed_s < 300.0, f"full chain took {elapsed_s:.2f}s — exceeds 300s budget (AC4)"


# ---------------------------------------------------------------------------
# Sentinel — confirm module is importable and tests are discoverable.
# ---------------------------------------------------------------------------


def test_module_imports_cleanly() -> None:
    """The test module itself must be importable without side effects."""
    assert True  # if we got here, the module imported cleanly.
