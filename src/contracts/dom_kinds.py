"""The typed extensions of the DOM — one model per kind.

Each kind narrows `Artifact.kind` with a `Literal` discriminator, so a consumer
holding a `KPIArtifact` knows it holds a KPI without inspecting the value.

Two kinds of narrowing happen here, and neither needs a table of its own:

- The prose kinds require a body. A dream, a plan, a wave, a phase, a weekly
  review and a daily note are markdown; "no body" is not a state they can be
  in. KPI, OKR and decisions are structured and carry their own typed fields
  instead, which is why they — and only they — have extension tables in the
  store.

A kind that later needs a typed column gets an extension table and a migration.
Until then its extra shape stays in the prose body, and the spine keeps the
data.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal, get_origin

from pydantic import Field

from .common import PlanTier, Priority, VectorKey
from .dom import Artifact, ArtifactKind

__all__ = [
    "KIND_MODELS",
    "KIND_TYPED_FIELDS",
    "ArtifactPayload",
    "DecisionArtifact",
    "FaseArtifact",
    "KPIArtifact",
    "NotaArtifact",
    "OKRArtifact",
    "OndaArtifact",
    "PlanoArtifact",
    "RevisaoArtifact",
    "SonhoArtifact",
    "TarefaArtifact",
    "typed_fields",
    "typed_from_meta",
]


class SonhoArtifact(Artifact):
    """`vault/ikigai/closing-2026/00-sonho/*.md` — the top of the planning tree."""

    kind: Literal[ArtifactKind.SONHO] = ArtifactKind.SONHO
    body: str
    ikigai_vectors: tuple[VectorKey, ...] = ()


class PlanoArtifact(Artifact):
    """`vault/ikigai/closing-2026/01-plano-trimestral/*.md` — the quarterly plan."""

    kind: Literal[ArtifactKind.PLANO] = ArtifactKind.PLANO
    body: str
    plan_tier: PlanTier | None = None


class OndaArtifact(Artifact):
    """`vault/ikigai/closing-2026/02-onda-<n>/` — a 15-day cycle."""

    kind: Literal[ArtifactKind.ONDA] = ArtifactKind.ONDA
    body: str


class FaseArtifact(Artifact):
    """A phase row inside the quarterly plan.

    A phase can be a row in the plan's table rather than a document of its own,
    so unlike the other prose kinds its body stays optional.
    """

    kind: Literal[ArtifactKind.FASE] = ArtifactKind.FASE


class RevisaoArtifact(Artifact):
    """`vault/ikigai/closing-2026/03-revisões-semanais/YYYY-Www.md` — a weekly review."""

    kind: Literal[ArtifactKind.REVISAO] = ArtifactKind.REVISAO
    body: str


class NotaArtifact(Artifact):
    """`vault/ikigai/closing-2026/04-relatórios-diários/YYYY-MM-DD.md` — a daily note."""

    kind: Literal[ArtifactKind.NOTA] = ArtifactKind.NOTA
    body: str


class KPIArtifact(Artifact):
    """A measured indicator. Decimal, never float — a KPI that loses precision is a wrong KPI."""

    kind: Literal[ArtifactKind.KPI] = ArtifactKind.KPI
    metric: str
    target: Decimal | None = None
    actual: Decimal | None = None
    unit: str | None = None
    period: str
    direction: Literal["up", "down", "flat"] = "up"


class OKRArtifact(Artifact):
    """An objective and one of its key results."""

    kind: Literal[ArtifactKind.OKR] = ArtifactKind.OKR
    objective: str
    key_result: str
    kr_target: Decimal | None = None
    kr_actual: Decimal | None = None
    kr_progress: Decimal | None = None


class DecisionArtifact(Artifact):
    """A recorded decision and why it was taken."""

    kind: Literal[ArtifactKind.DESC] = ArtifactKind.DESC
    decision: str
    rationale: str | None = None
    decider: str | None = None
    outcome: str | None = None


class TarefaArtifact(Artifact):
    """A task.

    A task's dependencies are edges in the graph, not a field on the artifact:
    `RelationType.DEPENDS_ON` already says it, in a place that can be traversed.
    """

    kind: Literal[ArtifactKind.TAREFA] = ArtifactKind.TAREFA
    priority: Priority = Priority.MEDIUM
    estimated_minutes: int | None = None


KIND_MODELS: dict[ArtifactKind, type[Artifact]] = {
    ArtifactKind.SONHO: SonhoArtifact,
    ArtifactKind.PLANO: PlanoArtifact,
    ArtifactKind.ONDA: OndaArtifact,
    ArtifactKind.FASE: FaseArtifact,
    ArtifactKind.REVISAO: RevisaoArtifact,
    ArtifactKind.NOTA: NotaArtifact,
    ArtifactKind.KPI: KPIArtifact,
    ArtifactKind.OKR: OKRArtifact,
    ArtifactKind.DESC: DecisionArtifact,
    ArtifactKind.TAREFA: TarefaArtifact,
}
"""Which model carries which kind. The sync and the clients use this to build the
right type instead of the bare spine.
"""

ArtifactPayload = Annotated[
    SonhoArtifact
    | PlanoArtifact
    | OndaArtifact
    | FaseArtifact
    | RevisaoArtifact
    | NotaArtifact
    | KPIArtifact
    | OKRArtifact
    | DecisionArtifact
    | TarefaArtifact,
    Field(discriminator="kind"),
]
"""Every kind, discriminated by `kind`.

