"""M133 — reopen_cli.py

CLI wrapper for `vault_propagation.preview_reopen()` and `apply_reopen()`.

Inverse of M131 (apply_toggle_cli). Reopens a closed checkbox
(`- [x] text` → `- [ ] text`). Same audit-log + preview gate pattern.

Usage:
  life v2 vault-reopen -p <plan> -l <line> -e <text> -r <reason>

If preview would fail, the command refuses (exit 1).
--skip-preview bypasses the gate (trusted scripts only).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from tools.vault.apply_toggle_cli import _resolve_plan_path  # type: ignore[import-untyped]


def _preview(rel_path: str, line: int, expected: str) -> dict[str, Any]:
    from tools.backtest.vault_propagation import preview_reopen
    plan = _resolve_plan_path(rel_path)
    return preview_reopen(plan, line, expected)


def _apply(
    rel_path: str,
    line: int,
    expected: str,
    actor: str,
    reason: str,
    *,
    skip_preview: bool = False,
) -> dict[str, Any]:
    from tools.backtest.vault_propagation import apply_reopen
    plan = _resolve_plan_path(rel_path)
    return apply_reopen(
        plan, line, expected,
        actor=actor, reason=reason,
        require_preview_ok=not skip_preview,
    )


def main(
    *,
    rel_path: str,
    line: int,
    expected: str,
    actor: str = "cli",
    reason: str,
    skip_preview: bool = False,
    json_output: bool = False,
) -> int:
    """CLI entry point for vault-reopen."""
    if not rel_path:
        print("ERROR: --plan-path required", file=sys.stderr)
        return 2
    if line is None or line < 1:
        print("ERROR: --line required (positive integer)", file=sys.stderr)
        return 2
    if not expected:
        print("ERROR: --expected required", file=sys.stderr)
        return 2
    if not reason:
        print("ERROR: --reason required for reopen", file=sys.stderr)
        return 2

    try:
        plan = _resolve_plan_path(rel_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not plan.exists():
        print(f"ERROR: plan not found: {plan}", file=sys.stderr)
        return 1

    try:
        preview = _preview(rel_path, line, expected)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    result: dict[str, Any] = {"preview": preview}
    if json_output:
        # In JSON mode, the preview portion goes into the result dict now;
        # the applied portion is added below before final print.
        pass
    else:
        print(f"# Reopen: {rel_path}:{line}")
        if preview.get("ok"):
            print(f"# Would become: {preview.get('would_become')}")
            print(f"# Checkboxes done after: {preview.get('checkboxes_done_after')}")
        else:
            print(f"# Preview REFUSED: {preview.get('error')}")

    if not preview.get("ok") and not skip_preview:
        if json_output:
            print(json.dumps(result, indent=2, default=str))
        return 1

    try:
        result["applied"] = _apply(
            rel_path, line, expected, actor, reason, skip_preview=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if json_output:
        print(json.dumps(result, indent=2, default=str))
    else:
        applied = result["applied"]
        if applied.get("ok"):
            print("# OK — checkbox reopened.")
        else:
            print(f"# REFUSED: {applied.get('error')}")

    return 0 if result["applied"].get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
