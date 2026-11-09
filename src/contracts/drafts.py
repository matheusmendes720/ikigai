"""A draft: prose that is being written and has not been committed yet.

A draft is NOT an artifact, and that is the whole point of it having a type of
its own:

- it is not searchable. A half-written sentence in the full-text index and in
  the vector index is a retrieval result nobody asked for, and it would push
  the finished prose down the ranking of every query that shares a word with
  it;
- it is not announced. The change feed exists so that a client learns what a
  WRITER changed; a keystroke is not a change to the DOM, and a feed that
  fires on every keystroke is a feed that carries nothing;
- it does not survive as history. A draft is overwritten in place and
  discarded without a trace — `artifact_revisions` is append-only and a draft
  belongs nowhere near it.

What it IS: the state of a client that has not finished thinking. The reason
it lives in the STORE and not in the client's memory is the same reason the
store exists — the client is one of several (Telegram, a TUI, a harness), it
reconnects, and a draft that dies with the socket is prose the owner has to
write twice.

Two rules, and they are the same two that govern every write here:

- **One writer.** A save goes through the service layer, carries the revision
  it expects, and a stale revision is a conflict — never a silent overwrite.
- **Guarded, not de-duplicated.** There is no idempotency key: a retry carries
  the revision it read, and once the first save has committed that revision is
  stale, so the retry is a conflict and the client rereads. A content key
  would make two saves of the same text inside one second the same save, and
  silently drop the second.

A draft is scoped to a CLIENT, not to the store: two devices composing at once
are two drafts, and neither can see the other's. That is why the key is
`(client_id, draft_id)` and not a UEID — a draft has no identity in the DOM
because it is not in the DOM yet.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import UEID
from .dom import ArtifactKind

__all__ = ["Draft", "DraftOutcome", "DraftSaveRequest"]


class Draft(BaseModel):
    """The prose a client is writing, and the kind it will be committed as."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: Which client is composing. One identity, several devices: this is the
    #: `client_id` the write envelope already carries, not a second identity.
    client_id: str
    #: Chosen by the client and stable across reconnections. A draft that
    #: changed its id on every reconnect would be a draft nobody could resume.
    draft_id: str
    #: What the draft becomes when it is committed. It decides the fields the
    #: commit will need, so the client knows what to ask for before it asks.
    kind: ArtifactKind
    title: str | None = None
    body: str = ""
    #: The artifact the draft will hang from, when it hangs from one.
    parent_uid: UEID | None = None
    revision: int = Field(default=1, ge=1)
    created_at: datetime
    updated_at: datetime


class DraftSaveRequest(BaseModel):
    """The envelope of a save: the draft, and the revision it expects.

    It is deliberately the shape of `WriteRequest` — the same guard, the same
    409 — because a client that knows how to write an artifact should not have
    to learn a second set of rules to save a draft.

    It carries NO idempotency key, and that is a correction rather than an
    omission. A key that identifies "this content at this second" makes two
    saves of the same text inside one second the same save — so the second one
    is silently a no-op. For a CREATE it cannot work at all: the caller does
    not know whether the draft exists, which is exactly what the conflict is
    for. The revision guard already de-duplicates a retry: a retry carries the
    revision it read, and once the first save has committed that revision is
    stale, so the retry is a 409 and the client rereads. That is the honest
    answer, and it is the one the rest of the store gives.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    draft: Draft
    expected_revision: int | None = None
    client_id: str


class DraftOutcome(BaseModel):
    """What a save or a discard actually did.

    `conflict` is a normal outcome, not an exception state — a client that
    lost the optimistic race rereads and reapplies, exactly as it does for an
    artifact.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    client_id: str
    draft_id: str
    revision: int
    outcome: Literal["created", "updated", "conflict", "unchanged", "discarded"]
    detail: str | None = None
