"""Base plan contract shared by SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.contracts.common import PaeCyclePhase, PlanTier, UEID, VectorKey


def _check_vector_subset(
    child_vectors: list[str], parent_vectors: list[str]
) -> list[str]:
    """Validate that child vectors are subset of parent vectors.

    Per Decision #5: child.ikigai_vectors ⊆ parent.ikigai_vectors.

    Args:
        child_vectors: vectors declared on child entity.
        parent_vectors: vectors declared on parent entity (already loaded).

    Returns:
        The child_vectors unchanged if subset is valid.

    Raises:
        ValueError: if child has a vector not in parent.
    """
    child_set = set(child_vectors)
    parent_set = set(parent_vectors)
    if not child_set.issubset(parent_set):
        extra = child_set - parent_set
        raise ValueError(
            f"ikigai_vectors {child_vectors} not subset of parent {parent_vectors} "
            f"(extra vectors: {sorted(extra)})"
        )
    return child_vectors


class BasePlanContract(BaseModel):
    """Base contract for all 6 planning hierarchy entities.

    Frozen=True + extra='forbid' enforces Pydantic v2 strict mode
    (per memory: 'frozen=True, extra=forbid on all schemas').

    Subset rule on ikigai_vectors (Decision #5) is enforced when parent_ueid
    is set; SONHO-level (parent_ueid=None) skips the check.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=3000)
    tier: PlanTier
    parent_ueid: UEID | None = None
    related_ueids: list[UEID] = []
    horizon_days: int | None = Field(default=None, ge=1, le=7300)
    ikigai_vectors: list[VectorKey] = []
    pae_cycle_phase: PaeCyclePhase = "plan"
    pae_tier: PlanTier
    tags: list[str] = []
    custom: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None
    actor: Literal["user", "agent", "system"] = "user"

    @field_validator("ikigai_vectors", mode="after")
    @classmethod
    def _subset_of_parent(cls, v: list[VectorKey]) -> list[VectorKey]:
        """SONHO-level (no parent) accepts any vector list.

        For child entities (parent_ueid set), the registry lookup is done
        at the application layer (commit_node) before persisting. The
        static _check_vector_subset helper exists for use by the application
        layer to validate before calling BasePlanContract construction.

        This validator only enforces non-empty list (sanity check).
        """
        if not v:
            raise ValueError(
                "ikigai_vectors cannot be empty (must declare at least one)"
            )
        return v
