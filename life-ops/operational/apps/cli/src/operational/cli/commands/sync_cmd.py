"""pav sync subcommand — bridges to vibe-ops vault_sync via subprocess.

operational is standalone — does NOT import vibe-ops directly. This
subcommand invokes ``python -m scripts.vault_sync`` (module mode) and
forwards JSON output to stdout.

Subcommands:
  - vault       Sync vault .md frontmatter -> SQLite planning_entities
  - code        Sync SQLite computed fields -> vault + evaluate hypotheses
  - all         Run vault and code in sequence
  - status      Show entity counts, last sync timestamps, conflict summary
  - conflicts   Print .sync-conflicts.md content

All subcommands support --json per repo convention.

Source: .omo/plans/vault-bidirectional-sync.md (T8)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import typer

from operational.cli.formatters import format_as_json
from operational.cli.telemetry import get_logger, trace_command

__all__ = ["app"]

app = typer.Typer(
    help="Bidirectional sync between Obsidian vault and vibe-ops engine.",
    no_args_is_help=True,
)
log = get_logger("sync_cmd")

# Path resolution: sync_cmd.py lives at life-ops/operational/apps/cli/src/
# operational/cli/commands/sync_cmd.py. Eight levels up is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[8]
_VIBE_OPS_SRC = _REPO_ROOT / "vibe-ops" / "src"


def _run_vault_sync(
    subcmd: str,
    vault: str,
    db: str,
    json_out: bool,
) -> tuple[int, str]:
    args = ["--vault", vault, "--db", db, subcmd]
    if json_out:
        args.append("--json")

    full_args = [sys.executable, "-m", "scripts.vault_sync", *args]

    child_env = dict(os.environ)
    child_env.pop("PYTHONPATH", None)
    extra_pp = [str(_VIBE_OPS_SRC)]
    child_env["PYTHONPATH"] = os.pathsep.join(extra_pp)

    result = subprocess.run(  # noqa: S603
        full_args,
        capture_output=True,
        text=True,
        env=child_env,
        cwd=str(_VIBE_OPS_SRC),
        check=False,
    )
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode, result.stdout


def _parse_json_output(stdout: str) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


@app.command(name="vault")
def sync_vault(
    vault: str = typer.Option(..., "--vault", help="Path to Obsidian vault"),
    db: str = typer.Option("./vibe_ops.db", "--db", help="Path to SQLite DB"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Sync vault .md frontmatter -> SQLite planning_entities."""
    with trace_command(log, "sync.vault", command="pav sync vault") as ctx:
        exit_code, stdout = _run_vault_sync("vault", vault, db, json_out)
        if json_out:
            parsed = _parse_json_output(stdout)
            if parsed is not None:
                typer.echo(format_as_json(parsed))
                ctx.info("sync.vault.complete")
                return
        typer.echo(stdout, nl=False)
        if exit_code != 0:
            ctx.error("sync.vault.failed")
            raise typer.Exit(code=exit_code)
        ctx.info("sync.vault.complete")


@app.command(name="code")
def sync_code(
    vault: str = typer.Option(..., "--vault", help="Path to Obsidian vault"),
    db: str = typer.Option("./vibe_ops.db", "--db", help="Path to SQLite DB"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Sync SQLite computed fields -> vault + evaluate hypotheses."""
    with trace_command(log, "sync.code", command="pav sync code") as ctx:
        exit_code, stdout = _run_vault_sync("code", vault, db, json_out)
        if json_out:
            parsed = _parse_json_output(stdout)
            if parsed is not None:
                typer.echo(format_as_json(parsed))
                ctx.info("sync.code.complete")
                return
        typer.echo(stdout, nl=False)
        if exit_code != 0:
            ctx.error("sync.code.failed")
            raise typer.Exit(code=exit_code)
        ctx.info("sync.code.complete")


@app.command(name="all")
def sync_all(
    vault: str = typer.Option(..., "--vault", help="Path to Obsidian vault"),
    db: str = typer.Option("./vibe_ops.db", "--db", help="Path to SQLite DB"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Run vault and code syncs in sequence."""
    with trace_command(log, "sync.all", command="pav sync all") as ctx:
        exit_code, stdout = _run_vault_sync("all", vault, db, json_out)
        if json_out:
            parsed = _parse_json_output(stdout)
            if parsed is not None:
                typer.echo(format_as_json(parsed))
                ctx.info("sync.all.complete")
                return
        typer.echo(stdout, nl=False)
        if exit_code != 0:
            ctx.error("sync.all.failed")
            raise typer.Exit(code=exit_code)
        ctx.info("sync.all.complete")


@app.command(name="status")
def sync_status(
    vault: str | None = typer.Option(None, "--vault", help="Vault path (optional)"),
    db: str = typer.Option("./vibe_ops.db", "--db", help="Path to SQLite DB"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show entity counts, last sync timestamps, and tracked files."""
    with trace_command(log, "sync.status", command="pav sync status") as ctx:
        exit_code, stdout = _run_vault_sync("status", vault or "", db, json_out)
        if json_out:
            parsed = _parse_json_output(stdout)
            if parsed is not None:
                typer.echo(format_as_json(parsed))
                ctx.info("sync.status.complete")
                return
        typer.echo(stdout, nl=False)
        if exit_code != 0:
            ctx.error("sync.status.failed")
            raise typer.Exit(code=exit_code)
        ctx.info("sync.status.complete")


@app.command(name="conflicts")
def sync_conflicts(
    vault: str = typer.Option(..., "--vault", help="Path to Obsidian vault"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Print .sync-conflicts.md content."""
    with trace_command(log, "sync.conflicts", command="pav sync conflicts") as ctx:
        exit_code, stdout = _run_vault_sync("conflicts", vault, "./vibe_ops.db", json_out)
        if json_out:
            parsed = _parse_json_output(stdout)
            if parsed is not None:
                typer.echo(format_as_json(parsed))
                ctx.info("sync.conflicts.complete")
                return
        typer.echo(stdout, nl=False)
        if exit_code != 0:
            ctx.error("sync.conflicts.failed")
            raise typer.Exit(code=exit_code)
        ctx.info("sync.conflicts.complete")