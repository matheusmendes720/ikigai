"""The store's change notifications, as domain events.

The store announces every write on a channel (the trigger is in the
migrations) AND keeps the event in a table. This module turns both of those
into something a client can act on: a sequence, a uid and an operation,
nothing else.

It exists because the writers are not all in one process. The vault ingestion
runs in its own container, the Telegram client in another, and the retrieval
layer in a third — and a client that only ever sees its own writes is not
synced with anything. The notification is how a write made by one process
reaches the others.

Two halves, and a client needs both:

- **live** — ``events()`` yields what is happening now. It is what makes the
  feed feel immediate, and it reaches whoever is listening at that instant.
- **replay** — ``replay(since)`` yields what happened while the client was
  away. A channel is a doorbell, not a mailbox: without this half, a client
  that was reconnecting when the write happened never learns it happened, and
  the gap is silent and permanent.

The sequence is the store's, and it is what ties the halves together: a client
remembers the last one it saw, asks for what came after it, and then follows
the live stream from there.

The SQL lives in the data layer. This module holds the meaning, and the
transport that subscribes to it holds none.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any

from src.data.repository import ArtifactRepository

__all__ = ["ChangeEvent", "ChangeFeed", "Replay"]


@dataclass(frozen=True)
class ChangeEvent:
    """One artifact changed in the store.

    `uid` is the identity, `op` the operation — ``INSERT``, ``UPDATE`` or
    ``DELETE``. That is the whole event: a client that wants more reads the
    artifact, and the store is the only place that has the current version.

    `seq` is where the event sits in the store's log, and it is what makes the
    feed resumable. It is None only for an announcement that arrived without
    one — an older trigger, or a payload the store built by hand.
    """

    uid: str
    op: str
    seq: int | None = None


@dataclass(frozen=True)
class Replay:
    """What happened after a sequence, and whether there is more.

    `truncated` is the honest part: a client that was away for a long time gets
    the first `limit` events and is told the gap is bigger than that. It can
    then decide — ask again from the last sequence it received, or reread the
    artifacts it cares about. Silence would be worse than either.
    """

    events: tuple[ChangeEvent, ...]
    tip: int
    truncated: bool = False

    @property
    def last_seq(self) -> int | None:
        return self.events[-1].seq if self.events else None


def _event(payload: Mapping[str, Any]) -> ChangeEvent | None:
    """One announcement, or one row, as an event."""
    uid = payload.get("uid")
    if not isinstance(uid, str) or not uid:
        return None
    op = str(payload.get("op") or "UPDATE").upper()
    raw_seq = payload.get("seq")
    seq: int | None = None
    if isinstance(raw_seq, int):
        seq = raw_seq
    elif isinstance(raw_seq, str) and raw_seq.isdigit():
        seq = int(raw_seq)
    return ChangeEvent(uid=uid, op=op, seq=seq)


class ChangeFeed:
    """The stream of changes the store announces, and the log it keeps."""

    def __init__(self, repo: ArtifactRepository) -> None:
        self._repo = repo

    async def events(self) -> AsyncIterator[ChangeEvent]:
        """Yield the changes, as they happen.

        The stream is open-ended: it ends when the connection ends. A caller
        that needs it to stop closes the generator.
        """
        async for payload in self._repo.artifact_events():
            event = _event(payload)
            if event is not None:
                yield event

    async def replay(self, since: int, limit: int = 500) -> Replay:
        """The changes written after `since`, oldest first.

        It asks for one row more than it was willing to return, so `truncated`
        is a fact and not a guess: a client that gets it knows the gap is
        bigger than one page and can decide what to do next.
        """
        rows = await self._repo.events_since(since, limit + 1)
        truncated = len(rows) > limit
        events = tuple(
            event for event in (_event(row) for row in rows[:limit]) if event is not None
        )
        return Replay(events=events, tip=await self.tip(), truncated=truncated)

    async def tip(self) -> int:
        """The sequence of the last event the store wrote, or 0 for none."""
        return await self._repo.event_tip()

    async def prune(self, keep: int = 10000) -> int:
        """Forget all but the last `keep` events. The log is not content."""
        return await self._repo.prune_events(keep)