This is what the tool surface takes — NOT the bare `Artifact`. The spine
forbids extra fields, so a KPI's `metric` and `target` only survive the wire
if the parameter is the typed model; and the repository writes the extension
tables by `isinstance`, so a bare spine drops the typed fields in silence.
"""

# ---------------------------------------------------------------------------
# The typed fields, as the MARKDOWN carries them
# ---------------------------------------------------------------------------

_SPINE_FIELDS = frozenset(Artifact.model_fields)
"""The fields every artifact has. What a kind adds on top of them is its own."""

KIND_TYPED_FIELDS: dict[ArtifactKind, tuple[str, ...]] = {
    kind: tuple(name for name in model.model_fields if name not in _SPINE_FIELDS)
    for kind, model in KIND_MODELS.items()
}
"""Which fields belong to which kind — read off the MODELS, never written twice.

The typed fields of a kind are exactly the ones its model adds to the spine,
so the map cannot drift from the models: a new field on `KPIArtifact` is in
here the moment the model declares it, and a field that is not on the model is
not in here at all.

Two things read this map, and they must agree: the write-back, which renders
these fields into the frontmatter of the file it writes, and the ingestion,
which reads them back out of it. A vocabulary written twice is two
vocabularies, and the second one is the one that loses a KPI's metric.
"""


def _plain(value: Any) -> Any:
    """A value the YAML writer can represent.

    PyYAML has no representer for `Decimal` — it raises instead of writing
    something — and a KPI's target is a `Decimal` because a KPI that loses
    precision is a wrong KPI. The text is exact, and the ingestion turns it
    back into a `Decimal` on the way in.
    """
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, StrEnum):
        return str(value.value)
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def typed_fields(artifact: Artifact) -> dict[str, Any]:
    """The typed fields of an artifact, as the frontmatter states them.

    The fields that are not there are left out: a KPI with no target says so
    by not saying it, and a frontmatter full of empty values is a frontmatter
    that lies about what is known.
    """
    out: dict[str, Any] = {}
    for name in KIND_TYPED_FIELDS.get(artifact.kind, ()):
        value = getattr(artifact, name, None)
        if value is None:
            continue
        out[name] = _plain(value)
    return out


def typed_from_meta(kind: ArtifactKind, meta: Mapping[str, Any]) -> dict[str, Any]:
    """The typed fields a FILE declares — for its kind, and only for its kind.

    The kind is what scopes this. A `target:` in the frontmatter of a note is
    the note's target, not a KPI's, and reading it as one would invent a
    field the file never claimed: the model forbids extra fields, so the file
    would be refused and the owner's prose would stop being ingested.

    A value whose shape does not fit the field is left out rather than
    coerced: a file that says `ikigai_vectors: passion` has not declared a
    vector, and guessing would put a wrong word in the store.
    """
    model = KIND_MODELS.get(kind)
    if model is None:
        return {}
    out: dict[str, Any] = {}
    for name in KIND_TYPED_FIELDS.get(kind, ()):
        if name not in meta:
            continue
        value = meta[name]
        if value is None or value == "":
            continue
        annotation = model.model_fields[name].annotation
        if get_origin(annotation) in (tuple, list):
            if not isinstance(value, (list, tuple)):
                continue
            value = list(value)
        out[name] = value
    return out
