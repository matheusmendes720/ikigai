"""PeriodReport mirror entity (operational) — stored as JSON blob in entities table.

Source: ADR-006 + period-reports-sync plan T9
Linked: vibe-ops PeriodReport (lenient extra="allow") → this (strict extra="forbid")

Operational uses single-table JSON blob storage (entities table). This entity is
the strict mirror — internal storage validates against unknown fields, while
the vault-facing vibe-ops PeriodReport is lenient (extra="allow") to preserve
user-added fields.

ADR-006 invariant: vault-wins for period_reports (no computed fields).
"""
from __future__ import annotations

import datetime as _dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["PeriodReport"]


# Per-period verdict enums (must match vibe-ops/_PERIOD_VERDICTS)
_VERDICT_DAILY = {"PASS", "PARTIAL", "FAIL"}
_VERDICT_WEEKLY = {"PASS", "PARTIAL", "FAIL"}
_VERDICT_ONDA = {"CONTINUE_WAVE", "CORRECT_TRAJECTORY", "KILL_WAVE"}
_VERDICT_QUARTERLY = {"PASS", "PARTIAL", "FAIL"}
_VERDICT_SONHO = {"ACTIVE", "VALIDATED", "FALSIFIED", "PIVOTED", "ABANDONED"}

_PERIOD_VERDICTS: dict[str, set[str]] = {
    "daily": _VERDICT_DAILY,
    "weekly": _VERDICT_WEEKLY,
    "onda": _VERDICT_ONDA,
    "quarterly": _VERDICT_QUARTERLY,
    "sonho": _VERDICT_SONHO,
}

_PERIOD_DAYS: dict[str, int | None] = {
    "daily": 1,
    "weekly": 7,
    "onda": 45,
    "quarterly": 90,
    "sonho": None,
}


class PeriodReport(BaseModel):
    """Mirror of vibe-ops PeriodReport for operational storage.

    Strict mode (extra="forbid") since this is internal storage.
    Vault-facing entity in vibe-ops is lenient (extra="allow").

    Stored as JSON in operational's ``entities`` table.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        validate_assignment=True,
    )

    id: str = Field(..., min_length=1, max_length=200)
    entity_type: Literal["period_report"] = "period_report"

    period: Literal["daily", "weekly", "onda", "quarterly", "sonho"]
    date_start: _dt.date
    date_end: _dt.date

    verdict: str
    verdict_score: float = Field(..., ge=0.0, le=1.0)

    # Optional metadata
    template_version: str = "1.0"
    ikigai_cluster: str = "plan"
    sonho_id: str | None = None
    ikigai_vector: Literal["passion", "skill", "market", "revenue"] | None = None
    xp_gained: int | None = Field(default=None, ge=0)
    mastery_delta: str | None = None
    policy_recommendation: Literal["push", "maintain", "reduce", "recover"] | None = None
    parent_period: str | None = None
    status: Literal["draft", "active", "closed"] = "active"
    tags: list[str] = Field(default_factory=list)

    # Sync metadata (operational-specific, separate from vibe-ops)
    vault_path: str | None = None
    vault_hash: str | None = None
    last_synced_at: _dt.datetime | None = None

    @model_validator(mode="after")
    def validate_hierarchy_or_verdict_per_period(self) -> PeriodReport:
        """Cross-field invariants for verdict, dates, and hierarchy.

        Checks:
        - verdict is valid for the given period
        - date_end >= date_start
        - period-day constraint (skip for sonho)
        - sonho cannot have parent_period

        Returns:
            The model instance (unchanged on success).

        Raises:
            ValueError: If any invariant is violated.
        """
        allowed = _PERIOD_VERDICTS.get(self.period, set())
        if self.verdict not in allowed:
            msg = (
                f"verdict {self.verdict!r} not allowed for period {self.period!r}. "
                f"Allowed: {sorted(allowed)}"
            )
            raise ValueError(msg)
        if self.date_end < self.date_start:
            msg = f"date_end {self.date_end} < date_start {self.date_start}"
            raise ValueError(msg)
        expected_days = _PERIOD_DAYS.get(self.period)
        if expected_days is not None:
            actual_days = (self.date_end - self.date_start).days + 1
            if abs(actual_days - expected_days) > 1:
                msg = (
                    f"period {self.period!r} expected ~{expected_days} days, "
                    f"got {actual_days} days"
                )
                raise ValueError(msg)
        if self.period == "sonho" and self.parent_period is not None:
            msg = "sonho reports cannot have parent_period"
            raise ValueError(msg)
        return self
