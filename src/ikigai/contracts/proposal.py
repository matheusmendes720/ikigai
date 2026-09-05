"""Meta-Planner Proposal contracts (Plan D Task A.1).

All models are Pydantic v2 strict per ADR-009:
  model_config = ConfigDict(frozen=True, extra="forbid")

UEIDs follow ADR-014 4-part canonical format.
SONHO writes require actor_required='user' per Plan A transition_validator.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


class IntentClassification(BaseModel):
    """Result of classify_intent node — keyword-based, no LLM."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: Literal["high", "medium", "low"]
    score: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Context fetches
# ---------------------------------------------------------------------------


class FolderReadOp(BaseModel):
    """A folder read captured during fetch_context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    excerpt: str
    reason: str


class MemoryRef(BaseModel):
    """A memory recall result from B-N12 (ADR-028)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str  # 4-part UEID
    vault_path: str | None
    relevance_score: float = Field(ge=0.0, le=1.0)


class HierarchyMatch(BaseModel):
    """Matched vault hierarchy levels for the user request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sonho: str | None = None
    objetivo: str | None = None
    meta: str | None = None
    projeto: str | None = None


class HierarchyContext(BaseModel):
    """Subset of HierarchyMatch included in Proposal for traceability."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    matched_sonho: str | None
    matched_objetivo: str | None
    matched_meta: str | None
    matched_projeto: str | None


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


class VaultWriteOp(BaseModel):
    """A proposed vault write. SONHO writes require actor_required='user'."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    vault_path: str
    entity_type: Literal["sonho", "objetivo", "meta", "projeto", "entrega", "tarefa"]
    fields: dict[str, Any]
    actor_required: Literal["user", "agent"]
    rationale: str

    @field_validator("actor_required")
    @classmethod
    def _sonho_requires_user(cls, v: str, info: Any) -> str:
        # SONHO writes are user-only per Plan A transition_validator (2026-09-03).
        entity = info.data.get("entity_type")
        if entity == "sonho" and v != "user":
            raise ValueError(
                "SONHO writes require actor_required='user' (Plan A transition_validator)"
            )
        return v


class TaskdogOp(BaseModel):
    """A proposed taskdog create (Path 1 per W3.6)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    priority: Literal["H", "M", "L"]
    due_date: date | None
    project: str | None
    tags: list[str]
    rationale: str


class ProposalOperation(BaseModel):
    """One operation in a Proposal (vault_write | taskdog_create | data_tasks_append)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    op_type: Literal["vault_write", "taskdog_create", "data_tasks_append"]
    vault_write: VaultWriteOp | None = None
    taskdog_create: TaskdogOp | None = None


class Traceability(BaseModel):
    """Provenance for a Proposal — required for audit trail."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    memory_refs: list[str]
    folder_reads: list[str]
    adrs_consulted: list[str]


# ---------------------------------------------------------------------------
# Proposal + Approval + Execution
# ---------------------------------------------------------------------------

_UEID_REGEX = r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$"


class Proposal(BaseModel):
    """A typed proposal of writes — requires approval before execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str  # 4-part UEID (ADR-014)
    created_at: datetime
    source_request: str
    hierarchy_context: HierarchyContext
    operations: list[ProposalOperation]
    traceability: Traceability
    approval_state: Literal["pending", "approved", "rejected", "rejected_safety", "partial"]
    actor_approving: str | None = None
    approval_timestamp: datetime | None = None

    @field_validator("id")
    @classmethod
    def _ueid_canonical(cls, v: str) -> str:
        import re

        if not re.match(_UEID_REGEX, v):
            raise ValueError(f"id {v!r} does not match 4-part UEID regex (ADR-014): {_UEID_REGEX}")
        return v


class ExecutionReport(BaseModel):
    """Result of proposal_executor — surfaces partial failures to user."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str
    ops_total: int = Field(ge=0)
    ops_completed: int = Field(ge=0)
    ops_failed: int = Field(ge=0)
    status: Literal["ok", "partial", "failed"]
    errors: list[str]


__all__ = [
    "ExecutionReport",
    "FolderReadOp",
    "HierarchyContext",
    "HierarchyMatch",
    "IntentClassification",
    "MemoryRef",
    "Proposal",
    "ProposalOperation",
    "TaskdogOp",
    "Traceability",
    "VaultWriteOp",
]
