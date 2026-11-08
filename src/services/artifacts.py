"""The artifact service — the only writer of the store.

ADR-037 D5 gives each store exactly one writer. Clients never touch the
database; they call this service, and the service is where the rules live:
validation, versioning, idempotency and the conflict contract.
"""

from __future__ import annotations

from typing import Any

from src.contracts.dom import (
    Artifact,
    ArtifactBundle,
    SearchQuery,
    SearchResult,
    WriteOutcome,
    WriteRequest,
)
from src.contracts.errors import InvalidPayloadError
from src.data.repository import ArtifactRepository
from src.services.embeddings import EmbeddingService

__all__ = ["ArtifactService"]


class ArtifactService:
    """Domain rules over the artifact repository."""

    def __init__(
        self,
        repo: ArtifactRepository,
        embeddings: EmbeddingService | None = None,
    ) -> None:
        self._repo = repo
        self._embeddings = embeddings

    @property
    def embedder(self) -> EmbeddingService | None:
        """The embedder, when one is wired.

        A service without one writes rows the semantic index cannot see. It
        is exposed so that fact can be checked rather than assumed.
        """
        return self._embeddings

    async def upsert(self, req: WriteRequest) -> WriteOutcome:
        """Write an artifact under optimistic concurrency.

        `expected_revision` of None means create. A stale value means the write
        is rejected: the artifact keeps whatever the other client wrote.

        The vector travels with the row. That is the service layer's call, and
        it is the call that makes the semantic index worth having: a row
        without a vector is a row the retrieval layer cannot see.
        """
        if not req.idempotency_key.strip():
            raise InvalidPayloadError("idempotency_key is required")
        if not req.client_id.strip():
            raise InvalidPayloadError("client_id is required")
        if req.expected_revision is not None and req.expected_revision < 1:
            raise InvalidPayloadError("expected_revision starts at 1")
        await self._check_relations(req)
        embedding = await self._embedding_for(req.artifact)
        return await self._repo.upsert(req, embedding=embedding)

    async def _embedding_for(self, artifact: Artifact) -> list[float] | None:
        """The vector that travels with the artifact.

        None when no embedder is wired: the write still succeeds and the row
        is simply invisible to the semantic index, which the backfill repairs.
        A service that cannot embed must not refuse to write.
        """
        if self._embeddings is None:
            return None
        return await self._embeddings.embed_artifact(artifact)

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
        """Search by structured index, full text, or semantics.

        The semantic path embeds the query HERE, with the same provider that
        wrote the rows. Embedding it in the data layer instead would mean two
        spaces: the rows written by one model and the query written by another,
        compared by a cosine distance that means nothing.
        """
        embedding: list[float] | None = None
        if query.semantic and query.text:
            if self._embeddings is None:
                raise InvalidPayloadError(
                    "a semantic search needs an embedding provider — the service "
                    "has none wired, so the query cannot be put in the same space "
                    "as the rows"
                )
            embedding = await self._embeddings.embed(query.text)
        return await self._repo.search(query, embedding=embedding)

    async def get(self, uid: Any, depth: int = 1) -> ArtifactBundle:
        """Read an artifact with its edges, and optionally its neighbours."""
        return await self._repo.get_with_relations(uid, depth)

    async def delete(self, uid: Any, expected_revision: int) -> WriteOutcome:
        """Soft delete. The row and its history stay in the store."""
        return await self._repo.soft_delete(uid, expected_revision)
