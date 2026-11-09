"""The frontmatter the vault writes and YAML refuses.

The vault writes its tags the Obsidian way:

    tags: [#moc, #ai, #engineering]

In YAML a `#` opens a comment, so the list is never closed, the parser gives
up, and the WHOLE block is lost with it — the date, the topic, the status.
Measured on the real tree: 242 of the 1800 files with a frontmatter lose it
that way.

The block is not garbage. It is a list of `key: value` lines with ONE broken
line in it, so the lines are read one by one and the broken one is the only
thing lost.

And a correction to the mapping has to REACH the rows that were written with
the wrong one: the bytes of the file did not change, so the body hash cannot
see that the artifact it maps to is now a different artifact.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.contracts.dom import ArtifactKind, WriteOutcome, WriteRequest
from src.services.sync import VaultSource, VaultSync


def _as_the_store_returns(value: datetime) -> datetime:
    """What the store gives back for a timestamp.

    The column is `timestamptz`, so a timestamp comes out with a timezone
    whatever went in — and a naive one is read in the timezone of whichever
    server is running. A fake that handed back exactly what it was given
    would hide that, and the row would be rewritten on every round.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class RecordingRepository:
    """A repository that keeps what it was asked to write, and what it holds."""

    def __init__(self) -> None:
        self.written: dict[str, Any] = {}
        self.reads: list[str] = []
        self.keys: list[str] = []

    async def get(self, uid: Any) -> Any:
        self.reads.append(str(uid))
        return self.written.get(str(uid))

    async def upsert(
        self,
        req: WriteRequest,
        embedding: Any = None,
    ) -> WriteOutcome:
        existed = str(req.artifact.uid) in self.written
        artifact = req.artifact
        stored = artifact.model_copy(
            update={
                "created_at": _as_the_store_returns(artifact.created_at),
                "updated_at": _as_the_store_returns(artifact.updated_at),
            }
        )
        self.written[str(req.artifact.uid)] = stored
        self.keys.append(req.idempotency_key)
        return WriteOutcome(
            uid=req.artifact.uid,
            revision=req.artifact.revision,
            outcome="updated" if existed else "created",
        )

    async def upsert_relation(self, relation: Any) -> None:
        return None


BROKEN_TAGS = """---
type: moc
topic: ai-engineer
created: 2026-01-15
updated: 2026-04-30
tags: [#moc, #ai, #engineering]
status: active
folder: 3_indice
---

# AI Engineer
"""


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


async def _ingest(root: Path) -> tuple[RecordingRepository, Any]:
    repo = RecordingRepository()
    sync = VaultSync(repo, sources=[VaultSource(root, "zones")])  # type: ignore[arg-type]
    report = await sync.ingest()
    return repo, report


async def test_a_frontmatter_yaml_refuses_is_still_read(tmp_path: Path) -> None:
    """The date, the topic and the status survive the broken line."""
    root = tmp_path / "vault"
    _write(root, "3_indice/AI-Engineer-MOC.md", BROKEN_TAGS)

    repo, report = await _ingest(root)

    assert report.skipped == [], f"the file was skipped: {report.skipped}"
    artifact = next(iter(repo.written.values()))
    assert artifact.title == "ai-engineer"
    assert artifact.status == "active"
    assert artifact.created_at == datetime(2026, 1, 15, tzinfo=UTC)
    assert artifact.updated_at == datetime(2026, 4, 30, tzinfo=UTC)


async def test_the_broken_tags_line_is_the_only_thing_lost(tmp_path: Path) -> None:
    """The tags are the line YAML choked on; the rest of the block is read."""
    root = tmp_path / "vault"
    _write(root, "3_indice/AI-Engineer-MOC.md", BROKEN_TAGS)

    repo, _ = await _ingest(root)

    artifact = next(iter(repo.written.values()))
    assert artifact.title == "ai-engineer"


async def test_a_frontmatter_yaml_accepts_is_read_the_same_way(tmp_path: Path) -> None:
    """The fallback does not change the files YAML was happy with."""
    root = tmp_path / "vault"
    _write(
        root,
        "3_indice/plain.md",
        "---\ntype: moc\ntopic: plain\ncreated: 2026-01-15\nstatus: active\n---\n\n# Plain\n",
    )

    repo, _ = await _ingest(root)

    artifact = next(iter(repo.written.values()))
    assert artifact.title == "plain"
    assert artifact.created_at == datetime(2026, 1, 15, tzinfo=UTC)


