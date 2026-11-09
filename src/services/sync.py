"""Ingestion of the vault's markdown into the store.

The vault is prose and stays prose. This module reads it and upserts what it
finds into the structured store, so the structured side stops depending on
`grep` over files.

Two properties matter more than the mapping itself:

- **Idempotent.** Re-running leaves the store count unchanged. The key is the
  vault path plus the content hash, so an unchanged file is recognised as
  already ingested.
- **Read-only.** The vault is append-only and is written by `vault_write`
  (ADR-012). Nothing here writes, moves or deletes anything under `vault/`.

Two tree shapes are ingested, because the repo has two of them:

- `closing` — `closing-2026/<quarter>/<kind>/<file>.md`, the scaffold the
  vault README describes.
- `persona` — `dreams/`, `objectives/`, `projects/`, `ikigai_state/`,
  `deliverables/`, the flat layout the production persona vault uses.

Where a file declares its own `ueid` in frontmatter, that identity wins. It is
the one the rest of the system already links to, and it survives a move of the
file between the two trees.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from src.contracts.common import UEID
from src.contracts.dom import ArtifactKind, Relation, RelationType, WriteRequest, make_uid
from src.contracts.dom_kinds import KIND_MODELS
from src.data.repository import ArtifactRepository
from src.services.embeddings import EmbeddingService

__all__ = ["SyncReport", "VaultSource", "VaultSync", "default_sources", "main"]

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_QUARTER_RE = re.compile(r"^\d+-q(\d)-(\d{4})$")
_SLUG_QUARTER_RE = re.compile(r"\bq(\d)-(\d{4})\b")
_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# The closing tree, from the directories that exist on disk. The prefixes are
# matched against a path SEGMENT, not the whole path, because the quarter
# directory sits in front of the kind directory.
_CLOSING_KINDS: tuple[tuple[str, ArtifactKind], ...] = (
    ("00-sonho", ArtifactKind.SONHO),
    ("01-plano-trimestral", ArtifactKind.PLANO),
    ("02-onda", ArtifactKind.ONDA),
    ("03-revis", ArtifactKind.REVISAO),
    ("04-relat", ArtifactKind.NOTA),
)

# The persona tree, flat, one directory per entity tier.
_PERSONA_KINDS: dict[str, ArtifactKind] = {
    "dreams": ArtifactKind.SONHO,
    "objectives": ArtifactKind.PLANO,
    "projects": ArtifactKind.ONDA,
    "ikigai_state": ArtifactKind.REVISAO,
    "deliverables": ArtifactKind.NOTA,
}

_ARCHIVE_DIR = "99-archive"
_LAYOUTS = ("closing", "persona")

#: Where the ingestion reads its trees from, when the container says so.
#:
#: Each entry is ``<path>=<layout>``, comma-separated. The separator is ``=``
#: and not ``:`` because a Windows path carries colons of its own, and a
#: separator that breaks on half the machines is a separator nobody trusts.
VAULT_ROOTS_ENV = "IKIGAI_VAULT_ROOTS"

#: How long the loop waits between two ingestion runs, in seconds.
SYNC_INTERVAL_ENV = "IKIGAI_VAULT_SYNC_INTERVAL"


@dataclass(frozen=True)
class VaultSource:
    """One markdown tree to ingest, and the shape it is laid out in."""

    root: Path
    layout: Literal["closing", "persona"]


@dataclass
class SyncReport:
    """What one ingestion run did."""

    scanned: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    relations: int = 0
    skipped: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.created + self.updated + self.unchanged


def default_sources() -> list[VaultSource]:
    """The trees the ingestion reads by default.

    Both are included: the closing tree is where prose is written today, and
    the persona tree is where the real content already is. Which one wins for
    a given file is decided by the file, not by the order.

    ``IKIGAI_VAULT_ROOTS`` overrides it, and a container needs that: the vault
    is a VOLUME there, mounted at a path of the deployment's choosing, not at
    the path the repository happens to use. Each entry is ``<path>=<layout>``.
    """
    override = (os.environ.get(VAULT_ROOTS_ENV) or "").strip()
    if override:
        sources: list[VaultSource] = []
        for entry in override.split(","):
            entry = entry.strip()
            if not entry:
                continue
            path, _, layout = entry.rpartition("=")
            if not path or layout not in _LAYOUTS:
                raise ValueError(
                    f"{VAULT_ROOTS_ENV} entry {entry!r} is not '<path>=<layout>', "
                    f"and the layout is one of {list(_LAYOUTS)}"
                )
            sources.append(VaultSource(Path(path), layout))
        if not sources:
            raise ValueError(f"{VAULT_ROOTS_ENV} is set but names no tree")
        return sources

    repo_root = Path(__file__).resolve().parents[2]
    return [
        VaultSource(repo_root / "vault" / "ikigai" / "closing-2026", "closing"),
        VaultSource(repo_root / "src" / "ikigai" / "data" / "matheus", "persona"),
    ]


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    slug = slug[:62].strip("-")
    if not slug:
        return "artefato"
    if len(slug) == 1:
        # A UEID slug is at least two characters.
        slug = f"{slug}0"
    return slug


def _front_matter(text: str) -> dict[str, Any]:
    """Parse the YAML frontmatter, if the file has any and PyYAML is present."""
    match = _FRONT_MATTER_RE.match(text)
    if match is None:
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    try:
        loaded = yaml.safe_load(match.group(1))
    except Exception:  # malformed frontmatter is not fatal to the sync
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _timestamp(value: Any) -> datetime | None:
    """Coerce a frontmatter timestamp into a datetime.

    PyYAML parses an unquoted `date: 2026-09-07` into a `datetime.date`, not
    into a string — so a coercion that only knows about strings drops the
    value without a word. `datetime` is a subclass of `date`, so it has to be
    tested first.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _locate_closing(path: Path, root: Path) -> tuple[ArtifactKind, str | None] | None:
    """Find the kind and the quarter in a `closing-2026/<quarter>/<kind>/` tree.

    The quarter directory sits in FRONT of the kind directory, and it is worth
    keeping: the spine has a `quarter` column precisely for it.

    Archived material is left where it is. It is still markdown and still
    append-only; it is just not part of the live vault.
    """
    try:
        relative = path.relative_to(root)
    except ValueError:
        return None
    if _ARCHIVE_DIR in relative.parts:
        return None
    kind: ArtifactKind | None = None
    quarter: str | None = None
    for part in relative.parts:
        for prefix, candidate in _CLOSING_KINDS:
            if part.startswith(prefix):
                kind = candidate
                break
        match = _QUARTER_RE.match(part)
        if match:
            quarter = f"Q{match.group(1)}-{match.group(2)}"
    if kind is None:
        return None
    return kind, quarter


