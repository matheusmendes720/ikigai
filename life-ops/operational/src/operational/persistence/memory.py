"""In-memory repository — dict-backed, no I/O.

:class:`InMemoryRepository[T_Entity]` implements :class:`RepositoryBase`
using a plain ``dict``.  Every operation is O(1) or O(n) scan for
``list``/``count`` with filters.  The store is **not** persisted across
process restarts.

Use in tests, REPL sessions, and anywhere persistence is not required.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic

from operational.persistence.base import RepositoryBase
from operational.types import T_Entity

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["InMemoryRepository"]


class InMemoryRepository(RepositoryBase[T_Entity], Generic[T_Entity]):
    """In-memory repository backed by a ``dict[str, dict[str, Any]]``.

    Args:
        model_class: The Pydantic model class (used for deserialization).
        seed_data: Optional initial entities (id → entity dict).

    Example:
        >>> from operational.entities.routine import Routine
        >>> repo: InMemoryRepository[Routine] = InMemoryRepository(Routine)
        >>> repo.count()
        0
    """

    def __init__(
        self,
        model_class: type[T_Entity],
        seed_data: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._model_class = model_class
        self._store: dict[str, dict[str, Any]] = dict(seed_data or {})

    # ------------------------------------------------------------------
    # Storage engine API
    # ------------------------------------------------------------------

    def _load_all(self) -> dict[str, dict[str, Any]]:
        """Return the full store dict."""
        return dict(self._store)

    def _persist_one(self, entity_id: str, data: dict[str, Any]) -> None:
        """Write or overwrite a single entity."""
        self._store[entity_id] = data

    def _remove_one(self, entity_id: str) -> None:
        """Delete a single entity by id — no-op if absent."""
        self._store.pop(entity_id, None)

    def _serialize(self, entity: T_Entity) -> dict[str, Any]:
        """Convert a Pydantic entity to a plain dict.

        Uses ``model_dump(mode='python')`` to preserve Python types
        (datetime, date, etc.) rather than JSON strings.

        Computed fields are excluded to allow roundtrip deserialization
        on models with ``extra="forbid"``.
        """
        computed: set[str] = set(type(entity).model_computed_fields.keys())
        return entity.model_dump(mode="python", exclude=computed)

    def _deserialize(self, data: dict[str, Any]) -> T_Entity:
        """Rebuild a Pydantic entity from a plain dict.

        Uses ``model_validate`` to run full Pydantic validation.
        """
        return self._model_class.model_validate(data)

    # ------------------------------------------------------------------
    # Extra query helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Remove all entities from the in-memory store."""
        self._store.clear()

    def __iter__(self) -> Iterator[T_Entity]:
        """Iterate over all deserialized entities."""
        return iter(self._deserialize(v) for v in self._store.values())

    def __len__(self) -> int:
        """Return the total number of entities."""
        return len(self._store)

    def __bool__(self) -> bool:
        """True if the store is non-empty."""
        return bool(self._store)
