"""Abstract repository base — generic CRUD for Pydantic entities.

Provides :class:`RepositoryBase[T_Entity]`, an ABC that fulfills the
:class:`operational.types.Repository` Protocol and leaves only
``_serialize`` / ``_deserialize`` / ``_load`` / ``_save`` to subclasses.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic

from operational.types import UEID, T_Entity

if TYPE_CHECKING:
    import builtins

__all__ = ["RepositoryBase"]


class RepositoryBase(ABC, Generic[T_Entity]):
    """Generic CRUD repository backed by an arbitrary storage engine.

    Subclasses must implement:
      * ``_load_all()`` — return dict of ``{id: serialized_data}``
      * ``_persist_one(entity_id, data)`` — write one entity
      * ``_remove_one(entity_id)`` — delete one entity
      * ``_serialize(entity)`` — convert entity to serializable dict
      * ``_deserialize(data)`` — convert dict back to entity

    The base class handles filtering, counting, and idempotent upsert.
    """

    @abstractmethod
    def _load_all(self) -> dict[str, dict[str, Any]]:
        """Load every stored entity as ``{id: data_dict}``."""

    @abstractmethod
    def _persist_one(self, entity_id: str, data: dict[str, Any]) -> None:
        """Write or overwrite a single entity by its id."""

    @abstractmethod
    def _remove_one(self, entity_id: str) -> None:
        """Delete a single entity by its id.  No-op if absent."""

    @abstractmethod
    def _serialize(self, entity: T_Entity) -> dict[str, Any]:
        """Convert a Pydantic entity to a plain dict for storage."""

    @abstractmethod
    def _deserialize(self, data: dict[str, Any]) -> T_Entity:
        """Rebuild a Pydantic entity from a plain dict."""

    # ------------------------------------------------------------------
    # Public CRUD (Repository Protocol)
    # ------------------------------------------------------------------

    def get(self, id: UEID) -> T_Entity | None:
        """Retrieve an entity by UEID.

        Args:
            id: Universal Entity ID.

        Returns:
            The entity, or ``None`` if not found.
        """
        all_ = self._load_all()
        raw = all_.get(str(id))
        return self._deserialize(raw) if raw is not None else None

    def list(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[T_Entity]:
        """List entities, optionally filtered by attribute equality.

        Args:
            filters: Mapping of attribute name → expected value.
                Unknown attributes raise ``AttributeError``.

        Returns:
            A new list of matching entities.
        """
        all_ = self._load_all()
        entities = [self._deserialize(v) for v in all_.values()]

        if not filters:
            return entities

        result: list[T_Entity] = []
        for ent in entities:
            for attr, expected in filters.items():
                actual = getattr(ent, attr)
                if actual != expected:
                    break
            else:
                result.append(ent)
        return result

    def upsert(self, entity: T_Entity) -> UEID:
        """Insert or replace an entity, returning its UEID.

        Args:
            entity: Pydantic entity with a string ``id`` attribute.

        Returns:
            The entity's UEID.
        """
        entity_id = str(entity.id)  # type: ignore[attr-defined]
        data = self._serialize(entity)
        self._persist_one(entity_id, data)
        return UEID(entity_id)

    def delete(self, id: UEID) -> bool:
        """Delete an entity by UEID.

        Args:
            id: Universal Entity ID.

        Returns:
            ``True`` if the entity existed, ``False`` otherwise.
        """
        existed = self.get(id) is not None
        self._remove_one(str(id))
        return existed

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities, optionally filtered.

        Args:
            filters: Same semantics as :meth:`list`.

        Returns:
            Number of matching entities (always ``>= 0``).
        """
        return len(self.list(filters))

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def exists(self, id: UEID) -> bool:
        """Check whether an entity exists by UEID.

        Args:
            id: Universal Entity ID.

        Returns:
            ``True`` if found.
        """
        return self.get(id) is not None

    def get_many(self, ids: builtins.list[UEID]) -> builtins.list[T_Entity]:
        """Batch-retrieve entities by their UEIDs.

        Args:
            ids: List of UEIDs to fetch.

        Returns:
            Entities that were found (order not guaranteed).
        """
        all_ = self._load_all()
        result: list[T_Entity] = []
        for eid in ids:
            raw = all_.get(str(eid))
            if raw is not None:
                result.append(self._deserialize(raw))
        return result

    def upsert_many(self, entities: builtins.list[T_Entity]) -> None:
        """Batch insert-or-replace entities.

        Args:
            entities: List of Pydantic entities.
        """
        for ent in entities:
            self.upsert(ent)

    def delete_many(self, ids: builtins.list[UEID]) -> int:
        """Batch-delete entities by UEID.

        Args:
            ids: List of UEIDs to delete.

        Returns:
            Number of entities actually removed.
        """
        count = 0
        for eid in ids:
            if self.delete(eid):
                count += 1
        return count
