"""M131 — apply_toggle_cli.py

CLI wrapper for `vault_propagation.preview_toggle()` and `apply_toggle()`.

Two-step API mirrors the M114f design:
  1. `preview` — read-only check: would `apply` succeed? Always safe.
  2. `apply`   — guarded mutation, requires preview first UNLESS
                 --force-preview-skip is passed (only for trusted scripts).

The audit log (`vault/.vault_events.jsonl`) records every call. This is
the agent's write path for marking vault checkboxes as done.

Commands:
  preview  — dry-run; never mutates; returns what `apply` would do
  apply    — mutates after preview (default: refuses without --yes flag)
  toggle   — convenience: preview + apply in one call (single user action)

The `apply` command requires:
  - Vault-relative path (no absolute paths; prevents accidental writes)
  - Target line number
  - Expected checkbox text
  - --reason (free text, recorded in audit log)
  - --actor (who is doing this; defaults to "cli")

The `apply` command refuses if preview fails (default behavior).

Honest scope:
  - This is the write path. Every mutation goes through this CLI.
  - The audit log (`vault/.vault_events.jsonl`) is append-only.
  - No remote sync — vault files stay local until an explicit sync step.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# Resolve repo root via the audit_drift_cli pattern.
def _resolve_plan_path(rel_path: str) -> Path:
    """Convert a vault-relative path to an absolute Path.

    Refuses absolute paths and parent traversal (..) for safety.
    """
    if Path(rel_path).is_absolute():
        raise ValueError(f"absolute paths not allowed: {rel_path}")
    p = Path(rel_path)
    if ".." in p.parts:
        raise ValueError(f"parent traversal not allowed: {rel_path}")
    # Vault root is the parent of "tools/", same convention as audit_drift_cli.
    # Find repo root by walking up from this file's location.
    here = Path(__file__).resolve()
    repo_root = here.parent.parent.parent  # tools/vault/<file> → repo root
    return (repo_root / "vault" / rel_path).resolve()


def _preview(rel_path: str, line: int, expected: str) -> dict[str, Any]:
    from tools.backtest.vault_propagation import preview_toggle
    plan = _resolve_plan_path(rel_path)
    return preview_toggle(plan, line, expected)


def _apply(
    rel_path: str,
    line: int,
    expected: str,
    actor: str,
    reason: str,
    *,
    skip_preview: bool = False,
) -> dict[str, Any]:
    from tools.backtest.vault_propagation import apply_toggle
    plan = _resolve_plan_path(rel_path)
    return apply_toggle(
        plan, line, expected,
        actor=actor, reason=reason,
        require_preview_ok=not skip_preview,
    )


def main(
    cmd: str,
    *,
    rel_path: str | None = None,
    line: int | None = None,
    expected: str | None = None,
    actor: str = "cli",
    reason: str | None = None,
    skip_preview: bool = False,
    json_output: bool = False,
) -> int:
    """CLI entry point. Validates args + dispatches."""
    if cmd not in ("preview", "apply", "toggle"):
        print(f"ERROR: unknown command: {cmd}", file=sys.stderr)
        return 2

    # Required args for all 3 commands.
    if not rel_path:
        print("ERROR: --plan-path required", file=sys.stderr)
        return 2
    if line is None or line < 1:
        print("ERROR: --line required (positive integer)", file=sys.stderr)
        return 2
    if not expected:
        print("ERROR: --expected required", file=sys.stderr)
        return 2
    # Apply/toggle also need reason.
    if cmd in ("apply", "toggle") and not reason:
        print("ERROR: --reason required for apply/toggle", file=sys.stderr)
        return 2

    # Resolve + path safety.
    try:
        plan = _resolve_plan_path(rel_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not plan.exists():
        print(f"ERROR: plan not found: {plan}", file=sys.stderr)
        return 1

    try:
        if cmd == "preview":
            result = _preview(rel_path, line, expected)
        elif cmd == "apply":
            result = _apply(rel_path, line, expected, actor, reason or "", skip_preview=skip_preview)
        else:  # toggle = preview then apply
            preview = _preview(rel_path, line, expected)
            if not preview.get("ok"):
                print("# Preview refused — not applying.", file=sys.stderr)
                if json_output:
                    print(json.dumps({"preview": preview, "applied": False}, indent=2, default=str))
                return 1
            result = _apply(rel_path, line, expected, actor, reason or "", skip_preview=True)
            result = {"preview": preview, "applied": result}
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if json_output:
        print(json.dumps(result, indent=2, default=str))
    else:
        if cmd == "preview":
            print(f"# Preview: {rel_path}:{line}")
            if result.get("ok"):
                print(f"# Would become: {result.get('would_become')}")
                print(f"# Checkboxes done after: {result.get('checkboxes_done_after')}")
            else:
                print(f"# REFUSED: {result.get('error')}")
        elif cmd == "apply":
            print(f"# Apply: {rel_path}:{line}")
            if result.get("ok"):
                print("# OK — checkbox toggled.")
                if "refused" in result:
                    print(f"# (refused by preview gate: {result.get('preview', {}).get('error')})")
            else:
                print(f"# REFUSED: {result.get('error')}")
        else:  # toggle
            print(f"# Toggle: {rel_path}:{line}")
            if result.get("applied", {}).get("ok"):
                print("# OK — checkbox toggled.")
            else:
                print(f"# REFUSED: {result.get('applied', {}).get('error')}")

    # Exit code: 0 on success, 1 on refused, 2 on error (already handled above).
    if cmd == "preview":
        return 0 if result.get("ok") else 1
    if cmd == "apply":
        return 0 if result.get("ok") else 1
    # toggle
    return 0 if result.get("applied", {}).get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
