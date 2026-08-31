"""Typer CLI root for IKIGAi meta-brain.

All commands support `--json` for machine-readable output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure ikigai package is on path (required for ikigai.* imports)
_ikigai_src = Path(__file__).parent.parent
if str(_ikigai_src) not in sys.path:
    sys.path.insert(0, str(_ikigai_src))
from typing import Any  # noqa: E402

import typer  # noqa: E402
from rich.console import Console  # noqa: E402

from ikigai.__init__ import __version__  # noqa: E402
from ikigai.constants import NSM  # noqa: E402
from ikigai.propagation.markdown_db import MarkdownDB  # noqa: E402
from ikigai.propagation.sqlite_adapter import SQLiteAdapter  # noqa: E402

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
    vault: Path | None = typer.Option(  # noqa: B008  Typer convention: Option in default
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
    """Compute all 5 vector scores.

    ARCHIVED per attribution §3 — vector score math is the algorithm
    layer's responsibility, not the CLI/agent layer's. Function and
    options retained for documentation; raises when invoked so callers
    know to use a different surface (algorithm package directly).
    """
    raise NotImplementedError(
        "vector score math archived per attribution §3 — "
        "see ikigai.core.scoring.vector_scores for the canonical implementation"
    )


@vector_app.command("meta")
def vector_meta(
    ctx: typer.Context,
    passion: float = typer.Option(50.0),
    skill: float = typer.Option(50.0),
    market: float = typer.Option(50.0),
    revenue: float = typer.Option(50.0),
    course: float = typer.Option(50.0),
) -> None:
    """Compute meta-vetor (hybrid: geo + harmonic).

    ARCHIVED per attribution §3 — meta-vetor math is the algorithm
    layer's responsibility, not the CLI/agent layer's. Function and
    options retained for documentation; raises when invoked.
    """
    raise NotImplementedError(
        "meta-vector math archived per attribution §3 — "
        "see ikigai.core.scoring.meta_vector for the canonical implementation"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan commands
# ─────────────────────────────────────────────────────────────────────────────


@plan_app.command("list")
def plan_list(
    ctx: typer.Context,
    entity_type: str = typer.Option(
        "dream", help="Entity type: dream|goal|objective|project|task|deliverable"
    ),
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
    """Show current regime decision from Q_HE + completion.

    ARCHIVED per attribution §3 — regime heuristics (PUSH/MAINTAIN/REDUCE/RECOVER
    with hysteresis) are the algorithm layer's responsibility, not the CLI/agent
    layer's. Function and options retained for documentation; raises when invoked.
    """
    raise NotImplementedError(
        "regime heuristics archived per attribution §3 — "
        "see ikigai.core.heuristics.regime for the canonical implementation"
    )


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
    """Show phase decision from IKIGAi score + revenue + momentum.

    ARCHIVED per attribution §3 — phase-pivot heuristics (warmup → compounding
    → meta → mastery) are the algorithm layer's responsibility, not the
    CLI/agent layer's. Function and options retained for documentation;
    raises when invoked.
    """
    raise NotImplementedError(
        "phase-pivot heuristics archived per attribution §3 — "
        "see ikigai.core.heuristics.phase_pivot for the canonical implementation"
    )


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
        _err(
            "--prefer sqlite not yet implemented (destructive; use with caution)",
            code="ERR_CLI_501",
        )
    else:  # merge
        # Generate triagem.md
        from ikigai.propagation.triagem import DriftEntry, Triagem

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
        data = {
            "action": "merge",
            "triagem_path": str(triagem_path),
            "drift_entries": len(triagem.entries),
        }

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


@sync_app.command("vault-to-taskdog")
def sync_vault_to_taskdog(
    ctx: typer.Context,
    vault_root: Path = typer.Option(  # noqa: B008  Typer convention: Option in default
        Path("vault"),
        "--vault",
        help="Path to vault root directory.",
    ),
    state_path: Path = typer.Option(  # noqa: B008  Typer convention: Option in default
        Path("data/sync-state.json"),
        "--state",
        help="Path to sync state file.",
    ),
) -> None:
    """Sync vault frontmatter-tagged tasks → taskdog via MCP.

    Incremental, idempotent. Only syncs files where frontmatter has
    ``tags: [task]`` or ``type: task``. Skips drafts, MOCs, evidence,
    strategics. Run ``ikigai sync vault-to-taskdog --help`` for options.
    """
    from ikigai.gateway.clients.taskdog import taskdog_adapter
    from ikigai.vault.sync import run_sync

    adapter = taskdog_adapter()
    result = run_sync(
        vault_root=vault_root,
        state_path=state_path,
        adapter=adapter,
    )
    _output(result.model_dump(mode="json"), ctx.obj.get("json_out", False))


@sync_app.command("vault-from-taskdog")
def sync_vault_from_taskdog(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show diff, don't emit events",
    ),
    state_file: Path = typer.Option(  # noqa: B008  Typer convention: Option in default
        Path("data/sync-state-reverse.json"),
        "--state-file",
        help="Reverse sync snapshot path",
    ),
) -> None:
    """Read taskdog state, diff vs snapshot, emit TaskChange to review_queue.

    Run this to push fork-side changes back into the agent review path.
    """
    from mesh.adapters.taskdog import TaskdogAdapter

    from ikigai.vault.sync import reverse_sync

    adapter = TaskdogAdapter()

    if dry_run:
        typer.echo("[dry-run] would reverse-sync from taskdog")
        typer.echo(f"[dry-run] state file: {state_file}")
        # Show current taskdog state for preview
        tasks = adapter.list_all()
        typer.echo(f"[dry-run] {len(tasks)} tasks in taskdog")
        return

    result = reverse_sync(
        state_path=state_file,
        adapter=adapter,
        source_fork="taskdog",
    )
    _output(result.model_dump(mode="json"), ctx.obj.get("json_out", False))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────


def main_entry() -> None:
    """Console script entry point (called by pyproject.toml [tool.poetry.scripts])."""
    app()


if __name__ == "__main__":
    main_entry()
