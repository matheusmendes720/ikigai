"""Shared Pydantic v2 contracts for the Algorithmic Life OS.

This package contains canonical Pydantic v2 models that are shared across
ALL layers (data, services, transport, clients). These are the ONLY contracts
between layers.

Design rules:
- frozen=True, extra="forbid" on all models
- UEID as primary identifier type
- No business logic — pure data containers with invariants
- Enums live here too (shared across layers)

ONE family lives here, and it is the DOM (ADR-037 D2):

- the **unified DOM** (`dom.py`, `dom_kinds.py`) — the model at the centre:
  ten artifact kinds, each a typed model, with the store's constants
  (`store.py`) and the error surface (`errors.py`) beside it;
- the **identity** (`common.py`) — the UEID and the two vocabularies the
  kinds share: the tier they sit at (`PlanTier`) and the priority axis.

Layers:
    - vault/      → markdown source of truth (no Python)
    - src/contracts/ → canonical Pydantic contracts (THIS PACKAGE)
    - src/data/   → consumer: the store client (imports from contracts/)
    - src/services/ → consumer: the domain rules (imports from contracts/)
    - src/transport/ → consumer: the MCP surface (imports from contracts/)
"""

from __future__ import annotations

from .common import (
    UEID,
    PlanTier,
    Priority,
    VectorKey,
)
from .dom import (
    Artifact,
    ArtifactBundle,
    ArtifactKind,
    ArtifactRevision,
    Relation,
    RelationType,
    SearchQuery,
    SearchResult,
    WriteOutcome,
    WriteRequest,
    make_uid,
)
from .dom_kinds import (
    KIND_MODELS,
    DecisionArtifact,
    FaseArtifact,
    KPIArtifact,
    NotaArtifact,
    OKRArtifact,
    OndaArtifact,
    PlanoArtifact,
    RevisaoArtifact,
    SonhoArtifact,
    TarefaArtifact,
)
from .errors import (
    ConflictError,
    DataLayerError,
    ErrorCode,
    ForbiddenError,
    InvalidPayloadError,
    NotFoundError,
)

# (alphabetical sort would destroy the intentional # common / # dom / # dom errors grouping)
# Ruff RUF022 cannot apply noqa to `__all__ = [...]` itself, so we suppress at the module level via per-file-ignore.
# See: pyproject.toml [tool.ruff.lint.per-file-ignores] for the canonical suppression.
__all__ = [  # noqa: RUF022 — entries are grouped by domain with comments, not alphabetically sorted
    # common
    "UEID",
    "Priority",
    "PlanTier",
    "VectorKey",
    # dom (unified data model — ADR-037 D2)
    "KIND_MODELS",
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
    "SonhoArtifact",
    "PlanoArtifact",
    "OndaArtifact",
    "FaseArtifact",
    "RevisaoArtifact",
    "NotaArtifact",
    "KPIArtifact",
    "OKRArtifact",
    "DecisionArtifact",
    "TarefaArtifact",
    # dom errors
    "ErrorCode",
    "DataLayerError",
    "ConflictError",
    "InvalidPayloadError",
    "ForbiddenError",
    "NotFoundError",
]
