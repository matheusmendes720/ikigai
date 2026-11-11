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

A third one is ingested because the deployment has one: `zones` — the owner's
knowledge tree, six buckets of markdown synced from the desktop onto the
Cloud Volume. There, the first path segment IS the zone, and the zone decides
the kind.

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
from src.contracts.dom_kinds import KIND_MODELS, typed_from_meta
from src.data.repository import ArtifactRepository
from src.services.embeddings import EmbeddingService

__all__ = ["SyncReport", "VaultSource", "VaultSync", "default_sources", "main", "slugify"]

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

#: The zones tree: the owner's knowledge base, synced from the desktop.
#:
#: The first path segment is the zone, and the zone decides the kind. Only the
#: zones that are NOT a bucket of notes are named here; every other zone is a
#: note zone, so adding a seventh bucket needs no code change.
#:
#: The zone's own `type:` in the frontmatter is deliberately NOT consulted.
#: It is the vault's taxonomy, not the DOM's, and it is not reliable: in the
#: real tree it types a control-theory note as `project`, a study plan as
#: `inbox`, and one file as `Line`. Promoting a note to a planning kind
#: because of that would put the wrong thing in the wrong drawer of the DOM.
#: The type stays in the body, where the prose keeps it.
_ZONE_KINDS: dict[str, ArtifactKind] = {
    "1_norte": ArtifactKind.SONHO,
    "2_projeto": ArtifactKind.PLANO,
}

#: The kind of a zone that is not named in `_ZONE_KINDS`.
_ZONE_DEFAULT_KIND = ArtifactKind.NOTA

_ARCHIVE_DIR = "99-archive"
_LAYOUTS = ("closing", "persona", "zones", "escrita")

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
    layout: Literal["closing", "persona", "zones", "escrita"]


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


def slugify(text: str) -> str:
    """The filesystem-safe name of a piece of text.

    Public because the write-back (`vault_write.py`) names its files by the
    same rule: two writers that slug differently would write two names for
    one thing.
    """
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
    except Exception:
        # The vault writes its tags the Obsidian way — `tags: [#moc, #ai]` —
        # and in YAML a `#` opens a comment. The list is therefore never
        # closed, the parser gives up, and the WHOLE block is lost with it.
        #
        # Measured on the real tree: 242 of the 1800 files with a frontmatter
        # lose it that way, and with it the date, the topic and the status.
        # The block is not garbage — it is a list of `key: value` lines with
        # ONE broken line in it — so the lines are read one by one, and the
        # broken one is the only thing lost.
        return _front_matter_lines(match.group(1))
    return loaded if isinstance(loaded, dict) else {}


def _front_matter_lines(block: str) -> dict[str, Any]:
    """Read a frontmatter block that YAML refused, one line at a time."""
    values: dict[str, Any] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, raw = line.partition(":")
        if not separator:
            continue
        key = key.strip()
        if not key or key in values:
            continue
        values[key] = _scalar(raw.strip())
    return values


def _scalar(raw: str) -> Any:
    """A frontmatter value read from a line, without a YAML parser.

    Only what the ingestion needs: a date, a datetime, a list of strings, or
    the text itself.
    """
    if not raw:
        return ""
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1]
        return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        return raw[1:-1]
    lowered = raw.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    stamp = _timestamp(raw)
    return stamp if stamp is not None else raw


def _timestamp(value: Any) -> datetime | None:
    """Coerce a frontmatter timestamp into a datetime.

    PyYAML parses an unquoted `date: 2026-09-07` into a `datetime.date`, not
    into a string — so a coercion that only knows about strings drops the
    value without a word. `datetime` is a subclass of `date`, so it has to be
    tested first.

    The result is ALWAYS timezone-aware. A vault that writes `created:
    2026-01-15` writes a CALENDAR DATE, and a calendar date is stored at
    midnight UTC — the store's column is `timestamptz`, and a naive
    timestamp handed to it is read in the timezone of whichever server
    happens to be running. That is two problems at once: the date lands on a
    different instant depending on the box, and the comparison that decides
    whether a row is still correct never matches — so the ingestion rewrites
    the same rows every round, forever.
    """
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return _as_utc(parsed)


