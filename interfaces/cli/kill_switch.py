"""W5.3 — KillSwitch consumer UX CLI (status / history / pause / resume/recover).

Pure consumer of `sys_ikigai.security.kill_switch`. Per design doc
`code-docs/design/w5-3-kill-switch-ux.md`:

  - No new schema in src/contracts/ (audit entry validated by a local
    Pydantic v2 strict model in `_kill_switch_helpers.py`).
  - No new constants (algorithm_constants.json stays untouched).
  - No new drift invariant (W5.3 is pure consumer).
  - activation lives in `sys_ikigai/security/kill_switch.py` only — the
    CLI never programmatically sets the kill switch (R5/R11 forbid it).

V5-F (2026-09-07 "Opção B-A — radical-máxima") inlined the render + action
helpers (formerly `_kill_switch_render.py` + `_kill_switch_actions.py`)
back into this module — those modules are now deleted. Audit / history /
atomic write / path helpers still live in `_kill_switch_helpers.py` (pure
infrastructure, no CLI logic).

State matrix (from design doc §3.5):
  is_active=false → status: exit 0 / pause: exit 0 no-op / resume: exit 0 no-op
  env_var active  → status: exit 1 / pause: exit 1 refuses / resume: exit 0 with --confirm
  vault_file      → status: exit 1 / pause: exit 1 refuses / resume: exit 0 with --confirm
  data_file       → status: exit 1 / pause: exit 0 writes data/.kill_switch
                     / resume: exit 0 with --confirm
  multiple        → exit 1 reports priority 1 reason; pause refuses;
                     resume clears all 3 with --confirm

Exit codes (per design §3.5):
  0 — success or no-op
  1 — kill switch active (status) or refused state (pause/resume)
  2 — resume refused without --confirm
  3 — resume/pause refused with empty --reason
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Callable

import typer
from rich.console import Console
from rich.table import Table

from sys_ikigai.security.kill_switch import (
    DATA_KILL_SWITCH_FILENAME,
    ENV_VAR_NAME,
    VAULT_KILL_SWITCH_FILENAME,
    build_kill_switch_event,
    check_kill_switch,
    fire_kill_switch,
    recover_kill_switch,
)

from ._kill_switch_helpers import (
    append_audit_entry,
    compute_rate_limit,
    read_kill_switch_history,
    repo_root,
    review_queue_dir,
)

if TYPE_CHECKING:
    from sys_ikigai.security.kill_switch import KillSwitchActivationStatus


# ===========================================================================
# Action constants + exit codes (inlined from _kill_switch_actions.py)
# ===========================================================================

_AUDIT_ACTION_PAUSE = "kill_switch_pause"
_AUDIT_ACTION_RESUME = "kill_switch_resume"

EXIT_OK = 0
EXIT_ACTIVE_OR_REFUSED = 1
EXIT_CONFIRM_REQUIRED = 2
EXIT_REASON_REQUIRED = 3


# ===========================================================================
# Internal path helpers (inlined from _kill_switch_actions.py)
# ===========================================================================


def _vault_root():
    return repo_root() / "vault"


def _data_root():
    return repo_root() / "data"


# ===========================================================================
# Action functions (inlined from _kill_switch_actions.py)
# ===========================================================================


def activate_data_file(
    reason: str,
    *,
    force: bool,
    printer: Callable[[str], None],
) -> dict[str, Any]:
    """Activate data-file mechanism + append audit entry.

    Returns a result dict; raises `SystemExit` (typer.Exit) on refusal.
    The `printer` callable receives a Rich-formatted message for the
    non-JSON path.
    """
    reason = reason.strip()
    status_obj = check_kill_switch(_vault_root(), _data_root())
    if (
        status_obj.is_active
        and not force
        and status_obj.active_reason in ("env_var", "vault_file")
    ):
        msg = (
            f"Refused: kill switch already active via {status_obj.active_reason}. "
            "That mechanism is owned by the shell (env_var) or vault_write "
            "MCP tool (vault_file). Pass --force to override; --force does "
            "NOT change the existing activation — it only allows this CLI to "
            "append a data/.kill_switch on top."
        )
        printer(msg)
        raise SystemExit(EXIT_ACTIVE_OR_REFUSED)

    kill_file = _data_root() / DATA_KILL_SWITCH_FILENAME
    kill_file.parent.mkdir(parents=True, exist_ok=True)
    kill_file.write_text("active\n", encoding="utf-8")

    audit_path = append_audit_entry(
        action=_AUDIT_ACTION_PAUSE,
        reason=reason,
        active_reason_at_action=status_obj.active_reason,
    )

    # Best-effort provenance — failure here does NOT roll back the data
    # file activation (the audit entry is the canonical record).
    try:
        kill_event = build_kill_switch_event(
            trigger="manual_override",
            actor_at_fault="user",
            entity_id=None,
            context={"reason": reason, "source": "interfaces/cli.kill_switch.pause"},
            recovery_reason="data_file",
        )
        fire_kill_switch(kill_event, review_queue_dir(), _vault_root())
    except Exception:
        pass

    return {
        "activated": True,
        "data_file": str(kill_file),
        "audit_entry": str(audit_path),
        "reason": reason,
    }


def resume_plan_message() -> str:
    """Plan message printed when `resume` is invoked without --confirm."""
    status_obj = check_kill_switch(_vault_root(), _data_root())
    return "\n".join(
        [
            "Kill switch recovery will:",
            f"  - pop {ENV_VAR_NAME} from os.environ",
            f"  - delete {_vault_root() / VAULT_KILL_SWITCH_FILENAME} (if present)",
            f"  - delete {_data_root() / DATA_KILL_SWITCH_FILENAME} (if present)",
            f"  - append audit entry to {review_queue_dir()}/",
            f"Current active_reason: {status_obj.active_reason or 'none'}",
            "",
            "Pass --confirm to proceed. Pass --dry-run to preview only.",
        ]
    )


def resume_plan_dict() -> dict[str, Any]:
    """JSON-equivalent of `resume_plan_message`."""
    status_obj = check_kill_switch(_vault_root(), _data_root())
    return {
        "active_reason": status_obj.active_reason,
        "plan_lines": resume_plan_message().splitlines(),
    }


def recover_kill_switch_and_audit(
    reason: str,
    *,
    json_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call recover_kill_switch + append audit entry, returning a result dict."""
    reason = reason.strip()
    status_obj = check_kill_switch(_vault_root(), _data_root())
    cleared = recover_kill_switch(_vault_root(), _data_root())
    audit_path = append_audit_entry(
        action=_AUDIT_ACTION_RESUME,
        reason=reason,
        active_reason_at_action=status_obj.active_reason,
    )
    payload: dict[str, Any] = {
        "recovered": cleared,
        "audit_entry": str(audit_path),
        "reason": reason,
        "active_reason_at_action": status_obj.active_reason,
    }
    if json_extra:
        payload.update(json_extra)
    return payload


