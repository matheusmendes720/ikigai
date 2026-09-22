"""M128 — audit_drift_cli.py

CLI wrapper for `tools.backtest.vault_propagation.audit_drift()`.

Lets the user (or agent) run drift detection from the command line
without going through the backtest harness. Designed for:
  - Human use: `life v2 audit-drift` to see what drift exists
  - Agent use: `life v2 audit-drift --json` to feed results into a prompt
  - CI use: `life v2 audit-drift --kind-filter phantom_task --exit-on-drift`

The drift kinds (6 total) are defined in vault_propagation.py.
This module is a thin façade — all logic stays in vault_propagation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Lazy import to keep `life v2 --help` fast.
def _audit_drift() -> dict[str, Any]:
    from tools.backtest.vault_propagation import audit_drift
    return audit_drift()


def _format_summary(drift: dict[str, Any]) -> str:
    """Format the drift dict as a human-readable table."""
    summary = drift.get("summary", {})
    drifts = drift.get("drifts", [])
    lines: list[str] = []
    lines.append("Vault ↔ Taskdog drift audit")
    lines.append("=" * 60)
    if not summary:
        lines.append("(no drift detected — vault and taskdog are in sync)")
        return "\n".join(lines)
    lines.append(f"Drifts by kind:")
    for kind, count in sorted(summary.items()):
        lines.append(f"  {kind:<22} {count:>5}")
    lines.append("")
    lines.append(f"Total drifts: {len(drifts)}")
    return "\n".join(lines)


def _format_kind_table(drifts: list[dict[str, Any]], kind: str) -> str:
    """Format drifts of one kind as a table."""
    matching = [d for d in drifts if d.get("drift_kind") == kind]
    if not matching:
        return f"No drifts of kind '{kind}'."
    lines: list[str] = []
    lines.append(f"Drifts of kind '{kind}':")
    lines.append("-" * 60)
    for d in matching[:20]:  # cap at 20 for readability
        plan = d.get("plan_file") or "?"
        line = d.get("plan_line", "?")
        text = (d.get("plan_text") or "")[:40]
        td_id = d.get("taskdog_id", "-")
        td_status = d.get("taskdog_status", "-")
        td_name = (d.get("taskdog_name") or "")[:30]
        # Use taskdog name for kinds without plan info (phantom_task).
        if plan == "?" and td_name:
            lines.append(f"  taskdog:{td_id}/{td_status}  {td_name}")
        else:
            lines.append(f"  {plan}:{line}  taskdog:{td_id}/{td_status}  {text}")
    if len(matching) > 20:
        lines.append(f"  ... and {len(matching) - 20} more (use --json for full list)")
    return "\n".join(lines)


def main(
    *,
    json_output: bool = False,
    kind_filter: str | None = None,
    exit_on_drift: bool = False,
) -> int:
    """Run audit_drift and render results.

    Args:
      json_output: emit JSON instead of human-readable table.
      kind_filter: only show drifts of this kind (e.g. 'phantom_task').
                   None = all kinds.
      exit_on_drift: exit code 1 if any drift is found (CI-friendly).

    Returns: exit code (0 = no drift or drift acknowledged; 1 = drift found with --exit-on-drift).
    """
    try:
        drift = _audit_drift()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: audit_drift failed: {exc}", file=sys.stderr)
        return 2

    summary = drift.get("summary", {})
    drifts = drift.get("drifts", [])
    total = sum(summary.values()) if summary else len(drifts)

    if json_output:
        if kind_filter:
            drift_out = {**drift, "drifts": [d for d in drifts if d.get("drift_kind") == kind_filter]}
        else:
            drift_out = drift
        print(json.dumps(drift_out, indent=2, default=str))
    else:
        if kind_filter:
            print(_format_kind_table(drifts, kind_filter))
        else:
            print(_format_summary(drift))
            if summary and total > 0:
                print("")
                # Group by kind for visibility.
                for kind in sorted(summary):
                    print("")
                    print(_format_kind_table(drifts, kind))

    if exit_on_drift and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
