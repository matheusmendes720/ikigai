"""Tests for DB migrations + advisory locks + WAL mode (T10)."""
from __future__ import annotations

import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
VIBE_OPS_ROOT = Path(__file__).resolve().parents[1]
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from middleware.bidirectional_sync import BidirectionalSync  # noqa: E402


def _make_db(db_path):
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS planning_entities (
                id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                upstream_id TEXT NOT NULL,
                synced_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL,
                PRIMARY KEY (id, entity_type)
            )
            """
        )
        conn.commit()


@pytest.fixture
def setup(tmp_path):
    vault = tmp_path / "vault"
    db = tmp_path / "vibe_ops.db"
    vault.mkdir(parents=True, exist_ok=True)
    _make_db(db)
    return vault, db


class TestEnsureSchema:
    def test_creates_vault_sync_state(self, setup):
        vault, db = setup
        BidirectionalSync(vault, db)
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='vault_sync_state'"
            ).fetchone()
        assert row is not None

    def test_creates_falsifiable_hypotheses(self, setup):
        vault, db = setup
        BidirectionalSync(vault, db)
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='falsifiable_hypotheses'"
            ).fetchone()
        assert row is not None

    def test_creates_hypothesis_evaluations(self, setup):
        vault, db = setup
        BidirectionalSync(vault, db)
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='hypothesis_evaluations'"
            ).fetchone()
        assert row is not None

    def test_idempotent_schema_creation(self, setup):
        vault, db = setup
        BidirectionalSync(vault, db)
        BidirectionalSync(vault, db)
        BidirectionalSync(vault, db)
        with sqlite3.connect(str(db)) as conn:
            tables = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
                "AND name IN ('vault_sync_state', 'falsifiable_hypotheses', "
                "'hypothesis_evaluations')"
            ).fetchone()[0]
        assert tables == 3

    def test_vault_sync_state_columns(self, setup):
        vault, db = setup
        BidirectionalSync(vault, db)
        with sqlite3.connect(str(db)) as conn:
            cols = [r[1] for r in conn.execute(
                "PRAGMA table_info(vault_sync_state)"
            ).fetchall()]
        expected = {"vault_path", "entity_type", "entity_id", "last_hash", "last_synced_at"}
        assert expected.issubset(set(cols))

    def test_hypothesis_evaluations_fk_to_falsifiable_hypotheses(self, setup):
        vault, db = setup
        BidirectionalSync(vault, db)
        with sqlite3.connect(str(db)) as conn:
            fk = conn.execute(
                "PRAGMA foreign_key_list(hypothesis_evaluations)"
            ).fetchall()
        assert len(fk) >= 1
        assert fk[0][2] == "falsifiable_hypotheses"


class TestWALMode:
    def test_wal_mode_enabled_after_init(self, setup):
        vault, db = setup
        BidirectionalSync(vault, db)
        with sqlite3.connect(str(db)) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"


class TestAdvisoryLock:
    def test_advisory_lock_yields_connection(self, setup):
        vault, db = setup
        sync = BidirectionalSync(vault, db)
        with sync.advisory_lock("test_lock") as conn:
            assert isinstance(conn, sqlite3.Connection)
            row = conn.execute("SELECT 1").fetchone()
            assert row[0] == 1

    def test_advisory_lock_commits_on_exit(self, setup):
        vault, db = setup
        sync = BidirectionalSync(vault, db)
        with sync.advisory_lock("write_lock") as conn:
            conn.execute(
                "INSERT INTO vault_sync_state (vault_path, entity_type, entity_id, last_hash) "
                "VALUES (?, ?, ?, ?)",
                ("test/path.md", "project", "test_id", "abc123"),
            )
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(
                "SELECT last_hash FROM vault_sync_state WHERE vault_path = ?",
                ("test/path.md",),
            ).fetchone()
        assert row[0] == "abc123"

    def test_advisory_lock_serializes_writers(self, setup):
        vault, db = setup
        sync = BidirectionalSync(vault, db)
        order: list[str] = []

        def _writer(name):
            with sync.advisory_lock("serialize_test"):
                order.append(f"{name}_start")
                time.sleep(0.2)
                order.append(f"{name}_end")

        t1 = threading.Thread(target=_writer, args=("A",))
        t2 = threading.Thread(target=_writer, args=("B",))
        t1.start()
        time.sleep(0.05)
        t2.start()
        t1.join()
        t2.join()

        assert len(order) == 4
        if order[0].startswith("A"):
            assert order == ["A_start", "A_end", "B_start", "B_end"]
        else:
            assert order == ["B_start", "B_end", "A_start", "A_end"]


class TestMigrationFiles:
    def test_vibe_ops_migration_sql_is_valid(self, tmp_path):
        migration = VIBE_OPS_ROOT / "migrations" / "005_vault_sync.sql"
        assert migration.exists(), f"migration missing: {migration}"
        db = tmp_path / "test.db"
        _make_db(db)
        sql = migration.read_text(encoding="utf-8")
        with sqlite3.connect(str(db)) as conn:
            conn.executescript(sql)
            conn.commit()
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('vault_sync_state', 'falsifiable_hypotheses', "
                "'hypothesis_evaluations')"
            ).fetchall()
        assert len(tables) == 3

    def test_operational_mirror_migration_sql_is_valid(self):
        migration = (
            VIBE_OPS_ROOT.parent
            / "life-ops" / "operational" / "packages" / "core" / "src"
            / "operational" / "persistence" / "migrations" / "003_vault_sync.sql"
        )
        assert migration.exists(), f"mirror migration missing: {migration}"
        sql = migration.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS vault_sync_state" in sql

    def test_migration_idempotent(self, tmp_path):
        db = tmp_path / "test.db"
        _make_db(db)
        migration = VIBE_OPS_ROOT / "migrations" / "005_vault_sync.sql"
        sql = migration.read_text(encoding="utf-8")
        with sqlite3.connect(str(db)) as conn:
            conn.executescript(sql)
            conn.executescript(sql)
            conn.commit()
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='vault_sync_state'"
            ).fetchall()
        assert len(tables) == 1