def _as_utc(value: datetime) -> datetime:
    """The same instant, with a timezone."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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


def _locate_zones(path: Path, root: Path) -> tuple[ArtifactKind, str | None] | None:
    """Find the kind of a file in the zones tree.

    The first path segment is the zone, and the zone decides the kind. A file
    that sits at the root of the tree belongs to no zone — the root holds the
    zones and the metadata of the sync, not artifacts — so it is skipped.

    A HIDDEN directory is not a zone either. The tree carries a `.git` (the
    owner's vault is a repository) and a `.stfolder`, and a zone called `.git`
    is not a bucket of knowledge: it is a bucket of whatever a repository
    happens to keep in markdown.
    """
    try:
        relative = path.relative_to(root)
    except ValueError:
        return None
    if len(relative.parts) < 2:
        return None
    if any(part.startswith(".") for part in relative.parts):
        return None
    zone = relative.parts[0]
    kind = _ZONE_KINDS.get(zone, _ZONE_DEFAULT_KIND)
    quarter = None
    match = _SLUG_QUARTER_RE.search(path.stem)
    if match:
        quarter = f"Q{match.group(1)}-{match.group(2)}"
    return kind, quarter


def _locate_escrita(path: Path, root: Path) -> tuple[ArtifactKind, str | None] | None:
    """Find the kind of a file in the write-back tree.

    The first path segment IS the kind, in the DOM's own vocabulary (`nota`,
    `plano`, `kpi`). It is the layout the write-back writes in, and it is
    the only one that carries the kind EXACTLY: the zones layout decides the
    kind by a table of buckets, so everything that is not a dream or a plan
    would come back as a note — and the round trip would quietly change what
    a thing is.

    The quarter travels in the file's name, as it does in every other layout:
    the ingestion reads it from the stem.
    """
    try:
        relative = path.relative_to(root)
    except ValueError:
        return None
    if len(relative.parts) < 2:
        return None
    try:
        kind = ArtifactKind(relative.parts[0])
    except ValueError:
        # A directory that is not a kind holds no artifact of the DOM.
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
            located = self._locate(path, source)
            if located is None:
                report.skipped.append(str(path))
                continue
            kind, quarter = located
            await self._ingest_file(path, source, kind, quarter, report)

    @staticmethod
    def _locate(path: Path, source: VaultSource) -> tuple[ArtifactKind, str | None] | None:
        """The kind and the quarter of a file, by the shape of its tree."""
        if source.layout == "closing":
            return _locate_closing(path, source.root)
        if source.layout == "persona":
            return _locate_persona(path, source.root)
        if source.layout == "escrita":
            return _locate_escrita(path, source.root)
        return _locate_zones(path, source.root)

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

        fields: dict[str, Any] = {
            "uid": uid,
            "kind": kind,
            "title": title,
            "body": content,
            "body_hash": body_hash,
            "quarter": quarter,
            # WHERE the prose came from. The path is relative to the tree the
            # ingestion read, so its first segment is the zone — which is what
            # makes the tree queryable by bucket — and the whole thing is what
            # a write-back needs to know where to write.
            "vault_path": relative,
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
        created = _timestamp(meta.get("created_at")) or _timestamp(meta.get("created"))
        if created is None and kind is ArtifactKind.NOTA:
            # A daily note carries the day it is about, and that day IS its
            # created_at — the DOM's spine has no second field for it. It used
            # to be written as `note_date`, a field the model forbids: a note
            # whose date was quoted was rejected by the model and dropped by
            # the sync without a word.
            created = _timestamp(meta.get("date"))
        if created is not None:
            # A declared date is a FACT about the prose. The clock is only the
            # fallback for a file that declares none — and a fallback that
            # shadows the truth afterwards is a date that lies.
            fields["created_at"] = created
        updated = _timestamp(meta.get("updated_at")) or _timestamp(meta.get("updated"))
        if updated is not None:
            fields["updated_at"] = updated
        # The typed fields of THIS kind, as the file declares them.
        #
        # The kind scopes the vocabulary: a `target:` in the frontmatter of a
        # note is the note's target, not a KPI's. Reading it as one would
        # invent a field the file never claimed, and the model forbids extra
        # fields — so the file would be refused and the owner's prose would
        # stop being ingested.
        fields.update(typed_from_meta(kind, meta))

        # The file did not change — but the MAPPING might have. A file whose
        # frontmatter used to be unreadable and is read NOW has another title
        # and another date, and the body hash cannot see that: the bytes are
        # the same bytes. Without this, a correction to the mapping would
        # never reach the rows that were written with the wrong one.
        declared: tuple[str, ...] = ()
        if created is not None:
            declared += ("created_at",)
        if updated is not None:
            declared += ("updated_at",)
        if (
            existing is not None
            and existing.body_hash == body_hash
            and _same_mapping(existing, fields, declared)
        ):
            report.unchanged += 1
            return

        try:
            artifact = KIND_MODELS[kind].model_validate(fields)
        except Exception as exc:  # one bad file must not stop the run
            report.skipped.append(f"{relative}: {exc}")
            return

        request = WriteRequest(
            artifact=artifact,
            expected_revision=existing.revision if existing else None,
            # The key identifies the WRITE, not the file.
            #
            # A key built from the body hash alone says "this file, at these
            # bytes" — and a correction to the MAPPING (a frontmatter that
            # becomes readable, a title read from another field) produces the
            # same bytes and a different artifact. The store would recognise
            # that key as a write it already did and refuse it, and the
            # correction would never reach the row.
            #
            # The revision is in the key because it is what makes a write
            # different from the one before it: a successful write advances
            # it, and a refused one leaves it stale — so a write that is
            # retried after a conflict carries a key the ledger has not seen.
            idempotency_key=(
                f"vault:{source.layout}:{relative}:{body_hash[:16]}:"
                f"{existing.revision if existing else 0}"
            ),
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
        slug = slugify(path.stem)
        digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()
        return make_uid(kind, slug, digest[:8], digest[8:24])

    @staticmethod
    def _title_for(meta: dict[str, Any], content: str, path: Path) -> str:
        declared = meta.get("title")
        if isinstance(declared, str) and declared.strip():
            return declared.strip()
        # The knowledge vault titles its notes with `topic`, not `title`
        # ("Life Vision & Goals", "projects-hub"). Without this, the artifact
        # is called NORTE or 02-onda, and the vector — which is the title and
        # the body — carries a filename instead of a subject.
        topic = meta.get("topic")
        if isinstance(topic, str) and topic.strip():
            return topic.strip()
        heading = _HEADING_RE.search(content)
        return heading.group(1).strip() if heading else path.stem


def _now() -> datetime:
    return datetime.now(UTC)


#: The fields the ingestion DERIVES from a file, as opposed to the ones it
#: reads from the clock. They are compared on every run, because a file that
#: did not change can still map to a different artifact.
_DERIVED_FIELDS = ("title", "kind", "quarter", "status", "vault_path")


def _same_mapping(existing: Any, fields: dict[str, Any], declared: tuple[str, ...]) -> bool:
    """Whether the stored artifact is the one this file maps to.

    `declared` names the fields the file states itself — its dates. The ones
    the clock filled in are not compared: the clock answers with a different
    value every run, and comparing it would make every file look changed.
    """
    for name in (*_DERIVED_FIELDS, *declared):
        if getattr(existing, name, None) != fields.get(name):
            return False
    return True


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
