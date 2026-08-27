"""dict_to_frontmatter — IKIGAiRecord → frontmatter-ready dict.

Lossless serializer (replaces the lossy f-string writer at tools.py:350-385).
Preserves:
  - `null` fields (RT-03)
  - tz-aware datetimes as ISO 8601 with offset
  - Path → str
  - Extra fields (SPEC D6 `extra="allow"`) — entity-specific fields
    like DreamEntity.motivation survive
  - The `custom` dict (forward-compat container)
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ikigai.entities.ikigai_record import IKIGAiRecord


def _to_primitive(value: Any) -> Any:
    """Coerce non-yaml-friendly values to primitives."""
    if value is None:
        return None  # RT-03: preserve null explicitly
    if isinstance(value, datetime):
        # ISO 8601 with offset so YAML round-trips and re-parses tz-aware
        return value.isoformat()
    if isinstance(value, Path):
        # Vault paths use forward slashes per data-first convention; portable
        # across OS and the agent's filesystem abstraction.
        return value.as_posix()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _to_primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_primitive(v) for v in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    # Last resort — pydantic-models (ScoreValue, FractalRegime, etc.)
    if hasattr(value, "model_dump"):
        return _to_primitive(value.model_dump())
    return value  # let yaml library handle the rest


def dict_to_frontmatter(record: IKIGAiRecord) -> dict[str, Any]:
    """Serialize IKIGAiRecord → dict suitable for the `python-frontmatter`
    library. Lossless on primitives; nested pydantic models dumped via
    `model_dump`.
    """
    payload = record.model_dump()
    return _to_primitive(payload)


__all__ = ["dict_to_frontmatter"]