def _locate_persona(path: Path, root: Path) -> tuple[ArtifactKind, str | None] | None:
    """Find the kind in the flat persona tree."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return None
    if not relative.parts:
        return None
    kind = _PERSONA_KINDS.get(relative.parts[0])
    if kind is None:
        return None
    quarter = None
    match = _SLUG_QUARTER_RE.search(path.stem)
    if match:
        quarter = f"Q{match.group(1)}-{match.group(2)}"
    return kind, quarter


class VaultSync:
    """Reads the vault's markdown and upserts it into the store."""

    def __init__(
        self,
        repo: ArtifactRepository,
        *,
        sources: list[VaultSource] | None = None,
        client_id: str = "vault-sync",
        embeddings: EmbeddingService | None = None,
    ) -> None:
        self._repo = repo
        self._sources = list(sources) if sources is not None else default_sources()
        self._client_id = client_id
        self._embeddings = embeddings

    async def ingest(self) -> SyncReport:
        report = SyncReport()
        for source in self._sources:
            if not source.root.exists():
                report.skipped.append(f"vault root not found: {source.root}")
                continue
            await self._ingest_source(source, report)
        return report

    async def _ingest_source(self, source: VaultSource, report: SyncReport) -> None:
        for path in sorted(source.root.rglob("*.md")):
            if path.name.lower() == "readme.md":
                # READMEs are scaffolding for the tree, not artifacts in it.
                report.skipped.append(str(path))
                continue
            located = (
                _locate_closing(path, source.root)
                if source.layout == "closing"
                else _locate_persona(path, source.root)
            )
            if located is None:
                report.skipped.append(str(path))
                continue
            kind, quarter = located
            await self._ingest_file(path, source, kind, quarter, report)

    async def _ingest_file(
        self,
        path: Path,
        source: VaultSource,
        kind: ArtifactKind,
        quarter: str | None,
        report: SyncReport,
    ) -> None:
        content = path.read_text(encoding="utf-8")
        body_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        relative = path.relative_to(source.root).as_posix()
        meta = _front_matter(content)

        uid = self._uid_for(meta, kind, path, relative)
        title = self._title_for(meta, content, path)

        report.scanned += 1
        existing = await self._repo.get(uid)
        if existing is not None and existing.body_hash == body_hash:
            report.unchanged += 1
            return

        fields: dict[str, Any] = {
            "uid": uid,
            "kind": kind,
            "title": title,
            "body": content,
            "body_hash": body_hash,
            "quarter": quarter,
            "revision": existing.revision if existing else 1,
            "created_at": existing.created_at if existing else _now(),
            "updated_at": _now(),
        }
        status = meta.get("status")
        if isinstance(status, str) and status:
            fields["status"] = status
        parent = meta.get("parent_ueid")
        if isinstance(parent, str) and parent:
            fields["parent_uid"] = parent
        created = _timestamp(meta.get("created_at"))
        if created is None and kind is ArtifactKind.NOTA:
            # A daily note carries the day it is about, and that day IS its
            # created_at — the DOM's spine has no second field for it. It used
            # to be written as `note_date`, a field the model forbids: a note
            # whose date was quoted was rejected by the model and dropped by
            # the sync without a word.
            created = _timestamp(meta.get("date"))
        if created is not None and existing is None:
            fields["created_at"] = created
        updated = _timestamp(meta.get("updated_at"))
        if updated is not None:
            fields["updated_at"] = updated
        if kind is ArtifactKind.SONHO:
            vectors = meta.get("ikigai_vectors")
            if isinstance(vectors, list) and vectors:
                fields["ikigai_vectors"] = tuple(vectors)

        try:
            artifact = KIND_MODELS[kind].model_validate(fields)
        except Exception as exc:  # one bad file must not stop the run
            report.skipped.append(f"{relative}: {exc}")
            return

        request = WriteRequest(
            artifact=artifact,
            expected_revision=existing.revision if existing else None,
            idempotency_key=f"vault:{source.layout}:{relative}:{body_hash[:16]}",
            client_id=self._client_id,
        )

        try:
            # The vector rides with the row, the same way it does for a client
            # write: prose that lands in the store and never in the vector
            # index is prose the retrieval layer cannot find.
            embedding = None
            if self._embeddings is not None:
                embedding = await self._embeddings.embed_artifact(artifact)
            outcome = await self._repo.upsert(request, embedding=embedding)
        except Exception as exc:  # one bad file must not stop the run
            report.skipped.append(f"{relative}: {exc}")
            return
        if outcome.outcome == "created":
            report.created += 1
        elif outcome.outcome == "updated":
            report.updated += 1
        else:
            report.unchanged += 1

        await self._write_relations(artifact.uid, meta, report)

    async def _write_relations(
        self,
        uid: UEID,
        meta: dict[str, Any],
        report: SyncReport,
    ) -> None:
        """Record the edges the frontmatter declares."""
        related = meta.get("related_ueids")
        if not isinstance(related, list):
            return
        for other in related:
            if not isinstance(other, str) or not other:
                continue
            try:
                relation = Relation(
                    src_uid=uid,
                    dst_uid=other,
                    rel=RelationType.REFERENCES,
                )
            except Exception:  # a malformed reference is not fatal
                continue
            try:
                await self._repo.upsert_relation(relation)
            except Exception:  # the artifact is already stored
                continue
            report.relations += 1

    @staticmethod
    def _uid_for(
        meta: dict[str, Any],
        kind: ArtifactKind,
        path: Path,
        relative: str,
    ) -> UEID:
        """The identity of the artifact.

        A declared `ueid` wins over anything derived: it is the identity the
        rest of the system already links to, and it survives the file moving
        between the two tree shapes.
        """
        declared = meta.get("ueid")
        if isinstance(declared, str) and declared:
            try:
                return UEID(declared)
            except ValueError:
                pass
        slug = _slugify(path.stem)
        digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()
        return make_uid(kind, slug, digest[:8], digest[8:24])

    @staticmethod
    def _title_for(meta: dict[str, Any], content: str, path: Path) -> str:
        declared = meta.get("title")
        if isinstance(declared, str) and declared.strip():
            return declared.strip()
        heading = _HEADING_RE.search(content)
        return heading.group(1).strip() if heading else path.stem


