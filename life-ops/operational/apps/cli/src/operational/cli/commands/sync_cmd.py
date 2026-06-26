"""Sync CLI commands — wraps vibe-ops PeriodReportSync via subprocess.

This module bridges operational's CLI to vibe-ops' PeriodReportSync.
Per plan guardrail, operational does NOT import vibe-ops directly; instead,
this module invokes ``vibe-ops/src/cli/period_sync_cli.py`` as a subprocess.

Path resolution: ``sync_cmd.py`` lives at::

    life-ops/operational/apps/cli/src/operational/cli/commands/sync_cmd.py

Eight levels up (``parents[8]``) is the repo root. From there,
``vibe-ops/src`` is one path join away.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import typer

from operational.cli.formatters import format_as_json
from operational.cli.telemetry import get_logger, trace_command

__all__ = ["app"]

app = typer.Typer(help="Sync vault period reports with vibe_ops.db.")
log = get_logger("sync_cmd")

# Eight parents up: commands/ → cli/ → operational/ → src/ → cli/ → apps/ →
# operational/ → life-ops/ → <repo-root>. From the repo root we join
# ``vibe-ops/src`` to reach the script we invoke.
_VIBE_OPS_SRC = Path(__file__).resolve().parents[8] / "vibe-ops" / "src"
_PERIOD_SYNC_SCRIPT = _VIBE_OPS_SRC / "cli" / "period_sync_cli.py"


def _run_period_cli(cmd: str, args: list[str], json_out: bool) -> tuple[int, str, str]:
    """Invoke ``vibe-ops/src/cli/period_sync_cli.py`` as a subprocess.

    Returns (exit_code, stdout, stderr).

    The script path is a hard-coded sibling location in the repo, so the
    subprocess call does not consume untrusted input — safe to ignore
    S603 / PLW1510 here.
    """
    full_args = [
        sys.executable,
        str(_PERIOD_SYNC_SCRIPT),
        cmd,
        *args,
    ]
    if json_out:
        full_args.append("--json")
    result = subprocess.run(full_args, capture_output=True, text=True, check=False)  # noqa: S603
    return result.returncode, result.stdout, result.stderr


def _parse_json_output(stdout: str) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


@app.command(name="vault")
def sync_vault(
    folder: str = typer.Option("_templates_periodos", "--folder", "-f"),
    vault: str = typer.Option(..., "--vault", help="Path to vault"),
    db: str = typer.Option("./vibe_ops.db", "--db", help="Path to SQLite DB"),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Sync period reports from vault to vibe_ops.db."""
    with trace_command(log, "sync.vault", command="pav sync vault") as ctx:
        vault_path = Path(vault).resolve()
        db_path = Path(db).resolve()
        exit_code, stdout, _stderr = _run_period_cli(
            "sync",
            ["--vault", str(vault_path), "--db", str(db_path), "--folder", folder],
            json_out,
        )
        if json_out:
            parsed = _parse_json_output(stdout)
            if parsed is not None:
                typer.echo(format_as_json(parsed))
                ctx.info("sync.vault.complete", **parsed)
                return
        typer.echo(stdout, nl=False)
        if exit_code != 0:
            ctx.error("sync.vault.failed")
            raise typer.Exit(code=exit_code)
        ctx.info("sync.vault.complete")


@app.command(name="list")
def sync_list(
    period: str | None = typer.Option(None, "--period", help="Filter by period"),
    db: str = typer.Option("./vibe_ops.db", "--db", help="Path to SQLite DB"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List recent period reports."""
    with trace_command(log, "sync.list", command="pav sync list") as ctx:
        db_path = Path(db).resolve()
        args = ["--db", str(db_path), "--limit", str(limit)]
        if period:
            args.extend(["--period", period])
        exit_code, stdout, _stderr = _run_period_cli("list", args, json_out)  # noqa: RUF059
        if json_out:
            parsed = _parse_json_output(stdout)
            if parsed is not None:
                typer.echo(format_as_json(parsed))
                ctx.info("sync.listed", count=len(parsed))
                return
        typer.echo(stdout, nl=False)
        ctx.info("sync.listed")


@app.command(name="hierarchy")
def sync_hierarchy(
    sonho: str = typer.Option(..., "--sonho", help="Sonho ID"),
    vault: str = typer.Option(..., "--vault", help="Path to vault"),
    db: str = typer.Option("./vibe_ops.db", "--db", help="Path to SQLite DB"),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show hierarchy tree for a sonho."""
    with trace_command(log, "sync.hierarchy", command="pav sync hierarchy") as ctx:
        vault_path = Path(vault).resolve()
        db_path = Path(db).resolve()
        args = ["--vault", str(vault_path), "--db", str(db_path), "--sonho", sonho]
        exit_code, stdout, _stderr = _run_period_cli("hierarchy", args, json_out)  # noqa: RUF059
        if json_out:
            parsed = _parse_json_output(stdout)
            if parsed is not None:
                typer.echo(format_as_json(parsed))
                ctx.info("sync.hierarchy.complete", count=parsed.get("count", 0))
                return
        typer.echo(stdout, nl=False)
        ctx.info("sync.hierarchy.complete")

