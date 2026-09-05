"""MCP tool: investigation_complete — Plan C Task 3."""
from __future__ import annotations

from typing import Any

from contracts.investigation import InvestigationStatus


def investigation_complete(
    inq_id: str,
    final_status: InvestigationStatus = "resolved",
    actor: str = "agent",
    inq_ueid: str | None = None,
) -> dict[str, Any]:
    """Complete an investigation (mark as in_progress, resolved or archived).

    Args:
        inq_id: Investigation ID.
        final_status: "in_progress", "resolved" (success) or "archived" (abandoned).
                     Note: resolved/archived are terminal states; use in_progress for ongoing work.
        actor: Who is completing the investigation.
        inq_ueid: Optional UEID if investigation crystallized into a hierarchy entry.

    Returns:
        {"inq_id": str, "status": final_status, "old_status": str} on success.
        {"error": ..., "detail": ...} on failure.
    """
    if final_status not in ("in_progress", "resolved", "archived"):
        return {
            "error": "invalid_terminal_state",
            "detail": f"final_status must be 'in_progress', 'resolved' or 'archived', got {final_status!r}",
        }

    # Local imports (matching investigation_enqueue pattern)
    from mesh.investigation_queue import get, log_transition, transition
    try:
        old = get(inq_id)
    except KeyError as exc:
        return {"error": "not_found", "detail": str(exc)}

    try:
        updated = transition(inq_id, final_status, actor, inq_ueid=inq_ueid)
    except ValueError as exc:
        return {"error": "invalid_transition", "detail": str(exc)}
    except KeyError as exc:
        return {"error": "not_found", "detail": str(exc)}

    log_transition(inq_id, old.status, final_status, actor)
    return {
        "inq_id": inq_id,
        "status": updated.status,
        "old_status": old.status,
    }