# ===========================================================================
# Render functions (inlined from _kill_switch_render.py)
# ===========================================================================


def render_status(
    console: Console,
    *,
    status_obj: "KillSwitchActivationStatus",
    rate_limit: dict[str, int],
    env_var_name: str,
    vault_filename: str,
    data_filename: str,
) -> None:
    """Rich-table + JSON payload for the `status` verb."""
    report = {
        "is_active": status_obj.is_active,
        "active_reason": status_obj.active_reason,
        "mechanisms": {
            "env_var_active": status_obj.env_var_active,
            "vault_file_active": status_obj.vault_file_active,
            "data_file_active": status_obj.data_file_active,
        },
        "env_var_name": env_var_name,
        "vault_kill_switch_filename": vault_filename,
        "data_kill_switch_filename": data_filename,
        "rate_limit": rate_limit,
    }
    console.print_json(json.dumps(report))


def render_status_table(
    console: Console,
    *,
    status_obj: "KillSwitchActivationStatus",
    rate_limit: dict[str, int],
) -> None:
    """Rich table form for the `status` verb (human-readable)."""
    table = Table(title="Kill Switch Status")
    table.add_column("Mechanism", style="cyan")
    table.add_column("Active", style="white")
    for name, active in (
        ("env_var", status_obj.env_var_active),
        ("vault_file", status_obj.vault_file_active),
        ("data_file", status_obj.data_file_active),
    ):
        mark = "[red]ACTIVE[/red]" if active else "[green]inactive[/green]"
        table.add_row(name, mark)
    table.add_row(
        "OVERALL",
        "[red]ACTIVE[/red]" if status_obj.is_active else "[green]INACTIVE[/green]",
    )
    table.add_row("Priority reason", status_obj.active_reason)
    table.add_row("Events in last 1h", str(rate_limit["events_in_last_window"]))
    console.print(table)


