"""Portfolio artifact CLI commands — import from job_hunter, sync GitHub, show.

The ``portfolio`` sub-typer gives the PAV kernel visibility into all
hackathon, side-project, and work-experience artifacts tracked in
``job_hunter/base/`` without the job_hunter package knowing about PAV at all.

Import path resolution:
    job_hunter/base/ is resolved by walking from this file's location:
    ``operational/cli/commands/portfolio_cmd.py``
      → .../cli/commands/
      → .../cli/
      → .../apps/cli/src/operational/
      → .../apps/cli/src/operational/   (packages/core/src/operational is a sibling)
      → .../apps/cli/src/              (go up past apps/cli/src/operational)
      → .../apps/cli/                  (go up past apps/cli/src)
      → .../apps/
      → .../life-ops/operational/
      → life-ops/                      (go up to workspace root)
      → job_hunter/base/               (sibling workspace)

In practice we use the ``JOB_HUNTER_BASE`` env var when set, and fall back to
the sibling workspace path.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from operational.cli.formatters import format_as_json
from operational.cli.state import portfolio_artifacts
from operational.cli.telemetry import get_logger, trace_command
from operational.entities.portfolio import ArtifactType, DeploymentStatus, PortfolioArtifact

app = typer.Typer(
    help="Portfolio artifacts — import from job_hunter, sync GitHub, show in PAV state.",
)
console = Console()
log = get_logger("portfolio_cmd")


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _job_hunter_base() -> Path:
    """Resolve ``job_hunter/base/`` as a sibling to ``life-ops/operational/``."""
    base = os.environ.get("JOB_HUNTER_BASE")
    if base:
        return Path(base)

    # operational/ life-ops/ operational/
    #   apps/cli/src/operational/cli/commands/portfolio_cmd.py
    # Walk up to find life-ops/operational/, then sibling job_hunter/base/
    here = Path(__file__).resolve()
    operational_root = here  # .../cli/commands/
    for _ in range(8):
        operational_root = operational_root.parent
        if (
            operational_root.name == "operational"
            and (operational_root / "pyproject.toml").exists()
        ):
            break
    # operational_root is now life-ops/operational/
    return operational_root.parent.parent / "job_hunter" / "base"


# ---------------------------------------------------------------------------
# Data loading (same logic as job_hunter/tracker)
# ---------------------------------------------------------------------------


class _ArtifactTypeLocal(StrEnum):
    HACKATHON = "hackathon"
    SIDE_PROJECT = "side_project"
    WORK_EXPERIENCE = "work_experience"
    CV_CONTENT = "cv_content"
    HTML_OUTPUT = "html_output"
    APP = "app"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_fill_in(obj: dict) -> bool:
    to_fill_values = {"TO_FILL", "TO_FILL — fill"}
    return any(v in to_fill_values for v in obj.values() if isinstance(v, str))


def _collect_gaps(obj: dict, prefix: str = "") -> list[str]:
    gaps = []
    for k, v in obj.items():
        if isinstance(v, str) and v in ("TO_FILL", "TO_FILL — fill"):
            gaps.append(f"{prefix}{k}: {v}")
        elif isinstance(v, dict):
            gaps.extend(_collect_gaps(v, prefix=f"{prefix}{k}."))
    return gaps


def _parse_status(s: str | None) -> DeploymentStatus:
    mapping = {
        "completed_productized": DeploymentStatus.DEPLOYED_PRODUCTION,
        "deployed_production": DeploymentStatus.DEPLOYED_PRODUCTION,
        "completed": DeploymentStatus.COMPLETED,
        "completed_ui_ready_not_deployed": DeploymentStatus.UI_READY_NOT_DEPLOYED,
        "ui_ready_not_deployed": DeploymentStatus.UI_READY_NOT_DEPLOYED,
        "in_progress": DeploymentStatus.IN_PROGRESS,
        "planned": DeploymentStatus.PLANNED,
        "to_fill": DeploymentStatus.TO_FILL,
    }
    return mapping.get(s or "", DeploymentStatus.TO_FILL)


def _find_exp_id(artifact_id: str, mapping: dict) -> str | None:
    """Map HB-001 → H-001, SP-001 → S-001, W-001 stays W-001."""
    prefix_map = {"HB": "H", "SP": "S"}
    parts = artifact_id.split("-", 1)
    if len(parts) == 2 and parts[0] in prefix_map:
        mapped = f"{prefix_map[parts[0]]}-{parts[1]}"
        if mapped in mapping.get("experiences", {}):
            return mapped
    if artifact_id in mapping.get("experiences", {}):
        return artifact_id
    return None


def _get_cv_weight(artifact_id: str, mapping: dict, variant: str) -> int | None:
    exp_id = _find_exp_id(artifact_id, mapping)
    if not exp_id:
        return None
    exp = mapping.get("experiences", {}).get(exp_id, {})
    return exp.get(f"weight_{variant}")


# ---------------------------------------------------------------------------
# GitHub helpers (mirrors job_hunter/tracker/github/sync.py)
# ---------------------------------------------------------------------------


def _gh(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _fetch_github_stats(owner: str, repo: str) -> tuple[int | None, int | None, str | None]:
    raw = _gh("api", f"repos/{owner}/{repo}")
    if not raw:
        return None, None, None
    try:
        data = json.loads(raw)
        pushed_at = data.get("pushed_at")
        return (
            data.get("stargazers_count"),
            None,  # open issues — expensive to count precisely; skip
            pushed_at[:10] if pushed_at else None,
        )
    except Exception:
        return None, None, None


def _owner_repo(url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2 and parts[-2] and parts[-1]:
        return parts[-2], parts[-1].replace(".git", "")
    return None


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------


def _build_portfolio_artifacts(
    base: Path,
    sync_github: bool = False,
) -> list[PortfolioArtifact]:
    """Build PortfolioArtifact list from job_hunter JSON sources."""
    db_path = base / "hackathons-db.json"
    showcase_path = base / "portfolio-showcase.json"
    mapping_path = base / "experiences-mapping.json"

    if not db_path.exists():
        raise FileNotFoundError(f"hackathons-db.json not found at {db_path}")

    db = _load_json(db_path)
    showcase = _load_json(showcase_path) if showcase_path.exists() else {}
    mapping = _load_json(mapping_path) if mapping_path.exists() else {}

    # Build a lookup: showcase by id for enrichment
    showcase_by_id: dict[str, dict] = {p["id"]: p for p in showcase.get("showcase_projects", [])}

    artifacts: list[PortfolioArtifact] = []

    # Hackathons
    for h in db.get("hackathons", []):
        artifact_id = h["id"]
        gh_url = h.get("github_frontend") or h.get("github_backend")
        stars: int | None = None
        last_commit: str | None = None
        if sync_github and gh_url:
            or_ = _owner_repo(gh_url)
            if or_:
                stars, _open_issues, last_commit = _fetch_github_stats(or_[0], or_[1])

        gaps = _collect_gaps(h)

        # Enrich from showcase if present
        showcase_item = showcase_by_id.get(artifact_id)
        is_flagship = h.get("status") == "completed_productized"
        if showcase_item:
            is_flagship = is_flagship or showcase_item.get("featured", False)

        artifacts.append(
            PortfolioArtifact.from_job_hunter(
                artifact_id=artifact_id,
                name=h["name"],
                artifact_type=ArtifactType.HACKATHON,
                deployment_status=_parse_status(h.get("status", "to_fill")),
                source_file="hackathons-db.json",
                source_key=f"hackathons[{artifact_id}]",
                github_url=gh_url,
                live_url=h.get("live_url"),
                period_start=h.get("period_start"),
                period_end=h.get("period_end"),
                has_to_fill=_to_fill_in(h),
                is_flagship=is_flagship,
                tech_stack=h.get("tech_stack", []),
                skills_demonstrated=h.get("skills_demonstrated", []),
                gaps=gaps,
                cv_weight_aiml=_get_cv_weight(artifact_id, mapping, "aiml"),
                cv_weight_fullstack=_get_cv_weight(artifact_id, mapping, "fullstack"),
                github_stars=stars,
                github_last_commit=last_commit,
            )
        )

    # Side projects
    for sp in db.get("side_projects", []):
        artifact_id = sp["id"]
        gh_url = sp.get("github")
        stars: int | None = None
        last_commit: str | None = None
        if sync_github and gh_url:
            or_ = _owner_repo(gh_url)
            if or_:
                stars, _open_issues, last_commit = _fetch_github_stats(or_[0], or_[1])

        showcase_item = showcase_by_id.get(artifact_id)
        is_flagship = showcase_item.get("featured", False) if showcase_item else False

        artifacts.append(
            PortfolioArtifact.from_job_hunter(
                artifact_id=artifact_id,
                name=sp["name"],
                artifact_type=ArtifactType.SIDE_PROJECT,
                deployment_status=_parse_status(sp.get("status", "to_fill")),
                source_file="hackathons-db.json",
                source_key=f"side_projects[{artifact_id}]",
                github_url=gh_url,
                live_url=sp.get("live_url"),
                period_start=sp.get("period_start"),
                period_end=sp.get("period_end"),
                has_to_fill=_to_fill_in(sp),
                is_flagship=is_flagship,
                tech_stack=sp.get("tech_stack", []),
                skills_demonstrated=sp.get("skills_demonstrated", []),
                gaps=_collect_gaps(sp),
                cv_weight_aiml=_get_cv_weight(artifact_id, mapping, "aiml"),
                cv_weight_fullstack=_get_cv_weight(artifact_id, mapping, "fullstack"),
                github_stars=stars,
                github_last_commit=last_commit,
            )
        )

    # Work experience
    for w in db.get("work_experience", []):
        artifact_id = w["id"]
        gh_url = w.get("github_backend") or w.get("github_frontend")
        stars: int | None = None
        last_commit: str | None = None
        if sync_github and gh_url:
            or_ = _owner_repo(gh_url)
            if or_:
                stars, _open_issues, last_commit = _fetch_github_stats(or_[0], or_[1])

        artifacts.append(
            PortfolioArtifact.from_job_hunter(
                artifact_id=artifact_id,
                name=w["name"],
                artifact_type=ArtifactType.WORK_EXPERIENCE,
                deployment_status=_parse_status(w.get("status", "to_fill")),
                source_file="hackathons-db.json",
                source_key=f"work_experience[{artifact_id}]",
                github_url=gh_url,
                live_url=w.get("portfolio_url"),
                period_start=w.get("period_start"),
                period_end=w.get("period_end"),
                has_to_fill=_to_fill_in(w),
                is_flagship=False,
                tech_stack=w.get("tech_stack", []),
                skills_demonstrated=w.get("skills_demonstrated", []),
                gaps=_collect_gaps(w),
                cv_weight_aiml=_get_cv_weight(artifact_id, mapping, "aiml"),
                cv_weight_fullstack=_get_cv_weight(artifact_id, mapping, "fullstack"),
                github_stars=stars,
                github_last_commit=last_commit,
            )
        )

    # Showcase-only projects (not in hackathons-db)
    for p in showcase.get("showcase_projects", []):
        artifact_id = p["id"]
        if any(a.source_key == f"showcase_projects[{artifact_id}]" for a in artifacts):
            continue  # already imported above
        gh = p.get("github", {})
        if isinstance(gh, dict):
            gh_url = gh.get("main") or gh.get("backend") or gh.get("frontend")
        else:
            gh_url = gh
        stars: int | None = None
        last_commit: str | None = None
        if sync_github and gh_url:
            or_ = _owner_repo(gh_url)
            if or_:
                stars, _open_issues, last_commit = _fetch_github_stats(or_[0], or_[1])

        cat = p.get("category", "side_project")
        atype = ArtifactType.HACKATHON if cat == "hackathon" else ArtifactType.SIDE_PROJECT

        artifacts.append(
            PortfolioArtifact.from_job_hunter(
                artifact_id=artifact_id,
                name=p["name"],
                artifact_type=atype,
                deployment_status=DeploymentStatus(p.get("status", "to_fill"))
                if p.get("status") in [e.value for e in DeploymentStatus]
                else DeploymentStatus.TO_FILL,
                source_file="portfolio-showcase.json",
                source_key=f"showcase_projects[{artifact_id}]",
                github_url=gh_url,
                live_url=p.get("live_url"),
                period_start=p.get("period"),
                has_to_fill=True,
                is_flagship=p.get("featured", False),
                tech_stack=p.get("tech_stack", []),
                skills_demonstrated=p.get("skills_demonstrated", []),
                github_stars=stars,
                github_last_commit=last_commit,
            )
        )

    return artifacts


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def import_artifact(
    sync_github: bool = typer.Option(
        False,
        "--sync-github",
        help="Also fetch GitHub stars and last-commit date for each artifact.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be imported without persisting."
    ),
    json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Import all artifacts from ``job_hunter/base/`` into PAV state.

    Reads ``hackathons-db.json`` and ``portfolio-showcase.json``, normalizes
    every hackathon, side-project, and work-experience entry, and writes
    them into ``~/.time-tasker/portfolio_artifacts.json``.

    Use ``--sync-github`` to also fetch GitHub stars and last-commit dates
    via the ``gh`` CLI (requires authentication: ``gh auth status``).
    """
    with trace_command(log, "portfolio.import", command="portfolio import") as ctx:
        try:
            base = _job_hunter_base()
        except FileNotFoundError as exc:
            console.print(f"[red]Error: {exc}[/red]")
            raise typer.Exit(1) from exc

        if not (base / "hackathons-db.json").exists():
            console.print(f"[red]Error: job_hunter base not found at {base}[/red]")
            console.print("Set the JOB_HUNTER_BASE env var to point to job_hunter/base/")
            raise typer.Exit(1)

        try:
            artifacts = _build_portfolio_artifacts(base, sync_github=sync_github)
        except Exception as exc:
            console.print(f"[red]Error reading job_hunter data: {exc}[/red]")
            raise typer.Exit(1) from exc

        if dry_run:
            console.print(f"[dim]Would import {len(artifacts)} artifacts from {base}[/dim]")
            for a in artifacts:
                console.print(f"  {a.id}  {a.artifact_type.value:<15} {a.name}")
            ctx.info("portfolio.dry_run", count=len(artifacts))
            return

        # Clear and repopulate — same semantics as demo seed
        portfolio_artifacts.clear()
        for a in artifacts:
            portfolio_artifacts.upsert(a)

        summary = {
            "total": len(artifacts),
            "by_type": {},
            "by_status": {},
            "has_github": sum(1 for a in artifacts if a.github_url),
            "flagships": sum(1 for a in artifacts if a.is_flagship),
            "has_gaps": sum(1 for a in artifacts if a.has_to_fill),
        }
        for a in artifacts:
            summary["by_type"][a.artifact_type.value] = (
                summary["by_type"].get(a.artifact_type.value, 0) + 1
            )
            summary["by_status"][a.deployment_status.value] = (
                summary["by_status"].get(a.deployment_status.value, 0) + 1
            )

        if json:
            typer.echo(format_as_json({"status": "imported", "summary": summary}))
        else:
            console.print(
                f"[green]✓[/green] Imported {len(artifacts)} portfolio artifacts into PAV state"
            )
            console.print(f"  By type: {summary['by_type']}")
            console.print(f"  By status: {summary['by_status']}")
            console.print(f"  With GitHub URLs: {summary['has_github']}")
            console.print(f"  Flagships: {summary['flagships']}")
            console.print(f"  With TO_FILL gaps: {summary['has_gaps']}")

        ctx.info("portfolio.imported", summary=summary)


