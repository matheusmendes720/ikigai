"""Reason stage: produces proposals (decision #9)."""
from __future__ import annotations
from uuid import uuid4


def reason_node(state):
    state = dict(state)
    state.setdefault("draft_proposal", None)
    user_request = state.get("user_request", "")
    proposal_id = f"ikigai:proposal:{uuid4().hex[:8]}:short"
    state["draft_proposal"] = {
        "proposal_id": proposal_id,
        "status": "draft",
        "reasoning": user_request[:200] if user_request else "",
        "operations": [{"type": "task.create", "target": user_request}] if user_request else [],
    }
    state["reasoning_chain_stage"] = "reason_complete"
    return state
