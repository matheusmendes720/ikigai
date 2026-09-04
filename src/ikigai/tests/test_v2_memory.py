"""W4.6 — Cross-cycle memory layer (B-N12) tests.

Per ADR-028 (cross-cycle memory layer):
- R1: 4 SQLite tables (memory_daily_intentions, memory_weekly_aggregations,
      memory_monthly_syntheses, memory_quarterly_strategies)
- R3: 4-part UEID canonical for all ``*_ueid`` fields + ``source_ueids``
- R4: Atomic vault_write + memory_write
- R5: 4 read functions with actor scoping
- R8: Prune-on-write via 4 MEMORY_RETENTION_* keys
- R11: Schema migration stub (_migrate_v1_to_v2 raises NotImplementedError)
- R12: 4 SQLite PRAGMAs (WAL, synchronous=NORMAL, busy_timeout=5000, foreign_keys=ON)

Acceptance criteria (per W4.6 brief):
- [x] Daily -> weekly rollup works (daily state visible in weekly invocation)
- [x] Weekly -> monthly -> quarterly rollup works
- [x] Memory layer is append-only (no overwrites)
- [x] Drift detector invariant: memory schema enforced

Tests use ``:memory:`` SQLite (PRAGMAs still applied) for fast isolated
runs. Integration tests use ``tmp_path`` to verify the on-disk DB is
created at the canonical path.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup (mirrors test_v2_stateful_subgraph.py)
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_IKIGAI_SRC = _THIS.parent.parent / "src"
_REPO_ROOT = _THIS.parent.parent.parent.parent
_SRC_ROOT = _REPO_ROOT / "src"
for _p in (str(_REPO_ROOT), str(_SRC_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Valid 4-part UEIDs for tests.
_UEID_DAILY_1 = "sa:demo-a3f19c2d:11111111-1111-1111-1111-111111111111:1111111111111111"
_UEID_DAILY_2 = "sa:demo-a3f19c2d:22222222-2222-2222-2222-222222222222:2222222222222222"
_UEID_DAILY_3 = "sa:demo-a3f19c2d:33333333-3333-3333-3333-333333333333:3333333333333333"
_UEID_WEEKLY_1 = "sa:demo-a3f19c2d:44444444-4444-4444-4444-444444444444:4444444444444444"
_UEID_WEEKLY_2 = "sa:demo-a3f19c2d:55555555-5555-5555-5555-555555555555:5555555555555555"
_UEID_MONTHLY_1 = "sa:demo-a3f19c2d:66666666-6666-6666-6666-666666666666:6666666666666666"
_UEID_QUARTERLY_1 = "sa:demo-a3f19c2d:77777777-7777-7777-7777-777777777777:7777777777777777"

# Invalid 5-part UEID (per ADR-014 R3 — 4-part is canonical, 5-part rejected).
_UEID_INVALID_5PART = "sa:demo-a3f19c2d:extra:11111111-1111-1111-1111-111111111111:1111111111111111"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_db(tmp_path: Path) -> str:
    """Per-test ephemeral file-based memory DB under tmp_path.

    SQLite ``:memory:`` databases are PER-CONNECTION — each call to
    ``memory_init(":memory:")`` creates a fresh empty DB. To test
    multi-call flows (write + read-back, prune, atomic rollback), we
    need a file-based DB so all connections share the same store.
    """
    return str(tmp_path / "ikigai_memory_test.db")


@pytest.fixture
def in_memory_db(tmp_path: Path) -> str:
    """File-based DB (used to be in-memory SQLite).

    Per ADR-028 + SQLite semantics: ``:memory:`` databases are PER-CONNECTION,
    so multi-call flows (write + read-back, prune, atomic rollback) need a
    file-based DB to share state. Returns a per-test ephemeral path.
    """
    return str(tmp_path / "ikigai_memory_inmem_test.db")


@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    """Per-test ephemeral vault root."""
    root = tmp_path / "vault"
    root.mkdir(parents=True, exist_ok=True)
    return root


# ---------------------------------------------------------------------------
# AC0 — Schema bootstrap + PRAGMAs (R1, R12)
# ---------------------------------------------------------------------------


def test_memory_schema_version_constant_is_1() -> None:
    """MEMORY_SCHEMA_VERSION MUST equal 1 (ADR-028 R11)."""
    from agents.v2.memory_schema import MEMORY_SCHEMA_VERSION

    assert MEMORY_SCHEMA_VERSION == 1


def test_memory_default_db_filename_is_ikigai_memory_db() -> None:
    """Default DB filename MUST be 'ikigai_memory.db' (ADR-028 R1)."""
    from agents.v2.memory_schema import MEMORY_DEFAULT_DB_FILENAME

    assert MEMORY_DEFAULT_DB_FILENAME == "ikigai_memory.db"


def test_memory_init_creates_4_tables(in_memory_db: str) -> None:
    """memory_init must create 4 tables (ADR-028 R1)."""
    from agents.v2.memory_schema import memory_init

    conn = memory_init(in_memory_db)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('memory_daily_intentions', 'memory_weekly_aggregations', "
            "             'memory_monthly_syntheses', 'memory_quarterly_strategies') "
            "ORDER BY name ASC"
        )
        tables = sorted(row[0] for row in cur.fetchall())
    finally:
        conn.close()
    assert tables == sorted(
        [
            "memory_daily_intentions",
            "memory_weekly_aggregations",
            "memory_monthly_syntheses",
            "memory_quarterly_strategies",
        ]
    )


def test_memory_init_applies_4_pragmas(memory_db: str) -> None:
    """memory_init must apply WAL + 4 PRAGMAs (ADR-028 R12).

    Uses a file-based DB because SQLite ``PRAGMA journal_mode = WAL`` is
    silently ignored on ``:memory:`` (returns 'memory' instead of 'wal').
    """
    from agents.v2.memory_schema import memory_init

    conn = memory_init(memory_db)
    try:
        # journal_mode
        cur = conn.execute("PRAGMA journal_mode")
        row = cur.fetchone()
        assert row is not None, "PRAGMA journal_mode returned no row"
        assert row[0].lower() == "wal", f"PRAGMA journal_mode must be WAL, got {row}"
        # synchronous
        cur = conn.execute("PRAGMA synchronous")
        row = cur.fetchone()
        assert row is not None, "PRAGMA synchronous returned no row"
        assert row[0] == 1, (  # 1 = NORMAL
            f"PRAGMA synchronous must be NORMAL (1), got {row}"
        )
        # busy_timeout
        cur = conn.execute("PRAGMA busy_timeout")
        row = cur.fetchone()
        assert row is not None, "PRAGMA busy_timeout returned no row"
        assert int(row[0]) == 5000, f"PRAGMA busy_timeout must be 5000, got {row}"
        # foreign_keys
        cur = conn.execute("PRAGMA foreign_keys")
        row = cur.fetchone()
        assert row is not None, "PRAGMA foreign_keys returned no row"
        assert int(row[0]) == 1, f"PRAGMA foreign_keys must be ON (1), got {row}"
    finally:
        conn.close()


def test_memory_init_creates_db_file_on_disk(tmp_path: Path) -> None:
    """memory_init must create the DB file at the given path."""
    from agents.v2.memory_schema import memory_init

    target = tmp_path / "ikigai_memory_test.db"
    assert not target.exists()
    conn = memory_init(str(target))
    try:
        assert target.exists(), f"memory_init did not create {target}"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# AC3 — Append-only (R8)
# ---------------------------------------------------------------------------


def test_memory_write_inserts_row(in_memory_db: str) -> None:
    """memory_write inserts a row successfully."""
    from agents.v2.memory_schema import MEMORY_TABLE_DAILY, memory_init
    from agents.v2.memory_write import memory_write

    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY_1,
        body_markdown="# Daily\n\nintentions...",
        sha256="abc123",
        vault_path="closing-2026/q3/daily-2026-09-04.md",
        actor="user",
        source_ueids=[],
        ts=1000.0,
    )
    conn = memory_init(in_memory_db)
    try:
        cur = conn.execute(
            "SELECT daily_ueid, actor, source_ueids, ts FROM memory_daily_intentions"
        )
        row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == _UEID_DAILY_1
    assert row[1] == "user"
    assert row[2] == "[]"
    assert float(row[3]) == 1000.0


def test_memory_write_append_only_raises_on_conflict(in_memory_db: str) -> None:
    """memory_write MUST raise on UEID conflict (append-only — no overwrite)."""
    from agents.v2.memory_schema import MEMORY_TABLE_DAILY
    from agents.v2.memory_write import memory_write

    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY_1,
        body_markdown="first",
        sha256="abc",
        vault_path="path-1.md",
        actor="user",
        source_ueids=[],
        ts=1000.0,
    )
    # Second write with same UEID must raise (append-only).
    with pytest.raises(ValueError, match="append-only"):
        memory_write(
            memory_db=in_memory_db,
            table=MEMORY_TABLE_DAILY,
            ueid=_UEID_DAILY_1,
            body_markdown="second",
            sha256="def",
            vault_path="path-2.md",
            actor="user",
            source_ueids=[],
            ts=2000.0,
        )


# ---------------------------------------------------------------------------
# AC — UEID validation (R3)
# ---------------------------------------------------------------------------


def test_memory_write_rejects_invalid_5part_ueid(in_memory_db: str) -> None:
    """memory_write MUST reject 5-part UEIDs (ADR-014 R3 + ADR-028 R3)."""
    from agents.v2.memory_schema import MEMORY_TABLE_DAILY
    from agents.v2.memory_write import memory_write

    with pytest.raises(ValueError, match="4-part UEID"):
        memory_write(
            memory_db=in_memory_db,
            table=MEMORY_TABLE_DAILY,
            ueid=_UEID_INVALID_5PART,
            body_markdown="x",
            sha256="x",
            vault_path="x.md",
            actor="user",
            source_ueids=[],
        )


def test_memory_write_rejects_invalid_actor(in_memory_db: str) -> None:
    """memory_write MUST reject actor not in {'user', 'agent', 'system'}."""
    from agents.v2.memory_schema import MEMORY_TABLE_DAILY
    from agents.v2.memory_write import memory_write

    with pytest.raises(ValueError, match="actor"):
        memory_write(
            memory_db=in_memory_db,
            table=MEMORY_TABLE_DAILY,
            ueid=_UEID_DAILY_1,
            body_markdown="x",
            sha256="x",
            vault_path="x.md",
            actor="admin",  # invalid
            source_ueids=[],
        )


def test_memory_write_rejects_invalid_source_ueids(in_memory_db: str) -> None:
    """memory_write MUST reject source_ueids with non-4-part UEIDs."""
    from agents.v2.memory_schema import MEMORY_TABLE_WEEKLY
    from agents.v2.memory_write import memory_write

    with pytest.raises(ValueError, match="source_ueids"):
        memory_write(
            memory_db=in_memory_db,
            table=MEMORY_TABLE_WEEKLY,
            ueid=_UEID_WEEKLY_1,
            body_markdown="x",
            sha256="x",
            vault_path="x.md",
            actor="agent",
            source_ueids=[_UEID_DAILY_1, "bad-ueid-format"],
        )


def test_memory_write_rejects_unknown_table(in_memory_db: str) -> None:
    """memory_write MUST reject unknown table names."""
    from agents.v2.memory_write import memory_write

    with pytest.raises(ValueError, match="not a recognized memory table"):
        memory_write(
            memory_db=in_memory_db,
            table="memory_unknown_table",
            ueid=_UEID_DAILY_1,
            body_markdown="x",
            sha256="x",
            vault_path="x.md",
            actor="user",
            source_ueids=[],
        )


# ---------------------------------------------------------------------------
# AC1 — Daily -> weekly rollup (R7)
# ---------------------------------------------------------------------------


def test_daily_to_weekly_rollup_visible(in_memory_db: str) -> None:
    """Daily state must be visible to weekly aggregation read."""
    from datetime import date as _date

    from agents.v2.memory_read import read_daily_intentions
    from agents.v2.memory_schema import MEMORY_TABLE_DAILY, MEMORY_TABLE_WEEKLY
    from agents.v2.memory_write import memory_write

    # Write 3 daily intentions (actor=user) at known timestamps.
    # 1700000000 ~= 2023-11-14 22:13 UTC. Day offsets 0/1/2 land on Nov 14/15/16.
    daily_ueids = [_UEID_DAILY_1, _UEID_DAILY_2, _UEID_DAILY_3]
    ts_base = 1700000000.0
    for i, ueid in enumerate(daily_ueids):
        memory_write(
            memory_db=in_memory_db,
            table=MEMORY_TABLE_DAILY,
            ueid=ueid,
            body_markdown=f"daily-{i}",
            sha256=f"hash-{i}",
            vault_path=f"daily-{i}.md",
            actor="user",
            source_ueids=[],
            ts=ts_base + i * 86400,
        )

    # Weekly reads dailies — must see all 3.
    dailies = read_daily_intentions(
        memory_db=in_memory_db,
        week_range=(_date(2023, 11, 14), _date(2023, 11, 20)),
    )
    assert len(dailies) == 3
    assert {d["ueid"] for d in dailies} == set(daily_ueids)
    assert all(d["actor"] == "user" for d in dailies)

    # Weekly writes an aggregation referencing the dailies.
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_WEEKLY,
        ueid=_UEID_WEEKLY_1,
        body_markdown="weekly-aggregated",
        sha256="weekly-hash",
        vault_path="weekly.md",
        actor="agent",
        source_ueids=daily_ueids,
        ts=ts_base + 7 * 86400,
    )

    # Verify the weekly row's source_ueids contains the dailies (rollup link).
    conn = sqlite3.connect(in_memory_db)
    try:
        cur = conn.execute(
            "SELECT source_ueids FROM memory_weekly_aggregations WHERE weekly_ueid = ?",
            (_UEID_WEEKLY_1,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    decoded = json.loads(row[0])
    assert set(decoded) == set(daily_ueids)


# ---------------------------------------------------------------------------
# AC2 — Weekly -> monthly -> quarterly chain (R7)
# ---------------------------------------------------------------------------


def test_full_pyramid_chain_reconstructable(in_memory_db: str) -> None:
    """Weekly -> monthly -> quarterly chain must be reconstructable via reads."""
    from datetime import date as _date
    from datetime import datetime, timezone

    from agents.v2.memory_read import (
        read_daily_intentions,
        read_monthly_syntheses,
        read_quarterly_strategies,
        read_weekly_aggregations,
    )
    from agents.v2.memory_schema import (
        MEMORY_TABLE_DAILY,
        MEMORY_TABLE_MONTHLY,
        MEMORY_TABLE_QUARTERLY,
        MEMORY_TABLE_WEEKLY,
    )
    from agents.v2.memory_write import memory_write

    # Anchor: 2026-09-04 00:00:00 UTC. Compute ts via the same logic
    # memory_read uses (so the test never drifts from real date math).
    anchor_date = _date(2026, 9, 4)
    ts_base = datetime(
        anchor_date.year, anchor_date.month, anchor_date.day, tzinfo=timezone.utc
    ).timestamp()
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY_1,
        body_markdown="daily",
        sha256="h",
        vault_path="d.md",
        actor="user",
        source_ueids=[],
        ts=ts_base,
    )
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_WEEKLY,
        ueid=_UEID_WEEKLY_1,
        body_markdown="weekly",
        sha256="h",
        vault_path="w.md",
        actor="agent",
        source_ueids=[_UEID_DAILY_1],
        ts=ts_base + 86400,
    )
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_MONTHLY,
        ueid=_UEID_MONTHLY_1,
        body_markdown="monthly",
        sha256="h",
        vault_path="m.md",
        actor="agent",
        source_ueids=[_UEID_WEEKLY_1],
        ts=ts_base + 2 * 86400,
    )
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_QUARTERLY,
        ueid=_UEID_QUARTERLY_1,
        body_markdown="quarterly",
        sha256="h",
        vault_path="q.md",
        actor="agent",
        source_ueids=[_UEID_MONTHLY_1],
        ts=ts_base + 3 * 86400,
    )

    # Read all 4 levels for the date range — each must return 1 row.
    dailies = read_daily_intentions(
        memory_db=in_memory_db,
        week_range=(_date(2026, 9, 1), _date(2026, 9, 30)),
    )
    weeklies = read_weekly_aggregations(
        memory_db=in_memory_db,
        month_range=(_date(2026, 9, 1), _date(2026, 9, 30)),
    )
    monthlies = read_monthly_syntheses(
        memory_db=in_memory_db,
        quarter_range=(_date(2026, 7, 1), _date(2026, 9, 30)),
    )
    quarterlies = read_quarterly_strategies(
        memory_db=in_memory_db,
        year=2026,
    )
    assert len(dailies) == 1
    assert len(weeklies) == 1
    assert len(monthlies) == 1
    assert len(quarterlies) == 1

    # Verify the chain links via source_ueids.
    assert weeklies[0]["source_ueids"] == [_UEID_DAILY_1]
    assert monthlies[0]["source_ueids"] == [_UEID_WEEKLY_1]
    assert quarterlies[0]["source_ueids"] == [_UEID_MONTHLY_1]


# ---------------------------------------------------------------------------
# AC — Actor scoping in reads (R5)
# ---------------------------------------------------------------------------


def test_actor_scoping_filters_by_actor(in_memory_db: str) -> None:
    """read_daily_intentions with actor='user' MUST filter out agent-written rows."""
    from datetime import date as _date
    from datetime import datetime, timezone

    from agents.v2.memory_read import read_daily_intentions
    from agents.v2.memory_schema import MEMORY_TABLE_DAILY
    from agents.v2.memory_write import memory_write

    # Use the same date math the read function uses.
    anchor_date = _date(2026, 9, 4)
    ts_base = datetime(
        anchor_date.year, anchor_date.month, anchor_date.day, tzinfo=timezone.utc
    ).timestamp()
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY_1,
        body_markdown="d1",
        sha256="h",
        vault_path="d1.md",
        actor="user",
        source_ueids=[],
        ts=ts_base,
    )
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY_2,
        body_markdown="d2",
        sha256="h",
        vault_path="d2.md",
        actor="agent",
        source_ueids=[],
        ts=ts_base + 86400,
    )
    # actor='user' returns 1 row.
    user_only = read_daily_intentions(
        memory_db=in_memory_db,
        week_range=(_date(2026, 9, 1), _date(2026, 9, 30)),
        actor="user",
    )
    assert len(user_only) == 1
    assert user_only[0]["actor"] == "user"
    assert user_only[0]["ueid"] == _UEID_DAILY_1
    # actor=None returns both.
    all_actors = read_daily_intentions(
        memory_db=in_memory_db,
        week_range=(_date(2026, 9, 1), _date(2026, 9, 30)),
    )
    assert len(all_actors) == 2


# ---------------------------------------------------------------------------
# AC — Prune-on-write (R8)
# ---------------------------------------------------------------------------


def test_prune_on_write_deletes_old_dailies(in_memory_db: str, monkeypatch) -> None:
    """prune_on_write with MEMORY_RETENTION_DAILY_DAYS=30 must delete old rows."""

    from agents.v2.memory_prune import prune_on_write
    from agents.v2.memory_schema import MEMORY_TABLE_DAILY
    from agents.v2.memory_write import memory_write

    # Use an explicit ``now_epoch`` anchor so the test is deterministic
    # regardless of real wall-clock time (the ts values are fixed below).
    now_epoch = 1756944000.0  # 2026-09-04 00:00:00 UTC
    # Insert a daily with ts 100 days ago (well past 30-day retention).
    ts_old = now_epoch - 100 * 86400
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY_1,
        body_markdown="old daily",
        sha256="h",
        vault_path="old.md",
        actor="user",
        source_ueids=[],
        ts=ts_old,
    )
    # Insert a recent daily (within 30-day window — 5 days old).
    ts_recent = now_epoch - 5 * 86400
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY_2,
        body_markdown="recent daily",
        sha256="h",
        vault_path="recent.md",
        actor="user",
        source_ueids=[],
        ts=ts_recent,
    )

    # Confirm 2 rows present.
    conn = sqlite3.connect(in_memory_db)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM memory_daily_intentions")
        count_before = cur.fetchone()[0]
    finally:
        conn.close()
    assert count_before == 2

    # Prune using the JSON-loaded retention key + explicit now_epoch.
    deleted = prune_on_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_DAILY,
        retention_days_key="MEMORY_RETENTION_DAILY_DAYS",
        now_epoch=now_epoch,
    )
    assert deleted == 1  # only the old row is pruned

    # Confirm only 1 row remains (the recent one).
    conn = sqlite3.connect(in_memory_db)
    try:
        cur = conn.execute("SELECT daily_ueid FROM memory_daily_intentions ORDER BY daily_ueid")
        remaining = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()
    assert remaining == [_UEID_DAILY_2]


def test_prune_quarterly_never_runs_by_default(in_memory_db: str) -> None:
    """prune_on_write for quarterly must skip when MEMORY_RETENTION_QUARTERLY_DAYS is None."""
    from agents.v2.memory_prune import prune_on_write
    from agents.v2.memory_schema import MEMORY_TABLE_QUARTERLY
    from agents.v2.memory_write import memory_write

    # Insert a quarterly with ts 100 years ago (well past any retention).
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_QUARTERLY,
        ueid=_UEID_QUARTERLY_1,
        body_markdown="q",
        sha256="h",
        vault_path="q.md",
        actor="agent",
        source_ueids=[],
        ts=0.0,  # 1970-01-01
    )

    # Default quarterly retention is None (forever) — prune_on_write returns 0.
    deleted = prune_on_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_QUARTERLY,
        retention_days_key="MEMORY_RETENTION_QUARTERLY_DAYS",
    )
    assert deleted == 0

    # Quarterly row must still be present.
    conn = sqlite3.connect(in_memory_db)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM memory_quarterly_strategies")
        count = cur.fetchone()[0]
    finally:
        conn.close()
    assert count == 1


# ---------------------------------------------------------------------------
# AC — Atomic vault_write + memory_write (R4)
# ---------------------------------------------------------------------------


def test_memory_write_atomic_writes_vault_and_db(in_memory_db: str, vault_root: Path) -> None:
    """memory_write_atomic must write BOTH the vault file AND the DB row."""
    from agents.v2.memory_schema import MEMORY_TABLE_DAILY
    from agents.v2.memory_write import memory_write_atomic

    vault_path = "plans/q3/daily-2026-09-04.md"
    result = memory_write_atomic(
        memory_db=in_memory_db,
        vault_root=vault_root,
        vault_path=vault_path,
        actor="user",
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY_1,
        body_markdown="# Daily 2026-09-04\n\nintentions...",
        sha256="deadbeef",
        frontmatter_fields={"ueid": _UEID_DAILY_1, "actor": "user"},
        source_ueids=[],
    )

    # Vault file exists.
    assert (vault_root / vault_path).exists()
    # Result has expected fields.
    assert result["written"] is True
    assert result["memory_written"] is True
    assert result["actor"] == "user"
    assert result["sha256"]
    # Audit log was appended.
    audit_log = vault_root / ".vault_audit.log"
    assert audit_log.exists()
    assert "actor=user" in audit_log.read_text(encoding="utf-8")
    # DB row exists.
    conn = sqlite3.connect(in_memory_db)
    try:
        cur = conn.execute("SELECT daily_ueid, actor FROM memory_daily_intentions")
        row = cur.fetchone()
    finally:
        conn.close()
    assert row == (_UEID_DAILY_1, "user")


def test_memory_write_atomic_rolls_back_vault_on_db_failure(
    in_memory_db: str, vault_root: Path
) -> None:
    """memory_write_atomic must roll back vault_write if memory_write fails (R4)."""
    from agents.v2.memory_schema import MEMORY_TABLE_DAILY
    from agents.v2.memory_write import memory_write, memory_write_atomic

    # Pre-insert a row to force an append-only conflict on the second write.
    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY_1,
        body_markdown="existing",
        sha256="h",
        vault_path="existing.md",
        actor="user",
        source_ueids=[],
        ts=1000.0,
    )

    vault_path = "plans/q3/daily-should-be-rolled-back.md"
    with pytest.raises(ValueError, match="append-only"):
        memory_write_atomic(
            memory_db=in_memory_db,
            vault_root=vault_root,
            vault_path=vault_path,
            actor="user",
            table=MEMORY_TABLE_DAILY,
            ueid=_UEID_DAILY_1,  # SAME UEID → append-only conflict
            body_markdown="conflicting",
            sha256="h",
            source_ueids=[],
        )
    # Vault file must NOT exist (rolled back).
    assert not (vault_root / vault_path).exists(), (
        "vault file should have been rolled back when memory_write failed"
    )


# ---------------------------------------------------------------------------
# AC — Schema migration stub (R11)
# ---------------------------------------------------------------------------


def test_apply_migrations_v1_is_noop() -> None:
    """apply_migrations with target_version=1 MUST return row as-is."""
    from agents.v2.memory_migrations import apply_migrations

    row = {"ueid": _UEID_DAILY_1, "schema_version": 1, "body_markdown": "x"}
    result = apply_migrations(row, target_version=1)
    assert result == row
    assert result["schema_version"] == 1


def test_apply_migrations_v2_raises_not_implemented() -> None:
    """apply_migrations with target_version=2 MUST raise NotImplementedError (R11 stub)."""
    from agents.v2.memory_migrations import apply_migrations

    row = {"ueid": _UEID_DAILY_1, "schema_version": 1}
    with pytest.raises(NotImplementedError, match="v2"):
        apply_migrations(row, target_version=2)


def test_apply_migrations_rejects_invalid_target_version() -> None:
    """apply_migrations with target_version < 1 MUST raise ValueError."""
    from agents.v2.memory_migrations import apply_migrations

    row = {"ueid": _UEID_DAILY_1, "schema_version": 1}
    with pytest.raises(ValueError, match=">= 1"):
        apply_migrations(row, target_version=0)


# ---------------------------------------------------------------------------
# AC — 4-part UEID regex enforcement on stored records (R3)
# ---------------------------------------------------------------------------


def test_stored_ueids_are_4_part_only(in_memory_db: str) -> None:
    """Every stored daily_ueid MUST match the 4-part regex (ADR-014 R3)."""
    import re

    from agents.v2.memory_schema import MEMORY_TABLE_DAILY
    from agents.v2.memory_write import memory_write

    canonical_pattern = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")

    memory_write(
        memory_db=in_memory_db,
        table=MEMORY_TABLE_DAILY,
        ueid=_UEID_DAILY_1,
        body_markdown="d",
        sha256="h",
        vault_path="d.md",
        actor="user",
        source_ueids=[],
    )
    conn = sqlite3.connect(in_memory_db)
    try:
        cur = conn.execute(f"SELECT {'daily_ueid'} FROM {MEMORY_TABLE_DAILY}")
        ueids = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()
    assert all(canonical_pattern.match(u) for u in ueids)


# ---------------------------------------------------------------------------
# AC — Constants present in JSON (drift detector foundation)
# ---------------------------------------------------------------------------


def test_memory_retention_constants_in_json() -> None:
    """algorithm_constants.json MUST define all 4 MEMORY_RETENTION_* keys."""
    json_path = (
        Path(__file__).parent.parent
        / "src"
        / "agents"
        / "v2"
        / "prompts"
        / "algorithm_constants.json"
    )
    if not json_path.exists():
        pytest.skip(f"{json_path} not present")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    required = (
        "MEMORY_RETENTION_DAILY_DAYS",
        "MEMORY_RETENTION_WEEKLY_DAYS",
        "MEMORY_RETENTION_MONTHLY_DAYS",
        "MEMORY_RETENTION_QUARTERLY_DAYS",
    )
    missing = [k for k in required if k not in data]
    assert not missing, (
        f"algorithm_constants.json missing MEMORY_RETENTION_* keys (ADR-028 R8): {missing}"
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_memory_write_rejects_empty_body(in_memory_db: str) -> None:
    """memory_write MUST reject empty body_markdown (NOT NULL constraint)."""
    from agents.v2.memory_schema import MEMORY_TABLE_DAILY
    from agents.v2.memory_write import memory_write

    with pytest.raises(ValueError, match="body_markdown"):
        memory_write(
            memory_db=in_memory_db,
            table=MEMORY_TABLE_DAILY,
            ueid=_UEID_DAILY_1,
            body_markdown="",
            sha256="h",
            vault_path="d.md",
            actor="user",
            source_ueids=[],
        )


def test_read_quarterly_strategies_year_bounds(in_memory_db: str) -> None:
    """read_quarterly_strategies must validate the year argument."""
    from agents.v2.memory_read import read_quarterly_strategies

    with pytest.raises(ValueError, match="year"):
        read_quarterly_strategies(memory_db=in_memory_db, year=1969)  # too old


def test_read_dailies_rejects_inverted_range(in_memory_db: str) -> None:
    """read_daily_intentions must reject start_date > end_date."""
    from datetime import date as _date

    from agents.v2.memory_read import read_daily_intentions

    with pytest.raises(ValueError, match="after end_date"):
        read_daily_intentions(
            memory_db=in_memory_db,
            week_range=(_date(2026, 9, 10), _date(2026, 9, 1)),
        )
