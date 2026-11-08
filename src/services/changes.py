"""The store's change notifications, as domain events.

The store announces every write on a channel (the trigger is in the
migrations). This module turns that stream of notifications into something a
client can act on: a uid and an operation, nothing else.

It exists because the writers are not all in one process. The vault ingestion
runs in its own container, the Telegram client in another, and the retrieval
layer in a third — and a client that only ever sees its own writes is not
synced with anything. The notification is how a write made by one process
reaches the others.

The SQL lives in the data layer. This module holds the meaning, and the
transport that subscribes to it holds none.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from src.data.repository import ArtifactRepository

__all__ = ["ChangeEvent", "ChangeFeed"]


@dataclass(frozen=True)
class ChangeEvent:
    """One artifact changed in the store.

    `uid` is the identity, `op` the operation — ``INSERT``, ``UPDATE`` or
    ``DELETE``. That is the whole event: a client that wants more reads the
    artifact, and the store is the only place that has the current version.
    """

    uid: str
    op: str


class ChangeFeed:
    """The stream of changes the store announces."""

    def __init__(self, repo: ArtifactRepository) -> None:
        self._repo = repo

    async def events(self) -> AsyncIterator[ChangeEvent]:
        """Yield the changes, as they happen.

        The stream is open-ended: it ends when the connection ends. A caller
        that needs it to stop closes the generator.
        """
        async for payload in self._repo.artifact_events():
            uid = payload.get("uid")
            if not isinstance(uid, str) or not uid:
                continue
            op = payload.get("op")
            yield ChangeEvent(uid=uid, op=str(op or "UPDATE").upper())
