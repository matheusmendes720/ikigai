"""The draft rules. The only writer of `ikig.drafts`.

A draft is the state of a client that has not finished thinking, and the two
things that can go wrong with it are the two things this layer is here to stop:

- **A save overwrites another device's paragraph.** The save carries the
  revision it expects; a stale one is a conflict, and the caller rereads and
  reapplies. The same rule the artifacts follow (ADR-037 D5), applied to prose
  that is not finished yet.
- **A client loses what it wrote.** A save must never be lost to a clock. The
  service stamps `updated_at` on every save so a reconnection can order the
  drafts, and it keeps `created_at` from the first save so a draft that is
  still open is still the same draft.

What this layer deliberately does NOT do:

- It does not commit. Turning a draft into an artifact is
  `ArtifactService.upsert`, with its own envelope, its own idempotency key and
  its own revision guard. A service that committed on the client's behalf
  would be a second writer of the DOM wearing the draft's name.
- It does not announce. A keystroke is not a change to the DOM, and the change
  feed exists to tell clients what a writer changed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.contracts.drafts import Draft, DraftOutcome, DraftSaveRequest
from src.data.drafts import DraftRepository

__all__ = ["DraftService"]


class DraftService:
    """The rules a draft obeys. The store is reached through the repository."""

    def __init__(self, repo: DraftRepository) -> None:
        self._repo = repo

    async def save(
        self,
        draft: Draft,
        *,
        expected_revision: int | None = None,
        idempotency_key: str,
    ) -> DraftOutcome:
        """Save the draft, stamped and guarded.

        The client states the prose and the kind; the service states the
        clock. `created_at` is only taken from the clock on the first save —
        a draft that is still open is still the same draft, and re-stamping it
        on every keystroke would make "when did I start this?" unanswerable.
        """
        now = datetime.now(UTC)
        stamped = draft.model_copy(
            update={
                "created_at": draft.created_at if expected_revision is not None else now,
                "updated_at": now,
                "revision": expected_revision or 1,
            }
        )
        request = DraftSaveRequest(
            draft=stamped,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            client_id=draft.client_id,
        )
        return await self._repo.save(request)

    async def get(self, client_id: str, draft_id: str) -> Draft | None:
        return await self._repo.get(client_id, draft_id)

    async def open_drafts(self, client_id: str, limit: int = 50) -> list[Draft]:
        """What the client was writing when it last went away."""
        return await self._repo.list(client_id, limit)

    async def discard(
        self,
        client_id: str,
        draft_id: str,
        *,
        expected_revision: int | None = None,
    ) -> DraftOutcome:
        return await self._repo.discard(client_id, draft_id, expected_revision)
