"""Persistence-layer exceptions.

All persistence errors inherit from :class:`PersistenceError` and carry
the repository name and the entity UEID for traceability.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "DuplicateEntityError",
    "EntityNotFoundError",
    "MigrationError",
    "PersistenceError",
    "StorageBackendError",
]


class PersistenceError(RuntimeError):
    """Base exception for all persistence-layer errors."""

    def __init__(
        self,
        message: str,
        repository: str = "unknown",
        entity_id: str | None = None,
        **extra: Any,
    ) -> None:
        self.repository = repository
        self.entity_id = entity_id
        self.extra = extra
        parts = [message]
        if repository != "unknown":
            parts.append(f"[repo={repository}]")
        if entity_id is not None:
            parts.append(f"[id={entity_id}]")
        super().__init__(" ".join(parts))


class EntityNotFoundError(PersistenceError):
    """Raised when an entity is expected but not found."""

    def __init__(
        self,
        entity_id: str,
        repository: str = "unknown",
        message: str | None = None,
    ) -> None:
        msg = message or f"Entity not found: {entity_id}"
        super().__init__(msg, repository=repository, entity_id=entity_id)


class DuplicateEntityError(PersistenceError):
    """Raised on insert when the entity already exists."""

    def __init__(
        self,
        entity_id: str,
        repository: str = "unknown",
        message: str | None = None,
    ) -> None:
        msg = message or f"Entity already exists: {entity_id}"
        super().__init__(msg, repository=repository, entity_id=entity_id)


class MigrationError(PersistenceError):
    """Raised when a database migration fails to apply or verify."""

    def __init__(
        self,
        message: str,
        migration_name: str = "unknown",
        reason: str | None = None,
    ) -> None:
        self.migration_name = migration_name
        self.reason = reason
        msg = f"Migration {migration_name!r} failed"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, repository="migration")


class StorageBackendError(PersistenceError):
    """Raised when the underlying storage backend raises an unexpected error."""

    def __init__(
        self,
        message: str,
        repository: str = "unknown",
        original_error: Exception | None = None,
    ) -> None:
        self.original_error = original_error
        super().__init__(
            message + (f" ({original_error})" if original_error else ""),
            repository=repository,
        )
