"""M115 — backtest_drift.py

Compares two backtest runs (current vs. baseline) and reports score drift.

Usage:
    # Compare current run against a saved baseline
    python tools/backtest/backtest_drift.py \\
        --current reports/backtest-Q1-judgment.json \\
        --baseline reports/backtest-Q1-judgment.bak.json \\
        --out reports/backtest-drift.md

    # Snapshot a run as baseline (for next comparison)
    cp reports/backtest-Q1-judgment.json reports/backtest-Q1-judgment.bak.json

Drift dimensions:
  - Total score delta (positive = improvement)
  - Per-dimension delta (anchor / tool / schema / scenario)
  - Per-anchor delta (sorted by largest regression)
  - Per-tool coverage delta (tools newly covered vs. newly missing)
  - Gap delta (new gaps vs. resolved gaps)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


# === Per-dimension comparison ===

def diff_scores(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, float]:
    """Compare the 4 score dimensions + total."""
    keys = [
        "anchor_pass_rate_pct",
        "tool_coverage_pct",
        "schema_valid_pct",
        "scenario_pass_rate_pct",
        "total_score",
    ]
    out: dict[str, float] = {}
    for k in keys:
        cur = current.get(k, 0.0)
        base = baseline.get(k, 0.0)
        out[k] = round(cur - base, 2)
    return out


# === Anchor diff ===

def diff_anchors(
    current: dict[int, dict[str, Any]],
    baseline: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Returns list of per-anchor regressions/improvements, sorted by largest regression."""
    all_ids = set(current.keys()) | set(baseline.keys())
    rows: list[dict[str, Any]] = []
    for aid in sorted(all_ids):
        c = current.get(aid, {})
        b = baseline.get(aid, {})
        cur_rate = c.get("pass_rate", 0.0)
        base_rate = b.get("pass_rate", 0.0)
        rows.append({
            "anchor_id": aid,
            "name": c.get("name") or b.get("name", "?"),
            "baseline_rate": base_rate,
            "current_rate": cur_rate,
            "delta": round(cur_rate - base_rate, 3),
            "baseline_n": b.get("n_scenarios", 0),
            "current_n": c.get("n_scenarios", 0),
        })
    rows.sort(key=lambda r: r["delta"])  # regressions first
    return rows


# === Tool diff ===