@app.command()
def sync_github(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be synced without fetching."
    ),
    json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Sync GitHub stars and last-commit date for all artifacts that have a GitHub URL.

    Updates ``~/.time-tasker/portfolio_artifacts.json`` in place.
    Requires ``gh`` CLI authentication (``gh auth status``).
    """
    with trace_command(log, "portfolio.sync_github", command="portfolio sync-github") as ctx:
        all_data = portfolio_artifacts._store
        targets = [(eid, data) for eid, data in all_data.items() if data.get("github_url")]

        if not targets:
            console.print("[yellow]No artifacts with GitHub URLs found.[/yellow]")
            return

        if dry_run:
            for eid, data in targets:
                console.print(f"[dim]  Would sync {data['github_url']}[/dim]")
            return

        updated = 0
        errors = 0
        for eid, data in targets:
            or_ = _owner_repo(data["github_url"])
            if not or_:
                errors += 1
                continue
            stars, _, last_commit = _fetch_github_stats(or_[0], or_[1])
            # Reload latest from store (handles concurrent writes)
            latest = portfolio_artifacts.get(eid)
            if latest is None:
                continue
            updated_data = latest.model_dump(mode="json")
            updated_data["github_stars"] = stars
            updated_data["github_last_commit"] = last_commit
            updated_data["updated_at"] = datetime.now(tz=UTC).isoformat()
            portfolio_artifacts.upsert(PortfolioArtifact.model_validate(updated_data))
            updated += 1

        console.print(
            f"[green]✓[/green] Synced GitHub stats for {updated} artifacts ({errors} errors)"
        )
        ctx.info("portfolio.github_synced", updated=updated, errors=errors)


@app.command(name="show")
def show(
    type_filter: str | None = typer.Option(
        None, "--type", help="Filter by type: hackathon, side_project, work_experience."
    ),
    status_filter: str | None = typer.Option(
        None,
        "--status",
        help="Filter by status: deployed_production, completed, in_progress, to_fill.",
    ),
    json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Show all portfolio artifacts currently stored in PAV state."""
    with trace_command(log, "portfolio.show", command="portfolio show") as ctx:
        all_data = portfolio_artifacts._store

        if not all_data:
            console.print(
                "[yellow]No portfolio artifacts in PAV state. Run: portfolio import[/yellow]"
            )
            return

        artifacts = []
        for eid, data in all_data.items():
            try:
                artifacts.append(PortfolioArtifact.model_validate(data))
            except Exception:
                continue

        if type_filter:
            artifacts = [a for a in artifacts if a.artifact_type.value == type_filter]
        if status_filter:
            artifacts = [a for a in artifacts if a.deployment_status.value == status_filter]

        if json:
            typer.echo(
                format_as_json(
                    {
                        "total": len(artifacts),
                        "artifacts": [a.model_dump(mode="json") for a in artifacts],
                    }
                )
            )
            return

        table = Table(title=f"Portfolio Artifacts ({len(artifacts)})")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("Stars", justify="right")
        table.add_column("Last Commit")
        table.add_column("Flagship", justify="center")

        for a in artifacts:
            table.add_row(
                a.id,
                a.name,
                a.artifact_type.value,
                a.deployment_status.value,
                str(a.github_stars) if a.github_stars is not None else "—",
                a.github_last_commit or "—",
                "★" if a.is_flagship else "",
            )
        console.print(table)
        ctx.info("portfolio.show", total=len(artifacts))
