"""The zones tree: the owner's six buckets of markdown.

The vault that reaches the VPS is not the closing tree. It is a knowledge tree
with six buckets — `1_norte`, `2_projeto`, `3_indice`, `4_leitura`,
`5_atomicas`, `6_permanentes` — synced from the desktop onto the Cloud Volume
and mounted read-only into the ingestion.

Three things have to hold, and none of them is visible in the code:

1. **The zone decides the kind.** The first path segment IS the zone, and the
   zone is what the owner filed the file under. A bucket that is not named in
   the code is a bucket of notes — adding a seventh needs no release.
2. **The vault's own `type:` does NOT decide the kind.** It is the vault's
   taxonomy, not the DOM's, and in the real tree it types a control-theory note
   as `project` and one file as `Line`. Promoting a note to a planning kind on
   the strength of that would put the wrong thing in the wrong drawer.
3. **The provenance is kept.** The store has to know which file an artifact
   came from: the zone is the first segment of that path, and a write-back
   needs the whole thing.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from src.contracts.dom import ArtifactKind, WriteOutcome, WriteRequest
from src.services.sync import VAULT_ROOTS_ENV, VaultSource, VaultSync, default_sources


class RecordingRepository:
    """A repository that keeps what it was asked to write."""

    def __init__(self) -> None:
        self.written: dict[str, Any] = {}

    async def get(self, uid: Any) -> Any:
        # The store is the one that knows: a file that was already ingested
        # comes back, and the ingestion recognises it by its body hash.
        return self.written.get(str(uid))

    async def upsert(
        self,
        req: WriteRequest,
        embedding: Any = None,
    ) -> WriteOutcome:
        self.written[str(req.artifact.uid)] = req.artifact
        return WriteOutcome(uid=req.artifact.uid, revision=req.artifact.revision, outcome="created")

    async def upsert_relation(self, relation: Any) -> None:
        return None


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def zones_tree(tmp_path: Path) -> Path:
    """A tree with one file per zone, plus the two things that are not artifacts."""
    root = tmp_path / "vault"
    _write(
        root,
        "1_norte/NORTE.md",
        "---\ntype: project\ntopic: Life Vision & Goals\nstatus: active\n"
        "created: 2026-01-01\nupdated: 2026-06-13\n---\n\n# SONHOS ; OBJETIVOS PRIMARIOS\n",
    )
    _write(
        root,
        "2_projeto/business/Business_SRC.md",
        "---\ntype: permanent\ntopic: Business\ncreated: 2026-04-30\n---\n\n# Business\n",
    )
    _write(
        root,
        "5_atomicas/MCP_Enterprise_Patterns.md",
        "---\ntype: atomic\ntopic: MCP\ncreated: 2026-01-15\n---\n\n# Patterns\n",
    )
    _write(
        root,
        "6_permanentes/meta-learning/logic.md",
        "---\ntype: permanent\ntopic: Logica\n---\n\n# Logica\n",
    )
    # A bucket the code has never heard of: it is a bucket of notes.
    _write(root, "7_nova/nota.md", "---\ntopic: Nota\n---\n\n# Nota\n")
    # Not an artifact: a README is scaffolding, and a file at the root of the
    # tree belongs to no zone.
    _write(root, "5_atomicas/README.md", "# Scratchpad\n")
    _write(root, "stray.md", "# Stray\n")
    return root


async def _ingest(root: Path) -> tuple[RecordingRepository, Any]:
    repo = RecordingRepository()
    sync = VaultSync(repo, sources=[VaultSource(root, "zones")])  # type: ignore[arg-type]
    report = await sync.ingest()
    return repo, report


async def test_the_zone_decides_the_kind(zones_tree: Path) -> None:
    repo, _ = await _ingest(zones_tree)
    kinds = {artifact.vault_path: artifact.kind for artifact in repo.written.values()}

    assert kinds["1_norte/NORTE.md"] is ArtifactKind.SONHO
    assert kinds["2_projeto/business/Business_SRC.md"] is ArtifactKind.PLANO
    assert kinds["5_atomicas/MCP_Enterprise_Patterns.md"] is ArtifactKind.NOTA
    assert kinds["6_permanentes/meta-learning/logic.md"] is ArtifactKind.NOTA


async def test_an_unknown_zone_is_a_bucket_of_notes(zones_tree: Path) -> None:
    """A seventh bucket needs no release: a zone the code does not name is a note zone."""
    repo, _ = await _ingest(zones_tree)
    kinds = {artifact.vault_path: artifact.kind for artifact in repo.written.values()}

    assert kinds["7_nova/nota.md"] is ArtifactKind.NOTA


async def test_the_vault_taxonomy_does_not_decide_the_kind(zones_tree: Path) -> None:
    """`type: permanent` inside `2_projeto` stays a PLANO.

    The `type:` is the vault's own vocabulary and it is not the DOM's. In the
    real tree it calls a control-theory note a `project` and one file `Line`,
    so a kind derived from it would be wrong more often than right.
    """
    repo, _ = await _ingest(zones_tree)
    kinds = {artifact.vault_path: artifact.kind for artifact in repo.written.values()}

    assert kinds["2_projeto/business/Business_SRC.md"] is ArtifactKind.PLANO
    assert kinds["5_atomicas/MCP_Enterprise_Patterns.md"] is ArtifactKind.NOTA


async def test_the_provenance_is_kept(zones_tree: Path) -> None:
    """The store has to know which file an artifact came from."""
    repo, _ = await _ingest(zones_tree)
    paths = {artifact.vault_path for artifact in repo.written.values()}

    assert "2_projeto/business/Business_SRC.md" in paths
    assert all(path is not None for path in paths)


async def test_the_zone_is_the_first_segment_of_the_path(zones_tree: Path) -> None:
    """The bucket a file belongs to is readable from its path alone."""
    repo, _ = await _ingest(zones_tree)
    zones = {str(artifact.vault_path).split("/")[0] for artifact in repo.written.values()}

    assert zones == {"1_norte", "2_projeto", "5_atomicas", "6_permanentes", "7_nova"}


async def test_the_vault_dates_are_the_dates_the_vault_declares(zones_tree: Path) -> None:
    """`created:` is the vault's spelling, and it is the date the note carries."""
    repo, _ = await _ingest(zones_tree)
    by_path = {artifact.vault_path: artifact for artifact in repo.written.values()}

    norte = by_path["1_norte/NORTE.md"]
    assert norte.created_at == datetime(2026, 1, 1)
    assert norte.updated_at == datetime(2026, 6, 13)


