"""pav plan subcommand — bridges to PAE-Maintainer via subprocess.

This creates the NEW pav plan subcommand (T11 of agentic-markdown-system plan).

Bridge architecture (same pattern as sync_cmd.py):
  - operational does NOT import vibe-ops directly (standalone rule).
  - We invoke ``python -m agents.pae_maintainer`` (module mode) to avoid
    relative-import errors that occur with script-mode invocation.
  - The agent imports ``operational.constants`` for Q_HE + 5x3x3 constants,
    so we inject ``life-ops/operational/packages/core/src`` and
    ``vibe-ops/src`` onto the child's PYTHONPATH before launch.

Path resolution:
  plan_cmd.py lives at::
      life-ops/operational/apps/cli/src/operational/cli/commands/plan_cmd.py

  Eight levels up (parents[8]) is the repo root. From there::
      vibe-ops/src/agents/pae_maintainer/main.py
      life-ops/operational/packages/core/src  (operational package)
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

app = typer.Typer(help="Strategic planning via PAE-Maintainer agent.")
log = get_logger("plan_cmd")

# Path resolution (matches sync_cmd.py pattern: parents[8] is repo root).
_REPO_ROOT = Path(__file__).resolve().parents[8]
_OPERATIONAL_SRC = _REPO_ROOT / "life-ops" / "operational" / "packages" / "core" / "src"
_AGENTS_SRC = _REPO_ROOT / "vibe-ops" / "src" / "agents"


def _run_pae(cmd: str, args: list[str], json_out: bool) -> tuple[int, str]:
    """Invoke PAE-Maintainer via subprocess in module mode.

    Module mode (`python -m agents.pae_maintainer`) is required because
    pae_maintainer/main.py uses relative imports (`.state`, `.graph`, `.nodes`)
    which only resolve when the parent package (`agents`) is on the import
    path. Script-mode invocation crashes with ``ImportError: attempted
    relative import with no known parent package``.

    Returns (exit_code, stdout). The agent writes logs to stderr, which we
    forward unchanged so structured PAV telemetry from the child surfaces
    in the parent CLI session.

    The PYTHONPATH injection is safe — the only controlled input here
    is the hard-coded sibling location in the repo, not untrusted data.
    """
    full_args = [
        sys.executable,
        "-m",
        "agents.pae_maintainer",
        cmd,
        *args,
    ]
    if json_out:
        full_args.append("--json")

    # Build a PYTHONPATH that exposes both ``operational`` (for Q_HE constants)
    # and ``vibe-ops/src`` (so ``agents.pae_maintainer`` resolves as a package).
    child_env = dict(os.environ)
    extra_pp = [
        str(_OPERATIONAL_SRC),
        str(_AGENTS_SRC),
        str(_REPO_ROOT / "vibe-ops" / "src"),
    ]
    existing_pp = child_env.get("PYTHONPATH", "")
    parts = extra_pp + ([existing_pp] if existing_pp else [])
    child_env["PYTHONPATH"] = os.pathsep.join(parts)

    result = subprocess.run(  # noqa: S603
        full_args,
        capture_output=True,
        text=True,
        env=child_env,
        check=False,
    )
    # Forward child's stderr so structured PAV telemetry surfaces.
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode, result.stdout


def _parse_json_output(stdout: str) -> dict[str, Any] | list[Any] | None:
    """Try to parse stdout as JSON; return None on failure."""
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


@app.command(name="run")
def plan_run(
    once: bool = typer.Option(True, "--once/--loop", help="Run once or loop"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip DB checkpoint write"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    db: str = typer.Option("./vibe_ops.db", "--db", help="Path to SQLite DB"),
    cycle_id: str = typer.Option("default-cycle", "--cycle-id"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Run one PAE cycle (default) or loop continuously."""
    with trace_command(log, "plan.run", command="pav plan run") as ctx:
        args = ["--db", db, "--cycle-id", cycle_id]
        if dry_run:
            args.append("--dry-run")
        if verbose:
            args.append("--verbose")
        if once:
            exit_code, stdout = _run_pae("run", args, json_out)
        else:
            typer.echo("--loop not yet supported; use daemon command", err=True)
            raise typer.Exit(code=1)
        if json_out:
            parsed = _parse_json_output(stdout)
            if parsed is not None:
                typer.echo(format_as_json(parsed))
                ctx.info("plan.run.complete")
                return
        typer.echo(stdout, nl=False)
        if exit_code != 0:
            ctx.error("plan.run.failed")
            raise typer.Exit(code=exit_code)
        ctx.info("plan.run.complete")


@app.command(name="status")
def plan_status(
    db: str = typer.Option("./vibe_ops.db", "--db"),
    cycle_id: str = typer.Option("default-cycle", "--cycle-id"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show last persisted PAE state."""
    with trace_command(log, "plan.status", command="pav plan status") as ctx:
        exit_code, stdout = _run_pae(
            "status", ["--db", db, "--cycle-id", cycle_id], json_out
        )
        if json_out:
            parsed = _parse_json_output(stdout)
            if parsed is not None:
                typer.echo(format_as_json(parsed))
                ctx.info("plan.status.complete")
                return
        typer.echo(stdout, nl=False)
        if exit_code != 0:
            ctx.error("plan.status.failed")
            raise typer.Exit(code=exit_code)
        ctx.info("plan.status.complete")


@app.command(name="balance")
def plan_balance(
    db: str = typer.Option("./vibe_ops.db", "--db"),
    cycle_id: str = typer.Option("default-cycle", "--cycle-id"),
) -> None:
    """Show balance node output (workload vs capacity vs Q_HE)."""
    with trace_command(log, "plan.balance", command="pav plan balance") as ctx:
        exit_code, stdout = _run_pae(
            "balance", ["--db", db, "--cycle-id", cycle_id], False
        )
        typer.echo(stdout, nl=False)
        if exit_code != 0:
            ctx.error("plan.balance.failed")
            raise typer.Exit(code=exit_code)
        ctx.info("plan.balance.complete")