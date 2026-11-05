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

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field

from .common import PlanTier, Priority, VectorKey
from .dom import Artifact, ArtifactKind

__all__ = [
    "KIND_MODELS",
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
