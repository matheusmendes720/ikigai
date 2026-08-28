"""Metrics contracts — Burndown, ExecutionRate, QHEScore.

These are the FEEDBACK signals that flow back from interfaces to the
Deep Agent for planning updates. They are computed from VaultEvent streams.

Source:
- strategics/Desempenho Subjacente.md
- ADR-004 (daily/weekly consolidation)
- PRD-05 (health metrics)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import RegimeState, UEID

# Note: ikigai import deferred - requires ikigai package to be installed
# from ikigai.core.scoring.qhe import compute_qhe


# ---------------------------------------------------------------------------
# Burndown
# ---------------------------------------------------------------------------


class Burndown(BaseModel):
    """How much work remains vs time — the sprint/daily burndown chart.

    Computed from VaultEvent streams: count of ``done`` events per day
    versus the total planned.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    cycle_id: str
    """PlanningCycle, Wave, or Sprint this burndown belongs to."""

    date: date
    """The day this snapshot was taken."""

    total_tasks: Annotated[int, Field(ge=0)]
    """Total planned tasks in the cycle."""

    done_tasks: Annotated[int, Field(ge=0)]
    """Tasks marked done as of this date."""

    remaining_tasks: Annotated[int, Field(ge=0)]
    """total_tasks - done_tasks (computed)."""

    ideal_remaining: float
    """Theoretical remaining if perfectly on-track."""

    velocity: float
    """Tasks done per day (rolling average)."""

    @property
    def completion_pct(self) -> float:
        if self.total_tasks == 0:
            return 1.0
        return self.done_tasks / self.total_tasks

    @property
    def is_on_track(self) -> bool:
        return self.remaining_tasks <= self.ideal_remaining

    @property
    def is_behind(self) -> bool:
        return self.remaining_tasks > self.ideal_remaining


# ---------------------------------------------------------------------------
# ExecutionRate
# ---------------------------------------------------------------------------


class ExecutionRate(BaseModel):
    """Ratio of planned work that got done — the planned vs actual gap.

    This is the PRIMARY signal the Deep Agent uses to update planning.
    High execution rate → increase load next cycle.
    Low execution rate → reduce scope or pivot approach.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    cycle_id: str
    period: Literal["daily", "weekly", "onda", "sprint", "quarterly"]

    date_start: date
    date_end: date

    planned_count: Annotated[int, Field(ge=0)]
    """Tasks planned to complete in this period."""

    done_count: Annotated[int, Field(ge=0)]
    """Tasks actually completed in this period."""

    blocked_count: Annotated[int, Field(ge=0)]
    """Tasks blocked (contributed to non-completion)."""

    @property
    def rate(self) -> float:
        if self.planned_count == 0:
            return 1.0 if self.done_count == 0 else 0.0
        return self.done_count / self.planned_count

    @property
    def is_blocked(self) -> bool:
        return self.blocked_count > 0 and self.done_count < self.planned_count

    @property
    def verdict(self) -> Literal["green", "yellow", "red"]:
        r = self.rate
        if r >= 0.8:
            return "green"
        if r >= 0.5:
            return "yellow"
        return "red"


# ---------------------------------------------------------------------------
# QHEScore
# ---------------------------------------------------------------------------


class QHEScore(BaseModel):
    """Quality-Habit-Effectiveness score for a single day.

    This is the PRIMARY policy input. Computed from habit completion data
    in operational/entities/habit.py (QHEMetrics).

    Formula:
        Q_HE = habit_avg * energy_ratio * (1 + eta * streak_bonus)

    Policy mapping:
        Q_HE >= 0.85 → PUSH
        Q_HE >= 0.65 → MAINTAIN
        Q_HE >= 0.45 → REDUCE
        Q_HE <  0.45 → RECOVER
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    date: date

    habit_avg: Annotated[float, Field(ge=0.0, le=1.0)]
    """Average normalized habit completion across all habits (0-1)."""

    consistency: Annotated[float, Field(ge=0.0, le=1.0)]
    """Fraction of habits completed this day (0-1)."""

    streak_bonus: Annotated[float, Field(ge=0.0, le=1.0)]
    """Normalized streak bonus (avg_streak / max_streak)."""

    energy_ratio: Annotated[float, Field(ge=0.0, le=1.0)]
    """Current energy / max energy (0-1)."""

    eta: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5
    """Streak bonus multiplier."""

    regime_input: RegimeState = RegimeState.MAINTAIN

    @property
    def qhe(self) -> float:
        """Quality-Habit-Effectiveness value.

        Delegates to ikigai.core.scoring.qhe.compute_qhe.
        """
        return compute_qhe(
            h_sono=self.habit_avg,
            h_med=self.habit_avg,
            h_workout=self.habit_avg,
            h_lunch=self.habit_avg,
            s_streak=self.streak_bonus,
        )

    @property
    def regime_predicted(self) -> RegimeState:
        """Predict operational regime from Q_HE value.

        PUSH: Q_HE >= 0.85
        MAINTAIN: 0.65 <= Q_HE < 0.85
        REDUCE: 0.45 <= Q_HE < 0.65
        RECOVER: Q_HE < 0.45
        """
        q = self.qhe
        if q >= 0.85:
            return RegimeState.PUSH
        if q >= 0.65:
            return RegimeState.MAINTAIN
        if q >= 0.45:
            return RegimeState.REDUCE
        return RegimeState.RECOVER