def _now() -> datetime:
    return datetime.now(UTC)


def _report_line(report: SyncReport) -> str:
    return (
        f"scanned={report.scanned} created={report.created} updated={report.updated} "
        f"unchanged={report.unchanged} relations={report.relations} "
        f"skipped={len(report.skipped)}"
    )


async def _run(interval: int) -> int:
    """Ingest, then wait, then ingest again — forever, or once."""
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient()
    repo = ArtifactRepository(client)
    sync = VaultSync(repo, embeddings=EmbeddingService(client))

    while True:
        try:
            report = await sync.ingest()
            print(_report_line(report), flush=True)
            for skipped in report.skipped:
                print(f"skipped: {skipped}", file=sys.stderr, flush=True)
        except Exception as exc:  # a failed round is not a dead loop
            print(f"ingestion failed: {exc}", file=sys.stderr, flush=True)
        if interval <= 0:
            return 0
        await asyncio.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    """Run the ingestion.

    The skill says "run the ingestion" and used to name nothing to run: the
    service existed and the routine had no command. This is that command.

        python -m src.services.sync                  # one round, then stop
        python -m src.services.sync --interval 60    # every minute, forever

    The interval also comes from ``IKIGAI_VAULT_SYNC_INTERVAL``, which is how
    the container asks for the loop without changing the command.
    """
    parser = argparse.ArgumentParser(prog="python -m src.services.sync")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="seconds between two runs; 0 (the default) runs once and stops",
    )
    args = parser.parse_args(argv)

    raw_interval = args.interval
    if raw_interval is None:
        raw_interval = int((os.environ.get(SYNC_INTERVAL_ENV) or "0").strip() or 0)

    # Before the loop exists: the store's driver refuses Windows' default
    # event loop, and the policy has to be chosen before the loop is created.
    from src.services.wiring import prepare_runtime

    prepare_runtime()
    return asyncio.run(_run(raw_interval))


if __name__ == "__main__":
    raise SystemExit(main())
