"""Persistence layer — Repository Protocol, in-memory and SQLite backends.

Public API
----------
- :class:`RepositoryBase` — Abstract CRUD base implementing the
  :class:`operational.types.Repository` Protocol.
- :class:`InMemoryRepository` — Dict-backed repo for tests.
- :class:`SqliteRepository` — SQLite-backed repo with JSON blob storage.
- :class:`MigrationRunner` — Apply ``NNN_name.sql`` migration files.
- Exceptions: :class:`PersistenceError`, :class:`EntityNotFoundError`,
  :class:`DuplicateEntityError`, :class:`MigrationError`,
  :class:`StorageBackendError`.
"""
from __future__ import annotations

from operational.persistence.base import RepositoryBase
from operational.persistence.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    MigrationError,
    PersistenceError,
    StorageBackendError,
)
from operational.persistence.memory import InMemoryRepository
from operational.persistence.runner import MigrationRunner, get_applied_migrations
from operational.persistence.sqlite import SqliteRepository, get_connection

__all__ = [
    "DuplicateEntityError",
    "EntityNotFoundError",
    "InMemoryRepository",
    "MigrationError",
    "MigrationRunner",
    "PersistenceError",
    "RepositoryBase",
    "SqliteRepository",
    "StorageBackendError",
    "get_applied_migrations",
    "get_connection",
]
