r"""Portfolio artifact entity — hackathons, side projects, and work experience.

Holds all portfolio objects from job_hunter/base/ synchronized into the
PAV state layer so they appear alongside routines, habits, and metrics in
``~/.time-tasker/portfolio_artifacts.json``.

This entity is a **leaf** — no other entity imports from it, and it
imports only from ``operational.enums`` and ``operational.types``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from operational.types import UEID  # noqa: TC001

__all__ = ["ArtifactType", "PortfolioArtifact"]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ArtifactType(StrEnum):
    """Category of portfolio artifact."""

    HACKATHON = "hackathon"
    SIDE_PROJECT = "side_project"
    WORK_EXPERIENCE = "work_experience"
    CV_CONTENT = "cv_content"
    HTML_OUTPUT = "html_output"
    APP = "app"


class DeploymentStatus(StrEnum):
    """Deployment / life-cycle status of the artifact."""

    DEPLOYED_PRODUCTION = "deployed_production"
    COMPLETED = "completed"
    UI_READY_NOT_DEPLOYED = "ui_ready_not_deployed"
    IN_PROGRESS = "in_progress"
    PLANNED = "planned"
    TO_FILL = "to_fill"


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------


class PortfolioArtifact(BaseModel):
    r"""A single portfolio artifact stored in PAV state.

    Normalized from ``job_hunter/base/hackathons-db.json`` and
    ``portfolio-showcase.json`` so the PAV CLI can query portfolio health
    alongside daily habits and routines.

    Attributes:
        id: UEID in the form ``port_<hex>`` (e.g. ``port_hb001``).
        artifact_type: One of :class:`ArtifactType`.
        deployment_status: One of :class:`DeploymentStatus`.
        name: Human-readable display name.
        source_file: Which JSON file this artifact came from
            (e.g. ``hackathons-db.json``).
        source_key: Dot-notation key within the source file
            (e.g. ``hackathons[HB-001]``).
        github_url: Primary GitHub repository URL, or None.
        live_url: Live/production URL, or None.
        period_start: Start date as ``YYYY-MM`` or ``YYYY-MM-DD``.
        period_end: End date, or ``"present"``.
        has_to_fill: True if any critical field is still a TO_FILL placeholder.
        is_flagship: True if this is a flagship/anchor project.
        github_stars: Stars count fetched via ``gh api``.
        github_open_issues: Open issues/PRs count fetched via ``gh api``.
        github_last_commit: Last push date as ``YYYY-MM-DD``.
        tech_stack: List of technology names.
        skills_demonstrated: List of skill labels.
        gaps: List of gap descriptions (from the source gaps arrays).
        cv_weight_aiml: CV relevance weight for AI/ML target (1-10, or None).
        cv_weight_fullstack: CV relevance weight for full-stack target (1-10, or None).
        created_at: Wall-clock timestamp when imported into PAV state.
        updated_at: Wall-clock timestamp of last sync from source JSON.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    id: UEID
    artifact_type: ArtifactType
    deployment_status: DeploymentStatus
    name: Annotated[str, Field(min_length=1, max_length=200)]
    source_file: Annotated[str, Field(max_length=300)]
    source_key: Annotated[str, Field(max_length=300)]
    github_url: Annotated[str | None, Field(max_length=500)] = None
    live_url: Annotated[str | None, Field(max_length=500)] = None
    period_start: Annotated[str | None, Field(max_length=20)] = None
    period_end: Annotated[str | None, Field(max_length=20)] = None
    has_to_fill: bool = False
    is_flagship: bool = False
    github_stars: Annotated[int | None, Field(ge=0)] = None
    github_open_issues: Annotated[int | None, Field(ge=0)] = None
    github_last_commit: Annotated[str | None, Field(max_length=20)] = None
    tech_stack: list[str] = Field(default_factory=list)
    skills_demonstrated: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    cv_weight_aiml: Annotated[int | None, Field(ge=1, le=10)] = None
    cv_weight_fullstack: Annotated[int | None, Field(ge=1, le=10)] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_job_hunter(
        cls,
        artifact_id: str,
        name: str,
        artifact_type: ArtifactType,
        deployment_status: DeploymentStatus,
        source_file: str,
        source_key: str,
        github_url: str | None = None,
        live_url: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        has_to_fill: bool = False,
        is_flagship: bool = False,
        tech_stack: list[str] | None = None,
        skills_demonstrated: list[str] | None = None,
        gaps: list[str] | None = None,
        cv_weight_aiml: int | None = None,
        cv_weight_fullstack: int | None = None,
        *,
        github_stars: int | None = None,
        github_open_issues: int | None = None,
        github_last_commit: str | None = None,
    ) -> PortfolioArtifact:
        """Factory: build a :class:`PortfolioArtifact` from job_hunter JSON data.

        Generates a deterministic-enough ``port_<hex>`` id from the
        ``artifact_id`` string so the same artifact always gets the same
        UEID on re-import.
        """
        import hashlib

        hex_id = hashlib.md5(artifact_id.encode()).hexdigest()[:12]
        now = datetime.now(tz=UTC)
        return cls(
            id=f"port_{hex_id}",
            artifact_type=artifact_type,
            deployment_status=deployment_status,
            name=name,
            source_file=source_file,
            source_key=source_key,
            github_url=github_url,
            live_url=live_url,
            period_start=period_start,
            period_end=period_end,
            has_to_fill=has_to_fill,
            is_flagship=is_flagship,
            github_stars=github_stars,
            github_open_issues=github_open_issues,
            github_last_commit=github_last_commit,
            tech_stack=tech_stack or [],
            skills_demonstrated=skills_demonstrated or [],
            gaps=gaps or [],
            cv_weight_aiml=cv_weight_aiml,
            cv_weight_fullstack=cv_weight_fullstack,
            created_at=now,
            updated_at=now,
        )
