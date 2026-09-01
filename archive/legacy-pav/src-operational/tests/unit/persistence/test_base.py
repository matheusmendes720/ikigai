"""Unit tests for :mod:`operational.persistence.base`."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from operational.persistence.base import RepositoryBase
from operational.types import UEID


# ---------------------------------------------------------------------------
# Concrete test implementation
# ---------------------------------------------------------------------------


class _DummyEntity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    name: str
    value: int = 0
    created_at: datetime


class _DictRepo(RepositoryBase[_DummyEntity]):
    """Minimal concrete repo backed by a dict."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def _load_all(self) -> dict[str, dict[str, Any]]:
        return dict(self._store)

    def _persist_one(self, entity_id: str, data: dict[str, Any]) -> None:
        self._store[entity_id] = data

    def _remove_one(self, entity_id: str) -> None:
        self._store.pop(entity_id, None)

    def _serialize(self, entity: _DummyEntity) -> dict[str, Any]:
        return entity.model_dump(mode="python")

    def _deserialize(self, data: dict[str, Any]) -> _DummyEntity:
        return _DummyEntity.model_validate(data)


@pytest.fixture
def repo() -> _DictRepo:
    return _DictRepo()


@pytest.fixture
def sample_entity() -> _DummyEntity:
    return _DummyEntity(
        id="dum_sample",
        name="Sample",
        value=42,
        created_at=datetime(2026, 6, 7, 10, 0),
    )


# ---------------------------------------------------------------------------
# CRUD: get
# ---------------------------------------------------------------------------


class TestGet:
    def test_get_nonexistent_returns_none(self, repo: _DictRepo) -> None:
        assert repo.get(UEID("dum_xxxx")) is None

    def test_get_existing_returns_entity(
        self, repo: _DictRepo, sample_entity: _DummyEntity,
    ) -> None:
        repo.upsert(sample_entity)
        retrieved = repo.get(UEID("dum_sample"))
        assert retrieved is not None
        assert retrieved.id == "dum_sample"
        assert retrieved.name == "Sample"
        assert retrieved.value == 42

    def test_get_returns_copy_not_reference(
        self, repo: _DictRepo, sample_entity: _DummyEntity,
    ) -> None:
        repo.upsert(sample_entity)
        retrieved = repo.get(UEID("dum_sample"))
        assert retrieved is not None
        assert retrieved == sample_entity


# ---------------------------------------------------------------------------
# CRUD: upsert
# ---------------------------------------------------------------------------


class TestUpsert:
    def test_upsert_new_creates(self, repo: _DictRepo) -> None:
        ent = _DummyEntity(
            id="dum_new", name="New", value=1,
            created_at=datetime(2026, 6, 7, 0, 0),
        )
        eid = repo.upsert(ent)
        assert eid == "dum_new"
        assert repo.count() == 1

    def test_upsert_existing_overwrites(self, repo: _DictRepo) -> None:
        ent = _DummyEntity(
            id="dum_x", name="Old", value=1,
            created_at=datetime(2026, 6, 7, 0, 0),
        )
        repo.upsert(ent)
        ent2 = _DummyEntity(
            id="dum_x", name="New", value=2,
            created_at=datetime(2026, 6, 7, 0, 0),
        )
        repo.upsert(ent2)
        retrieved = repo.get(UEID("dum_x"))
        assert retrieved is not None
        assert retrieved.name == "New"
        assert retrieved.value == 2
        assert repo.count() == 1

    def test_upsert_idempotent(self, repo: _DictRepo) -> None:
        ent = _DummyEntity(
            id="dum_y", name="Y", value=10,
            created_at=datetime(2026, 6, 7, 0, 0),
        )
        repo.upsert(ent)
        repo.upsert(ent)
        assert repo.count() == 1


# ---------------------------------------------------------------------------
# CRUD: list
# ---------------------------------------------------------------------------


class TestList:
    def test_list_empty_returns_empty(self, repo: _DictRepo) -> None:
        assert repo.list() == []

    def test_list_all(self, repo: _DictRepo) -> None:
        for i in range(3):
            repo.upsert(_DummyEntity(
                id=f"dum_{i}", name=f"E{i}", value=i,
                created_at=datetime(2026, 6, 7, 0, 0),
            ))
        assert len(repo.list()) == 3

    def test_list_with_filter(self, repo: _DictRepo) -> None:
        for i in range(5):
            repo.upsert(_DummyEntity(
                id=f"dum_{i}", name=f"E{i}", value=i % 2,
                created_at=datetime(2026, 6, 7, 0, 0),
            ))
        evens = repo.list({"value": 0})
        odds = repo.list({"value": 1})
        assert len(evens) == 3  # i=0,2,4
        assert len(odds) == 2  # i=1,3

    def test_list_unknown_filter_raises(self, repo: _DictRepo) -> None:
        repo.upsert(_DummyEntity(
            id="dum_0", name="X", value=0,
            created_at=datetime(2026, 6, 7, 0, 0),
        ))
        with pytest.raises(AttributeError):
            repo.list({"nonexistent": True})

    def test_list_empty_filter_returns_all(self, repo: _DictRepo) -> None:
        for i in range(2):
            repo.upsert(_DummyEntity(
                id=f"dum_{i}", name=f"E{i}", value=i,
                created_at=datetime(2026, 6, 7, 0, 0),
            ))
        assert len(repo.list({})) == 2

    def test_list_multiple_filters_and(self, repo: _DictRepo) -> None:
        for i in range(6):
            repo.upsert(_DummyEntity(
                id=f"dum_{i}", name=f"E{i}", value=i % 3,
                created_at=datetime(2026, 6, 7, 0, 0),
            ))
        result = repo.list({"value": 0, "name": "E0"})
        assert len(result) == 1
        assert result[0].id == "dum_0"


