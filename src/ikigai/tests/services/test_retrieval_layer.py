"""The retrieval layer: the vector index actually holds something.

The store had the column, the HNSW index and the search that compares vectors
— and the vector was never written. `set_embedding` existed, and nothing
called it: the artifact was stored, the row's `embedding` column stayed NULL,
and the semantic search filtered on `embedding is not null`. It therefore
answered "nothing found" about everything, forever, without a word.

These tests hold the two halves of the repair:

1. the vector is written WITH the artifact — the same write, the same
   transaction, so a row cannot exist without its vector;
2. the query is embedded by the SAME provider that wrote the rows, because a
   cosine distance between two spaces is a number, not a meaning.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import pytest

from src.contracts.dom import ArtifactKind, SearchQuery, WriteOutcome, WriteRequest, make_uid
from src.contracts.dom_kinds import KIND_MODELS
from src.contracts.store import EMBEDDING_DIM
from src.services.artifacts import ArtifactService
from src.services.embeddings import EmbeddingService, local_embedding

NOW = datetime.now(UTC)


class RecordingRepository:
    """A repository that keeps the vector it was handed."""

    def __init__(self) -> None:
        self.embeddings: dict[str, list[float] | None] = {}
        self.queries: list[tuple[SearchQuery, Sequence[float] | None]] = []

    async def upsert(
        self,
        req: WriteRequest,
        embedding: Sequence[float] | None = None,
    ) -> WriteOutcome:
        self.embeddings[str(req.artifact.uid)] = list(embedding) if embedding is not None else None
        return WriteOutcome(uid=req.artifact.uid, revision=req.artifact.revision, outcome="created")

    async def search(
        self,
        query: SearchQuery,
        embedding: Sequence[float] | None = None,
    ) -> Any:
        self.queries.append((query, list(embedding) if embedding is not None else None))
        from src.contracts.dom import SearchResult

        return SearchResult(artifacts=())

    async def require(self, uid: Any) -> Any:
        raise AssertionError("the test does not write edges")


def _artifact() -> Any:
    return KIND_MODELS[ArtifactKind.NOTA].model_validate(
        {
            "uid": str(make_uid(ArtifactKind.NOTA, "sono", "aabbccdd", "0123456789abcdef")),
            "title": "Sono",
            "body": "dormi oito horas",
            "body_hash": "0" * 64,
            "created_at": NOW,
            "updated_at": NOW,
        }
    )


def _request(artifact: Any) -> WriteRequest:
    return WriteRequest(
        artifact=artifact,
        idempotency_key="k",
        client_id="owner",
    )


async def test_a_write_carries_the_vector_with_it() -> None:
    """The artifact and its vector are the same write.

    If they were two writes, a failure between them would leave a row the
    semantic index cannot see — the exact bug this layer was built to fix.
    """
    repo = RecordingRepository()
    service = ArtifactService(repo, EmbeddingService(provider=local_embedding))

    await service.upsert(_request(_artifact()))

    vector = repo.embeddings[str(_artifact().uid)]
    assert vector is not None, "the artifact was stored without a vector"
    assert len(vector) == EMBEDDING_DIM


async def test_a_service_without_an_embedder_still_writes() -> None:
    """A service that cannot embed must not refuse to write."""
    repo = RecordingRepository()
    service = ArtifactService(repo)

    await service.upsert(_request(_artifact()))

    assert repo.embeddings[str(_artifact().uid)] is None


async def test_the_query_is_embedded_by_the_same_provider() -> None:
    """One space, not two.

    The rows are embedded by the provider; the query has to be embedded by
    the same one, or the comparison is between different spaces.
    """
    repo = RecordingRepository()
    provider_calls: list[str] = []

    def provider(text: str) -> list[float]:
        provider_calls.append(text)
        return local_embedding(text)

    service = ArtifactService(repo, EmbeddingService(provider=provider))

    await service.search(SearchQuery(text="como dormi", semantic=True))

    assert repo.queries, "the search never reached the repository"
    query, vector = repo.queries[-1]
    assert query.semantic is True
    assert vector is not None, "the query was never embedded"
    assert len(vector) == EMBEDDING_DIM
    assert provider_calls == ["como dormi"]


async def test_a_structured_search_embeds_nothing() -> None:
    """The full-text path does not need a vector, and does not ask for one."""
    repo = RecordingRepository()
    service = ArtifactService(repo, EmbeddingService(provider=local_embedding))

    await service.search(SearchQuery(text="sono", semantic=False))

    _query, vector = repo.queries[-1]
    assert vector is None


async def test_a_semantic_search_without_an_embedder_is_refused() -> None:
    """It says the service is incomplete instead of answering with nothing."""
    from src.contracts.errors import InvalidPayloadError

    repo = RecordingRepository()
    service = ArtifactService(repo)

    with pytest.raises(InvalidPayloadError):
        await service.search(SearchQuery(text="sono", semantic=True))


def test_the_wiring_gives_the_service_an_embedder(monkeypatch: pytest.MonkeyPatch) -> None:
    """The wiring is what production uses, so it is what has to be checked.

    A wiring that forgets the embedder reproduces the original bug exactly:
    every write lands, and the vector index stays empty.
    """
    from src.services.wiring import build_services

    monkeypatch.setenv("IKIGAI_STORE_DSN", "postgresql://ikigai:ikigai@localhost:5432/ikigai")
    services = build_services()

    assert services.artifacts.embedder is not None, (
        "the wiring writes artifacts without a vector — the semantic index would "
        "answer 'nothing found' about everything"
    )
    assert services.changes is not None


def test_the_provider_is_chosen_by_the_environment() -> None:
    """The provider is a decision of the deployment, not of the code."""
    from src.services.embeddings import provider_from_env

    local = provider_from_env({})
    assert local is not None

    with pytest.raises(ValueError, match="IKIGAI_EMBEDDING_PROVIDER"):
        provider_from_env({"IKIGAI_EMBEDDING_PROVIDER": "telepathy"})

    with pytest.raises(ValueError, match="IKIGAI_EMBEDDING_BASE_URL"):
        provider_from_env({"IKIGAI_EMBEDDING_PROVIDER": "openai"})

    provider = provider_from_env(
        {
            "IKIGAI_EMBEDDING_PROVIDER": "openai",
            "IKIGAI_EMBEDDING_BASE_URL": "https://example.invalid/v1",
            "IKIGAI_EMBEDDING_MODEL": "a-model",
        }
    )
    assert provider is not None
