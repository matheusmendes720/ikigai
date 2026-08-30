"""StateReducer — collapses IKIGAiStateDict into the canonical IKIGAiRecord.

Layer 2 of the unified data model (§2): bridges the LangGraph in-memory
state shape (defined in src/agents/ikigai_maintainer/state.py) into the
polymorphic IKIGAiRecord root.

Task 10 of data-model-unification.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ikigai.entities.fractal_regime import FractalRegime, FractalRegimeState
from ikigai.entities.ikigai_record import IKIGAiRecord, EntityType, StatusType
from ikigai.entities.score_value import ScoreUnit, ScoreValue


# Default phase weights when state does not supply them (I7: phase weights
# live on IKIGAiRecord, NOT PhaseSnapshot).
_DEFAULT_PHASE_WEIGHTS: dict[str, float] = {
    "passion": 0.20,
    "skill": 0.20,
    "market": 0.20,
    "revenue": 0.20,
    "course": 0.20,
}


class StateReducer:
    """Pure function from state dict to IKIGAiRecord.

    Stateless: every call is independent. The reducer does not touch the
    filesystem; the caller decides what to do with the resulting record
    (writer writes, SQLiteAdapter mirrors, CheckpointAdapter persists).
    """

    @staticmethod
    def reduce(state: dict[str, Any], source_md_path: Path) -> IKIGAiRecord:
        """Collapse `state` into an IKIGAiRecord.

        The cycle record is always EntityType.CYCLE and is_placeholder=True
        per SPEC D7 (derived from ephemeral state, not authored in the vault).
        """
        now = datetime.now(timezone.utc)
        ueid = state["cycle_id"]

        meta_raw = state.get("meta_vector_score")
        qhe_raw = state.get("q_he_score")

        return IKIGAiRecord(
            ueid=ueid,
            entity_type=EntityType.CYCLE,
            slug=state.get("cycle_start", ueid.split(":")[-2]),
            title=f"IKIGAi Cycle — {state.get('cycle_start', 'unknown')}",
            status=StatusType.ACTIVE,
            is_placeholder=True,
            placeholder_owner="ikigai-agent",
            ikigai_vectors=list(state.get("vector_scores", {}).keys()),
            vector_scores=StateReducer._map_vector_scores(state.get("vector_scores", {})),
            meta_vector_score=ScoreValue(value=float(meta_raw), unit=ScoreUnit.RATIO)
            if meta_raw is not None
            else None,
            q_he_score=ScoreValue(value=float(qhe_raw), unit=ScoreUnit.RATIO)
            if qhe_raw is not None
            else None,
            regime=StateReducer._map_regime(state),
            phase=state.get("phase"),
            phase_iteration=state.get("phase_iteration", 0),
            phase_converged=state.get("phase_converged", False),
            active_dream_ueid=state.get("active_dream_ueid"),
            active_goal_ueids=state.get("active_goal_ueids", []),
            active_objective_ueids=state.get("active_objective_ueids", []),
            active_project_ueids=state.get("active_project_ueids", []),
            active_task_ueids=state.get("active_task_ueids", []),
            workload_estimate=state.get("workload_estimate"),
            capacity_estimate=state.get("capacity_estimate"),
            balancer_verdict=StateReducer._map_balancer_verdict(state.get("balancer_verdict")),
            prospective_buffer=list(state.get("prospective_buffer", [])),
            retrospective_log=list(state.get("retrospective_log", [])),
            corrections=list(state.get("corrections", [])),
            created_at=now,
            updated_at=now,
            source_md_path=Path(source_md_path),
        )

    # ──────── Mappers ────────

    @staticmethod
    def _map_balancer_verdict(raw: str | None) -> Any:
        """Pass through the balancer verdict string; the IKIGAiRecord
        field type is permissive (Literal) — we keep the typed enum out
        of this adapter to avoid coupling to the operational core."""
        return raw

    @staticmethod
    def _map_vector_scores(scores: dict[str, float]) -> dict[str, ScoreValue]:
        """Map raw vector scores (0..1) → ScoreValue with unit='percent' (0..100).

        Per ScoreUnit literal in score_value.py, "percent" means 0..100.
        The state dict stores raw ratios (0..1); we scale up here.
        """
        return {
            k: ScoreValue(value=float(v) * 100.0, unit=ScoreUnit.PERCENT) for k, v in scores.items()
        }

    @staticmethod
    def _map_regime(state: dict[str, Any]) -> FractalRegime | None:
        regime_name = state.get("regime_state")
        if not regime_name:
            return None
        # Global level gets the active regime; lower levels get a
        # placeholder 'MAINTAIN' so the 4-level invariant (D13) holds
        # without overreaching what the state dict knows.
        return FractalRegime(
            levels=[
                FractalRegimeState(
                    level="global",
                    regime=regime_name,
                    days_in_regime=state.get("days_in_regime", 0),
                    is_hysteresis_active=state.get("is_hysteresis_active", False),
                    hysteresis_days=0,
                ),
                FractalRegimeState(
                    level="cluster",
                    regime="MAINTAIN",
                    days_in_regime=0,
                    is_hysteresis_active=False,
                    hysteresis_days=0,
                ),
                FractalRegimeState(
                    level="vector",
                    regime="MAINTAIN",
                    days_in_regime=0,
                    is_hysteresis_active=False,
                    hysteresis_days=0,
                ),
                FractalRegimeState(
                    level="sub_vector",
                    regime="MAINTAIN",
                    days_in_regime=0,
                    is_hysteresis_active=False,
                    hysteresis_days=0,
                ),
            ],
        )


__all__ = ["StateReducer"]
