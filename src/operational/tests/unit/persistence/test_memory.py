"""Unit tests for :mod:`operational.persistence.memory`."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from operational.persistence.memory import InMemoryRepository
from operational.types import UEID


# ---------------------------------------------------------------------------
# Test model
# ---------------------------------------------------------------------------


class _Task(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    title: str
    done: bool = False
    created_at: datetime


@pytest.fixture
def repo() -> InMemoryRepository[_Task]:
    return InMemoryRepository(_Task)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_empty_repo(self) -> None:
        repo = InMemoryRepository(_Task)
        assert repo.count() == 0
        assert len(repo) == 0
        assert bool(repo) is False

    def test_seed_data(self) -> None:
        seed = {
            "t1": {"id": "t1", "title": "A", "done": False,
                   "created_at": datetime(2026, 6, 7, 10, 0)},
            "t2": {"id": "t2", "title": "B", "done": True,
                   "created_at": datetime(2026, 6, 7, 11, 0)},
        }
        repo = InMemoryRepository(_Task, seed_data=seed)
        assert repo.count() == 2
        assert repo.get(UEID("t1")) is not None


# ---------------------------------------------------------------------------
# CRUD (inherited from base — smoke tests)
# ---------------------------------------------------------------------------


class TestCrud:
    def test_upsert_and_get(self, repo: InMemoryRepository[_Task]) -> None:
        task = _Task(
            id="tsk_1", title="Buy milk", created_at=datetime(2026, 6, 7, 8, 0),
        )
        repo.upsert(task)
        retrieved = repo.get(UEID("tsk_1"))
        assert retrieved is not None
        assert retrieved.title == "Buy milk"

    def test_list_filtered(self, repo: InMemoryRepository[_Task]) -> None:
        for i in range(3):
            repo.upsert(_Task(
                id=f"tsk_{i}", title=f"Task {i}",
                done=i == 1,
                created_at=datetime(2026, 6, 7, 8, 0),
            ))
        done = repo.list({"done": True})
        assert len(done) == 1
        assert done[0].id == "tsk_1"

    def test_delete_and_count(self, repo: InMemoryRepository[_Task]) -> None:
        repo.upsert(_Task(
            id="tsk_del", title="Delete me",
            created_at=datetime(2026, 6, 7, 8, 0),
        ))
        assert repo.count() == 1
        repo.delete(UEID("tsk_del"))
        assert repo.count() == 0


# ---------------------------------------------------------------------------
# Type-specific features
# ---------------------------------------------------------------------------


class TestMemoryFeatures:
    def test_clear(self, repo: InMemoryRepository[_Task]) -> None:
        repo.upsert(_Task(
            id="tsk_c", title="C", created_at=datetime(2026, 6, 7, 8, 0),
        ))
        repo.clear()
        assert repo.count() == 0
        assert bool(repo) is False

    def test_iteration(self, repo: InMemoryRepository[_Task]) -> None:
        tasks = [
            _Task(id=f"tsk_{i}", title=f"T{i}",
                  created_at=datetime(2026, 6, 7, 8, 0))
            for i in range(3)
        ]
        for t in tasks:
            repo.upsert(t)
        ids = {e.id for e in repo}
        assert ids == {"tsk_0", "tsk_1", "tsk_2"}

    def test_bool_empty(self, repo: InMemoryRepository[_Task]) -> None:
        assert bool(repo) is False

    def test_bool_nonempty(self, repo: InMemoryRepository[_Task]) -> None:
        repo.upsert(_Task(
            id="tsk_b", title="B", created_at=datetime(2026, 6, 7, 8, 0),
        ))
        assert bool(repo) is True

    def test_len(self, repo: InMemoryRepository[_Task]) -> None:
        assert len(repo) == 0
        repo.upsert(_Task(
            id="tsk_l", title="L", created_at=datetime(2026, 6, 7, 8, 0),
        ))
        assert len(repo) == 1

    def test_serialize_deserialize_roundtrip(self) -> None:
        """Verify that serialization preserves Python types."""
        repo: InMemoryRepository[_Task] = InMemoryRepository(_Task)
        original = _Task(
            id="tsk_rt", title="Roundtrip", done=True,
            created_at=datetime(2026, 6, 7, 9, 30),
        )
        repo.upsert(original)
        restored = repo.get(UEID("tsk_rt"))
        assert restored == original
        assert restored.created_at == datetime(2026, 6, 7, 9, 30)

    def test_repr(self) -> None:
        repo: InMemoryRepository[_Task] = InMemoryRepository(_Task)
        assert "InMemoryRepository" in repr(repo)
