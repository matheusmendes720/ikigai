"""The write-back: the store writes the prose back into a tree of markdown.

This is the inverse of the ingestion, and it is the arrow that was missing
(ADR-043). The properties under test are the ones that keep it from
destroying work:

1. **Only NEW files.** The writer writes the artifacts that have no
   `vault_path`; one that has one belongs to whoever wrote that file.
2. **The conflict is EXPLICIT.** A file that exists with different bytes is
   not rewritten — the prose of a human is not last-write-wins.
3. **The cycle closes in ONE turn.** The file carries the artifact's `ueid`,
   so the ingestion recognises it as the same artifact, and the writer tells
   the store WHAT it wrote, so the ingestion finds the store already saying
   `unchanged`.
4. **The bytes are a function of the artifact.** No clock: two runs produce
   the same file, which is what makes the write idempotent.

The deployment half of the contract — the read-only mounts, the tree that is
not the repository's, and the absence of a push — is asserted where the
deployment is read: `tests/test_deployment_surface.py`.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from src.contracts.common import UEID
from src.contracts.dom import Artifact, ArtifactKind, WriteOutcome, WriteRequest
from src.contracts.errors import ConflictError
from src.services.sync import VaultSource, VaultSync
from src.services.vault_write import (
    CLIENT_ID,
    VaultWrite,
    relative_path_for,
    render_artifact,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


class RecordingRepository:
    """A repository that keeps what it was asked to write."""

    def __init__(self, artifacts: list[Artifact] | None = None) -> None:
        self.artifacts = list(artifacts or [])
        self.requests: list[WriteRequest] = []

    async def artifacts_without_vault_path(self, limit: int = 500) -> list[Artifact]:
        return self.artifacts[:limit]

    async def upsert(
        self,
        req: WriteRequest,
        embedding: Any = None,
    ) -> WriteOutcome:
        self.requests.append(req)
        return WriteOutcome(
            uid=req.artifact.uid,
            revision=req.artifact.revision,
            outcome="updated",
        )


def _artifact(**overrides: Any) -> Artifact:
    fields: dict[str, Any] = {
        "uid": UEID("not:2026-11-10:74dfed05:d6ad7bd8023c5f59"),
        "kind": ArtifactKind.NOTA,
        "title": "Revisão da semana",
        "body": "A prosa do dia, escrita pelo dono.",
        "body_hash": "0" * 64,
        "revision": 1,
        "created_at": datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
    }
    fields.update(overrides)
    return Artifact(**fields)


async def test_the_writer_writes_the_files_the_store_asked_for(tmp_path: Path) -> None:
    """PASS 3: only what has no `vault_path` is written.

    The store is the one that knows: a NULL `vault_path` is the answer to
    "is this already a file?". The writer asks the store and writes exactly
    what it was given.
    """
    artifact = _artifact()
    repo = RecordingRepository([artifact])
    writer = VaultWrite(repo, root=tmp_path)

    report = await writer.write_back()

    assert report.scanned == 1
    assert report.written == 1
    written = list(tmp_path.rglob("*.md"))
    assert len(written) == 1, "the writer wrote something other than the artifact it was given"
    assert written[0].read_text(encoding="utf-8")


async def test_the_file_carries_the_uid_of_the_store(tmp_path: Path) -> None:
    """PASS 4: the frontmatter has the `ueid`, and it is the store's.

    It is the piece that closes the cycle: the ingestion reads the declared
    identity and writes THAT artifact, instead of creating a second one.
    """
    artifact = _artifact()
    repo = RecordingRepository([artifact])
    writer = VaultWrite(repo, root=tmp_path)

    await writer.write_back()

    content = next(tmp_path.rglob("*.md")).read_text(encoding="utf-8")
    assert content.startswith("---\n"), "the file has no frontmatter"
    assert f"ueid: {artifact.uid}" in content, (
        "the file does not carry the store's identity: the ingestion would "
        "create a second artifact for the same prose"
    )


async def test_the_kind_is_the_directory(tmp_path: Path) -> None:
    """The kind travels in the tree, so the round trip preserves it."""
    artifact = _artifact(kind=ArtifactKind.KPI, title="Receita do trimestre")
    repo = RecordingRepository([artifact])
    writer = VaultWrite(repo, root=tmp_path)

    await writer.write_back()

    written = next(tmp_path.rglob("*.md"))
    assert written.parent.name == "kpi", (
        f"the kind is not the directory: {written} — the ingestion reads the "
        f"kind from the tree, and a kind that is lost in the round trip is a "
        f"thing that quietly changes what it is"
    )


async def test_two_rounds_write_the_same_bytes(tmp_path: Path) -> None:
    """PASS 5: the write is idempotent.

    The file is a function of the artifact and of nothing else. A clock in
    the content would make every pass a different file, and a write-back
    that rewrites the file on every pass is a write-back that fights the
    owner's edits.
    """
    artifact = _artifact()
    repo = RecordingRepository([artifact])
    writer = VaultWrite(repo, root=tmp_path)

    await writer.write_back()
    written = next(tmp_path.rglob("*.md"))
    first = hashlib.sha256(written.read_bytes()).hexdigest()

    # The artifact the store holds now carries what was written, so the
    # second round sees the same artifact and must produce the same file.
    await writer.write_back()
    second = hashlib.sha256(written.read_bytes()).hexdigest()

    assert first == second, "the second round rewrote the file"


def test_the_rendered_file_has_no_clock_in_it() -> None:
    """The bytes do not depend on WHEN they were rendered."""
    artifact = _artifact()
    first = render_artifact(artifact)
    second = render_artifact(artifact)
    assert first == second


async def test_a_file_that_differs_is_a_conflict_and_is_not_rewritten(tmp_path: Path) -> None:
    """PASS 7: the conflict is explicit.

    The file on disk is not the file the store describes: somebody edited
    it. It is not overwritten — the prose of a human is not last-write-wins
    — and the divergence is recorded.
    """
    artifact = _artifact()
    repo = RecordingRepository([artifact])
    writer = VaultWrite(repo, root=tmp_path)

    # The owner's edit, already on disk.
    target = tmp_path / relative_path_for(artifact)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("a versão do dono\n", encoding="utf-8")

    report = await writer.write_back()

    assert report.conflicts == 1, "the divergence was not recorded as a conflict"
    assert target.read_text(encoding="utf-8") == "a versão do dono\n", (
        "the writer overwrote a file that was not its own"
    )


async def test_the_writer_says_who_it_is(tmp_path: Path) -> None:
    """PASS 8: the authorship is visible in the store.

    The store distinguishes its writers: the ingestion is `vault-sync`, the
    owner and the agent are their own clients. A write-back with no name of
    its own is a write-back the store cannot account for.
    """
    artifact = _artifact()
    repo = RecordingRepository([artifact])
    writer = VaultWrite(repo, root=tmp_path)

    await writer.write_back()

    assert repo.requests, "the writer wrote a file and told nobody"
    assert repo.requests[0].client_id == CLIENT_ID
    assert CLIENT_ID != "vault-sync", "the writer is indistinguishable from the ingestion"


async def test_the_store_learns_which_file_was_written(tmp_path: Path) -> None:
    """The store records WHAT was written, so the ingestion finds `unchanged`.

    Without this the ingestion would compare the file's bytes with the
    store's prose, see a difference, and rewrite the artifact — which means
    the revision would rise on every pass of the cycle.
    """
    artifact = _artifact()
    repo = RecordingRepository([artifact])
    writer = VaultWrite(repo, root=tmp_path)

    await writer.write_back()

    request = repo.requests[0]
    written = next(tmp_path.rglob("*.md")).read_text(encoding="utf-8")
    assert request.artifact.vault_path == relative_path_for(artifact)
    assert request.artifact.body == written, (
        "the store's body is not the file: the ingestion would rewrite the "
        "artifact on the next pass, and the revision would rise every time"
    )
    assert request.artifact.body_hash == hashlib.sha256(written.encode("utf-8")).hexdigest()


async def test_the_writer_refuses_the_repository_own_vault(tmp_path: Path) -> None:
    """PASS 1 and PASS 10: the tree is not the clone the deploy discards.

    The deploy does `git reset --hard origin/main`: a file written in the
    repository's `vault/` is a file that does not exist after the next
    deploy, and a commit made there is a commit the next deploy undoes.
    """
    repo = RecordingRepository([_artifact()])
    vault = REPO_ROOT / "vault"
    writer = VaultWrite(repo, root=vault)

    with pytest.raises(ValueError, match="vault"):
        await writer.write_back()

    # And nothing was written into it.
    assert not list(vault.glob("escrita/**/*.md")), "the writer wrote into the deploy's tree"


async def test_the_writer_refuses_a_tree_inside_the_repository_vault(tmp_path: Path) -> None:
    """A tree INSIDE the repository's vault is the same tree, and refused."""
    repo = RecordingRepository([_artifact()])
    writer = VaultWrite(repo, root=REPO_ROOT / "vault" / "escrita")

    with pytest.raises(ValueError, match="vault"):
        await writer.write_back()


