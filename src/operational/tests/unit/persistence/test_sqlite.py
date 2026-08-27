"""Unit tests for :mod:`operational.persistence.sqlite`."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from operational.persistence.sqlite import SqliteRepository, get_connection
from operational.types import UEID


# ---------------------------------------------------------------------------
# Test model
# ---------------------------------------------------------------------------


class _Gadget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    name: str
    price: float = 0.0
    created_at: datetime


@pytest.fixture
def conn() -> Any:
    c = get_connection(":memory:")
    yield c
    c.close()


@pytest.fixture
def repo(conn: Any) -> SqliteRepository[_Gadget]:
    r = SqliteRepository(_Gadget, "gadget", conn)
    r.ensure_table()
    return r


# ---------------------------------------------------------------------------
# Construction + table creation
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_ensure_table_creates(self, conn: Any) -> None:
        repo = SqliteRepository(_Gadget, "gadget", conn)
        repo.ensure_table()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entities'",
        ).fetchall()
        assert len(rows) == 1

    def test_ensure_table_idempotent(self, conn: Any) -> None:
        repo = SqliteRepository(_Gadget, "gadget", conn)
        repo.ensure_table()
        repo.ensure_table()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entities'",
        ).fetchall()
        assert len(rows) == 1

    def test_properties(self, repo: SqliteRepository[_Gadget]) -> None:
        assert repo.entity_type == "gadget"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


class TestCrud:
    def test_empty_count(self, repo: SqliteRepository[_Gadget]) -> None:
        assert repo.count() == 0

    def test_upsert_and_get(self, repo: SqliteRepository[_Gadget]) -> None:
        gadget = _Gadget(
            id="gad_phone", name="Phone", price=999.0,
            created_at=datetime(2026, 6, 7, 10, 0),
        )
        repo.upsert(gadget)
        retrieved = repo.get(UEID("gad_phone"))
        assert retrieved is not None
        assert retrieved.name == "Phone"
        assert retrieved.price == 999.0

    def test_get_nonexistent(self, repo: SqliteRepository[_Gadget]) -> None:
        assert repo.get(UEID("gad_nope")) is None

    def test_list_all(self, repo: SqliteRepository[_Gadget]) -> None:
        for i in range(3):
            repo.upsert(_Gadget(
                id=f"gad_{i}", name=f"Gadget {i}", price=float(i * 100),
                created_at=datetime(2026, 6, 7, 10, 0),
            ))
        assert len(repo.list()) == 3

    def test_list_filtered(self, repo: SqliteRepository[_Gadget]) -> None:
        for i in range(4):
            repo.upsert(_Gadget(
                id=f"gad_{i}", name=f"G{i}", price=float(i % 2),
                created_at=datetime(2026, 6, 7, 10, 0),
            ))
        result = repo.list({"price": 0.0})
        assert len(result) == 2

    def test_delete_existing(self, repo: SqliteRepository[_Gadget]) -> None:
        repo.upsert(_Gadget(
            id="gad_del", name="Del", price=1.0,
            created_at=datetime(2026, 6, 7, 10, 0),
        ))
        assert repo.delete(UEID("gad_del")) is True
        assert repo.count() == 0

    def test_delete_nonexistent(self, repo: SqliteRepository[_Gadget]) -> None:
        assert repo.delete(UEID("gad_nope")) is False

    def test_upsert_existing_replaces(self, repo: SqliteRepository[_Gadget]) -> None:
        repo.upsert(_Gadget(
            id="gad_upd", name="Old", price=1.0,
            created_at=datetime(2026, 6, 7, 10, 0),
        ))
        repo.upsert(_Gadget(
            id="gad_upd", name="New", price=2.0,
            created_at=datetime(2026, 6, 7, 10, 0),
        ))
        retrieved = repo.get(UEID("gad_upd"))
        assert retrieved is not None
        assert retrieved.name == "New"
        assert retrieved.price == 2.0


# ---------------------------------------------------------------------------
# Type isolation
# ---------------------------------------------------------------------------


class TestTypeIsolation:
    def test_different_types_isolated(self, conn: Any) -> None:
        repo_a = SqliteRepository(_Gadget, "type_a", conn)
        repo_a.ensure_table()
        repo_b = SqliteRepository(_Gadget, "type_b", conn)
        repo_b.ensure_table()

        repo_a.upsert(_Gadget(
            id="gad_x", name="A-only", price=10.0,
            created_at=datetime(2026, 6, 7, 10, 0),
        ))
        assert repo_a.count() == 1
        assert repo_b.count() == 0


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_exists(self, repo: SqliteRepository[_Gadget]) -> None:
        repo.upsert(_Gadget(
            id="gad_e", name="Exists", price=5.0,
            created_at=datetime(2026, 6, 7, 10, 0),
        ))
        assert repo.exists(UEID("gad_e")) is True
        assert repo.exists(UEID("gad_nope")) is False

    def test_get_many(self, repo: SqliteRepository[_Gadget]) -> None:
        for i in range(4):
            repo.upsert(_Gadget(
                id=f"gad_{i}", name=f"G{i}", price=float(i),
                created_at=datetime(2026, 6, 7, 10, 0),
            ))
        result = repo.get_many([UEID("gad_0"), UEID("gad_2"), UEID("gad_99")])
        assert len(result) == 2

    def test_upsert_many(self, repo: SqliteRepository[_Gadget]) -> None:
        gadgets = [
            _Gadget(id=f"gad_{i}", name=f"G{i}", price=float(i),
                    created_at=datetime(2026, 6, 7, 10, 0))
            for i in range(3)
        ]
        repo.upsert_many(gadgets)
        assert repo.count() == 3

    def test_delete_many(self, repo: SqliteRepository[_Gadget]) -> None:
        for i in range(5):
            repo.upsert(_Gadget(
                id=f"gad_{i}", name=f"G{i}", price=float(i),
                created_at=datetime(2026, 6, 7, 10, 0),
            ))
        removed = repo.delete_many([UEID("gad_0"), UEID("gad_2"), UEID("gad_99")])
        assert removed == 2
        assert repo.count() == 3


# ---------------------------------------------------------------------------
# Serialization edge cases
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_date_field_roundtrip(self, conn: Any) -> None:
        class _WithDate(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            id: str
            event_date: date
            created_at: datetime

        repo = SqliteRepository(_WithDate, "wdate", conn)
        repo.ensure_table()
        original = _WithDate(
            id="wdt_1", event_date=date(2026, 6, 7),
            created_at=datetime(2026, 6, 7, 10, 0),
        )
        repo.upsert(original)
        restored = repo.get(UEID("wdt_1"))
        assert restored is not None
        assert restored.event_date == date(2026, 6, 7)
        assert restored == original

    def test_json_data_stored_correctly(self, conn: Any) -> None:
        repo = SqliteRepository(_Gadget, "gadget", conn)
        repo.ensure_table()
        gadget = _Gadget(
            id="gad_json", name="JSON Test", price=42.5,
            created_at=datetime(2026, 6, 7, 10, 0),
        )
        repo.upsert(gadget)
        row = conn.execute(
            "SELECT data FROM entities WHERE id = ?", ("gad_json",),
        ).fetchone()
        data = json.loads(row["data"])
        assert data["name"] == "JSON Test"
        assert data["price"] == 42.5


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrors:
    def test_bad_table_returns_empty(self) -> None:
        conn = get_connection(":memory:")
        repo = SqliteRepository(_Gadget, "gadget", conn, table_name="nonexistent")
        assert repo.list() == []
        conn.close()

    def test_vacuum_works(self, repo: SqliteRepository[_Gadget]) -> None:
        repo.upsert(_Gadget(
            id="gad_v", name="V", price=1.0,
            created_at=datetime(2026, 6, 7, 10, 0),
        ))
        # Should not raise
        repo.vacuum()


# ---------------------------------------------------------------------------
# get_connection helper
# ---------------------------------------------------------------------------


class TestGetConnection:
    def test_in_memory(self) -> None:
        conn = get_connection(":memory:")
        assert conn is not None
        conn.close()

    def test_wal_mode(self, tmp_path: Any) -> None:
        db_path = tmp_path / "test.db"
        conn = get_connection(db_path)
        pragma = conn.execute("PRAGMA journal_mode").fetchone()
        assert pragma[0] == "wal"
        conn.close()