async def test_a_correction_to_the_mapping_reaches_the_row(tmp_path: Path) -> None:
    """The bytes did not change; the artifact they map to did.

    Without this, a frontmatter that becomes readable leaves the row with the
    old title and the old date forever: the body hash is the same, so the
    ingestion recognises the file as already ingested and moves on.
    """
    root = tmp_path / "vault"
    _write(root, "3_indice/AI-Engineer-MOC.md", BROKEN_TAGS)

    repo = RecordingRepository()
    sync = VaultSync(repo, sources=[VaultSource(root, "zones")])  # type: ignore[arg-type]
    await sync.ingest()
    first = next(iter(repo.written.values()))
    assert first.created_at == datetime(2026, 1, 15, tzinfo=UTC)

    # The row as it was written by a mapping that could not read the block:
    # the same bytes, the wrong date.
    stale = first.model_copy(update={"created_at": datetime(2026, 11, 9), "title": "AI Engineer"})
    repo.written[str(first.uid)] = stale

    report = await sync.ingest()

    assert report.updated == 1, f"the correction did not reach the row: {report}"
    assert report.unchanged == 0
    assert repo.written[str(first.uid)].created_at == datetime(2026, 1, 15, tzinfo=UTC)
    assert repo.written[str(first.uid)].title == "ai-engineer"


async def test_an_unchanged_file_is_still_unchanged(tmp_path: Path) -> None:
    """The comparison does not make every file look changed.

    A file that declares no date gets the clock's, and the clock answers with
    a different value every run: comparing it would rewrite the whole tree on
    every round.
    """
    root = tmp_path / "vault"
    _write(root, "3_indice/plain.md", "---\ntopic: plain\n---\n\n# Plain\n")

    repo, _ = await _ingest(root)
    sync = VaultSync(repo, sources=[VaultSource(root, "zones")])  # type: ignore[arg-type]
    second = await sync.ingest()

    assert second.created == 0
    assert second.updated == 0
    assert second.unchanged == 1


async def test_the_kind_of_a_broken_frontmatter_file_is_still_the_zone(tmp_path: Path) -> None:
    """The zone decides the kind, and the broken line does not change that."""
    root = tmp_path / "vault"
    _write(root, "2_projeto/broken.md", BROKEN_TAGS)

    repo, _ = await _ingest(root)

    artifact = next(iter(repo.written.values()))
    assert artifact.kind is ArtifactKind.PLANO
    assert artifact.vault_path == "2_projeto/broken.md"


async def test_the_idempotency_key_carries_the_revision(tmp_path: Path) -> None:
    """A correction is not a repeat of a write that already happened.

    A key built from the body hash alone says "this file, at these bytes" —
    and a correction to the mapping produces the same bytes and a different
    artifact. The store would recognise the key as a write it already did and
    refuse it, and the correction would never reach the row.
    """
    root = tmp_path / "vault"
    _write(root, "3_indice/AI-Engineer-MOC.md", BROKEN_TAGS)

    repo, _ = await _ingest(root)
    first_key = repo.keys[0]

    stale = next(iter(repo.written.values())).model_copy(update={"title": "MOC Specific"})
    repo.written[str(stale.uid)] = stale

    sync = VaultSync(repo, sources=[VaultSource(root, "zones")])  # type: ignore[arg-type]
    await sync.ingest()
    second_key = repo.keys[1]

    assert first_key != second_key, (
        "the correction would be refused as a repeat of the write that already happened"
    )


async def test_a_declared_date_does_not_rewrite_the_row_every_round(tmp_path: Path) -> None:
    """A calendar date is stored at midnight UTC, and it stays put.

    The store's column is `timestamptz`: a naive timestamp handed to it is
    read in the timezone of whichever server is running, and it comes back
    with a timezone. The comparison that decides whether the row is still
    correct then never matches, and the ingestion rewrites the same rows
    every round — forever, on a timer.
    """
    root = tmp_path / "vault"
    _write(
        root,
        "3_indice/dated.md",
        "---\ntopic: dated\ncreated: 2026-01-15\nupdated: 2026-04-30\n---\n\n# Dated\n",
    )

    repo, _ = await _ingest(root)
    sync = VaultSync(repo, sources=[VaultSource(root, "zones")])  # type: ignore[arg-type]
    second = await sync.ingest()

    assert second.created == 0
    assert second.updated == 0, "the row is rewritten on every round"
    assert second.unchanged == 1

    artifact = next(iter(repo.written.values()))
    assert artifact.created_at == datetime(2026, 1, 15, tzinfo=UTC)
    assert artifact.updated_at == datetime(2026, 4, 30, tzinfo=UTC)
