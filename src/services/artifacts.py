"""The artifact service — the only writer of the store.

ADR-037 D5 gives each store exactly one writer. Clients never touch the
database; they call this service, and the service is where the rules live:
validation, versioning, idempotency and the conflict contract.
"""

from __future__ import annotations

from typing import Any

from src.contracts.dom import (
    ArtifactBundle,
    SearchQuery,
    SearchResult,
    WriteOutcome,
    WriteRequest,
)
from src.contracts.errors import InvalidPayloadError
from src.data.repository import ArtifactRepository

__all__ = ["ArtifactService"]


class ArtifactService:
    """Domain rules over the artifact repository."""

    def __init__(self, repo: ArtifactRepository) -> None:
        self._repo = repo

    async def upsert(self, req: WriteRequest) -> WriteOutcome:
        """Write an artifact under optimistic concurrency.

        `expected_revision` of None means create. A stale value means the write
        is rejected: the artifact keeps whatever the other client wrote.
        """
        if not req.idempotency_key.strip():
            raise InvalidPayloadError("idempotency_key is required")
        if not req.client_id.strip():
            raise InvalidPayloadError("client_id is required")
        if req.expected_revision is not None and req.expected_revision < 1:
            raise InvalidPayloadError("expected_revision starts at 1")
        await self._check_relations(req)
        return await self._repo.upsert(req)

    async def _check_relations(self, req: WriteRequest) -> None:
        """The edges must start at the artifact and land on something that exists.

        An edge leaves FROM the artifact being written: the envelope describes
        one artifact and the edges that artifact starts. An edge from anywhere
        else is a different intent — linking two artifacts that are not being
        written — and it is refused rather than quietly accepted.

        The destination must already be in the DOM. A provenance edge points at
        what came before: the decision, the parent, the wave it derives from.
        The store's foreign key refuses a destination that does not exist; this
        check turns the refusal into the NOT_FOUND the agent knows how to
        handle, before the artifact is written at all.
        """
        uid = str(req.artifact.uid)
        for relation in req.relations:
            if str(relation.src_uid) != uid:
                raise InvalidPayloadError(
                    f"a relation must start at the artifact being written ({uid}), "
                    f"not at {relation.src_uid}"
                )
            if str(relation.dst_uid) == uid:
                raise InvalidPayloadError("an artifact cannot relate to itself")
            await self._repo.require(relation.dst_uid)

    async def search(self, query: SearchQuery) -> SearchResult:
        """Search by structured index, full text, or semantics."""
        return await self._repo.search(query)

    async def get(self, uid: Any, depth: int = 1) -> ArtifactBundle:
        """Read an artifact with its edges, and optionally its neighbours."""
        return await self._repo.get_with_relations(uid, depth)

    async def delete(self, uid: Any, expected_revision: int) -> WriteOutcome:
        """Soft delete. The row and its history stay in the store."""
        return await self._repo.soft_delete(uid, expected_revision)