def diff_tools(
    current: dict[str, dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    """Identify tools newly covered, newly missing, unchanged."""
    all_tools = set(current.keys()) | set(baseline.keys())
    newly_covered: list[str] = []
    newly_missing: list[str] = []
    unchanged: list[str] = []
    for t in sorted(all_tools):
        cur_cov = current.get(t, {}).get("covered", False)
        base_cov = baseline.get(t, {}).get("covered", False)
        if cur_cov and not base_cov:
            newly_covered.append(t)
        elif base_cov and not cur_cov:
            newly_missing.append(t)
        elif cur_cov == base_cov:
            unchanged.append(t)
    return {
        "newly_covered": newly_covered,
        "newly_missing": newly_missing,
        "unchanged": unchanged,
    }


# === Gap diff ===

def diff_gaps(
    current_gaps: list[dict[str, Any]],
    baseline_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Identify gaps newly surfaced vs. resolved."""
    def _gap_key(g: dict[str, Any]) -> tuple[str, str]:
        who = g.get("anchor") or g.get("tool") or g.get("scenario_day") or "?"
        return (g.get("kind", "?"), str(who))

    current_set = {_gap_key(g) for g in current_gaps}
    baseline_set = {_gap_key(g) for g in baseline_gaps}

    new = sorted(current_set - baseline_set)
    resolved = sorted(baseline_set - current_set)
    persistent = sorted(current_set & baseline_set)
    return {
        "new": [{"kind": k, "who": w} for k, w in new],
        "resolved": [{"kind": k, "who": w} for k, w in resolved],
        "persistent": [{"kind": k, "who": w} for k, w in persistent],
        "n_current": len(current_set),
        "n_baseline": len(baseline_set),
        "n_delta": len(current_set) - len(baseline_set),
    }


# === Render markdown ===

def render_drift_report(
    score_delta: dict[str, float],
    anchor_rows: list[dict[str, Any]],
    tool_delta: dict[str, list[str]],
    gap_delta: dict[str, Any],
    baseline_meta: dict[str, Any] | None = None,
    current_meta: dict[str, Any] | None = None,
    score_current: dict[str, float] | None = None,
    score_baseline: dict[str, float] | None = None,
) -> str:
    out: list[str] = []
    out += [
        "# Backtest Drift Report",
        "",
        f"_Generated: {datetime.now().isoformat(timespec='seconds')}_",
        "",
    ]

    # Score delta summary
    total_delta = score_delta.get("total_score", 0.0)
    trend = "📈 IMPROVING" if total_delta > 0.5 else ("📉 REGRESSING" if total_delta < -0.5 else "➡️  STABLE")
    out += [
        f"## {trend} — total score delta = {total_delta:+.2f}",
        "",
        "| Dimension | Baseline | Current | Δ |",
        "|-----------|----------|---------|---|",
    ]
    for dim in [
        "anchor_pass_rate_pct",
        "tool_coverage_pct",
        "schema_valid_pct",
        "scenario_pass_rate_pct",
        "total_score",
    ]:
        delta = score_delta.get(dim, 0.0)
        flag = "↑" if delta > 0.5 else ("↓" if delta < -0.5 else "=")
        base_v = (score_baseline or {}).get(dim, 0.0)
        cur_v = (score_current or {}).get(dim, 0.0)
        out.append(f"| `{dim}` | {base_v:.1f} | {cur_v:.1f} | {delta:+.2f} {flag} |")
    out += [""]

    # Anchor diff
    out += [
        "## Per-anchor drift (sorted by largest regression)",
        "",
        "| # | Anchor | Baseline | Current | Δ | n_baseline | n_current |",
        "|---|--------|----------|---------|---|------------|-----------|",
    ]
    for r in anchor_rows:
        flag = "📉" if r["delta"] < -0.01 else ("📈" if r["delta"] > 0.01 else "=")
        out.append(
            f"| {r['anchor_id']} | {r['name']} | {r['baseline_rate']:.0%} | "
            f"{r['current_rate']:.0%} | {r['delta']:+.0%} {flag} | "
            f"{r['baseline_n']} | {r['current_n']} |"
        )
    out += [""]

    # Tool diff
    out += [
        "## Tool coverage drift",
        "",
        f"**Newly covered**: {len(tool_delta['newly_covered'])}",
        "",
    ]
    for t in tool_delta["newly_covered"]:
        out.append(f"- ✅ `{t}`")
    out += [
        "",
        f"**Newly missing**: {len(tool_delta['newly_missing'])}",
        "",
    ]
    for t in tool_delta["newly_missing"]:
        out.append(f"- ❌ `{t}`")
    out += [
        "",
        f"**Unchanged**: {len(tool_delta['unchanged'])}",
        "",
    ]

    # Gap diff
    out += [
        "## Gap drift",
        "",
        f"Baseline gaps: {gap_delta['n_baseline']} | Current gaps: {gap_delta['n_current']} | Δ = {gap_delta['n_delta']:+d}",
        "",
        f"**New gaps ({len(gap_delta['new'])})**:",
        "",
    ]
    for g in gap_delta["new"]:
        out.append(f"- 🆕 `{g['kind']}` — {g['who']}")
    if not gap_delta["new"]:
        out.append("- (none)")
    out += [
        "",
        f"**Resolved gaps ({len(gap_delta['resolved'])})**:",
        "",
    ]
    for g in gap_delta["resolved"]:
        out.append(f"- ✅ `{g['kind']}` — {g['who']}")
    if not gap_delta["resolved"]:
        out.append("- (none)")
    out += [
        "",
        f"**Persistent gaps ({len(gap_delta['persistent'])})**:",
        "",
    ]
    for g in gap_delta["persistent"]:
        out.append(f"- ⚠ `{g['kind']}` — {g['who']}")
    if not gap_delta["persistent"]:
        out.append("- (none)")

    out += [
        "",
        "## Interpretation",
        "",
    ]
    if total_delta > 0.5:
        out.append(f"Harness/scenario improvements moved score +{total_delta:.2f}. Investigate which dimension contributed most.")
    elif total_delta < -0.5:
        out.append(f"Score regressed by {total_delta:.2f}. Check gap diff for newly surfaced failures.")
    else:
        out.append(f"Score stable at Δ{total_delta:+.2f}. Run-to-run variance is bounded by task state at run time.")
    out += [
        "",
        "- **Anchor regressions** (top of table) deserve immediate investigation.",
        "- **Newly missing tools** suggest a scenario dropped a tool from `expected_tools`, or the harness lost an action.",
        "- **New gaps** are more actionable than persistent gaps (they're new regressions).",
        "- **Persistent gaps** are stable failures — schedule them as separate workstreams.",
        "",
    ]
    return "\n".join(out) + "\n"


# === CLI ===

def load_judgment(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two backtest runs.")
    parser.add_argument(
        "--current", type=Path,
        default=REPO_ROOT / "reports" / "backtest-Q1-judgment.json",
    )
    parser.add_argument(
        "--baseline", type=Path,
        default=REPO_ROOT / "reports" / "backtest-Q1-judgment.bak.json",
    )
    parser.add_argument(
        "--out", type=Path,
        default=REPO_ROOT / "reports" / "backtest-drift.md",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--snapshot", action="store_true",
                        help="Snapshot current run as baseline (copy current to baseline path).")
    args = parser.parse_args(argv)

    if not args.current.exists():
        print(f"# Missing current file: {args.current}", file=sys.stderr)
        return 1

    if args.snapshot:
        # Snapshot mode: just copy current → baseline.
        import shutil
        if not args.baseline.exists():
            args.baseline.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(args.current, args.baseline)
            print(f"# Snapshotted {args.current} → {args.baseline}")
            return 0
        print(f"# Baseline already exists at {args.baseline}; not overwriting", file=sys.stderr)
        return 0

    if not args.baseline.exists():
        print(f"# Missing baseline file: {args.baseline}", file=sys.stderr)
        print(f"# Run with --snapshot first to create a baseline, or specify --baseline <other-file>", file=sys.stderr)
        return 1

    current = load_judgment(args.current)
    baseline = load_judgment(args.baseline)

    score_delta = diff_scores(current["scores"], baseline["scores"])
    score_current = current["scores"]
    score_baseline = baseline["scores"]
    anchor_rows = diff_anchors(current["anchors"], baseline["anchors"])
    tool_delta = diff_tools(current["tools"]["by_tool"], baseline["tools"]["by_tool"])
    gap_delta = diff_gaps(current["gaps"], baseline["gaps"])

    md = render_drift_report(
        score_delta, anchor_rows, tool_delta, gap_delta,
        score_current=score_current,
        score_baseline=score_baseline,
    )

    if args.dry_run:
        sys.stdout.write(md)
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(f"# Wrote {args.out} ({len(md)} chars)")
    print(json.dumps(score_delta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