async def test_a_writer_without_a_tree_writes_nothing(tmp_path: Path) -> None:
    """Without a tree, the writer writes nothing at all.

    A writer with no tree is a writer that would put prose somewhere nobody
    looks.
    """
    repo = RecordingRepository([_artifact()])
    writer = VaultWrite(repo, root=None)

    report = await writer.write_back()

    assert report.written == 0
    assert report.skipped, "the writer said nothing about the tree it does not have"


# ---------------------------------------------------------------------------
# The cycle, end to end
# ---------------------------------------------------------------------------


class FakeStore:
    """A store that behaves like the repository: versioned, and never silent.

    The write is refused when the revision moved under the writer's feet, the
    same way the real repository refuses it — a fake that accepted everything
    would pass a cycle test that the store would fail.
    """

    def __init__(self, artifacts: list[Artifact] | None = None) -> None:
        self.artifacts: dict[str, Artifact] = {
            str(artifact.uid): artifact for artifact in (artifacts or [])
        }
        self.upserts: list[WriteRequest] = []

    async def artifacts_without_vault_path(self, limit: int = 500) -> list[Artifact]:
        return [a for a in self.artifacts.values() if a.vault_path is None][:limit]

    async def get(self, uid: Any) -> Artifact | None:
        return self.artifacts.get(str(uid))

    async def upsert(
        self,
        req: WriteRequest,
        embedding: Any = None,
    ) -> WriteOutcome:
        self.upserts.append(req)
        current = self.artifacts.get(str(req.artifact.uid))
        if (
            req.expected_revision is not None
            and current is not None
            and current.revision != req.expected_revision
        ):
            raise ConflictError(
                f"artifact {req.artifact.uid} was changed by someone else",
                detail="expected_revision is stale — reread and reapply",
            )
        stored = req.artifact.model_copy(update={"revision": req.artifact.revision + 1})
        self.artifacts[str(req.artifact.uid)] = stored
        return WriteOutcome(
            uid=stored.uid,
            revision=stored.revision,
            # The real repository says which of the two happened, and the
            # ingestion's counters are read off this answer.
            outcome="updated" if current is not None else "created",
        )

    async def upsert_relation(self, relation: Any) -> None:
        return None