def render_history_json(console: Console, rows: list[dict[str, Any]]) -> None:
    console.print_json(json.dumps({"events": rows, "count": len(rows)}))


def render_history_table(console: Console, rows: list[dict[str, Any]]) -> None:
    table = Table(title=f"Kill Switch History — {len(rows)} event(s)")
    table.add_column("event_id", style="cyan", width=20)
    table.add_column("action", style="magenta", width=22)
    table.add_column("ueid", style="dim", width=40)
    table.add_column("reason", style="white", width=36)
    table.add_column("active_reason_at_action", style="yellow", width=18)
    for r in rows:
        fields = r.get("fields", {}) if isinstance(r.get("fields"), dict) else {}
        reason = str(fields.get("reason", "—"))[:36]
        active_reason = str(fields.get("active_reason_at_action", "—"))[:18]
        table.add_row(
            str(r.get("event_id", "—"))[:20],
            str(r.get("action", "—"))[:22],
            str(r.get("ueid", "—"))[:40],
            reason,
            active_reason,
        )
    console.print(table)


# ===========================================================================
# CLI app + verbs (status / history / pause / resume / recover)
# ===========================================================================

app = typer.Typer(
    name="kill-switch",
    help="Inspect and recover the IKIGAI kill switch (W5.3 — consumer UX).",
    no_args_is_help=True,
)
console = Console()

_AUDIT_ACTION_PREFIX = "kill_switch_"


def _require_nonempty(reason: str) -> str:
    """Trim + validate `--reason`; raise typer.Exit(3) on empty."""
    if not reason or not reason.strip():
        console.print("[red]--reason must be non-empty[/red]")
        raise typer.Exit(EXIT_REASON_REQUIRED)
    return reason.strip()


# ===========================================================================
# Verb: status — read-only
# ===========================================================================


@app.command()
def status(
    json_output: bool = typer.Option(
        False, "--json", help="Machine-readable JSON output"
    ),
) -> None:
    """Print kill switch activation status across all 3 mechanisms (design §3.1)."""
    repo_root = __import__("pathlib").Path(__file__).resolve().parents[2]
    status_obj = check_kill_switch(repo_root / "vault", repo_root / "data")
    rate_limit = compute_rate_limit()

    if json_output:
        render_status(
            console,
            status_obj=status_obj,
            rate_limit=rate_limit,
            env_var_name=ENV_VAR_NAME,
            vault_filename=VAULT_KILL_SWITCH_FILENAME,
            data_filename=DATA_KILL_SWITCH_FILENAME,
        )
    else:
        render_status_table(console, status_obj=status_obj, rate_limit=rate_limit)

    if status_obj.is_active:
        raise typer.Exit(EXIT_ACTIVE_OR_REFUSED)


# ===========================================================================
# Verb: history — read-only
# ===========================================================================


@app.command()
def history(
    limit: int = typer.Option(
        10, "--limit", "-n", help="Max entries to show (default 10)"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Machine-readable JSON output"
    ),
) -> None:
    """Show recent kill_switch events from data/review_queue/ (design §3.1)."""
    rows = read_kill_switch_history(limit=limit)
    if json_output:
        render_history_json(console, rows)
        return
    if not rows:
        console.print(
            f"[dim]No kill-switch events in {review_queue_dir()} "
            f"(matched: action.startswith('{_AUDIT_ACTION_PREFIX}'))[/dim]"
        )
        return
    render_history_table(console, rows)