async def test_the_title_is_the_topic_when_there_is_one(zones_tree: Path) -> None:
    """A vector is the title and the body: a filename is not a subject."""
    repo, _ = await _ingest(zones_tree)
    by_path = {artifact.vault_path: artifact for artifact in repo.written.values()}

    assert by_path["1_norte/NORTE.md"].title == "Life Vision & Goals"


async def test_a_file_at_the_root_of_the_tree_belongs_to_no_zone(zones_tree: Path) -> None:
    repo, report = await _ingest(zones_tree)

    assert not any("stray.md" in str(path) for path in repo.written)
    assert any("stray.md" in skipped for skipped in report.skipped)


async def test_a_readme_is_scaffolding_and_not_an_artifact(zones_tree: Path) -> None:
    repo, report = await _ingest(zones_tree)

    assert not any("README.md" in str(path) for path in repo.written)
    assert any("README.md" in skipped for skipped in report.skipped)


async def test_a_hidden_directory_is_not_a_zone(zones_tree: Path) -> None:
    """The tree carries a `.git` — the owner's vault is a repository.

    A zone called `.git` is not a bucket of knowledge: it is whatever a
    repository happens to keep in markdown.
    """
    _write(zones_tree, ".git/notes.md", "# A commit message\n")
    _write(zones_tree, ".obsidian/workspace.md", "# Workspace\n")

    repo, report = await _ingest(zones_tree)
    paths = {str(artifact.vault_path) for artifact in repo.written.values()}
    # The skipped paths are reported as they are on disk, and the separator is
    # the platform's — so they are normalised before they are compared.
    skipped = {Path(item).as_posix() for item in report.skipped}

    assert not any(path.startswith(".") for path in paths)
    assert any(".git/notes.md" in item for item in skipped)


async def test_the_ingestion_is_idempotent(zones_tree: Path) -> None:
    """A second run recognises every file as already ingested."""
    repo = RecordingRepository()
    sync = VaultSync(repo, sources=[VaultSource(zones_tree, "zones")])  # type: ignore[arg-type]

    first = await sync.ingest()
    second = await sync.ingest()

    assert first.created == len(repo.written)
    assert second.created == 0
    assert second.unchanged == len(repo.written)


def test_the_zones_layout_is_a_layout_the_environment_can_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VAULT_ROOTS_ENV, "/app/zonas=zones")

    sources = default_sources()

    assert len(sources) == 1
    assert sources[0].root == Path("/app/zonas")
    assert sources[0].layout == "zones"


def test_two_trees_can_be_named_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """The closing tree and the zones tree are ingested in the same round."""
    monkeypatch.setenv(
        VAULT_ROOTS_ENV,
        "/app/vault/ikigai/closing-2026=closing,/app/zonas=zones",
    )

    sources = default_sources()

    assert [source.layout for source in sources] == ["closing", "zones"]
