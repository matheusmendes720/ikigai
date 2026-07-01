"""Entity registry — auto-discovery and mapping of entity classes."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = [
    "EntityRegistry",
    "entity_registry",
    "get_entity_class",
    "registered_entity_types",
]

# Map entity type string (from UEID prefix) to Pydantic model.
# Built by scanning operational.entities at first call.
_ENTITY_TYPE_MAP: dict[str, type[BaseModel]] = {}


def _discover_entities() -> dict[str, type[BaseModel]]:
    """Scan entity submodules for public Pydantic model classes.

    Returns:
        Mapping of UEID prefix → model class.
    """
    # Late imports to avoid circular dependencies during bootstrap.
    from operational.entities.ajuste_fino import AjusteFino
    from operational.entities.habit import Habit
    from operational.entities.journal import JournalEntry
    from operational.entities.metric import DailyLog, SleepRecord
    from operational.entities.policy import (
        DecisionRecord,
        PolicySetpoints,
    )
    from operational.entities.pomodoro import PomodoroSession
    from operational.entities.routine import Routine, RoutineLog
    from operational.entities.time_block import TimeBlock

    return {
        "rou": Routine,
        "rlog": RoutineLog,
        "blk": TimeBlock,
        "hab": Habit,
        "pmo": PomodoroSession,
        "day": JournalEntry,
        "sle": SleepRecord,
        "log": DailyLog,
        "pol": PolicySetpoints,
        "dec": DecisionRecord,
        "aju": AjusteFino,
    }


class EntityRegistry:
    """Central catalog of entity classes, keyed by UEID prefix.

    Usage:
        >>> from operational.meta import entity_registry
        >>> entity_registry.get("rou")
        <class 'operational.entities.routine.Routine'>
        >>> entity_registry.get("blk_abc")
        <class 'operational.entities.time_block.TimeBlock'>
    """

    def __init__(self) -> None:
        self._map: dict[str, type[BaseModel]] = {}

    def _ensure_loaded(self) -> None:
        if not self._map:
            self._map.update(_discover_entities())

    def register(self, prefix: str, model_class: type[BaseModel]) -> None:
        """Manually register an entity class under a prefix."""
        self._map[prefix] = model_class

    def get(self, ueid_or_prefix: str) -> type[BaseModel] | None:
        """Resolve a UEID (or prefix) to its entity class.

        Args:
            ueid_or_prefix: E.g. ``"rou_morning_water"`` or just ``"rou"``.

        Returns:
            The model class, or ``None`` if unknown.
        """
        self._ensure_loaded()
        prefix = ueid_or_prefix.split("_", maxsplit=1)[0] if "_" in ueid_or_prefix else ueid_or_prefix
        return self._map.get(prefix)

    @property
    def types(self) -> dict[str, type[BaseModel]]:
        """All registered prefix → model mappings."""
        self._ensure_loaded()
        return dict(self._map)

    def __contains__(self, ueid_or_prefix: str) -> bool:
        return self.get(ueid_or_prefix) is not None

    def __repr__(self) -> str:
        self._ensure_loaded()
        items = ", ".join(f"{k}: {v.__name__}" for k, v in sorted(self._map.items()))
        return f"EntityRegistry({items})"


# Singleton
entity_registry: EntityRegistry = EntityRegistry()


def get_entity_class(ueid_or_prefix: str) -> type[BaseModel]:
    """Resolve a UEID to its entity class, raising on failure.

    Args:
        ueid_or_prefix: UEID string or prefix.

    Returns:
        The Pydantic model class.

    Raises:
        ValueError: If the prefix is not registered.
    """
    cls = entity_registry.get(ueid_or_prefix)
    if cls is None:
        msg = f"Unknown entity type: {ueid_or_prefix!r}"
        raise ValueError(msg)
    return cls


def registered_entity_types() -> dict[str, str]:
    """Return human-friendly prefix → class name mapping."""
    return {
        k: v.__name__ for k, v in entity_registry.types.items()
    }
