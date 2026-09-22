"""M134 — drift_baseline.py

Daily snapshot of audit_drift summary counts. Stores per-day drift
counts in `reports/baselines/<DATE>.drift.json`, groups by ISO week,
and renders a markdown trend table.

Commands:
  snapshot  — capture today's drift summary, write <DATE>.drift.json (first-wins)
  list      — list all drift snapshots, newest first
  weekly    — group snapshots by ISO week, render markdown trend table

Format:
  <DATE>.drift.json: {"date": "2026-09-22", "summary": {<kind>: count, ...}, "total": N}

Honest scope:
  - "Drift is getting worse" means: same drift kinds, but more of them.
    A new drift kind appearing counts as a regression.
  - ISO-week grouping follows M118/M119 pattern (Monday-start week).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DRIFT_DIR = REPO_ROOT / "reports" / "baselines"
FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.drift\.json$")
# All 7 drift kinds — explicit list for stable reporting.
ALL_KINDS = (
    "unmarked_done", "unmarked_open", "phantom_task", "planned_orphan",
    "priority_mismatch", "tag_mismatch", "due_date_mismatch",
)


def _audit_drift_summary() -> dict[str, int]:
    """Run audit_drift() and return the summary dict (kind → count)."""
    from tools.backtest.vault_propagation import audit_drift
    result = audit_drift()
    summary = result.get("summary", {})
    # Ensure all 7 kinds present (even with 0 count).
    return {kind: int(summary.get(kind, 0)) for kind in ALL_KINDS}


def snapshot(bdir: Path = DEFAULT_DRIFT_DIR, day: date | None = None) -> Path | None:
    """Capture today's drift summary, write <DATE>.drift.json. First-wins."""
    day = day or date.today()
    date_str = day.isoformat()
    target = bdir / f"{date_str}.drift.json"
    if target.exists():
        print(f"# Skipped (already snapshotted): {target.name}")
        return target
    summary = _audit_drift_summary()
    total = sum(summary.values())
    payload = {
        "date": date_str,
        "summary": summary,
        "total": total,
    }
    bdir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"# Wrote {target}  (total: {total})")
    return target


def list_snapshots(bdir: Path = DEFAULT_DRIFT_DIR) -> list[Path]:
    """Return all drift snapshot files, newest first."""
    if not bdir.exists():
        return []
    files = [p for p in bdir.iterdir() if FILENAME_RE.match(p.name)]
    return sorted(files, reverse=True)


def _iso_week_key(date_str: str) -> str:
    """Convert 'YYYY-MM-DD' → 'YYYY-Www' ISO week label."""
    d = date.fromisoformat(date_str)
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def weekly(bdir: Path = DEFAULT_DRIFT_DIR, since_days: int = 90) -> list[dict[str, Any]]:
    """Group snapshots by ISO week, return weekly aggregates.

    since_days=0 means all-time (no cutoff filter).

    Returns list of dicts: {week, snapshot_count, totals: {kind: count}, ...}
    """
    snapshots = list_snapshots(bdir)
    if since_days > 0:
        cutoff = date.today().toordinal() - since_days
        snapshots = [
            p for p in snapshots
            if date.fromisoformat(FILENAME_RE.match(p.name).group(1)).toordinal() >= cutoff
        ]
    by_week: dict[str, dict[str, Any]] = {}
    for path in snapshots:
        date_str = FILENAME_RE.match(path.name).group(1)
        week = _iso_week_key(date_str)
        entry = by_week.setdefault(week, {"week": week, "snapshot_count": 0, "totals": {}})
        entry["snapshot_count"] += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for kind, count in data.get("summary", {}).items():
            entry["totals"][kind] = entry["totals"].get(kind, 0) + int(count)
    return [by_week[k] for k in sorted(by_week)]