# ---------------------------------------------------------------------------
# CRUD: delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_existing_returns_true(self, repo: _DictRepo) -> None:
        repo.upsert(_DummyEntity(
            id="dum_del", name="Del", value=0,
            created_at=datetime(2026, 6, 7, 0, 0),
        ))
        assert repo.delete(UEID("dum_del")) is True
        assert repo.count() == 0

    def test_delete_nonexistent_returns_false(self, repo: _DictRepo) -> None:
        assert repo.delete(UEID("dum_nope")) is False

    def test_delete_then_get_returns_none(self, repo: _DictRepo) -> None:
        repo.upsert(_DummyEntity(
            id="dum_gone", name="Gone", value=0,
            created_at=datetime(2026, 6, 7, 0, 0),
        ))
        repo.delete(UEID("dum_gone"))
        assert repo.get(UEID("dum_gone")) is None

    def test_delete_is_idempotent(self, repo: _DictRepo) -> None:
        repo.delete(UEID("dum_nope"))
        repo.delete(UEID("dum_nope"))
        assert repo.count() == 0


# ---------------------------------------------------------------------------
# CRUD: count
# ---------------------------------------------------------------------------


class TestCount:
    def test_count_empty(self, repo: _DictRepo) -> None:
        assert repo.count() == 0

    def test_count_after_upsert(self, repo: _DictRepo) -> None:
        repo.upsert(_DummyEntity(
            id="dum_c1", name="C1", value=0,
            created_at=datetime(2026, 6, 7, 0, 0),
        ))
        assert repo.count() == 1
        repo.upsert(_DummyEntity(
            id="dum_c2", name="C2", value=1,
            created_at=datetime(2026, 6, 7, 0, 0),
        ))
        assert repo.count() == 2

    def test_count_after_delete(self, repo: _DictRepo) -> None:
        repo.upsert(_DummyEntity(
            id="dum_c1", name="C1", value=0,
            created_at=datetime(2026, 6, 7, 0, 0),
        ))
        repo.upsert(_DummyEntity(
            id="dum_c2", name="C2", value=1,
            created_at=datetime(2026, 6, 7, 0, 0),
        ))
        repo.delete(UEID("dum_c1"))
        assert repo.count() == 1

    def test_count_with_filter(self, repo: _DictRepo) -> None:
        for i in range(4):
            repo.upsert(_DummyEntity(
                id=f"dum_{i}", name=f"E{i}", value=i % 2,
                created_at=datetime(2026, 6, 7, 0, 0),
            ))
        assert repo.count({"value": 1}) == 2


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


class TestExists:
    def test_exists_true(self, repo: _DictRepo) -> None:
        repo.upsert(_DummyEntity(
            id="dum_exists", name="X", value=0,
            created_at=datetime(2026, 6, 7, 0, 0),
        ))
        assert repo.exists(UEID("dum_exists")) is True

    def test_exists_false(self, repo: _DictRepo) -> None:
        assert repo.exists(UEID("dum_nope")) is False

    def test_exists_after_delete(self, repo: _DictRepo) -> None:
        repo.upsert(_DummyEntity(
            id="dum_gone", name="Gone", value=0,
            created_at=datetime(2026, 6, 7, 0, 0),
        ))
        repo.delete(UEID("dum_gone"))
        assert repo.exists(UEID("dum_gone")) is False


class TestGetMany:
    def test_get_many_returns_found(self, repo: _DictRepo) -> None:
        for i in range(5):
            repo.upsert(_DummyEntity(
                id=f"dum_{i}", name=f"E{i}", value=i,
                created_at=datetime(2026, 6, 7, 0, 0),
            ))
        result = repo.get_many([UEID("dum_0"), UEID("dum_2"), UEID("dum_99")])
        assert len(result) == 2
        ids = {e.id for e in result}
        assert ids == {"dum_0", "dum_2"}

    def test_get_many_empty(self, repo: _DictRepo) -> None:
        assert repo.get_many([]) == []


class TestUpsertMany:
    def test_upsert_many(self, repo: _DictRepo) -> None:
        entities = [
            _DummyEntity(id=f"dum_{i}", name=f"E{i}", value=i,
                         created_at=datetime(2026, 6, 7, 0, 0))
            for i in range(3)
        ]
        repo.upsert_many(entities)
        assert repo.count() == 3

    def test_upsert_many_empty(self, repo: _DictRepo) -> None:
        repo.upsert_many([])
        assert repo.count() == 0


class TestDeleteMany:
    def test_delete_many(self, repo: _DictRepo) -> None:
        for i in range(5):
            repo.upsert(_DummyEntity(
                id=f"dum_{i}", name=f"E{i}", value=i,
                created_at=datetime(2026, 6, 7, 0, 0),
            ))
        removed = repo.delete_many([UEID("dum_0"), UEID("dum_2"), UEID("dum_99")])
        assert removed == 2
        assert repo.count() == 3

    def test_delete_many_empty(self, repo: _DictRepo) -> None:
        assert repo.delete_many([]) == 0
