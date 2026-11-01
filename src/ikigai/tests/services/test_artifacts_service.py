"""Behaviour of the service layer, against an in-memory repository double.

These tests always run: they need no database. They cover the service's own
logic — the write envelope, the idempotency gate, the conflict contract and the
cycle-safe traversal.

They do NOT prove the SQL behaves the same way. That is what
`tests/store/test_store_concurrency.py` is for, against a real Postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.contracts.dom import (
    Artifact,
    ArtifactBundle,
    ArtifactKind,
    Relation,
    RelationType,
    SearchQuery,
    SearchResult,
    WriteOutcome,
    WriteRequest,
)
from src.contracts.errors import ConflictError, InvalidPayloadError, NotFoundError
from src.contracts.store import EMBEDDING_DIM
from src.services.artifacts import ArtifactService
from src.services.embeddings import EmbeddingService, local_embedding
from src.services.relations import RelationService
from src.services.sync import VaultSync

NOW = datetime.now(UTC)


def _uid(slug: str) -> str:
    padded = slug if len(slug) >= 2 else f"{slug}0"
    return f"kpi:{padded}:a1b2c3d4:0123456789abcdef"


def _artifact(slug: str = "taxa", title: str = "Taxa", revision: int = 1) -> Artifact:
    return Artifact(
        uid=_uid(slug),
        kind=ArtifactKind.KPI,
        title=title,
        revision=revision,
        created_at=NOW,
        updated_at=NOW,
    )


class FakeRepository:
    """An in-memory stand-in that honours the same optimistic rules as the SQL."""

    def __init__(self) -> None:
        self.artifacts: dict[str, Artifact] = {}
        self.relations: list[Relation] = []
        self.keys: set[str] = set()

    async def get(self, uid: object) -> Artifact | None:
        return self.artifacts.get(str(uid))

    async def upsert(self, req: WriteRequest) -> WriteOutcome:
        key = req.idempotency_key
        uid = str(req.artifact.uid)
        if key in self.keys:
            existing = self.artifacts.get(uid)
            return WriteOutcome(
                uid=req.artifact.uid,
                revision=existing.revision if existing else req.artifact.revision,
                outcome="unchanged",
            )
        self.keys.add(key)

        existing = self.artifacts.get(uid)
        if req.expected_revision is None:
            if existing is not None:
                raise ConflictError(f"{uid} already exists")
            self.artifacts[uid] = req.artifact
            return WriteOutcome(
                uid=req.artifact.uid,
                revision=req.artifact.revision,
                outcome="created",
            )
        if existing is None:
            raise NotFoundError(f"no artifact with uid {uid}")
        if existing.revision != req.expected_revision:
            raise ConflictError(f"{uid} was changed by someone else")
        updated = req.artifact.model_copy(update={"revision": existing.revision + 1})
        self.artifacts[uid] = updated
        return WriteOutcome(uid=updated.uid, revision=updated.revision, outcome="updated")

    async def soft_delete(self, uid: object, expected_revision: int) -> WriteOutcome:
        key = str(uid)
        existing = self.artifacts.get(key)
        if existing is None:
            raise NotFoundError(f"no artifact with uid {key}")
        if existing.revision != expected_revision:
            raise ConflictError(f"{key} was changed by someone else")
        deleted = existing.model_copy(
            update={"revision": existing.revision + 1, "deleted_at": NOW}
        )
        self.artifacts[key] = deleted
        return WriteOutcome(uid=existing.uid, revision=deleted.revision, outcome="updated")

    async def search(self, query: SearchQuery) -> SearchResult:
        found = [
            artifact
            for artifact in self.artifacts.values()
            if artifact.deleted_at is None
            and (not query.kinds or artifact.kind in query.kinds)
            and (query.quarter is None or artifact.quarter == query.quarter)
        ]
        return SearchResult(artifacts=tuple(found[: query.limit]))

    async def get_with_relations(self, uid: object, depth: int = 1) -> ArtifactBundle:
        key = str(uid)
        artifact = self.artifacts.get(key)
        if artifact is None:
            raise NotFoundError(f"no artifact with uid {key}")
        relations = tuple(
            relation
            for relation in self.relations
            if str(relation.src_uid) == key or str(relation.dst_uid) == key
        )
        return ArtifactBundle(artifact=artifact, relations=relations)

    async def list_relations(
        self, uid: object, rel: RelationType | None = None
    ) -> list[Relation]:
        key = str(uid)
        return [
            relation
            for relation in self.relations
            if (str(relation.src_uid) == key or str(relation.dst_uid) == key)
            and (rel is None or relation.rel == rel)
        ]

    async def upsert_relation(self, relation: Relation) -> None:
        self.relations = [r for r in self.relations if r != relation]
        self.relations.append(relation)


def _request(
    slug: str = "taxa",
    *,
    expected_revision: int | None = None,
    idempotency_key: str = "key-1",
    client_id: str = "laptop",
    title: str = "Taxa",
) -> WriteRequest:
    return WriteRequest(
        artifact=_artifact(slug, title=title),
        expected_revision=expected_revision,
        idempotency_key=idempotency_key,
        client_id=client_id,
    )


async def test_same_idempotency_key_writes_once() -> None:
    repo = FakeRepository()
    service = ArtifactService(repo)  # type: ignore[arg-type]

    first = await service.upsert(_request())
    second = await service.upsert(_request())

    assert first.outcome == "created"
    assert second.outcome == "unchanged"
    assert len(repo.artifacts) == 1


async def test_stale_revision_conflicts_and_keeps_the_stored_value() -> None:
    repo = FakeRepository()
    service = ArtifactService(repo)  # type: ignore[arg-type]

    await service.upsert(_request())
    with pytest.raises(ConflictError):
        await service.upsert(
            _request(expected_revision=99, idempotency_key="key-2", title="Outro")
        )
    stored = repo.artifacts[_uid("taxa")]
    assert stored.title == "Taxa"


async def test_update_bumps_the_revision() -> None:
    repo = FakeRepository()
    service = ArtifactService(repo)  # type: ignore[arg-type]

    await service.upsert(_request())
    outcome = await service.upsert(
        _request(expected_revision=1, idempotency_key="key-2", title="Revisto")
    )
    assert outcome.outcome == "updated"
    assert outcome.revision == 2


async def test_the_write_envelope_is_validated() -> None:
    repo = FakeRepository()
    service = ArtifactService(repo)  # type: ignore[arg-type]

    with pytest.raises(InvalidPayloadError):
        await service.upsert(_request(idempotency_key="  "))
    with pytest.raises(InvalidPayloadError):
        await service.upsert(_request(client_id=""))
    with pytest.raises(InvalidPayloadError):
        await service.upsert(_request(expected_revision=0))


async def test_soft_delete_marks_the_artifact() -> None:
    repo = FakeRepository()
    service = ArtifactService(repo)  # type: ignore[arg-type]

    await service.upsert(_request())
    outcome = await service.delete(_uid("taxa"), 1)
    assert outcome.revision == 2
    assert repo.artifacts[_uid("taxa")].deleted_at is not None


async def test_relation_traversal_terminates_on_a_cycle() -> None:
    repo = FakeRepository()
    service = RelationService(repo)  # type: ignore[arg-type]

    a, b, c = _uid("a"), _uid("b"), _uid("c")
    await service.link(a, b, RelationType.DEPENDS_ON)
    await service.link(b, c, RelationType.DEPENDS_ON)
    await service.link(c, a, RelationType.DEPENDS_ON)

    edges = await service.traverse(a, depth=5)
    assert len(edges) == 3
    assert {str(edge.src_uid) for edge in edges} == {a, b, c}


async def test_embedding_cache_calls_the_provider_once() -> None:
    calls: list[str] = []

    def provider(text: str) -> list[float]:
        calls.append(text)
        return local_embedding(text)

    service = EmbeddingService(provider=provider)
    first = await service.embed("mesma nota")
    second = await service.embed("mesma nota")
    other = await service.embed("outra nota")

    assert first == second
    assert len(first) == service.dim
    assert calls == ["mesma nota", "outra nota"]
    assert service.provider_calls == 2


async def test_local_embedding_is_deterministic_and_unit_length() -> None:
    a = local_embedding("texto de teste")
    b = local_embedding("texto de teste")
    assert a == b
    assert abs(sum(value * value for value in a) - 1.0) < 1e-9
    assert local_embedding("") == [0.0] * EMBEDDING_DIM


async def test_sync_ingestion_is_idempotent(tmp_path: Path) -> None:
    vault = tmp_path / "closing-2026"
    (vault / "02-q4-2026" / "00-sonho").mkdir(parents=True)
    (vault / "02-q4-2026" / "00-sonho" / "sonho-01.md").write_text(
        "# Sonho um\n\nConstruir a camada de dados.\n", encoding="utf-8"
    )

    repo = FakeRepository()
    sync = VaultSync(repo, vault_root=vault)  # type: ignore[arg-type]

    first = await sync.ingest()
    second = await sync.ingest()

    assert first.created == 1
    assert first.scanned == 1
    assert second.created == 0
    assert second.unchanged == 1
    assert len(repo.artifacts) == 1


async def test_sync_reads_the_real_vault_layout(tmp_path: Path) -> None:
    """The tree is closing-2026/<quarter>/<kind>/<file>.md.

    The quarter directory sits in FRONT of the kind directory. A sync that looks
    for the kind in the first segment ingests nothing at all — and still passes
    a test built on a flat fixture.
    """
    vault = tmp_path / "closing-2026"
    quarter_dir = vault / "02-q4-2026"
    (quarter_dir / "04-relatórios-diários").mkdir(parents=True)
    (quarter_dir / "04-relatórios-diários" / "2026-10-30.md").write_text(
        "# Nota do dia\n\nConteúdo real.\n", encoding="utf-8"
    )
    (vault / "99-archive").mkdir(parents=True)
    (vault / "99-archive" / "velho.md").write_text("# Arquivado\n", encoding="utf-8")
    (vault / "README.md").write_text("# Vault\n", encoding="utf-8")

    repo = FakeRepository()
    sync = VaultSync(repo, vault_root=vault)  # type: ignore[arg-type]

    report = await sync.ingest()

    assert report.created == 1, f"the real layout ingested {report.created} artifacts"
    assert report.scanned == 1
    stored = next(iter(repo.artifacts.values()))
    assert stored.kind is ArtifactKind.NOTA
    assert stored.quarter == "Q4-2026"


async def test_sync_skips_readmes_and_archived_material(tmp_path: Path) -> None:
    vault = tmp_path / "closing-2026"
    (vault / "02-q4-2026" / "00-sonho").mkdir(parents=True)
    (vault / "02-q4-2026" / "00-sonho" / "README.md").write_text("# Sonhos\n", encoding="utf-8")
    (vault / "02-q4-2026" / "00-sonho" / "sonho-01.md").write_text(
        "# Sonho um\n", encoding="utf-8"
    )
    (vault / "99-archive").mkdir(parents=True)
    (vault / "99-archive" / "antigo.md").write_text("# Antigo\n", encoding="utf-8")

    repo = FakeRepository()
    sync = VaultSync(repo, vault_root=vault)  # type: ignore[arg-type]

    report = await sync.ingest()

    assert report.created == 1
    assert len(repo.artifacts) == 1


async def test_sync_updates_a_file_whose_content_changed(tmp_path: Path) -> None:
    vault = tmp_path / "closing-2026"
    (vault / "02-q4-2026" / "00-sonho").mkdir(parents=True)
    note = vault / "02-q4-2026" / "00-sonho" / "sonho-01.md"
    note.write_text("# Sonho um\n\nPrimeira versão.\n", encoding="utf-8")

    repo = FakeRepository()
    sync = VaultSync(repo, vault_root=vault)  # type: ignore[arg-type]

    first = await sync.ingest()
    note.write_text("# Sonho um\n\nSegunda versão.\n", encoding="utf-8")
    second = await sync.ingest()

    assert first.created == 1
    assert second.updated == 1
    assert second.created == 0
    assert len(repo.artifacts) == 1
    stored = next(iter(repo.artifacts.values()))
    assert "Segunda versão" in (stored.body or "")
