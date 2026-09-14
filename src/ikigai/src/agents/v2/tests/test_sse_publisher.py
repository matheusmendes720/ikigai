"""Tests for AgentSSEPublisher (decision #4).

3 tests:
  1. EVENT_TAXONOMY exposes all 9 expected canonical event names.
  2. Each of the 9 publish_* methods emits the canonical event via a fake gateway.
  3. The publisher swallows gateway errors so a broken downstream never breaks emit.
"""
from __future__ import annotations

from src.ikigai.src.agents.v2.sse_publisher import (
    AgentSSEPublisher,
    EVENT_TAXONOMY,
)


class FakeGateway:
    """Canned-response mock that records every publish_event call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.raise_on_publish: bool = False

    def publish_event(self, event: str, payload: dict) -> None:
        if self.raise_on_publish:
            raise RuntimeError("downstream gateway is broken")
        self.calls.append((event, dict(payload)))


def test_event_taxonomy_has_all_nine_constants() -> None:
    expected = (
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
    assert tuple(EVENT_TAXONOMY) == expected
    assert len(EVENT_TAXONOMY) == 9


def test_publish_methods_emit_canonical_events() -> None:
    gateway = FakeGateway()
    pub = AgentSSEPublisher(gateway=gateway)

    pub.publish_thread_created(thread_id="t-1", profile_active="ikigai", soul_path="souls/ikigai.md")
    pub.publish_profile_switched(from_profile="ikigai", to_profile="taskdog", reason="bootstrap")
    pub.publish_entry_message(entry_id="e-1", actor="user", ts="2026-09-14T00:00:00Z", content="hi")
    pub.publish_entry_proposal(entry_id="e-2", proposal_id="p-1", status="open")
    pub.publish_proposal_status_changed(proposal_id="p-1", from_status="open", to_status="approved")
    pub.publish_proposal_approved(proposal_id="p-1", approved_at="2026-09-14T00:01:00Z", approver="alice")
    pub.publish_proposal_rejected(proposal_id="p-2", rejected_at="2026-09-14T00:02:00Z", reason="nope")
    pub.publish_thread_closed(thread_id="t-1", closed_at="2026-09-14T00:03:00Z", summary_path="summaries/t-1.md")
    pub.publish_handoff_visible(from_profile="ikigai", to_profile="taskdog", context_summary="send task X")

    assert len(gateway.calls) == 9

    # Every emitted event name must be one of the 9 canonical values
    canonical = set(EVENT_TAXONOMY)
    for event, payload in gateway.calls:
        assert event in canonical
        assert isinstance(payload, dict) and payload

    # Spot-check exact (event, payload) pairs
    expected_pairs = [
        ("thread.created", {"thread_id": "t-1", "profile_active": "ikigai", "soul_path": "souls/ikigai.md"}),
        ("profile.switched", {"from": "ikigai", "to": "taskdog", "reason": "bootstrap"}),
        ("entry.message", {"entry_id": "e-1", "actor": "user", "ts": "2026-09-14T00:00:00Z", "content": "hi"}),
        ("entry.proposal", {"entry_id": "e-2", "proposal_id": "p-1", "status": "open"}),
        ("proposal.status_changed", {"proposal_id": "p-1", "from": "open", "to": "approved", "reason": ""}),
        ("proposal.approved", {"proposal_id": "p-1", "approved_at": "2026-09-14T00:01:00Z", "approver": "alice"}),
        ("proposal.rejected", {"proposal_id": "p-2", "rejected_at": "2026-09-14T00:02:00Z", "reason": "nope"}),
        ("thread.closed", {"thread_id": "t-1", "closed_at": "2026-09-14T00:03:00Z", "summary_path": "summaries/t-1.md"}),
        ("handoff.visible", {"from": "ikigai", "to": "taskdog", "context_summary": "send task X"}),
    ]
    assert gateway.calls == expected_pairs


def test_publisher_swallows_gateway_errors() -> None:
    """A broken gateway must NOT raise out of the publish_* methods."""
    gateway = FakeGateway()
    gateway.raise_on_publish = True
    pub = AgentSSEPublisher(gateway=gateway)

    # All 9 publish_* must complete without raising
    pub.publish_thread_created(thread_id="t", profile_active="ikigai", soul_path="s.md")
    pub.publish_profile_switched(from_profile="a", to_profile="b")
    pub.publish_entry_message(entry_id="e", actor="user", ts="2026-09-14T00:00:00Z", content="x")
    pub.publish_entry_proposal(entry_id="e", proposal_id="p", status="open")
    pub.publish_proposal_status_changed(proposal_id="p", from_status="open", to_status="rejected")
    pub.publish_proposal_approved(proposal_id="p", approved_at="2026-09-14T00:00:00Z", approver="alice")
    pub.publish_proposal_rejected(proposal_id="p", rejected_at="2026-09-14T00:00:00Z", reason="x")
    pub.publish_thread_closed(thread_id="t", closed_at="2026-09-14T00:00:00Z", summary_path="s.md")
    pub.publish_handoff_visible(from_profile="a", to_profile="b", context_summary="x")

    # And a publisher without a gateway is a no-op (does not raise either)
    bare = AgentSSEPublisher()
    bare.publish_thread_created(thread_id="t", profile_active="ikigai", soul_path="s.md")
    bare.publish_handoff_visible(from_profile="a", to_profile="b", context_summary="x")

    # Gateway that raises recorded zero successful calls
    assert gateway.calls == []