def trend_report_markdown(
    weeks: list[dict[str, Any]],
    *,
    show_delta: bool = False,
    kinds: tuple[str, ...] | None = None,
) -> str:
    """Render weekly trend as markdown table.

    kinds: filter to a subset of kinds (None = all ALL_KINDS).
    show_delta: include Δ column (week-over-week change) per kind.
    """
    if not weeks:
        return "# Drift trend\n\n(no snapshots)\n"
    selected = kinds if kinds else ALL_KINDS
    lines = ["# Drift trend", ""]
    header = ["Week", "Snaps"] + list(selected) + ["Total"]
    if show_delta:
        # Append Δ per kind (in same order as selected).
        header += [f"Δ{k}" for k in selected]
        header += ["ΔTotal"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    prev_totals: dict[str, int] | None = None
    for w in weeks:
        totals = w["totals"]
        row = [
            w["week"],
            str(w["snapshot_count"]),
            *[str(totals.get(k, 0)) for k in selected],
            str(sum(totals.get(k, 0) for k in selected)),
        ]
        if show_delta:
            if prev_totals is None:
                row += ["—"] * (len(selected) + 1)
            else:
                for k in selected:
                    cur = totals.get(k, 0)
                    prv = prev_totals.get(k, 0)
                    row.append(f"{cur - prv:+d}")
                cur_total = sum(totals.get(k, 0) for k in selected)
                prv_total = sum(prev_totals.get(k, 0) for k in selected)
                row.append(f"{cur_total - prv_total:+d}")
        lines.append("| " + " | ".join(row) + " |")
        prev_totals = totals
    return "\n".join(lines) + "\n"


def trend_report_json(
    weeks: list[dict[str, Any]],
    *,
    kinds: tuple[str, ...] | None = None,
) -> str:
    """Render weekly trend as JSON.

    Includes week-over-week deltas (computed here, not in trend_report_markdown
    to keep formatting concerns separate).
    """
    import json as _json
    selected = list(kinds) if kinds else list(ALL_KINDS)
    rows: list[dict[str, Any]] = []
    prev_totals: dict[str, int] | None = None
    for w in weeks:
        totals = w["totals"]
        filtered_totals = {k: totals.get(k, 0) for k in selected}
        row: dict[str, Any] = {
            "week": w["week"],
            "snapshot_count": w["snapshot_count"],
            "totals": filtered_totals,
            "total": sum(filtered_totals.values()),
        }
        if prev_totals is not None:
            row["delta"] = {
                k: filtered_totals[k] - prev_totals.get(k, 0) for k in selected
            }
            row["delta_total"] = row["total"] - sum(prev_totals.get(k, 0) for k in selected)
        rows.append(row)
        prev_totals = filtered_totals
    return _json.dumps({"weeks": rows}, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Drift baseline snapshots + weekly trend")
    sub = p.add_subparsers(dest="cmd", required=True)

    snap = sub.add_parser("snapshot")
    snap.add_argument("--drift-dir", type=Path, default=DEFAULT_DRIFT_DIR)
    snap.add_argument("--date", default=None, help="Override date (YYYY-MM-DD)")

    ls = sub.add_parser("list")
    ls.add_argument("--drift-dir", type=Path, default=DEFAULT_DRIFT_DIR)

    w = sub.add_parser("weekly")
    w.add_argument("--drift-dir", type=Path, default=DEFAULT_DRIFT_DIR)
    w.add_argument("--since-days", type=int, default=90)
    w.add_argument("--kind", action="append", default=None,
                   help="Filter to one drift kind (repeatable). Default: all.")
    w.add_argument("--delta", action="store_true",
                   help="Include week-over-week Δ column (markdown only).")
    w.add_argument("--format", choices=("markdown", "json"), default="markdown")
    w.add_argument("--out", type=Path, default=None, help="Write output to file")

    args = p.parse_args(argv)

    if args.cmd == "snapshot":
        d = date.fromisoformat(args.date) if args.date else None
        snapshot(args.drift_dir, d)
        return 0
    if args.cmd == "list":
        for path in list_snapshots(args.drift_dir):
            print(path.name)
        return 0
    if args.cmd == "weekly":
        weeks = weekly(args.drift_dir, args.since_days)
        kinds = tuple(args.kind) if args.kind else None
        # Validate kinds.
        if kinds:
            unknown = [k for k in kinds if k not in ALL_KINDS]
            if unknown:
                print(f"# Error: unknown drift kind(s): {unknown}", file=sys.stderr)
                print(f"# Valid kinds: {list(ALL_KINDS)}", file=sys.stderr)
                return 2
        if args.format == "json":
            out = trend_report_json(weeks, kinds=kinds)
        else:
            out = trend_report_markdown(weeks, show_delta=args.delta, kinds=kinds)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(out, encoding="utf-8")
            print(f"# Wrote {args.out}")
        else:
            print(out, end="")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
