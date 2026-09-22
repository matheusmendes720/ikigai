"""M135 — vault_rollback.py

Walk `vault/.vault_events.jsonl` backwards and reverse mutations.

Supported reversals:
  vault.toggle_applied   → reopen the checkbox (call reopen_checkbox)
  vault.reopen_applied   → toggle the checkbox (call toggle_checkbox)
  vault.*_refused        → no-op (nothing was mutated)

Commands:
  list   — show recent events (newest first), filter by --since / --actor / --event
  undo   — reverse one or more events (with --dry-run support)

The audit log is append-only. Rollback writes a NEW event
(`vault.rollback_applied`) recording what was reversed — never mutates
the log itself.

Honest scope:
  - Rollback only handles toggle/reopen reversals. Other events
    (refactor_plan, audit_drift) are non-mutating or have no inverse.
  - The rollback uses the SAME preview-gate pattern as toggle/reopen
    (preview → apply). If the underlying file state has changed
    since the original toggle, the rollback refuses.
  - "Since N hours ago" filter uses naive timestamp comparison —
    timezones are preserved from the log.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_EVENTS = REPO_ROOT / "vault" / ".vault_events.jsonl"


def _read_events(path: Path = VAULT_EVENTS) -> list[dict[str, Any]]:
    """Read all events from the audit log, oldest first."""
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _parse_ts(ts: str) -> datetime | None:
    """Parse ISO timestamp; returns timezone-aware datetime or None."""
    try:
        # Python 3.11+ handles 'Z' suffix.
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _now_utc() -> datetime:
    """Return current UTC time. Wrapped for testability."""
    return datetime.now(timezone.utc)


def list_events(
    path: Path = VAULT_EVENTS,
    *,
    since_hours: float | None = None,
    actor: str | None = None,
    event_type: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """List events, newest first, with optional filters.

    since_hours: only events newer than this many hours ago.
    actor: only events from this actor.
    event_type: only events of this type (e.g. 'vault.toggle_applied').
    """
    events = _read_events(path)
    if since_hours is not None:
        cutoff = _now_utc() - timedelta(hours=since_hours)
        events = [
            e for e in events
            if (parsed := _parse_ts(e.get("ts", ""))) is not None and parsed >= cutoff
        ]
    if actor:
        events = [e for e in events if e.get("actor") == actor]
    if event_type:
        events = [e for e in events if e.get("event") == event_type]
    events.reverse()  # newest first
    if limit:
        events = events[:limit]
    return events


def _rollback_one(
    event: dict[str, Any],
    actor: str,
    reason: str,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    """Reverse a single event. Returns {ok, action, plan_file, line, error?}.

    On dry_run, doesn't actually mutate — just returns what WOULD happen.
    On apply, mutates the file and writes a vault.rollback_applied event.
    """
    evt_type = event.get("event")
    rel_path = event.get("rel_path", "")
    target_line = event.get("target_line")
    expected_text = event.get("expected_text", "")
    ok_flag = event.get("ok", True)

    result: dict[str, Any] = {
        "ok": False,
        "action": None,
        "plan_file": rel_path,
        "line": target_line,
        "original_event": evt_type,
        "dry_run": dry_run,
    }

    # Refused events are no-ops (nothing was mutated).
    if evt_type and evt_type.endswith("_refused"):
        result["ok"] = True
        result["action"] = "no-op (refused event)"
        return result

    # Need a target line + path + text for reversals.
    if not rel_path or target_line is None or not expected_text:
        result["error"] = f"cannot rollback {evt_type}: missing rel_path/line/text"
        return result

    # Skip events that didn't actually mutate.
    if ok_flag is False:
        result["ok"] = True
        result["action"] = "no-op (ok=False)"
        return result

    # Determine the reverse action.
    if evt_type == "vault.toggle_applied":
        reverse_action = "reopen"
    elif evt_type == "vault.reopen_applied":
        reverse_action = "toggle"
    elif evt_type == "vault.rollback_applied":
        result["error"] = "cannot rollback a rollback (would create infinite undo chain)"
        return result
    else:
        result["error"] = f"no rollback handler for event type: {evt_type}"
        return result

    result["action"] = reverse_action

    if dry_run:
        result["ok"] = True
        result["preview"] = True
        return result

    # Apply the reverse mutation via the preview-gated API.
    from tools.backtest.vault_propagation import (
        preview_toggle,
        preview_reopen,
        apply_toggle,
        apply_reopen,
        append_event,
    )
    from tools.vault.apply_toggle_cli import _resolve_plan_path  # type: ignore[import-untyped]

    try:
        plan = _resolve_plan_path(rel_path)
    except ValueError as exc:
        result["error"] = f"path resolution: {exc}"
        return result

    if not plan.exists():
        result["error"] = f"plan file no longer exists: {plan}"
        return result

    if reverse_action == "reopen":
        preview = preview_reopen(plan, target_line, expected_text)
        if not preview.get("ok"):
            result["error"] = f"preview failed: {preview.get('error')}"
            return result
        mutation = apply_reopen(
            plan, target_line, expected_text,
            actor=actor, reason=reason, require_preview_ok=False,
        )
    else:  # toggle
        preview = preview_toggle(plan, target_line, expected_text)
        if not preview.get("ok"):
            result["error"] = f"preview failed: {preview.get('error')}"
            return result
        mutation = apply_toggle(
            plan, target_line, expected_text,
            actor=actor, reason=reason, require_preview_ok=False,
        )

    if not mutation.get("ok"):
        result["error"] = f"mutation failed: {mutation.get('error')}"
        return result

    # Record the rollback.
    append_event({
        "event": "vault.rollback_applied",
        "original_event": evt_type,
        "rel_path": rel_path,
        "target_line": target_line,
        "expected_text": expected_text,
        "reverse_action": reverse_action,
        "reason": reason,
        "actor": actor,
        "ok": True,
    })

    result["ok"] = True
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rollback vault mutations from audit log")
    sub = p.add_subparsers(dest="cmd", required=True)

    ls = sub.add_parser("list")
    ls.add_argument("--log-path", type=Path, default=VAULT_EVENTS)
    ls.add_argument("--since-hours", type=float, default=None)
    ls.add_argument("--actor", default=None)
    ls.add_argument("--event", dest="event_type", default=None)
    ls.add_argument("--limit", type=int, default=20)
    ls.add_argument("--json", action="store_true")

    undo = sub.add_parser("undo")
    undo.add_argument("--log-path", type=Path, default=VAULT_EVENTS)
    undo.add_argument("--since-hours", type=float, default=None)
    undo.add_argument("--actor", default=None)
    undo.add_argument("--event", dest="event_type", default=None)
    undo.add_argument("--limit", type=int, default=1,
                      help="Roll back this many most-recent matching events.")
    undo.add_argument("--reason", default="user rollback",
                      help="Reason for the rollback (audit-logged).")
    undo.add_argument("--actor-name", default="cli-rollback",
                      help="Actor name to record in the rollback event.")
    undo.add_argument("--dry-run", action="store_true")
    undo.add_argument("--json", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "list":
        events = list_events(
            args.log_path,
            since_hours=args.since_hours,
            actor=args.actor,
            event_type=args.event_type,
            limit=args.limit,
        )
        if args.json:
            print(json.dumps(events, indent=2, default=str))
        else:
            for e in events:
                ts = e.get("ts", "")
                evt = e.get("event", "?")
                actor = e.get("actor", "?")
                rel = e.get("rel_path", "")
                line = e.get("target_line", "")
                text = e.get("expected_text", "")[:30]
                ok = e.get("ok", True)
                marker = "✓" if ok else "✗"
                print(f"{marker} {ts}  {evt}  actor={actor}  {rel}:{line}  {text}")
        return 0

    if args.cmd == "undo":
        events = list_events(
            args.log_path,
            since_hours=args.since_hours,
            actor=args.actor,
            event_type=args.event_type,
            limit=args.limit,
        )
        if not events:
            print("# No matching events to rollback.", file=sys.stderr)
            return 1
        results = []
        for e in events:
            r = _rollback_one(
                e,
                actor=args.actor_name,
                reason=args.reason,
                dry_run=args.dry_run,
            )
            results.append({"event": e, "rollback": r})
            if not args.json:
                action = r.get("action")
                status = "OK" if r.get("ok") else f"FAIL: {r.get('error')}"
                print(f"# {e.get('event')} → {action}: {status}")
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        # Exit 0 if all succeeded, 1 if any failed.
        return 0 if all(r["rollback"]["ok"] for r in results) else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
