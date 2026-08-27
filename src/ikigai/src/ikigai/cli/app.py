"""Typer CLI root for IKIGAi meta-brain.

All commands support `--json` for machine-readable output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from ikigai.__init__ import __version__
from ikigai.constants import NSM
from ikigai.propagation.markdown_db import MarkdownDB
from ikigai.propagation.sqlite_adapter import SQLiteAdapter

app = typer.Typer(
    name="ikigai",
    help="IKIGAi meta-brain — standalone, local-first, deterministic.",
    no_args_is_help=True,
    add_completion=False,
)

vector_app = typer.Typer(help="Manage IKIGAi vectors.")
profile_app = typer.Typer(help="Manage IKIGAi profiles.")
plan_app = typer.Typer(help="Manage plan entities (Dream → Deliverable).")
regime_app = typer.Typer(help="Manage regime decisions.")
phase_app = typer.Typer(help="Manage phase decisions.")
sync_app = typer.Typer(help="Sync between markdown and SQLite.")

app.add_typer(vector_app, name="vector")
app.add_typer(profile_app, name="profile")
app.add_typer(plan_app, name="plan")
app.add_typer(regime_app, name="regime")
app.add_typer(phase_app, name="phase")
app.add_typer(sync_app, name="sync")

console = Console()
err_console = Console(stderr=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _output(data: Any, as_json: bool, success: bool = True) -> None:
    """Print either JSON or human-readable output."""
    if as_json:
        payload = {"ok": success, "data": data}
        typer.echo(json.dumps(payload, indent=2, default=str, ensure_ascii=False))
    else:
        if isinstance(data, list):
            for item in data:
                typer.echo(str(item))
        elif isinstance(data, dict):
            for k, v in data.items():
                typer.echo(f"{k}: {v}")
        else:
            typer.echo(str(data))


def _err(message: str, code: str = "ERR_CLI_001") -> None:
    """Print error as JSON or human."""
    payload = {"ok": False, "error": {"code": code, "message": message}}
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False), err=True)
    raise typer.Exit(code=1)


def _get_db(ctx: typer.Context) -> MarkdownDB:
    """Resolve MarkdownDB from context or create with default path."""
    vault = ctx.obj.get("vault_root") if ctx.obj else None
    if vault is None:
        vault = Path.home() / "ikigai-vault"
    return MarkdownDB(vault)


def _get_sqlite(ctx: typer.Context, db: MarkdownDB) -> SQLiteAdapter:
    """Resolve SQLiteAdapter."""
    sqlite_path = ctx.obj.get("sqlite_path") if ctx.obj else None
    if sqlite_path is None:
        sqlite_path = db.vault_root / "meta" / "ikigai_mirror.db"
    return SQLiteAdapter(sqlite_path)


# ─────────────────────────────────────────────────────────────────────────────
# Root command
# ─────────────────────────────────────────────────────────────────────────────


@app.callback()
def main(
    ctx: typer.Context,
    vault: Path | None = typer.Option(
        None,
        "--vault",
        "-V",
        help="Vault root directory (default: ~/ikigai-vault).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output JSON instead of human-readable text.",
    ),
) -> None:
    """IKIGAi meta-brain."""
    ctx.ensure_object(dict)
    ctx.obj["vault_root"] = vault
    ctx.obj["json_out"] = json_out


@app.command("version")
def version_cmd(
    ctx: typer.Context,
) -> None:
    """Print IKIGAi version + NSM constants."""
    data = {
        "version": __version__,
        "nsm": {
            "lambda": NSM.LAMBDA,
            "rho": NSM.RHO,
            "wave_days": NSM.WAVE_DAYS,
            "cycle_days": NSM.CYCLE_DAYS,
            "phase_days": NSM.PHASE_DAYS,
            "qhe_push": NSM.Q_HE_PUSH,
            "qhe_reduce": NSM.Q_HE_REDUCE,
            "qhe_recover": NSM.Q_HE_RECOVER,
            "meta_vetor_w_geo": NSM.META_VETOR_W_GEO,
            "meta_vetor_w_harm": NSM.META_VETOR_W_HARM,
        },
    }
    _output(data, ctx.obj.get("json_out", False))


@app.command("health")
def health_cmd(
    ctx: typer.Context,
) -> None:
    """Health check: vault exists, SQLite reachable, NSM loaded."""
    db = _get_db(ctx)
    sqlite = _get_sqlite(ctx, db)
    data = {
        "vault_root": str(db.vault_root),
        "vault_exists": db.vault_root.exists(),
        "sqlite_path": str(sqlite.db_path),
        "sqlite_ok": sqlite.db_path.exists(),
        "nsm_loaded": True,
    }
    _output(data, ctx.obj.get("json_out", False))


# ─────────────────────────────────────────────────────────────────────────────
# Vector commands
# ─────────────────────────────────────────────────────────────────────────────


@vector_app.command("list")
def vector_list(
    ctx: typer.Context,
) -> None:
    """List all 5 canonical IKIGAi vectors."""
    from ikigai.enums import VectorType

    data = [
        {
            "name": v.value,
            "is_external": v.is_external,
        }
        for v in VectorType
    ]
    _output(data, ctx.obj.get("json_out", False))


@vector_app.command("score")
def vector_score(
    ctx: typer.Context,
    passion_streak: float = typer.Option(0.0, help="Passion streak in days."),
    skill_levels: str = typer.Option("", help="Comma-separated skill level scores (0-100)."),
    skill_demands: str = typer.Option("", help="Comma-separated market demand weights (0-100)."),
    skill_momentum: float = typer.Option(0.0, help="Learning momentum (0-100)."),
    skill_completion: float = typer.Option(0.0, help="Project completion (0-100)."),
    market_fit: float = typer.Option(50.0, help="Fit average (0-100)."),
    market_demand: float = typer.Option(50.0, help="Skills demand avg (0-100)."),
    market_pipeline: float = typer.Option(50.0, help="Opportunities pipeline (0-100)."),
    revenue_actual: float = typer.Option(0.0, help="Revenue actual (BRL)."),
    revenue_target: float = typer.Option(1000.0, help="Revenue target (BRL)."),
    revenue_health: float = typer.Option(50.0, help="Pipeline health (0-100)."),
    course_attendance: float = typer.Option(80.0, help="Course attendance rate (0-100)."),
    course_assignments: float = typer.Option(80.0, help="Assignments on-time (0-100)."),
    course_exams: float = typer.Option(75.0, help="Exam average (0-100)."),
) -> None:
    """Compute all 5 vector scores."""
    from ikigai.core.scoring.vector_scores import compute_vector_scores

    skills = [float(x) for x in skill_levels.split(",") if x.strip()] or [50.0]
    demands = [float(x) for x in skill_demands.split(",") if x.strip()] or [50.0]

    scores = compute_vector_scores(
        passion_streak_days=passion_streak,
        skill_inputs=(skills, demands, skill_momentum, skill_completion),
        market_inputs=(market_fit, market_demand, market_pipeline),
        revenue_inputs=(revenue_actual, revenue_target, revenue_health),
        course_inputs=(course_attendance, course_assignments, course_exams),
    )

    data = {v.value: {"value": s.value, "unit": s.unit} for v, s in scores.items()}
    _output(data, ctx.obj.get("json_out", False))


@vector_app.command("meta")
def vector_meta(
    ctx: typer.Context,
    passion: float = typer.Option(50.0),
    skill: float = typer.Option(50.0),
    market: float = typer.Option(50.0),
    revenue: float = typer.Option(50.0),
    course: float = typer.Option(50.0),
) -> None:
    """Compute meta-vetor (hybrid: geo + harmonic)."""
    from ikigai.core.scoring.meta_vector import meta_vector, compute_alignment_label
    from ikigai.enums import VectorType

    scores = {
        VectorType.PASSION: __import__("ikigai.types", fromlist=["ScoreValue"]).ScoreValue(value=passion, unit="percent"),
        VectorType.SKILL: __import__("ikigai.types", fromlist=["ScoreValue"]).ScoreValue(value=skill, unit="percent"),
        VectorType.MARKET: __import__("ikigai.types", fromlist=["ScoreValue"]).ScoreValue(value=market, unit="percent"),
        VectorType.REVENUE: __import__("ikigai.types", fromlist=["ScoreValue"]).ScoreValue(value=revenue, unit="percent"),
        VectorType.COURSE: __import__("ikigai.types", fromlist=["ScoreValue"]).ScoreValue(value=course, unit="percent"),
    }
    weights = {
        VectorType.PASSION: 0.15,
        VectorType.SKILL: 0.40,
        VectorType.MARKET: 0.15,
        VectorType.REVENUE: 0.10,
        VectorType.COURSE: 0.20,
    }

    meta = meta_vector(scores, weights)
    label = compute_alignment_label(meta)

    data = {
        "meta_vector": {"value": meta.value, "unit": meta.unit},
        "alignment_label": label.value,
    }
    _output(data, ctx.obj.get("json_out", False))


# ─────────────────────────────────────────────────────────────────────────────
# Plan commands
# ─────────────────────────────────────────────────────────────────────────────


@plan_app.command("list")
def plan_list(
    ctx: typer.Context,
    entity_type: str = typer.Option("dream", help="Entity type: dream|goal|objective|project|task|deliverable"),
    status: str | None = typer.Option(None, help="Filter by status."),
) -> None:
    """List plan entities of a given type."""
    from ikigai.enums import EntityType

    try:
        etype = EntityType(entity_type)
    except ValueError:
        _err(f"Invalid entity_type: {entity_type}")

    db = _get_db(ctx)
    entities = db.query(entity_type=etype, status=status)
    data = [
        {
            "ueid": str(e.ueid),
            "slug": e.slug,
            "title": e.title,
            "status": e.status.value,
            "horizon_days": e.horizon_days,
        }
        for e in entities
    ]
    _output(data, ctx.obj.get("json_out", False))


@plan_app.command("show")
def plan_show(
    ctx: typer.Context,
    entity_type: str = typer.Option(..., help="Entity type."),
    slug: str = typer.Option(..., help="Slug."),
) -> None:
    """Show a single plan entity by type + slug."""
    from ikigai.enums import EntityType
    from ikigai.exceptions import MarkdownParseError

    try:
        etype = EntityType(entity_type)
    except ValueError:
        _err(f"Invalid entity_type: {entity_type}")

    db = _get_db(ctx)
    path = db.find_by_slug(etype, slug)
    if not path:
        _err(f"Not found: {entity_type}/{slug}", code="ERR_CLI_404")
    try:
        entity = db.read(path)
    except MarkdownParseError as e:
        _err(str(e), code="ERR_IO_001")

    data = entity.to_frontmatter_dict()
    data["source_md_path"] = str(data.get("source_md_path", ""))
    _output(data, ctx.obj.get("json_out", False))


@plan_app.command("query")
def plan_query(
    ctx: typer.Context,
    ikigai_vector: str | None = typer.Option(None, help="Filter by IKIGAi vector (e.g., 'skill')."),
    needs_review_days: int | None = typer.Option(None, help="Entities not reviewed in N days."),
) -> None:
    """Dynamic query across the vault."""
    db = _get_db(ctx)
    entities = db.query(
        ikigai_vector=ikigai_vector,
        needs_review_days=needs_review_days,
    )
    data = [
        {
            "ueid": str(e.ueid),
            "entity_type": e.entity_type.value,
            "slug": e.slug,
            "title": e.title,
            "status": e.status.value,
            "ikigai_vectors": [v.value for v in e.ikigai_vectors],
        }
        for e in entities
    ]
    _output(data, ctx.obj.get("json_out", False))


# ─────────────────────────────────────────────────────────────────────────────
# Regime commands
# ─────────────────────────────────────────────────────────────────────────────


@regime_app.command("status")
def regime_status(
    ctx: typer.Context,
    qhe: float = typer.Option(..., help="Q_HE 7d average (0-1)."),
    c_comp: float = typer.Option(1.0, help="Completion ratio 24h (0-1)."),
    infractions: int = typer.Option(0, help="Infractions in 24h."),
    sleep_debt: float = typer.Option(0.0, help="Sleep debt in hours."),
) -> None:
    """Show current regime decision from Q_HE + completion."""
    from ikigai.core.heuristics.regime import compute_regime

    decision = compute_regime(
        qhe_7d_avg=qhe,
        c_comp_24h=c_comp,
        infractions_24h=infractions,
        sleep_debt_h=sleep_debt,
    )
    data = {
        "regime": decision.regime.value,
        "rationale": decision.rationale,
        "qhe_score": decision.qhe_score,
        "c_comp_score": decision.c_comp_score,
        "infractions": decision.infractions,
        "sleep_debt_h": decision.sleep_debt_h,
        "raw_score": decision.raw_score,
        "setpoints": {
            "hardwork_budget_h": decision.regime.hardwork_budget_h,
            "pause_min": decision.regime.pause_min,
            "sleep_target_h": decision.regime.sleep_target_h,
            "qhe_target": decision.regime.qhe_target,
            "c_comp_target": decision.regime.c_comp_target,
        },
    }
    _output(data, ctx.obj.get("json_out", False))


# ─────────────────────────────────────────────────────────────────────────────
# Phase commands
# ─────────────────────────────────────────────────────────────────────────────


@phase_app.command("status")
def phase_status(
    ctx: typer.Context,
    ikigai_score: float = typer.Option(..., help="IKIGAi meta-vetor score (0-100)."),
    revenue_actual: float = typer.Option(0.0, help="Revenue actual 30d (BRL)."),
    revenue_target: float = typer.Option(1000.0, help="Revenue target (BRL)."),
    opportunities: int = typer.Option(0, help="Opportunities pursuing."),
    cognitive_debt: float = typer.Option(0.0, help="Cognitive debt (0-10+)."),
) -> None:
    """Show phase decision from IKIGAi score + revenue + momentum."""
    from ikigai.core.heuristics.phase_pivot import compute_phase

    decision = compute_phase(
        ikigai_score=ikigai_score,
        revenue_actual_30d=revenue_actual,
        revenue_target=revenue_target,
        opportunities_pursuing=opportunities,
        cognitive_debt=cognitive_debt,
    )
    data = {
        "phase": decision.phase.value,
        "ikigai_score": decision.ikigai_score,
        "momentum": decision.momentum,
        "iterations": decision.iterations,
        "converged": decision.converged,
        "weights": {k.value: v for k, v in decision.weights.items()},
        "rationale": decision.rationale,
    }
    _output(data, ctx.obj.get("json_out", False))


# ─────────────────────────────────────────────────────────────────────────────
# Sync commands
# ─────────────────────────────────────────────────────────────────────────────


@sync_app.command("run")
def sync_run(
    ctx: typer.Context,
    prefer: str = typer.Option(
        "markdown",
        "--prefer",
        help="Preference: markdown | sqlite | merge",
    ),
) -> None:
    """Sync markdown vault ↔ SQLite mirror."""
    if prefer not in ("markdown", "sqlite", "merge"):
        _err(f"Invalid --prefer value: {prefer}. Must be markdown|sqlite|merge.")

    db = _get_db(ctx)
    sqlite = _get_sqlite(ctx, db)

    if prefer == "markdown":
        # Rebuild SQLite from markdown vault
        count = 0
        for path in db.list_all():
            try:
                entity = db.read(path)
                # Check if already exists; if not, insert
                existing = sqlite.get_by_ueid(str(entity.ueid))
                if not existing:
                    sqlite.insert(entity)
                    count += 1
            except Exception:
                continue
        data = {"action": "markdown→sqlite", "inserted": count, "skipped": "existing"}
    elif prefer == "sqlite":
        # Write SQLite state back to markdown (destructive to vault)
        _err("--prefer sqlite not yet implemented (destructive; use with caution)", code="ERR_CLI_501")
    else:  # merge
        # Generate triagem.md
        from ikigai.propagation.triagem import Triagem, DriftEntry

        triagem = Triagem(vault_root=db.vault_root)
        for path in db.list_all():
            try:
                entity = db.read(path)
                md_mtime = path.stat().st_mtime
                sqlite_mtime = sqlite.mtime_for(str(entity.ueid))
                from datetime import datetime, timezone

                md_dt = datetime.fromtimestamp(md_mtime, tz=timezone.utc)
                sqlite_dt = sqlite_mtime
                if sqlite_dt is None:
                    triagem.add(
                        DriftEntry(
                            timestamp=md_dt,
                            entity_ueid=str(entity.ueid),
                            entity_path=path,
                            markdown_mtime=md_dt,
                            sqlite_mtime=None,
                            drift_kind="missing_sqlite",
                            decision="needs_sqlite_insert",
                        )
                    )
                elif abs((md_dt - sqlite_dt).total_seconds()) > 300:  # 5 min drift
                    triagem.add(
                        DriftEntry(
                            timestamp=max(md_dt, sqlite_dt),
                            entity_ueid=str(entity.ueid),
                            entity_path=path,
                            markdown_mtime=md_dt,
                            sqlite_mtime=sqlite_dt,
                            drift_kind="drift_detected",
                            decision="needs_reconciliation",
                        )
                    )
            except Exception:
                continue
        triagem_path = triagem.write()
        data = {"action": "merge", "triagem_path": str(triagem_path), "drift_entries": len(triagem.entries)}

    _output(data, ctx.obj.get("json_out", False))


@sync_app.command("index")
def sync_index(
    ctx: typer.Context,
) -> None:
    """Build a JSON index of the vault for cross-DB queries."""
    db = _get_db(ctx)
    path = db.index_save()
    data = {"index_path": str(path), "vault_root": str(db.vault_root)}
    _output(data, ctx.obj.get("json_out", False))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────


def main_entry() -> None:
    """Console script entry point (called by pyproject.toml [tool.poetry.scripts])."""
    app()


if __name__ == "__main__":
    main_entry()
