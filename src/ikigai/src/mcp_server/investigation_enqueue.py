"""MCP tool: investigation_enqueue — Plan C Task 3."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from contracts.investigation import Investigation
from pydantic import ValidationError


def investigation_enqueue(
    inq_id: str,
    source: str,
    payload: str,
    tags: list[str] | None = None,
    actor: str = "agent",
) -> dict[str, Any]:
    """Enqueue a new investigation.

    Args:
        inq_id: Investigation ID. Format: inq-YYYYMMDD-NNN. Must be unique.
        source: One of "agent", "user", "external".
        payload: Free-form description (min 1 char).
        tags: Optional list of tags.
        actor: Creator actor (default: "agent").

    Returns:
        {"inq_id": str, "path": str, "status": "open"} on success.
        {"error": str, "detail": str} on failure.
    """
    try:
        inv = Investigation(
            inq_id=inq_id,
            source=source,  # type: ignore[arg-type]
            payload=payload,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            actor=actor,
            tags=tuple(tags or ()),
        )
    except ValidationError as exc:
        return {"error": "validation_failed", "detail": str(exc)}

    # Local import to avoid circular: server.py imports this module at registration time
    from mesh.investigation_queue import enqueue as _enqueue

    try:
        path = _enqueue(inv)
    except (OSError, ValueError) as exc:
        return {"error": "enqueue_failed", "detail": str(exc)}

    return {"inq_id": inv.inq_id, "path": str(path), "status": inv.status}
