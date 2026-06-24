"""PlanEntity — polymorphic base for all plan entities (Dream → Deliverable).

Discriminator: `entity_type`. Forward-compat via `extra="allow"` and `custom` dict.
Anti-fragile identity via tri-key UEID (slug + uuid_short + content_hash_short).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ikigai.enums import (
    EntityType,
    Phase,
    RegimeType,
    SourceType,
    StatusType,
    VectorType,
)
from ikigai.types import ScoreValue, UEID


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlanEntity(BaseModel):
    """Polymorphic base for all plan entities.

    Discriminator: `entity_type`. Forward-compat via `extra="allow"` and `custom` dict.
    """

    model_config = ConfigDict(
        extra="allow",
        frozen=False,
        use_enum_values=False,
        validate_assignment=True,
    )

    # ── Identity (anti-fragile tri-key) ──
    ueid: UEID
    entity_type: EntityType
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*[a-z0-9]$")

    # ── Tree structure ──
    parent_ueid: UEID | None = None
    related_ueids: list[UEID] = Field(default_factory=list)

    # ── Common fields ──
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: StatusType = StatusType.DRAFT

    # ── Timestamps ──
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    last_reviewed_at: datetime | None = None
    archived_at: datetime | None = None

    # ── IKIGAi alignment (cascade from parent) ──
    ikigai_vectors: list[VectorType] = Field(default_factory=list)
    vector_weights_snapshot: dict[VectorType, float] = Field(default_factory=dict)
    phase_at_creation: Phase | None = None
    regime_at_creation: RegimeType | None = None

    # ── Level metadata ──
    horizon_days: int | None = Field(default=None, ge=1, le=7300)
    primary_score: ScoreValue | None = None

    # ── Forward-compat placeholders ──
    is_placeholder: bool = False
    placeholder_owner: str | None = None  # e.g., "cluster_proj", "cluster_study"
    claimed_by: str | None = None  # subsystem that claimed this placeholder

    # ── Provenance ──
    source: SourceType = SourceType.USER
    source_md_path: Path | None = None

    # ── Forward-compat pass-through (any YAML frontmatter field) ──
    custom: dict[str, Any] = Field(default_factory=dict)

    # ── Tags (free-form) ──
    tags: list[str] = Field(default_factory=list)

    # ─────────────────────────────────────────────────────────────────────────
    # Validators
    # ─────────────────────────────────────────────────────────────────────────

    @field_validator("ikigai_vectors", mode="before")
    @classmethod
    def _coerce_vector_types(cls, v: Any) -> list[VectorType]:
        """Accept strings, coerce to VectorType enum."""
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        out: list[VectorType] = []
        for item in v:
            if isinstance(item, VectorType):
                out.append(item)
            elif isinstance(item, str):
                # Support sub-vectors: "skill.python" -> VectorType.SKILL
                root = item.split(".", 1)[0]
                try:
                    out.append(VectorType(root))
                except ValueError:
                    raise ValueError(f"Unknown vector root: {root!r} (from {item!r})")
            else:
                raise ValueError(f"Invalid vector type: {item!r}")
        return out

    @field_validator("vector_weights_snapshot", mode="before")
    @classmethod
    def _coerce_weight_keys(cls, v: Any) -> dict[VectorType, float]:
        """Accept string keys, coerce to VectorType enum."""
        if v is None:
            return {}
        out: dict[VectorType, float] = {}
        for k, val in v.items():
            if isinstance(k, VectorType):
                out[k] = val
            elif isinstance(k, str):
                try:
                    out[VectorType(k)] = val
                except ValueError:
                    raise ValueError(f"Unknown vector key: {k!r}")
            else:
                raise ValueError(f"Invalid weight key: {k!r}")
        return out

    @model_validator(mode="after")
    def _validate_weights_range(self) -> "PlanEntity":
        """Vector weights must be in [0, 1.5]."""
        for vec, w in self.vector_weights_snapshot.items():
            if not 0.0 <= w <= 1.5:
                raise ValueError(
                    f"Vector weight for {vec} out of range [0, 1.5]: {w}"
                )
        return self

    @model_validator(mode="after")
    def _validate_placeholder_consistency(self) -> "PlanEntity":
        """If is_placeholder, must have placeholder_owner."""
        if self.is_placeholder and not self.placeholder_owner:
            raise ValueError("is_placeholder=True requires placeholder_owner")
        if self.claimed_by and not self.is_placeholder:
            raise ValueError("claimed_by requires is_placeholder=True")
        return self

    # ─────────────────────────────────────────────────────────────────────────
    # Behaviors
    # ─────────────────────────────────────────────────────────────────────────

    def mark_reviewed(self) -> None:
        """Update last_reviewed_at to now (UTC)."""
        self.last_reviewed_at = _utc_now()
        self.updated_at = _utc_now()

    def add_related(self, ueid: UEID) -> None:
        """Add a related entity (idempotent)."""
        if ueid not in self.related_ueids:
            self.related_ueids.append(ueid)
            self.updated_at = _utc_now()

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """Serialize to YAML frontmatter-compatible dict."""
        d = self.model_dump(mode="json", exclude={"custom"})
        # Flatten VectorType keys to strings
        if "ikigai_vectors" in d:
            d["ikigai_vectors"] = [v if isinstance(v, str) else v.value for v in d["ikigai_vectors"]]
        if "vector_weights_snapshot" in d:
            d["vector_weights_snapshot"] = {
                (k if isinstance(k, str) else k.value): v
                for k, v in d["vector_weights_snapshot"].items()
            }
        if "status" in d:
            d["status"] = self.status.value
        if "entity_type" in d:
            d["entity_type"] = self.entity_type.value
        if "phase_at_creation" in d and d["phase_at_creation"]:
            d["phase_at_creation"] = (
                self.phase_at_creation.value
                if hasattr(self.phase_at_creation, "value")
                else self.phase_at_creation
            )
        if "regime_at_creation" in d and d["regime_at_creation"]:
            d["regime_at_creation"] = (
                self.regime_at_creation.value
                if hasattr(self.regime_at_creation, "value")
                else self.regime_at_creation
            )
        if d.get("source_md_path"):
            d["source_md_path"] = str(self.source_md_path)
        d["custom"] = self.custom
        return d

    @classmethod
    def from_frontmatter_dict(cls, data: dict[str, Any]) -> "PlanEntity":
        """Deserialize from YAML frontmatter dict."""
        data = dict(data)
        custom = data.pop("custom", {})
        # Coerce UEID
        if "ueid" in data and isinstance(data["ueid"], str):
            data["ueid"] = UEID(data["ueid"])
        # Coerce source_md_path
        if "source_md_path" in data and data["source_md_path"]:
            data["source_md_path"] = Path(data["source_md_path"])
        instance = cls(**data)
        if custom:
            instance.custom = custom
        return instance


__all__ = ["PlanEntity"]
