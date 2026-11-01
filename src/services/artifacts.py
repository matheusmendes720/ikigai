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
        return await self._repo.upsert(req)

    async def search(self, query: SearchQuery) -> SearchResult:
        """Search by structured index, full text, or semantics."""
        return await self._repo.search(query)

    async def get(self, uid: Any, depth: int = 1) -> ArtifactBundle:
        """Read an artifact with its edges, and optionally its neighbours."""
        return await self._repo.get_with_relations(uid, depth)

    async def delete(self, uid: Any, expected_revision: int) -> WriteOutcome:
        """Soft delete. The row and its history stay in the store."""
        return await self._repo.soft_delete(uid, expected_revision)
