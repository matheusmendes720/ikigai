"""MCP tool: investigation_status — Plan C Task 3."""
from __future__ import annotations

from typing import Any

from mesh.investigation_queue import get, list_all


def investigation_status(inq_id: str | None = None) -> dict[str, Any]:
    """Fetch the status of one or all investigations.

    Args:
        inq_id: Optional specific investigation. If omitted, returns a summary
                of all investigations grouped by status.

    Returns:
        If inq_id: {"inq_id": str, "status": str, "actor": str, ...} or
                   {"error": "not_found", "detail": str}
        If no inq_id: {"total": int, "by_status": {status: count, ...}}
    """
    if inq_id is not None:
        try:
            inv = get(inq_id)
        except KeyError as exc:
            return {"error": "not_found", "detail": str(exc)}
        return {
            "inq_id": inv.inq_id,
            "status": inv.status,
            "actor": inv.actor,
            "source": inv.source,
            "created_at": inv.created_at.isoformat(),
            "updated_at": inv.updated_at.isoformat(),
            "inq_ueid": inv.inq_ueid,
            "tags": list(inv.tags),
            "payload": inv.payload,
        }
    # No inq_id → return summary
    summary: dict[str, int] = {}
    for inv in list_all():
        summary[inv.status] = summary.get(inv.status, 0) + 1
    return {"total": sum(summary.values()), "by_status": summary}