async def test_the_cycle_closes_in_one_turn(tmp_path: Path) -> None:
    """PASS 6: the ingestion finds the store already saying `unchanged`.

    This is the whole point of the arrow. The writer writes a file and tells
    the store what it wrote; the ingestion then reads that file, recognises
    the artifact by the `ueid` in the frontmatter, compares the bytes with
    what the store holds — and finds them equal. So it writes nothing, the
    revision does not rise, and no second artifact is created for the same
    prose.

    The falsification is in the test itself: take the `ueid` out of the
    frontmatter and the ingestion creates a SECOND artifact, and the count
    below stops being one.
    """
    artifact = _artifact()
    store = FakeStore([artifact])

    written = await VaultWrite(store, root=tmp_path).write_back()
    assert written.written == 1
    revision_after_write = store.artifacts[str(artifact.uid)].revision

    sync = VaultSync(store, sources=[VaultSource(tmp_path, "escrita")])  # type: ignore[arg-type]
    ingestion = await sync.ingest()

    assert ingestion.created == 0, (
        "the ingestion created a second artifact for the same prose: the file "
        "does not carry the identity of the one the store holds"
    )
    assert ingestion.updated == 0, "the ingestion rewrote an artifact that did not change"
    assert ingestion.unchanged == 1, (
        f"the ingestion did not recognise the file: {ingestion}"
    )
    assert len(store.artifacts) == 1, "the cycle created another artifact"
    assert store.artifacts[str(artifact.uid)].revision == revision_after_write, (
        "the revision rose on a file that did not change"
    )