# ===========================================================================
# Verb: pause — writes audit + touches data/.kill_switch
# ===========================================================================


@app.command()
def pause(
    reason: str = typer.Option(
        ..., "--reason", help="Non-empty reason explaining why activation is needed"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Override env_var/vault_file refusal (still does NOT set them)",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Machine-readable JSON output"
    ),
) -> None:
    """Activate the DATA kill switch + append audit entry (design §3.5)."""
    reason = _require_nonempty(reason)

    def _red(msg: str) -> None:
        console.print(f"[red]{msg}[/red]")

    try:
        result = activate_data_file(reason, force=force, printer=_red)
    except SystemExit as exc:
        if exc.code == EXIT_ACTIVE_OR_REFUSED and json_output:
            console.print_json(
                json.dumps(
                    {
                        "refused": True,
                        "reason": check_kill_switch(
                            __import__("pathlib").Path(__file__).resolve().parents[2]
                            / "vault",
                            __import__("pathlib").Path(__file__).resolve().parents[2]
                            / "data",
                        ).active_reason,
                        "message": "see non-JSON output above",
                    }
                )
            )
        raise

    if json_output:
        console.print_json(json.dumps(result))
    else:
        console.print(
            f"[green]Kill switch activated.[/green] "
            f"data_file={result['data_file']} "
            f"audit_entry={result['audit_entry']}"
        )


# ===========================================================================
# Verb: resume — clears mechanisms + appends audit entry
# ===========================================================================


@app.command(name="resume")
def do_resume(
    reason: str = typer.Option(
        ...,
        "--reason",
        help="Non-empty rationale — persisted to audit entry's fields.reason",
    ),
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="Required confirmation — without it, prints plan and exits 2",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the recovery plan without executing"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Machine-readable JSON output"
    ),
) -> None:
    """Clear all 3 kill switch mechanisms + append audit entry (design §3.5)."""
    reason = _require_nonempty(reason)

    if not confirm:
        if json_output:
            console.print_json(
                json.dumps({"confirm_required": True, **resume_plan_dict()})
            )
        else:
            console.print(resume_plan_message())
        raise typer.Exit(EXIT_CONFIRM_REQUIRED)

    if dry_run:
        console.print("[dim]--dry-run: not executing recovery.[/dim]")
        return

    result = recover_kill_switch_and_audit(reason)
    if json_output:
        console.print_json(json.dumps(result))
    else:
        cleared = result["recovered"]
        mark = (
            "[green]Kill switch recovered.[/green]"
            if cleared
            else "[yellow]Recovery returned False — one or more mechanisms may still be active.[/yellow]"
        )
        console.print(f"{mark} audit_entry={result['audit_entry']}")


@app.command(name="recover")
def do_recover(
    reason: str = typer.Option(
        ..., "--reason", help="Non-empty rationale (alias for resume --reason)"
    ),
    confirm: bool = typer.Option(
        False, "--confirm", help="Required confirmation (alias for resume --confirm)"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Machine-readable JSON output"
    ),
) -> None:
    """Alias for `resume --reason <text> --confirm` (design §2.2)."""
    reason = _require_nonempty(reason)
    if not confirm:
        console.print(
            "[red]--confirm required (alias: `recover --reason <text> --confirm`)[/red]"
        )
        raise typer.Exit(EXIT_CONFIRM_REQUIRED)

    result = recover_kill_switch_and_audit(reason, json_extra={"alias": "recover"})
    if json_output:
        console.print_json(json.dumps(result))
    else:
        cleared = result["recovered"]
        mark = (
            "[green]Recovered.[/green]"
            if cleared
            else "[yellow]Recovery returned False.[/yellow]"
        )
        console.print(f"{mark} audit_entry={result['audit_entry']}")


__all__ = ["app"]
