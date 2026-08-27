"""Integration: entity factories → in-memory repository → CRUD roundtrip."""
from __future__ import annotations

import pytest

from operational.entities.habit import Habit
from operational.entities.journal import JournalEntry
from operational.entities.metric import SleepRecord
from operational.entities.routine import Routine
from operational.entities.time_block import TimeBlock
from operational.meta.factories import (
    make_habit,
    make_journal_entry,
    make_routine,
    make_sleep_record,
    make_time_block,
)
from operational.persistence.memory import InMemoryRepository
from operational.types import UEID


@pytest.mark.parametrize(
    ("factory", "model_class", "prefix"),
    [
        (make_routine, Routine, "rou"),
        (make_time_block, TimeBlock, "blk"),
        (make_habit, Habit, "hab"),
        (make_journal_entry, JournalEntry, "day"),
        (make_sleep_record, SleepRecord, "sle"),
    ],
)
def test_factory_to_memory_roundtrip(factory, model_class, prefix: str) -> None:
    repo: InMemoryRepository = InMemoryRepository(model_class=model_class)
    entity = factory()
    uid = repo.upsert(entity)
    assert isinstance(uid, str)
    assert uid.startswith(prefix)

    retrieved = repo.get(UEID(uid))
    assert retrieved is not None
    assert getattr(retrieved, "id") == uid


def test_filter_by_attribute() -> None:
    repo: InMemoryRepository = InMemoryRepository(model_class=Habit)
    w = make_habit(id=UEID("hab_water"), name="Water", resistance=2.0)
    e = make_habit(id=UEID("hab_exercise"), name="Exercise", resistance=8.0)
    r = make_habit(id=UEID("hab_read"), name="Read", resistance=3.0)
    repo.upsert(w)
    repo.upsert(e)
    repo.upsert(r)

    easy = repo.list(filters={"resistance": 2.0})
    assert len(easy) == 1
    assert easy[0].name == "Water"


def test_delete_and_exists() -> None:
    repo: InMemoryRepository = InMemoryRepository(model_class=Routine)
    entity = make_routine()
    uid = repo.upsert(entity)
    assert repo.exists(UEID(uid))
    repo.delete(UEID(uid))
    assert not repo.exists(UEID(uid))
