"""Reason stage: produces proposals (decision #9).

M88: Real implementation - uses recalled context (from recall_node) to
ground proposals in actual project history. Falls back to a stub
proposal when no context is available (no memory_db, first cycle, etc).

Also increments state['iteration'] so the route_after_reason function
can bound the recall<->reason loop (MAX_REASON_LOOPS).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def _build_proposal_from_context(
    user_request: str,
    recent_intentions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a proposal that references recalled context (M88).

    Strategy:
    - If recent intentions exist, reference the most recent in
      'reasoning' so the proposal is grounded in project history.
    - Build operations from user_request; if empty, fall back to
      'reflect on recent intentions' so the graph produces SOMETHING
      and can route to reflect (which is the intended exit).
    """
    proposal_id = f"ikigai:proposal:{uuid4().hex[:8]}:short"
    operations: list[dict[str, Any]] = []
    reasoning_parts: list[str] = []

    if user_request:
        operations.append({"type": "task.create", "target": user_request})
        reasoning_parts.append(f"User request: {user_request[:120]}")

    if recent_intentions:
        last = recent_intentions[-1]
        ueid = last.get("ueid", "?")
        body = (last.get("body_markdown") or "")[:200]
        reasoning_parts.append(
            f"Grounded in recent intention {ueid}: {body}"
        )
        # If no user_request, propose reflecting on the latest intention
        if not user_request:
            operations.append(
                {"type": "reflect.intention", "target_ueid": ueid}
            )
    else:
        reasoning_parts.append("No recent intentions in memory (first cycle?)")

    return {
        "proposal_id": proposal_id,
        "status": "draft",
        "reasoning": " | ".join(reasoning_parts),
        "operations": operations,
        "context_refs": [r.get("ueid") for r in recent_intentions if r.get("ueid")],
    }


def reason_node(state: dict[str, Any]) -> dict[str, Any]:
    """Produce a draft proposal grounded in recalled context (M88).

    Always returns a non-empty draft_proposal so the route_after_reason
    function routes to reflect (not back to recall) on the first try.
    Bounded by MAX_REASON_LOOPS via state['iteration'].
    """
    state = dict(state)

    # Bump iteration counter so route_after_reason can bound the loop
    state["iteration"] = state.get("iteration", 0) + 1

    user_request = state.get("user_request", "") or state.get("user_input", "") or ""
    context = state.get("context") or {}
    recent_intentions = context.get("recent_intentions") or []

    proposal = _build_proposal_from_context(user_request, recent_intentions)
    state["draft_proposal"] = proposal
    state["reasoning_chain_stage"] = "reason_complete"
    state["last_step"] = "reason"

    # Log for diagnostics (visible with IKIGAI_LOG_LEVEL=DEBUG)
    logger.debug(
        "reason_node produced proposal %s with %d operations, iteration=%d",
        proposal["proposal_id"],
        len(proposal["operations"]),
        state["iteration"],
    )

    return state