async def test_the_cycle_closes_without_the_ueid_only_by_making_a_second_artifact(
    tmp_path: Path,
) -> None:
    """The falsification of PASS 6, run on purpose.

    The `ueid` in the frontmatter is what closes the cycle. Without it the
    ingestion derives an identity from the file's path — and that identity is
    not the store's, so the same prose arrives twice. This test proves the
    guard above is not vacuous: it takes the piece away and watches the
    cycle open.
    """
    artifact = _artifact()
    store = FakeStore([artifact])

    await VaultWrite(store, root=tmp_path).write_back()
    for path in tmp_path.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        path.write_text(
            content.replace(f"ueid: {artifact.uid}\n", ""),
            encoding="utf-8",
            newline="\n",
        )

    sync = VaultSync(store, sources=[VaultSource(tmp_path, "escrita")])  # type: ignore[arg-type]
    ingestion = await sync.ingest()

    assert ingestion.created == 1, (
        "removing the ueid did NOT make the ingestion create a second "
        "artifact: the guard that proves the cycle closes is vacuous"
    )
    assert len(store.artifacts) == 2


# ---------------------------------------------------------------------------
# The typed fields: a KPI with no numbers is not a KPI
# ---------------------------------------------------------------------------


def _kpi() -> Any:
    from src.contracts.dom_kinds import KPIArtifact

    return KPIArtifact(
        uid=UEID("kpi:receita-do-trimestre:abc12345:def67890"),
        kind=ArtifactKind.KPI,
        title="Receita do trimestre",
        body="A medição que decide o trimestre.",
        metric="receita mensal",
        target=Decimal("10000.50"),
        actual=Decimal("2500"),
        unit="EUR",
        period="2026-Q4",
        direction="up",
        created_at=datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
    )


def test_the_numbers_of_a_kpi_travel_with_the_prose() -> None:
    """The typed fields of the kind are in the file.

    A KPI written without its metric and its target is a title with a
    paragraph: the file says what the thing is called and not what it
    measures. The numbers live in the store's extension table, and the file
    is the prose the owner reads.
    """
    content = render_artifact(_kpi())

    assert "metric: receita mensal" in content
    assert "target: '10000.50'" in content, (
        "the target is not in the file: a KPI that loses its precision, or "
        "its target, is a wrong KPI"
    )
    assert "actual: '2500'" in content
    assert "period: 2026-Q4" in content
    assert "direction: up" in content


async def test_a_kpi_comes_back_from_the_file_with_its_numbers(tmp_path: Path) -> None:
    """The round trip keeps the typed fields — the writer and the ingestion
    share ONE vocabulary.

    The ingestion reads the file, the file states the KPI's own fields, and
    the model that comes out is a KPI with the same metric and the same
    target. A vocabulary written twice is two vocabularies, and the second
    one is the one that loses the measurement.
    """
    store = FakeStore([_kpi()])
    await VaultWrite(store, root=tmp_path).write_back()

    sync = VaultSync(store, sources=[VaultSource(tmp_path, "escrita")])  # type: ignore[arg-type]
    ingestion = await sync.ingest()

    assert ingestion.created == 0, "the ingestion could not read the KPI back"
    assert ingestion.skipped == [], f"the ingestion refused the file: {ingestion.skipped}"

    stored = store.artifacts["kpi:receita-do-trimestre:abc12345:def67890"]
    assert getattr(stored, "metric", None) == "receita mensal"
    assert getattr(stored, "target", None) == Decimal("10000.50")
    assert getattr(stored, "period", None) == "2026-Q4"


def test_a_note_does_not_become_a_kpi_because_it_says_target() -> None:
    """The kind scopes the vocabulary.

    A `target:` in the frontmatter of a note is the note's target. Reading
    it as a KPI's would invent a field the file never claimed — and the
    model forbids extra fields, so the owner's prose would stop being
    ingested over a word.
    """
    from src.contracts.dom_kinds import typed_from_meta

    fields = typed_from_meta(ArtifactKind.NOTA, {"target": "2026", "metric": "x"})

    assert fields == {}, f"a note was read as a KPI: {fields}"
