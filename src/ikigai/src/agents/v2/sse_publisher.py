"""9-event SSE publisher (decision #4)."""
from __future__ import annotations
from typing import Any

EVENT_TAXONOMY = (
    "thread.created",
    "profile.switched",
    "entry.message",
    "entry.proposal",
    "proposal.status_changed",
    "proposal.approved",
    "proposal.rejected",
    "thread.closed",
    "handoff.visible",
)


class AgentSSEPublisher:
    def __init__(self, gateway=None):
        self._gateway = gateway

    def _emit(self, event, payload):
        if self._gateway is None:
            return
        try:
            self._gateway.publish_event(event, payload)
        except Exception:
            pass

    def publish_thread_created(self, thread_id, profile_active, soul_path):
        self._emit("thread.created", {"thread_id": thread_id, "profile_active": profile_active, "soul_path": soul_path})

    def publish_profile_switched(self, from_profile, to_profile, reason=""):
        self._emit("profile.switched", {"from": from_profile, "to": to_profile, "reason": reason})

    def publish_entry_message(self, entry_id, actor, ts, content):
        self._emit("entry.message", {"entry_id": entry_id, "actor": actor, "ts": ts, "content": content})

    def publish_entry_proposal(self, entry_id, proposal_id, status):
        self._emit("entry.proposal", {"entry_id": entry_id, "proposal_id": proposal_id, "status": status})

    def publish_proposal_status_changed(self, proposal_id, from_status, to_status, reason=""):
        self._emit("proposal.status_changed", {"proposal_id": proposal_id, "from": from_status, "to": to_status, "reason": reason})

    def publish_proposal_approved(self, proposal_id, approved_at, approver):
        self._emit("proposal.approved", {"proposal_id": proposal_id, "approved_at": approved_at, "approver": approver})

    def publish_proposal_rejected(self, proposal_id, rejected_at, reason):
        self._emit("proposal.rejected", {"proposal_id": proposal_id, "rejected_at": rejected_at, "reason": reason})

    def publish_thread_closed(self, thread_id, closed_at, summary_path):
        self._emit("thread.closed", {"thread_id": thread_id, "closed_at": closed_at, "summary_path": summary_path})

    def publish_handoff_visible(self, from_profile, to_profile, context_summary):
        self._emit("handoff.visible", {"from": from_profile, "to": to_profile, "context_summary": context_summary})
