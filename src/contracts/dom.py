"""The unified DOM — one model, ten kinds, UID as the primary key.

Per SPEC-01 (docs/superpowers/specs/2026-11-01-01-unified-dom.md) and ADR-037
D2: every application projects the same data model. The DOM states what an
artifact IS; it never states how a client should render it.

The spine (`Artifact`) holds only what every kind shares. Kind-specific fields
live in `dom_kinds.py` as typed subclasses, so no client can invent a field and
no kind degrades into a free-shape JSON blob.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import UEID

__all__ = [
    "DOMAIN",
    "KIND_NAMESPACE",
    "Artifact",
    "ArtifactBundle",
    "ArtifactKind",
    "ArtifactRevision",
    "Relation",
    "RelationType",
    "SearchQuery",
    "SearchResult",
    "WriteOutcome",
    "WriteRequest",
    "make_uid",
]

DOMAIN = "ikig"


class ArtifactKind(StrEnum):
    """The ten kinds, derived from the real vault tree plus the views that need them.

    Six come from `vault/ikigai/closing-2026/` (00-sonho, 01-plano-trimestral,
    02-onda-*, 03-revisões-semanais, 04-relatórios-diários, and the phase rows
    inside the quarterly plan). The other four are what the Vanilla Pivot §7
    proved necessary for the views.
    """

    SONHO = "sonho"
    PLANO = "plano"
    ONDA = "onda"
    FASE = "fase"
    REVISAO = "revisao"
    NOTA = "nota"
    KPI = "kpi"
    DESC = "desc"
    OKR = "okr"
    TAREFA = "tarefa"


KIND_NAMESPACE: dict[ArtifactKind, str] = {
    ArtifactKind.SONHO: "snh",
    ArtifactKind.PLANO: "pln",
    ArtifactKind.ONDA: "ond",
    ArtifactKind.FASE: "fse",
    ArtifactKind.REVISAO: "rev",
    ArtifactKind.NOTA: "not",
    ArtifactKind.KPI: "kpi",
    ArtifactKind.DESC: "dec",
    ArtifactKind.OKR: "okr",
    ArtifactKind.TAREFA: "tsk",
}
"""The kind → UEID namespace mapping clients use to turn a vault item into a UID.

The namespace travels in the first segment of the UEID, so the UID alone tells
a consumer what kind of thing it is holding.
"""


class Artifact(BaseModel):
    """The spine. Every kind inherits these fields; nothing else is common."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    uid: UEID
    kind: ArtifactKind
    title: str
    body: str | None = None
    body_hash: str | None = None
    parent_uid: UEID | None = None
    quarter: str | None = None
    status: str | None = None
    revision: int = Field(default=1, ge=1)
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class RelationType(StrEnum):
    """Typed edges. The graph is a first-class relation between artifacts, not a side effect."""

    DEPENDS_ON = "depends_on"
    PARENT_OF = "parent_of"
    BLOCKS = "blocks"
    EVIDENCES = "evidences"
    DERIVES_FROM = "derives_from"
    REFERENCES = "references"
    SUPERSEDES = "supersedes"


class Relation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    src_uid: UEID
    dst_uid: UEID
    rel: RelationType
    weight: float | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class WriteRequest(BaseModel):
    """The write envelope: optimistic revision + idempotency key + originating client.

    `relations` travel WITH the artifact, and are written in the same
    transaction. An edge written on its own can survive the artifact it
    describes — a graph that points at a node that was never stored — and an
    edge whose node failed leaves a graph that points at nothing. The graph is
    written with the node, or not at all.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact: Artifact
    expected_revision: int | None = None
    idempotency_key: str
    client_id: str
    relations: tuple[Relation, ...] = ()


class WriteOutcome(BaseModel):
    """What a write actually did.

    `conflict` is a normal outcome, not an exception state: the caller learns the
    write lost the optimistic race and can reread and reapply.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    uid: UEID
    revision: int
    outcome: Literal["created", "updated", "conflict", "unchanged"]
    detail: str | None = None


class SearchQuery(BaseModel):
    """Structured search over the indexes. Cursor pagination, never offset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str | None = None
    kinds: tuple[ArtifactKind, ...] = ()
    quarter: str | None = None
    status: str | None = None
    parent_uid: UEID | None = None
    semantic: bool = False
    limit: int = Field(default=20, ge=1, le=200)
    cursor: str | None = None


class SearchResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    artifacts: tuple[Artifact, ...]
    next_cursor: str | None = None
    total_estimate: int | None = None


class ArtifactRevision(BaseModel):
    """An append-only snapshot of one revision. Never updated, never deleted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    uid: UEID
    revision: int = Field(ge=1)
    snapshot: dict[str, Any]
    author: str | None = None
    client_id: str
    created_at: datetime


class ArtifactBundle(BaseModel):
    """An artifact plus its relations, and optionally its neighbours."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact: Artifact
    relations: tuple[Relation, ...] = ()
    neighbors: tuple[ArtifactBundle, ...] = ()


ArtifactBundle.model_rebuild()


def make_uid(kind: ArtifactKind, slug: str, uuid_short: str, content_hash_short: str) -> UEID:
    """Build a canonical 4-part UID (ADR-014) for an artifact of the given kind.

    Validation goes through the UEID constructor rather than string concatenation,
    so a malformed slug or hash is rejected at the boundary instead of reaching
    the store and failing a CHECK constraint there.
    """
    namespace = KIND_NAMESPACE[kind]
    return UEID(f"{namespace}:{slug}:{uuid_short}:{content_hash_short}")
