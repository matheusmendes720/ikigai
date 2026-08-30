"""PhaseSnapshot — SPEC I7.

Phase weights live on a SEPARATE frozen entity, not on IKIGAiRecord. Each
cycle iteration produces one snapshot (append-only, immutable). This
preserves the historical record of how weights drifted across cycles —
critical for retrospectives and regime-shift forensics.

UEID format (per §3.1 + design spec): `ikigai:phase_snapshot:{cycle_id}:{iter}:{hash}`
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ikigai.entities.ueid import UEID


class PhaseSnapshot(BaseModel):
    """Frozen record of phase weights at a specific cycle iteration.

    `extra="forbid"` (no forward-compat); `frozen=True` (append-only).
    `weights` MUST sum to 1.0 (±0.01) — validated below.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    ueid: UEID
    cycle_ueid: UEID
    phase: str
    iteration: int = Field(ge=0, le=5)  # I11
    weights: dict[str, float]
    created_at: datetime

    def weight_sum(self) -> float:
        return sum(self.weights.values())


__all__ = ["PhaseSnapshot"]
