"""SSE publisher for agent UI streaming (decision #4).

Emits the canonical EVENT_TAXONOMY to subscribers in JSON form. Buffers
events in-memory; subscribers attach via :meth:`subscribe` and pull
with :meth:`drain`.

The taxonomy mirrors the operator TUI surface (Chat / Tasks / State /
KillSwitch) so events from agent nodes land in the matching pane.

Phase 8.x (parallel branch). No filesystem writes, no daemon, no subprocess.
"""
from __future__ import annotations

import json
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable


# Canonical event taxonomy (9 events). Keys are stable, snake_case,
# dot-namespaced; consumers index by these literals.
EVENT_TAXONOMY: dict[str, str] = {
    "THREAD_CREATED": "thread.created",
    "PROFILE_SWITCHED": "profile.switched",
    "ENTRY_MESSAGE": "entry.message",
    "ENTRY_PROPOSAL": "entry.proposal",
    "PROPOSAL_STATUS_CHANGED": "proposal.status_changed",
    "PROPOSAL_APPROVED": "proposal.approved",
    "PROPOSAL_REJECTED": "proposal.rejected",
    "THREAD_CLOSED": "thread.closed",
    "HANDOFF_VISIBLE": "handoff.visible",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentSSEPublisher:
    """In-process publisher of SSE-style events for the agent UI.

    The publisher is thread-safe (lock-guarded buffer + subscriber set).
    Each :meth:`publish_*` call appends one canonical event; subscribers
    drain them via :meth:`drain`.

    Args:
        thread_id: Optional stable thread identifier; embedded in every
            event for downstream filtering. Auto-generated UUID4 when
            omitted.
        max_buffer: Upper bound on buffered events (oldest dropped on
            overflow). Default 1024 — covers a long session without
            unbounded memory growth.
    """

    def __init__(
        self,
        thread_id: str | None = None,
        max_buffer: int = 1024,
    ) -> None:
        self.thread_id = thread_id or str(uuid.uuid4())
        self._buffer: deque[dict[str, Any]] = deque(maxlen=max_buffer)
        self._subscribers: set[Callable[[dict[str, Any]], None]] = set()
        self._token_map: dict[str, Callable[[dict[str, Any]], None]] = {}
        self._lock = threading.Lock()
        self._dropped: int = 0

    # ----- subscription ----------------------------------------------------

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> str:
        """Register a callback to receive new events.

        Returns a token that can be passed to :meth:`unsubscribe`.
        """
        token = str(uuid.uuid4())
        with self._lock:
            self._subscribers.add(callback)
        # Bind the token to the callback so unsubscribe(token) can detach
        # even when the caller no longer holds the original callable.
        self._token_map[token] = callback
        return token

    def unsubscribe(self, token: str) -> None:
        """Remove a previously-registered subscriber."""
        cb = self._token_map.pop(token, None)
        if cb is not None:
            with self._lock:
                self._subscribers.discard(cb)

    # ----- emit primitive --------------------------------------------------

    def _emit(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Record an event in the buffer and fan out to subscribers."""
        event: dict[str, Any] = {
            "event": event_type,
            "thread_id": self.thread_id,
            "ts": _utcnow_iso(),
            "id": str(uuid.uuid4()),
            "data": dict(payload),
        }
        with self._lock:
            if len(self._buffer) == self._buffer.maxlen:
                self._dropped += 1
            self._buffer.append(event)
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(event)
            except Exception:
                # Subscriber errors must not break the publisher.
                pass
        return event

    # ----- drain -----------------------------------------------------------

    def drain(self) -> list[dict[str, Any]]:
        """Return and clear all buffered events."""
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
        return events

    def history(self) -> list[dict[str, Any]]:
        """Return a snapshot of buffered events without clearing."""
        with self._lock:
            return list(self._buffer)

    # ----- publish_* -------------------------------------------------------

    def publish_thread_created(self, *, profile: str, actor: str = "user") -> dict[str, Any]:
        """Announce that a new chat thread has been created."""
        return self._emit(EVENT_TAXONOMY["THREAD_CREATED"], {
            "profile": profile,
            "actor": actor,
        })

    def publish_profile_switched(
        self,
        *,
        from_profile: str,
        to_profile: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Announce a profile switch within an existing thread."""
        return self._emit(EVENT_TAXONOMY["PROFILE_SWITCHED"], {
            "from": from_profile,
            "to": to_profile,
            "reason": reason,
        })

    def publish_entry_message(self, *, role: str, content: str, entry_id: str | None = None) -> dict[str, Any]:
        """Append a chat message to the active thread."""
        return self._emit(EVENT_TAXONOMY["ENTRY_MESSAGE"], {
            "role": role,
            "content": content,
            "entry_id": entry_id or str(uuid.uuid4()),
        })

    def publish_entry_proposal(
        self,
        *,
        title: str,
        body: str,
        ueid: str | None = None,
    ) -> dict[str, Any]:
        """Submit a proposal (e.g. a planning delta) into the thread."""
        return self._emit(EVENT_TAXONOMY["ENTRY_PROPOSAL"], {
            "title": title,
            "body": body,
            "ueid": ueid,
        })

    def publish_proposal_status_changed(
        self,
        *,
        proposal_id: str,
        from_status: str,
        to_status: str,
    ) -> dict[str, Any]:
        """Record a transition on a tracked proposal."""
        return self._emit(EVENT_TAXONOMY["PROPOSAL_STATUS_CHANGED"], {
            "proposal_id": proposal_id,
            "from": from_status,
            "to": to_status,
        })

    def publish_proposal_approved(
        self,
        *,
        proposal_id: str,
        approver: str,
        comment: str = "",
    ) -> dict[str, Any]:
        """Record an approval decision on a proposal."""
        return self._emit(EVENT_TAXONOMY["PROPOSAL_APPROVED"], {
            "proposal_id": proposal_id,
            "approver": approver,
            "comment": comment,
        })

    def publish_proposal_rejected(
        self,
        *,
        proposal_id: str,
        rejecter: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Record a rejection decision on a proposal."""
        return self._emit(EVENT_TAXONOMY["PROPOSAL_REJECTED"], {
            "proposal_id": proposal_id,
            "rejecter": rejecter,
            "reason": reason,
        })

    def publish_thread_closed(self, *, reason: str = "completed") -> dict[str, Any]:
        """Mark the thread as closed."""
        return self._emit(EVENT_TAXONOMY["THREAD_CLOSED"], {
            "reason": reason,
        })

    def publish_handoff_visible(
        self,
        *,
        from_agent: str,
        to_agent: str,
        summary: str,
    ) -> dict[str, Any]:
        """Make a handoff between agents visible to the UI."""
        return self._emit(EVENT_TAXONOMY["HANDOFF_VISIBLE"], {
            "from": from_agent,
            "to": to_agent,
            "summary": summary,
        })

    # ----- diagnostics -----------------------------------------------------

    @property
    def buffered_count(self) -> int:
        with self._lock:
            return len(self._buffer)

    @property
    def dropped_count(self) -> int:
        return self._dropped

    def render_sse(self, events: list[dict[str, Any]] | None = None) -> str:
        """Render events as an SSE-formatted string (data: ...\\n\\n per event).

        Default drains the buffer. Pass an explicit list to render without
        consuming.
        """
        if events is None:
            events = self.drain()
        chunks = []
        for event in events:
            chunks.append(f"event: {event['event']}\n")
            chunks.append(f"id: {event['id']}\n")
            chunks.append(f"data: {json.dumps(event, separators=(',', ':'))}\n")
            chunks.append("\n")
        return "".join(chunks)