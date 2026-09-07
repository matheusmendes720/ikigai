"""W5.3 — Operator TUI KillSwitch tab + persistent status banner.

Pure consumer of `sys_ikigai.security.kill_switch`. The 5th tab mirrors
the existing 4-tab layout (Tasks / Adapters / Backend / Queue) per
Phase 9 Option A precedent.

The status banner is rendered at the top of every tab (including this
one) when `check_kill_switch(vault_root, data_root)` reports active.
Per design doc §4.4 the banner is READ-ONLY — no `p` / `r` keys without
`shift+` prefix. The actual `p` / `r` actions shell out to the CLI via
``subprocess.run`` (NOT direct kill_switch.py imports — keeps the TUI
import chain shallow per `data.py:18-22`).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Static

from sys_ikigai.security.kill_switch import (
    DATA_KILL_SWITCH_FILENAME,
    ENV_VAR_NAME,
    VAULT_KILL_SWITCH_FILENAME,
    check_kill_switch,
    _recovery_path_for_reason,  # type: ignore[attr-defined]  # noqa: PGH003 - intentional local use
)

# ---------------------------------------------------------------------------
# Constants (paths) — derived from operator/data.py precedent
# ---------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
REPO_ROOT = _THIS_FILE.parents[3]  # interfaces/tui/operator/_kill_switch_tab.py → life/
VAULT_ROOT = REPO_ROOT / "vault"
DATA_ROOT = REPO_ROOT / "data"
REVIEW_QUEUE_DIR = DATA_ROOT / "review_queue"


# ---------------------------------------------------------------------------
# Status snapshot — light-weight dataclass-style helper
# ---------------------------------------------------------------------------


def is_active() -> bool:
    """Return True iff any kill switch mechanism is active."""
    return check_kill_switch(VAULT_ROOT, DATA_ROOT).is_active


def snapshot() -> dict[str, object]:
    """Snapshot of kill-switch state for tab + banner rendering.

    Pure read of `check_kill_switch(...)` + a sliding-window count from
    `data/review_queue/*.json` filtered to `action.startswith('kill_switch_')`.
    No state — caller may invoke as often as the auto-refresh fires.
    """
    status_obj = check_kill_switch(VAULT_ROOT, DATA_ROOT)
    events_in_last_1h = _count_recent_kill_switch_events()
    last_trigger = _last_kill_switch_trigger()
    return {
        "is_active": status_obj.is_active,
        "active_reason": status_obj.active_reason,
        "mechanisms": {
            "env_var_active": status_obj.env_var_active,
            "vault_file_active": status_obj.vault_file_active,
            "data_file_active": status_obj.data_file_active,
        },
        "events_in_last_1h": events_in_last_1h,
        "last_trigger": last_trigger,
        "recovery_path": _recovery_path_for_reason(status_obj.active_reason),
    }


def _count_recent_kill_switch_events(window_s: float = 3600.0) -> int:
    """Count review-queue entries with action.startswith('kill_switch_')
    inside a sliding window (default 1h per ADR-029 R10).
    """
    import time

    if not REVIEW_QUEUE_DIR.is_dir():
        return 0
    cutoff = time.time() - window_s
    count = 0
    for f in REVIEW_QUEUE_DIR.glob("*.json"):
        if f.stat().st_mtime < cutoff:
            continue
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        action = str(payload.get("action", ""))
        if action.startswith("kill_switch_"):
            count += 1
    return count


def _last_kill_switch_trigger() -> str | None:
    """Return the most recent kill-switch trigger (or None)."""
    if not REVIEW_QUEUE_DIR.is_dir():
        return None
    candidates: list[tuple[float, dict[str, object]]] = []
    for f in REVIEW_QUEUE_DIR.glob("*.json"):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        action = str(payload.get("action", ""))
        if action.startswith("kill_switch_"):
            candidates.append((f.stat().st_mtime, payload))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    last = candidates[0][1]
    return str(last.get("action"))


# ---------------------------------------------------------------------------
# Banner — top-of-every-tab when kill switch is active (read-only)
# ---------------------------------------------------------------------------


def banner_widget() -> Static | None:
    """Return a Static banner if kill switch is active, else None.

    Caller mounts this widget as the first child of `#content` (or skips
    it). Per design doc §4.4 the banner is read-only; the `p` / `r` keys
    are registered ONLY on the KillSwitch tab itself with `shift+`
    prefix (see `KillSwitchTab` below).
    """
    snap = snapshot()
    if not snap["is_active"]:
        return None
    lines = [
        "[bold red]KILL SWITCH ACTIVE[/bold red] — "
        f"reason: [yellow]{snap['active_reason']}[/yellow]",
        f"events in last 1h: {snap['events_in_last_1h']}  ·  "
        f"last trigger: {snap['last_trigger'] or '—'}",
        f"recovery: {snap['recovery_path']}",
    ]
    return Static("\n".join(lines), id="killswitch-banner", classes="killswitch-active")


# ---------------------------------------------------------------------------
# Tab widget — read-only by default (per design doc §4.4)
# ---------------------------------------------------------------------------


class KillSwitchTab(Container):
    """5th TUI tab — Kill Switch state + recovery path.

    Default state is read-only. The `shift+p` / `shift+r` keys shell
    out to the CLI (no direct kill_switch.py imports — TUI import chain
    stays shallow per `data.py:18-22`).
    """

    # NOTE: `p` and `r` without shift would conflict with global
    # `drilldown_queue` and `refresh` bindings. Design §4.4 mandates
    # `shift+` prefix so the accidental-pause risk is one keystroke
    # heavier than the read-only refresh.
    BINDINGS = [
        Binding("shift+p", "open_pause", "Pause (CLI)"),
        Binding("shift+r", "open_resume", "Resume (CLI)"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(id="killswitch-tab-body")

    def on_mount(self) -> None:
        self._render()

    def _render(self) -> None:
        snap = snapshot()
        try:
            body = self.query_one("#killswitch-tab-body", Static)
        except Exception:
            return

        if not snap["is_active"]:
            body.update(
                "[bold green]Kill Switch: INACTIVE[/bold green]\n\n"
                f"No kill switch mechanism active. "
                f"All 3 layers (env var, vault file, data file) clear.\n\n"
                f"  - env var: {ENV_VAR_NAME}\n"
                f"  - vault file: vault/{VAULT_KILL_SWITCH_FILENAME}\n"
                f"  - data file: data/{DATA_KILL_SWITCH_FILENAME}\n\n"
                f"[dim]Press shift+p to pause (data file), "
                f"shift+r to resume.[/dim]"
            )
            return

        mechanisms = snap["mechanisms"]
        mech_lines = []
        for name in ("env_var_active", "vault_file_active", "data_file_active"):
            active = bool(mechanisms.get(name))
            mark = "[red]ACTIVE[/red]" if active else "[green]inactive[/green]"
            mech_lines.append(f"  - {name.replace('_active', '')}: {mark}")
        body.update(
            "[bold red]Kill Switch: ACTIVE[/bold red]\n\n"
            + "\n".join(mech_lines)
            + f"\n\n  active_reason (R1 priority): {snap['active_reason']}"
            + f"\n  events in last 1h: {snap['events_in_last_1h']}"
            + f"\n  last trigger: {snap['last_trigger'] or '—'}"
            + f"\n\n[bold]Recovery path:[/bold] {snap['recovery_path']}\n\n"
            + "[dim]Read-only — press shift+r to invoke `life kill-switch resume` "
            "via subprocess.[/dim]"
        )

    # ---- Action handlers (subprocess into the CLI) ----

    def action_open_pause(self) -> None:
        """Spawn `life kill-switch pause --reason ...` in a subprocess.

        The TUI does NOT import `interfaces.cli.kill_switch`; shelling
        out keeps the TUI import chain shallow (precedent: data.py:18-22).
        """
        try:
            subprocess.Popen(  # noqa: S603 — fire-and-forget subprocess
                [sys.executable, "-m", "interfaces.cli", "kill-switch", "pause"],
                cwd=str(REPO_ROOT),
            )
        except OSError:
            pass
        self._render()

    def action_open_resume(self) -> None:
        """Spawn `life kill-switch resume --confirm --reason ...` in a subprocess."""
        try:
            subprocess.Popen(  # noqa: S603 — fire-and-forget subprocess
                [
                    sys.executable,
                    "-m",
                    "interfaces.cli",
                    "kill-switch",
                    "resume",
                    "--confirm",
                ],
                cwd=str(REPO_ROOT),
            )
        except OSError:
            pass
        self._render()


__all__ = [
    "banner_widget",
    "KillSwitchTab",
    "is_active",
    "snapshot",
]
