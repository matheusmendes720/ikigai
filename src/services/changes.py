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
    """What happened after a sequence, and whether anything was LOST.

    `truncated` is the honest part, and it covers the two ways a client can be
    behind without knowing it:

    - **more than one page** — the gap is bigger than `limit`, so the client
      gets the first page and is told to ask again from where it stopped;
    - **older than the log** — the prune has already forgotten the events the
      client needs. An empty page is the answer to both "you are up to date"
      and "I no longer have what you missed", and only one of them is good
      news. `floor` is what tells them apart.
    """

    events: tuple[ChangeEvent, ...]
    tip: int
    truncated: bool = False
    #: The oldest sequence the log still holds. A `since` below it lost events.
    floor: int = 0
    #: The cursor the replay was asked for. `lost` cannot be answered without
    #: it: an empty page means "up to date" AFTER the floor and "gone" BEFORE
    #: it, and the two are the same page.
    since: int = 0

    @property
    def last_seq(self) -> int | None:
        return self.events[-1].seq if self.events else None

    @property
    def lost(self) -> bool:
        """Whether events the client needed are gone for good."""
        return bool(self.floor) and self.since + 1 < self.floor


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

        It asks for one row more than it was willing to return, so "there is
        more" is a fact and not a guess. And it reads the FLOOR of the log,
        because a cursor older than the oldest event kept is a client that
        missed something the store already forgot — which is a different
        answer from "nothing happened", and must not look like one.
        """
        rows = await self._repo.events_since(since, limit + 1)
        floor = await self._repo.event_floor()
        # A gap bigger than one page, or a cursor the prune has overtaken.
        truncated = len(rows) > limit or (bool(floor) and since + 1 < floor)
        events = tuple(
            event for event in (_event(row) for row in rows[:limit]) if event is not None
        )
        return Replay(
            events=events,
            tip=await self.tip(),
            truncated=truncated,
            floor=floor,
            since=since,
        )

    async def tip(self) -> int:
        """The sequence of the last event the store wrote, or 0 for none."""
        return await self._repo.event_tip()

    async def prune(self, keep: int = 10000) -> int:
        """Forget all but the last `keep` events. The log is not content."""
        return await self._repo.prune_events(keep)
