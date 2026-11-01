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
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from src.contracts.dom import ArtifactKind, WriteRequest, make_uid
from src.contracts.dom_kinds import KIND_MODELS

from src.data.repository import ArtifactRepository

__all__ = ["SyncReport", "VaultSync", "default_vault_root"]

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_QUARTER_RE = re.compile(r"^\d+-q(\d)-(\d{4})$")

# The vault tree, from the directories that exist on disk. The prefixes are
# matched against a path SEGMENT, not the whole path, because the quarter
# directory sits in front of the kind directory.
_VAULT_KINDS: tuple[tuple[str, ArtifactKind], ...] = (
    ("00-sonho", ArtifactKind.SONHO),
    ("01-plano-trimestral", ArtifactKind.PLANO),
    ("02-onda", ArtifactKind.ONDA),
    ("03-revis", ArtifactKind.REVISAO),
    ("04-relat", ArtifactKind.NOTA),
)

_ARCHIVE_DIR = "99-archive"


@dataclass
class SyncReport:
    """What one ingestion run did."""

    scanned: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.created + self.updated + self.unchanged


def default_vault_root() -> Path:
    """The vault tree the ingestion reads."""
    return Path(__file__).resolve().parents[2] / "vault" / "ikigai" / "closing-2026"


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    slug = slug[:62].strip("-")
    if not slug:
        return "artefato"
    if len(slug) == 1:
        # A UEID slug is at least two characters.
        slug = f"{slug}0"
    return slug


def _locate(path: Path, root: Path) -> tuple[ArtifactKind, str | None] | None:
    """Find the kind and the quarter a vault file belongs to.

    The tree is `closing-2026/<quarter>/<kind>/<file>.md`, so the kind directory
    is NOT the first segment — `01-q3-2026` comes first and the quarter it
    names is worth keeping, because the spine has a `quarter` column precisely
    for it.

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
        for prefix, candidate in _VAULT_KINDS:
            if part.startswith(prefix):
                kind = candidate
                break
        match = _QUARTER_RE.match(part)
        if match:
            quarter = f"Q{match.group(1)}-{match.group(2)}"
    if kind is None:
        return None
    return kind, quarter


class VaultSync:
    """Reads the vault's markdown and upserts it into the store."""

    def __init__(
        self,
        repo: ArtifactRepository,
        *,
        vault_root: Path | None = None,
        client_id: str = "vault-sync",
    ) -> None:
        self._repo = repo
        self._root = vault_root or default_vault_root()
        self._client_id = client_id

    async def ingest(self) -> SyncReport:
        report = SyncReport()
        if not self._root.exists():
            report.skipped.append(f"vault root not found: {self._root}")
            return report

        for path in sorted(self._root.rglob("*.md")):
            if path.name.lower() == "readme.md":
                # READMEs are scaffolding for the tree, not artifacts in it.
                report.skipped.append(str(path))
                continue
            located = _locate(path, self._root)
            if located is None:
                report.skipped.append(str(path))
                continue
            kind, quarter = located
            await self._ingest_file(path, kind, quarter, report)
        return report

    async def _ingest_file(
        self,
        path: Path,
        kind: ArtifactKind,
        quarter: str | None,
        report: SyncReport,
    ) -> None:
        content = path.read_text(encoding="utf-8")
        body_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        relative = path.relative_to(self._root).as_posix()
        slug = _slugify(path.stem)
        path_digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()
        uid = make_uid(kind, slug, path_digest[:8], path_digest[8:24])
        heading = _HEADING_RE.search(content)
        title = heading.group(1).strip() if heading else path.stem

        report.scanned += 1
        existing = await self._repo.get(uid)
        if existing is not None and existing.body_hash == body_hash:
            report.unchanged += 1
            return

        request = WriteRequest(
            artifact=KIND_MODELS[kind].model_validate(
                {
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
            ),
            expected_revision=existing.revision if existing else None,
            idempotency_key=f"vault:{relative}:{body_hash[:16]}",
            client_id=self._client_id,
        )

        try:
            outcome = await self._repo.upsert(request)
        except Exception as exc:  # noqa: BLE001 — one bad file must not stop the run
            report.skipped.append(f"{relative}: {exc}")
            return
        if outcome.outcome == "created":
            report.created += 1
        elif outcome.outcome == "updated":
            report.updated += 1
        else:
            report.unchanged += 1


def _now() -> datetime:
    return datetime.now(UTC)
