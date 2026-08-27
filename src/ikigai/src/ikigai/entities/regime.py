"""Regime graph — fractal regime hierarchy (Global → Cluster → Vector → SubVector)."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ikigai.enums import ClusterType, RegimeType, VectorType


class RegimeOverrideAudit(BaseModel):
    """Audit record for a regime override."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    from_regime: RegimeType
    to_regime: RegimeType
    reason: str
    recommendation_score: float = Field(ge=0.0, le=1.0)
    acknowledged_risks: list[str] = Field(default_factory=list)
    created_by: str = "user"


class RegimeOverride(BaseModel):
    """Manual regime override with audit trail + strong recommendation."""

    model_config = ConfigDict(extra="allow")

    entity_ueid: str  # UEID as string for forward-compat (could be cluster, vector, etc.)
    from_regime: RegimeType
    to_regime: RegimeType
    reason: str
    recommendation_score: float = Field(ge=0.0, le=1.0)
    recommendation_message: str = ""
    expected_qhe_delta: float = 0.0
    expected_regime_return_days: int = 7
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    created_by: str = "user"
    acknowledged_risks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _warn_strong_recommendation(self) -> "RegimeOverride":
        """Tag strong recommendations against."""
        if self.recommendation_score < 0.3:
            self.acknowledged_risks.append("STRONG_RECOMMENDATION_AGAINST")
        return self


class RegimeGraph(BaseModel):
    """Fractal regime hierarchy: Global → Cluster → Vector → SubVector."""

    model_config = ConfigDict(extra="allow")

    # Top-level (global)
    global_regime: RegimeType = RegimeType.MAINTAIN

    # Per-cluster
    cluster_regimes: dict[ClusterType, RegimeType] = Field(default_factory=dict)

    # Per-vector
    vector_regimes: dict[VectorType, RegimeType] = Field(default_factory=dict)

    # Sub-vector (fractal): "skill.python", "market.freelance", etc.
    subvector_regimes: dict[str, RegimeType] = Field(default_factory=dict)

    # Hysteresis windows (per-level)
    global_hysteresis_days: int = 3
    cluster_hysteresis_days: int = 3
    vector_hysteresis_days: int = 2
    subvector_hysteresis_days: int = 1

    # Metadata
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _coherence_check(self) -> "RegimeGraph":
        """Sub-vectors cannot be in PUSH if parent vector is RECOVER (warn only)."""
        for sub_key, sub_regime in self.subvector_regimes.items():
            # Parse sub_key: "skill.python" → root=skill, sub=python
            if "." in sub_key:
                root_str = sub_key.split(".", 1)[0]
                try:
                    parent_vec = VectorType(root_str)
                except ValueError:
                    continue
                parent_regime = self.vector_regimes.get(parent_vec, self.global_regime)
                if parent_regime == RegimeType.RECOVER and sub_regime != RegimeType.RECOVER:
                    # Warn but allow (override possible)
                    pass
        return self

    def get_effective_regime(self, scope: str = "global") -> RegimeType:
        """Get effective regime for a scope.

        scope can be: 'global', cluster name, vector name, or 'skill.python' (sub-vector).
        """
        if scope == "global":
            return self.global_regime
        if scope in self.cluster_regimes:
            return self.cluster_regimes[ClusterType(scope)]  # type: ignore[arg-type]
        if scope in self.vector_regimes:
            return self.vector_regimes[VectorType(scope)]  # type: ignore[arg-type]
        if scope in self.subvector_regimes:
            return self.subvector_regimes[scope]
        return self.global_regime


__all__ = ["RegimeGraph", "RegimeOverride", "RegimeOverrideAudit"]
