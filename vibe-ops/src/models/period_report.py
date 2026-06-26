"""PeriodReport entity — parses _templates_periodos/*.md into queryable structure.

Source: ADR-006 (Period Reports Schema Contract)
Linked: .omo/plans/period-reports-sync.md T2
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import warnings
from pathlib import Path
from typing import Any, Literal

import frontmatter
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = ["PeriodReport", "PeriodReportParser", "PeriodSyncStats"]


# Per-period verdict enums (ADR-006 §2.3)
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
    """A single period_report — Relatório Diário, Semanal, Onda, Trimestral, or Sonho.

    Source: ADR-006 schema contract, _templates_periodos/*.md.
    Parsed from YAML frontmatter + body sections.

    Lenient mode (extra="allow") so user-added fields don't break validation.
    Sync metadata (vault_path, vault_hash) is required.
    """
    model_config = ConfigDict(
        frozen=False,
        extra="allow",
        validate_assignment=False,
    )

    # Identity
    id: str = Field(default="")
    entity_type: Literal["period_report"] = "period_report"

    # Period contract (required, 6 fields per ADR-006)
    period: Literal["daily", "weekly", "onda", "quarterly", "sonho"]
    date_start: _dt.date
    date_end: _dt.date

    # Verdict contract (required)
    verdict: str
    verdict_score: float = Field(..., ge=0.0, le=1.0)

    # Optional metadata (ADR-006 §3.2)
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

    # Sync metadata (required)
    vault_path: str = Field(..., min_length=1, max_length=500)
    vault_hash: str = Field(..., min_length=16, max_length=64)
    last_synced_at: _dt.datetime | None = None

    @field_validator("verdict")
    @classmethod
    def validate_verdict_per_period(cls, v: str, info: Any) -> str:
        period = info.data.get("period")
        if period is None:
            return v
        allowed = _PERIOD_VERDICTS.get(period, set())
        if v not in allowed:
            raise ValueError(
                f"verdict {v!r} not allowed for period {period!r}. "
                f"Allowed: {sorted(allowed)}"
            )
        return v

    @model_validator(mode="after")
    def auto_id_from_vault_path(self) -> "PeriodReport":
        if not self.id:
            # Derive id from vault_path: filename without extension
            stem = Path(self.vault_path).stem
            self.id = stem
        return self

    @model_validator(mode="after")
    def validate_date_range(self) -> "PeriodReport":
        if self.date_end < self.date_start:
            raise ValueError(
                f"date_end {self.date_end} < date_start {self.date_start}"
            )
        expected_days = _PERIOD_DAYS.get(self.period)
        if expected_days is not None:
            actual_days = (self.date_end - self.date_start).days + 1
            if abs(actual_days - expected_days) > 1:
                raise ValueError(
                    f"period {self.period!r} expected ~{expected_days} days, "
                    f"got {actual_days} days ({self.date_start} to {self.date_end})"
                )
        return self

    @model_validator(mode="after")
    def validate_hierarchy(self) -> "PeriodReport":
        if self.period == "sonho" and self.parent_period is not None:
            raise ValueError(
                "sonho reports cannot have parent_period (sonho is the root)"
            )
        return self

    @model_validator(mode="after")
    def validate_verdict_score_consistency(self) -> "PeriodReport":
        if self.verdict in ("FAIL", "KILL_WAVE", "FALSIFIED", "ABANDONED"):
            if self.verdict_score >= 0.5:
                warnings.warn(
                    f"verdict={self.verdict} but verdict_score={self.verdict_score} "
                    f"(expected < 0.5). Check consistency.",
                    UserWarning,
                    stacklevel=2,
                )
        return self


class PeriodSyncStats(BaseModel):
    """Result of a sync run.

    Defined here so sync layer (period_sync.py) can import without circular deps.
    """
    model_config = ConfigDict(frozen=True)

    ingested: int = 0
    skipped: int = 0
    updated: int = 0
    errors: int = 0
    conflicts: int = 0
    orphans: int = 0
    file_errors: list[dict[str, str]] = Field(default_factory=list)


class PeriodReportParser:
    """Parse a Markdown file into a PeriodReport.

    Expects YAML frontmatter with required fields (ADR-006):
    type, entity_type, period, date_start, date_end, verdict, verdict_score
    """

    @staticmethod
    def parse_file(file_path: str) -> PeriodReport | None:
        """Returns PeriodReport or None if file is not a valid period_report."""
        try:
            post = frontmatter.load(file_path)
        except Exception:
            return None
        if post.metadata.get("type") != "period_report":
            return None
        if post.metadata.get("entity_type") != "period_report":
            return None

        metadata = dict(post.metadata)
        metadata["vault_path"] = str(file_path)
        canonical = json.dumps(metadata, sort_keys=True, default=str)
        metadata["vault_hash"] = hashlib.sha256(canonical.encode()).hexdigest()[:16]

        try:
            return PeriodReport(**metadata)
        except Exception:
            return None
