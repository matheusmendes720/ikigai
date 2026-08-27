"""Tests for :mod:`operational.meta.registry`."""
from __future__ import annotations

import pytest

from operational.entities.ajuste_fino import AjusteFino
from operational.entities.habit import Habit
from operational.entities.journal import JournalEntry
from operational.entities.metric import DailyLog, SleepRecord
from operational.entities.policy import DecisionRecord, PolicySetpoints
from operational.entities.pomodoro import PomodoroSession
from operational.entities.routine import Routine, RoutineLog
from operational.entities.time_block import TimeBlock
from operational.meta.registry import (
    EntityRegistry,
    entity_registry,
    get_entity_class,
    registered_entity_types,
)


class TestEntityRegistry:
    def test_singleton(self) -> None:
        assert EntityRegistry() is not entity_registry
        assert isinstance(entity_registry, EntityRegistry)

    def test_has_all_prefixes(self) -> None:
        expected = {"rou", "blk", "hab", "pmo", "day", "sle", "log", "pol", "dec", "aju", "rlog"}
        assert set(entity_registry.types.keys()) == expected

    def test_resolve_prefix(self) -> None:
        assert entity_registry.get("rou") is Routine

    def test_resolve_ueid(self) -> None:
        assert entity_registry.get("blk_morning_001") is TimeBlock

    def test_resolve_unknown(self) -> None:
        assert entity_registry.get("xyz") is None

    def test_contains(self) -> None:
        assert "rou" in entity_registry
        assert "xyz" not in entity_registry

    @pytest.mark.parametrize(
        ("prefix", "expected_cls"),
        [
            ("rou", Routine),
            ("rlog", RoutineLog),
            ("blk", TimeBlock),
            ("hab", Habit),
            ("pmo", PomodoroSession),
            ("day", JournalEntry),
            ("sle", SleepRecord),
            ("log", DailyLog),
            ("pol", PolicySetpoints),
            ("dec", DecisionRecord),
            ("aju", AjusteFino),
        ],
    )
    def test_all_registrations(self, prefix: str, expected_cls: type) -> None:
        assert entity_registry.get(prefix) is expected_cls

    def test_manual_register(self) -> None:
        reg = EntityRegistry()
        reg.register("xyz", TimeBlock)
        assert reg.get("xyz") is TimeBlock

    def test_get_entity_class(self) -> None:
        assert get_entity_class("hab") is Habit

    def test_get_entity_class_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown entity type"):
            get_entity_class("nope")

    def test_registered_entity_types(self) -> None:
        types = registered_entity_types()
        assert types["rou"] == "Routine"
        assert types["blk"] == "TimeBlock"
        assert len(types) == 11
