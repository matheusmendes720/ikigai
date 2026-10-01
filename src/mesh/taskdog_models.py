"""Pydantic v2 strict models for taskdog slice data (M163).

Schema v2 introduces 6 new columns (tags, deps, audit_log, started_at,
completed_at, priority_label) on top of the original 8. This module
gives the mesh read/write paths a typed contract for the slice shape
returned by ``TaskdogAdapter.read()`` and ``list_all()``.

Pydantic v2 strict: ``frozen=True``, ``extra="forbid"`` per repo
conventions (see ``CLAUDE.md`` "Pydantic v2 strict").

Kept self-contained (no import from ``taskdog.py``) to avoid circular
imports — the adapter reads ``sqlite3.Row``-shaped dicts and converts
into these models at the boundary.
"""
from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Audit log entry shape — one element of the `audit_log` JSON column.
class TaskdogAuditEntry(BaseModel):
    """One entry in the taskdog `audit_log` JSON array.

    `timestamp` is ISO8601, `action` matches the canonical task action
    vocabulary, `actor` is the source fork / user / agent name, and
    `fields_diff` records what changed in this audit event.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: str
    action: Literal["create", "update", "done", "delete"]
    actor: str
    fields_diff: dict[str, Any] = Field(default_factory=dict)


# Priority label — constrained to the P0/P1/P2/P3 textual scale.
PriorityLabel = Literal["P0", "P1", "P2", "P3"]


class TaskdogSlice(BaseModel):
    """Typed view of one row in the taskdog `tasks` table (schema v2).

    Mirrors the 14-column schema:
      - 8 original:   ueid, name, status, priority, planned_start,
                      planned_end, deadline, created_at
      - 6 M163 v2:    tags, deps, audit_log, started_at, completed_at,
                      priority_label

    The ``model_validator(mode="before")`` below coerces values that
    arrive from SQLite (where `tags`, `deps`, `audit_log` are stored as
    JSON strings) into the typed list shapes the Pydantic fields expect.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Original v1 columns
    ueid: str
    name: str | None = None
    status: str | None = None
    priority: int | None = None
    planned_start: str | None = None
    planned_end: str | None = None
    deadline: str | None = None
    created_at: str | None = None

    # v2 columns (M163)
    tags: list[str] = Field(default_factory=list)
    deps: list[str] = Field(default_factory=list)
    audit_log: list[TaskdogAuditEntry] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    priority_label: PriorityLabel = "P2"

    @model_validator(mode="before")
    @classmethod
    def _coerce_from_sqlite(cls, data: Any) -> Any:
        """Accept dicts (or dict-like) and normalize SQLite-shaped values.

        SQLite stores JSON arrays as TEXT. When `TaskdogAdapter` reads
        a row it returns ``tags`` / ``deps`` / ``audit_log`` as JSON
        strings — this validator parses them into proper Python lists
        so the Pydantic fields can validate.

        Also coerces ``priority_label`` fallback (None → "P2").
        """
        if not isinstance(data, dict):
            # Pydantic will raise its own validation error for non-dict.
            return data

        out = dict(data)

        # Parse JSON-string list columns.
        for col in ("tags", "deps", "audit_log"):
            if col not in out:
                continue
            value = out[col]
            if value is None:
                # Field defaults to [] / [] / [] via Field(default_factory=…).
                # Drop the key so the default fires cleanly.
                out.pop(col, None)
                continue
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed = []
                out[col] = parsed
            elif not isinstance(value, list):
                # Anything else: drop and let the default apply.
                out.pop(col, None)

        # Priority label fallback for missing / None.
        if out.get("priority_label") is None:
            out["priority_label"] = "P2"

        return out


__all__ = ["TaskdogAuditEntry", "TaskdogSlice", "PriorityLabel"]
