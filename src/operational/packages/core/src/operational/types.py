"""Type aliases, protocols and type variables for the operational domain.

This module centralizes the **type system** that the rest of the package
relies on. It is intentionally free of domain logic and depends only on
the standard library and Pydantic. By design it has **no imports from
``operational.entities`` or ``operational.core``** to avoid circular
dependencies during the package bootstrap.

Three artifacts are exposed:

1. **Branded type aliases** (``Hour``, ``Minute``, ``UEID``, ``StreakInt``,
   ``Score``) — built on :class:`typing.Annotated` and
   :class:`pydantic.Field` so that Pydantic models can use them for
   validation while static type checkers see plain primitives.
2. **Protocols** (``Repository``, ``Clock``, ``Logger``) — structural
   interfaces decorated with :func:`typing.runtime_checkable` so that
   ``isinstance(obj, Protocol)`` works in tests and adapters.
3. **TypeVars** (``T``, ``T_Entity``, ``T_Enum``) — generic parameters
   bound to the appropriate upper bound.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Generic,
    Protocol,
    TypeAlias,
    TypeVar,
    runtime_checkable,
)

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import date, datetime

__all__ = [
    "UEID",
    "UEID_PATTERN",
    "Clock",
    "Hour",
    "Logger",
    "Minute",
    "Repository",
    "Score",
    "StreakInt",
    "T",
    "T_Entity",
    "T_Enum",
]


# ---------------------------------------------------------------------------
# Branded type aliases
# ---------------------------------------------------------------------------

Hour: TypeAlias = Annotated[
    int,
    Field(ge=0, le=23, description="Hour of day in 24h format (0-23)"),
]
"""Hour of day in 24h format. Valid range: ``[0, 23]``."""

Minute: TypeAlias = Annotated[
    int,
    Field(ge=0, le=59, description="Minute of hour (0-59)"),
]
"""Minute of hour. Valid range: ``[0, 59]``."""

UEID: TypeAlias = Annotated[
    str,
    Field(
        pattern=r"^[a-z]{3,5}_[a-z0-9_]+$",
        description="Universal Entity ID (e.g. 'hab_morning_water')",
    ),
]
"""Universal Entity ID.

Format: ``<prefix>_<slug>`` where ``<prefix>`` is 3-5 lowercase letters
(``hab``, ``rou``, ``pmo``, ``blk``, ``day``, ``wkl``) and ``<slug>`` is
one or more lowercase alphanumerics or underscores.
"""

UEID_PATTERN: re.Pattern[str] = re.compile(r"^[a-z]{3,5}_[a-z0-9_]+$")
"""Compiled regex matching a valid UEID.

See :data:`UEID` for the format specification.
"""

StreakInt: TypeAlias = Annotated[
    int,
    Field(ge=0, description="Non-negative streak count (days or sessions)"),
]
"""Non-negative integer streak count."""

Score: TypeAlias = Annotated[
    float,
    Field(ge=0.0, le=1.0, description="Normalized score in [0.0, 1.0]"),
]
"""Normalized score in the closed interval ``[0.0, 1.0]``."""


# ---------------------------------------------------------------------------
# Type variables (declared before Protocols that use them)
# ---------------------------------------------------------------------------

T = TypeVar("T")
"""Unbound type variable. Use when no specific bound is required."""

T_Entity = TypeVar("T_Entity", bound=BaseModel)
"""Type variable bounded by :class:`pydantic.BaseModel`.

Use in generic repositories, serializers, and entity transformers.
"""

T_Enum = TypeVar("T_Enum", bound=StrEnum)
"""Type variable bounded by :class:`enum.StrEnum`.

Use in generic enum-aware helpers (label resolvers, serializers,
CLI converters).
"""


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class Repository(Protocol, Generic[T_Entity]):
    """Generic CRUD repository for any Pydantic entity.

    Concrete implementations include :class:`InMemoryRepository` and
    :class:`SqliteRepository`. All operations are **idempotent** — calling
    ``upsert`` twice with the same entity yields the same final state.

    Type parameter:
        T_Entity: A :class:`pydantic.BaseModel` subclass that the
            repository stores.
    """

    def get(self, id: UEID) -> T_Entity | None:
        """Retrieve a single entity by its :data:`UEID`.

        Args:
            id: Universal Entity ID.

        Returns:
            The entity, or ``None`` if not found.
        """
        ...

    def list(self, filters: dict[str, Any] | None = None) -> list[T_Entity]:
        """List entities, optionally filtered by attribute equality.

        Args:
            filters: Optional mapping of attribute name to expected
                value. Comparisons are ``==``. Unknown attributes raise
                :class:`AttributeError` in concrete implementations.

        Returns:
            A new list of matching entities (never ``None``).
        """
        ...

    def upsert(self, entity: T_Entity) -> UEID:
        """Insert or update an entity, returning its :data:`UEID`.

        Args:
            entity: Entity to persist. Must expose a string ``id`` or
                ``ueid`` attribute (implementation-defined).

        Returns:
            The persisted entity's :data:`UEID`.
        """
        ...

    def delete(self, id: UEID) -> bool:
        """Delete an entity by its :data:`UEID`.

        Args:
            id: Universal Entity ID.

        Returns:
            ``True`` if the entity existed and was removed, ``False``
            otherwise.
        """
        ...

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities, optionally filtered.

        Args:
            filters: Optional mapping of attribute name to expected
                value (same semantics as :meth:`list`).

        Returns:
            Number of matching entities. Always ``>= 0``.
        """
        ...


@runtime_checkable
class Clock(Protocol):
    """Abstract clock for time-based logic.

    Implemented by :class:`SystemClock` (production) and
    :class:`FrozenClock` (tests). Decoupling time from the global
    :func:`datetime.datetime.now` makes every algorithm in the package
    deterministic and easy to test.
    """

    def now(self) -> datetime:
        """Return the current wall-clock datetime.

        Returns:
            A timezone-aware :class:`datetime.datetime` in production;
            tests may return naive datetimes.
        """
        ...

    def today(self) -> date:
        """Return today's date in the clock's local zone.

        Returns:
            A :class:`datetime.date` instance.
        """
        ...


@runtime_checkable
class Logger(Protocol):
    """Structured logger protocol.

    Compatible with ``logging.Logger``, ``loguru.Logger``, and any custom
    logger that exposes ``info``/``warning``/``error`` accepting a
    ``msg`` plus keyword-only structured fields.
    """

    def info(self, msg: str, **fields: Any) -> None:
        """Record an info-level event with structured fields.

        Args:
            msg: Human-readable message.
            **fields: Structured key/value metadata.
        """
        ...

    def warning(self, msg: str, **fields: Any) -> None:
        """Record a warning-level event with structured fields.

        Args:
            msg: Human-readable message.
            **fields: Structured key/value metadata.
        """
        ...

    def error(self, msg: str, **fields: Any) -> None:
        """Record an error-level event with structured fields.

        Args:
            msg: Human-readable message.
            **fields: Structured key/value metadata.
        """
        ...
