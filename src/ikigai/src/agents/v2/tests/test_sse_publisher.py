"""Tests for AgentSSEPublisher (decision #4).

3 tests:
  1. EVENT_TAXONOMY exposes all 9 expected canonical event names.
  2. Each of the 9 publish_* methods emits a correctly-shaped event.
  3. End-to-end flow: subscribe -> emit -> drain -> unsubscribe.
"""
from __future__ import annotations

import json

from src.ikigai.src.agents.v2.sse_publisher import (
    AgentSSEPublisher,
    EVENT_TAXONOMY,
)


def test_event_taxonomy_has_all_nine_constants() -> None:
    expected_keys = {
        "THREAD_CREATED",
        "PROFILE_SWITCHED",
        "ENTRY_MESSAGE",
        "ENTRY_PROPOSAL",
        "PROPOSAL_STATUS_CHANGED",
        "PROPOSAL_APPROVED",
        "PROPOSAL_REJECTED",
        "THREAD_CLOSED",
        "HANDOFF_VISIBLE",
    }
    assert set(EVENT_TAXONOMY.keys()) == expected_keys

    expected_values = {
        "thread.created",
        "profile.switched",
        "entry.message",
        "entry.proposal",
        "proposal.status_changed",
        "proposal.approved",
        "proposal.rejected",
        "thread.closed",
        "handoff.visible",
    }
    assert set(EVENT_TAXONOMY.values()) == expected_values


def test_publish_methods_emit_canonical_events() -> None:
    pub = AgentSSEPublisher(thread_id="t-fixed")
    # Thread must be the one we passed in — every event carries it.
    assert pub.thread_id == "t-fixed"

    # exercise every publish_* method, capturing each event
    events: list[dict] = []
    events.append(pub.publish_thread_created(profile="ikigai"))
    events.append(pub.publish_profile_switched(from_profile="a", to_profile="b"))
    events.append(pub.publish_entry_message(role="user", content="hi"))
    events.append(pub.publish_entry_proposal(title="t", body="b", ueid="ueid-1"))
    events.append(pub.publish_proposal_status_changed(
        proposal_id="p1", from_status="open", to_status="approved"
    ))
    events.append(pub.publish_proposal_approved(proposal_id="p1", approver="alice"))
    events.append(pub.publish_proposal_rejected(proposal_id="p2", rejecter="bob"))
    events.append(pub.publish_thread_closed(reason="done"))
    events.append(pub.publish_handoff_visible(
        from_agent="ikigai", to_agent="taskdog", summary="send task"
    ))

    assert len(events) == 9

    # Each event must carry the canonical envelope: event / thread_id / ts / id / data
    for ev in events:
        assert ev["thread_id"] == "t-fixed"
        assert isinstance(ev["ts"], str) and "T" in ev["ts"]
        assert isinstance(ev["id"], str) and len(ev["id"]) > 0
        assert isinstance(ev["data"], dict)

    # Each event's "event" field must be one of the 9 taxonomy values
    taxonomy_values = set(EVENT_TAXONOMY.values())
    for ev in events:
        assert ev["event"] in taxonomy_values, ev["event"]

    # Spot-check specific event-type assignments
    assert events[0]["event"] == EVENT_TAXONOMY["THREAD_CREATED"]
    assert events[0]["data"]["profile"] == "ikigai"
    assert events[1]["event"] == EVENT_TAXONOMY["PROFILE_SWITCHED"]
    assert events[1]["data"]["from"] == "a"
    assert events[1]["data"]["to"] == "b"
    assert events[2]["event"] == EVENT_TAXONOMY["ENTRY_MESSAGE"]
    assert events[2]["data"]["role"] == "user"
    assert events[3]["event"] == EVENT_TAXONOMY["ENTRY_PROPOSAL"]
    assert events[3]["data"]["ueid"] == "ueid-1"
    assert events[4]["event"] == EVENT_TAXONOMY["PROPOSAL_STATUS_CHANGED"]
    assert events[4]["data"]["from"] == "open"
    assert events[5]["event"] == EVENT_TAXONOMY["PROPOSAL_APPROVED"]
    assert events[5]["data"]["approver"] == "alice"
    assert events[6]["event"] == EVENT_TAXONOMY["PROPOSAL_REJECTED"]
    assert events[6]["data"]["rejecter"] == "bob"
    assert events[7]["event"] == EVENT_TAXONOMY["THREAD_CLOSED"]
    assert events[7]["data"]["reason"] == "done"
    assert events[8]["event"] == EVENT_TAXONOMY["HANDOFF_VISIBLE"]
    assert events[8]["data"]["from"] == "ikigai"
    assert events[8]["data"]["to"] == "taskdog"

    # Drain returns and clears the buffered events
    drained = pub.drain()
    assert len(drained) == 9
    assert pub.buffered_count == 0
    # A second drain is empty (idempotent)
    assert pub.drain() == []


def test_subscribe_drain_render_flow() -> None:
    pub = AgentSSEPublisher(thread_id="t-flow")

    received: list[dict] = []

    def on_event(event: dict) -> None:
        received.append(event)

    token = pub.subscribe(on_event)

    # Emit 3 events; subscriber receives them live AND they buffer
    a = pub.publish_entry_message(role="user", content="hello")
    b = pub.publish_entry_message(role="assistant", content="hi back")
    c = pub.publish_thread_closed(reason="resolved")

    assert len(received) == 3
    assert [e["event"] for e in received] == [
        EVENT_TAXONOMY["ENTRY_MESSAGE"],
        EVENT_TAXONOMY["ENTRY_MESSAGE"],
        EVENT_TAXONOMY["THREAD_CLOSED"],
    ]
    # Live delivery matches the return value of each publish_* call
    assert received[0]["id"] == a["id"]
    assert received[1]["id"] == b["id"]
    assert received[2]["id"] == c["id"]

    # Buffer holds the same 3 events
    assert pub.buffered_count == 3
    history = pub.history()
    assert len(history) == 3
    # history() does not clear
    assert pub.buffered_count == 3

    # render_sse drains and produces a valid SSE stream
    sse = pub.render_sse()
    assert sse.startswith(f"event: {EVENT_TAXONOMY['ENTRY_MESSAGE']}\n")
    assert "event: entry.message\n" in sse
    assert "event: thread.closed\n" in sse
    # data: lines carry JSON-encoded events
    for line in sse.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[len("data: "):])
            assert payload["event"] in EVENT_TAXONOMY.values()
            assert payload["thread_id"] == "t-flow"
    # After render_sse (default drains), buffer is empty
    assert pub.buffered_count == 0

    # Unsubscribe: no further events delivered to callback
    pub.unsubscribe(token)
    pub.publish_entry_message(role="user", content="after unsub")
    assert len(received) == 3  # unchanged

    # But the buffer still records (no subscriber ≠ no record)
    assert pub.buffered_count == 1