"""M136 — drift_regression.py

Detect week-over-week drift regression. Fails CI if any drift kind
grows by >10% relative OR a new drift kind appears (0 → >0).

Commands:
  check   — compare current snapshot vs prior week; exit 0 if no regression,
            exit 1 if any drift kind regressed.
  report  — render markdown comparison (current vs prior) without exit code.

The regression threshold is configurable via --threshold (default 0.10 = 10%).

Honest scope:
  - "Regression" defined as:
      (a) any kind grew by >threshold relative to prior week, OR
      (b) a new drift kind appeared (prior=0, current>0)
  - 0 → 0 is not a regression (kinds that stayed absent are fine).
  - Only the most-recent TWO snapshots are compared (this week vs last week).
    If only one snapshot exists, `check` exits 0 with a warning.
  - We do NOT compare absolute counts because drift baselines grow with the
    vault — relative growth is the meaningful signal.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.backtest.drift_baseline import (  # type: ignore[import-untyped]
    DEFAULT_DRIFT_DIR,
    list_snapshots,
    FILENAME_RE,
    ALL_KINDS,
)


def _load_snapshot(path: Path) -> dict[str, Any] | None:
    """Load a single drift snapshot JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_two_snapshots(bdir: Path = DEFAULT_DRIFT_DIR) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Load the two most-recent snapshots. Returns (newer, older)."""
    snapshots = list_snapshots(bdir)
    if len(snapshots) < 2:
        return (_load_snapshot(snapshots[0]) if snapshots else None, None)
    newer = _load_snapshot(snapshots[0])
    older = _load_snapshot(snapshots[1])
    return newer, older


def _is_regression(
    prior: dict[str, int],
    current: dict[str, int],
    threshold: float,
) -> list[dict[str, Any]]:
    """Compare prior vs current; return list of regressions.

    Each entry: {kind, prior, current, delta, delta_pct, reason}
    """
    regressions: list[dict[str, Any]] = []
    for kind in ALL_KINDS:
        p = prior.get(kind, 0)
        c = current.get(kind, 0)
        if p == 0 and c > 0:
            # New drift kind appearing.
            regressions.append({
                "kind": kind,
                "prior": p,
                "current": c,
                "delta": c - p,
                "delta_pct": float("inf"),
                "reason": "new_kind",
            })
        elif p > 0:
            delta = c - p
            delta_pct = delta / p
            if delta_pct > threshold:
                regressions.append({
                    "kind": kind,
                    "prior": p,
                    "current": c,
                    "delta": delta,
                    "delta_pct": delta_pct,
                    "reason": f"growth>{threshold:.0%}",
                })
    return regressions


def check(
    bdir: Path = DEFAULT_DRIFT_DIR,
    *,
    threshold: float = 0.10,
    snapshot: bool = False,
) -> dict[str, Any]:
    """Compare most-recent two snapshots. Returns structured result.

    snapshot=True: take a fresh snapshot first (so check always reflects
    the live state, not just the last saved snapshot).
    """
    if snapshot:
        from tools.backtest.drift_baseline import snapshot
        snapshot(bdir)

    newer, older = _load_two_snapshots(bdir)
    result: dict[str, Any] = {
        "ok": True,
        "regressions": [],
        "insufficient_data": False,
        "current_date": newer.get("date") if newer else None,
        "prior_date": older.get("date") if older else None,
        "threshold": threshold,
    }
    if older is None:
        result["insufficient_data"] = True
        result["ok"] = True
        return result

    prior_summary = older.get("summary", {})
    current_summary = newer.get("summary", {})
    regressions = _is_regression(prior_summary, current_summary, threshold)
    result["regressions"] = regressions
    result["ok"] = len(regressions) == 0
    return result


def _format_report(result: dict[str, Any], bdir: Path = DEFAULT_DRIFT_DIR) -> str:
    """Render comparison as a markdown table."""
    lines: list[str] = []
    if result.get("insufficient_data"):
        lines.append("# Drift regression check")
        lines.append("")
        lines.append("**Insufficient data** — only 1 snapshot exists. Need ≥ 2 to compare.")
        return "\n".join(lines) + "\n"

    lines.append("# Drift regression check")
    lines.append("")
    lines.append(f"- Current: {result['current_date']}")
    lines.append(f"- Prior:   {result['prior_date']}")
    lines.append(f"- Threshold: {result['threshold']:.0%} relative growth")
    lines.append("")
    lines.append("| Kind | Prior | Current | Δ | Δ% | Status |")
    lines.append("|---|---|---|---|---|---|")
    # Load summaries from the same bdir as the check (passed through).
    newer, older = _load_two_snapshots(bdir)
    prior_summary = older.get("summary", {}) if older else {}
    current_summary = newer.get("summary", {}) if newer else {}
    regression_kinds = {r["kind"] for r in result["regressions"]}
    for kind in ALL_KINDS:
        p = prior_summary.get(kind, 0)
        c = current_summary.get(kind, 0)
        delta = c - p
        if p > 0:
            delta_pct = delta / p
            delta_pct_str = f"{delta_pct:+.1%}"
        elif c > 0:
            delta_pct_str = "+∞"
        else:
            delta_pct_str = "—"
        status = "🚨 REGRESSION" if kind in regression_kinds else "OK"
        lines.append(f"| {kind} | {p} | {c} | {delta:+d} | {delta_pct_str} | {status} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Drift regression detection")
    sub = p.add_subparsers(dest="cmd", required=True)

    for cmd in ("check", "report"):
        sp = sub.add_parser(cmd)
        sp.add_argument("--drift-dir", type=Path, default=DEFAULT_DRIFT_DIR)
        sp.add_argument("--threshold", type=float, default=0.10)
        sp.add_argument("--snapshot", action="store_true",
                        help="Take a fresh snapshot before checking.")
        sp.add_argument("--json", action="store_true")

    args = p.parse_args(argv)

    if args.cmd in ("check", "report"):
        result = check(args.drift_dir, threshold=args.threshold, snapshot=args.snapshot)
        if args.cmd == "report":
            md = _format_report(result, args.drift_dir)
            if args.json:
                print(json.dumps({"report": md, **result}, indent=2, default=str))
            else:
                print(md)
            return 0
        # check
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            if result.get("insufficient_data"):
                print("# Insufficient data (only 1 snapshot); check is OK.")
            elif result["ok"]:
                print(f"# OK — no regressions detected across {len(ALL_KINDS)} drift kinds.")
            else:
                print(f"# 🚨 REGRESSION — {len(result['regressions'])} drift kinds regressed:")
                for r in result["regressions"]:
                    kind = r["kind"]
                    reason = r["reason"]
                    print(f"   - {kind}: {reason} (prior={r['prior']}, current={r['current']})")
        return 0 if result["ok"] else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
