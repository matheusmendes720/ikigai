"""M114g — backtest_report.py

Generates a human-readable markdown report from harness results + judgment.

Usage:
    python tools/backtest/backtest_report.py [--results ...] [--judgment ...] [--out ...]
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

from tools.backtest.role_anchors import ROLE_ANCHORS  # noqa: E402


def render_report(
    results: dict[str, Any],
    judgment: dict[str, Any],
    *,
    cycle_start: str = "2026-09-22",
    cycle_end: str = "2026-10-19",
) -> str:
    """Returns a markdown string."""
    scores = judgment["scores"]
    anchors = judgment["anchors"]
    tools = judgment["tools"]
    gaps = judgment["gaps"]
    out: list[str] = []
    by_tool = results.get("by_tool", {})
    n_total = results.get("n_total", 0)
    n_pass = results.get("n_pass", 0)
    n_skip = results.get("n_skip", 0)
    n_error = results.get("n_error", 0)
    elapsed = results.get("elapsed_seconds", "?")

    out += [
        f"# Backtest Q1 — {cycle_start} → {cycle_end}",
        "",
        f"_Generated: {datetime.now().isoformat(timespec='seconds')}_",
        "",
        "## TL;DR",
        "",
        f"**{scores['total_score']:.1f} / 100** — backtest of {n_total} deterministic scenarios through real taskdog-server.",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Scenarios PASS | {n_pass} |",
        f"| Scenarios SKIP | {n_skip} (lifecycle-blocked, expected) |",
        f"| Scenarios ERROR | {n_error} |",
        f"| Tools exercised | {len(by_tool)} unique |",
        f"| Anchors met | {sum(1 for v in anchors.values() if v.get('n_scenarios', 0) > 0 and v.get('pass_rate', 0) > 0)} of {len(anchors)} |",
        f"| Elapsed | {elapsed}s |",
        "",
        "## Score breakdown",
        "",
        "| Dimension | Weight | Score |",
        "|-----------|--------|-------|",
        f"| Anchor pass rate | 0.40 | {scores['anchor_pass_rate_pct']:.1f}% |",
        f"| Tool coverage | 0.30 | {scores['tool_coverage_pct']:.1f}% |",
        f"| Schema valid | 0.10 | {scores['schema_valid_pct']:.1f}% |",
        f"| Scenario pass rate | 0.20 | {scores['scenario_pass_rate_pct']:.1f}% |",
        f"| **TOTAL** | 1.00 | **{scores['total_score']:.1f}/100** |",
        "",
        "## Per-anchor coverage",
        "",
        "| # | Anchor | Scenarios | PASS | SKIP | ERROR | Pass rate |",
        "|---|--------|-----------|------|------|-------|-----------|",
    ]

    # Sort anchors by pass_rate ascending so low-coverage surfaces first.
    sorted_anchors = sorted(anchors.items(), key=lambda kv: kv[1].get("pass_rate", 0))
    for aid, v in sorted_anchors:
        flag = "✓" if v["pass_rate"] >= 0.95 else ("⚠" if v["pass_rate"] >= 0.5 else "✗")
        out.append(
            f"| {aid} | {v['name']} | {v['n_scenarios']} | {v['n_pass']} | {v['n_skip']} | "
            f"{v['n_error']} | {v['pass_rate']:.0%} {flag} |"
        )

    out += [
        "",
        "## Per-tool coverage",
        "",
        "Coverage matrix: which tools the corpus expected vs. which the harness called.",
        "",
        "| Tool | Expected | Actual | Covered |",
        "|------|----------|--------|---------|",
    ]
    sorted_tools = sorted(tools["by_tool"].items(), key=lambda kv: (kv[1]["covered"], kv[0]))
    for t, v in sorted_tools:
        flag = "✓" if v["covered"] else "✗"
        out.append(f"| `{t}` | {v['expected']} | {v['actual']} | {flag} |")

    out += [
        "",
        f"**Coverage**: {tools['expected_unique_tools']} expected tools, "
        f"{tools['actual_unique_tools']} actually exercised, "
        f"{len(tools['missing_tools'])} missing.",
        "",
        "## Tool invocation totals (from harness run)",
        "",
        "| Tool | Times called |",
        "|------|--------------|",
    ]
    for tool, count in sorted(by_tool.items()):
        out.append(f"| `{tool}` | {count} |")

    out += [
        "",
        "## Gaps identified",
        "",
    ]
    if not gaps:
        out.append("No gaps. Harness meets all measurable criteria.")
    else:
        gap_counts = Counter(g["kind"] for g in gaps)
        out += [
            "| Gap kind | Count |",
            "|----------|-------|",
        ]
        for kind, n in gap_counts.most_common():
            out.append(f"| `{kind}` | {n} |")
        out += ["", "### Detail", ""]
        for g in gaps:
            who = g.get("anchor") or g.get("tool") or g.get("scenario_day") or "?"
            out.append(f"- **[{g['kind']}]** `{who}` — {g['detail']}")

    out += [
        "",
        "## Methodology",
        "",
        "- **Harness** (`backtest_harness.py`) runs 73 padded scenarios through real taskdog-server HTTP API.",
        "- **Judge** (`judge_llm.py`) scores 4 dimensions: anchor pass rate, tool coverage, schema validity, scenario pass rate.",
        "- **Anchors** = 11 role-anchor requirements from M113 v2 spec (drilled from strategics/ + algorithm-attribution-design.md).",
        "- **Tools** = canonical 26 taskdog-mcp tool names (excludes server-missing tools from coverage denominator).",
        "- **SKIP** = real-world blocker (task depends on upstream, lifecycle conflict); counted as 50% credit for anchor scoring.",
        "",
        "## Next steps",
        "",
    ]
    server_missing = [g for g in gaps if g["kind"] == "tool_server_missing"]
    if server_missing:
        out += [
            f"- Resolve {len(server_missing)} `tool_server_missing` gaps: either add HTTP endpoints to taskdog-server, or mark tools as retired in `seed_q3_scenarios.py`.",
        ]
    harness_missing = [g for g in gaps if g["kind"] == "tool_under_exercised"]
    if harness_missing:
        out += [
            f"- Fix {len(harness_missing)} harness coverage gaps in `backtest_harness.py`.",
        ]
    if not server_missing and not harness_missing:
        out += ["- Run again next quarter to track coverage drift."]
    out += [
        "- Consider adding **LLM-judge** dimension for qualitative scoring (was the response helpful, did it cite vault sources, etc.).",
        "- Add **argument-validation** dimension: did the agent pass the right args to each tool?",
        "- Wire `audit_drift` from M114f into the harness so anchor #7 (propagation driver) is exercised end-to-end.",
    ]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render backtest markdown report.")
    parser.add_argument(
        "--results", type=Path,
        default=REPO_ROOT / "reports" / "backtest-Q1-results.json",
    )
    parser.add_argument(
        "--judgment", type=Path,
        default=REPO_ROOT / "reports" / "backtest-Q1-judgment.json",
    )
    parser.add_argument(
        "--out", type=Path,
        default=REPO_ROOT / "reports" / "backtest-Q1.md",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing")
    parser.add_argument("--cycle-start", default="2026-09-22")
    parser.add_argument("--cycle-end", default="2026-10-19")
    args = parser.parse_args(argv)

    if not args.results.exists():
        print(f"# Missing results file: {args.results}", file=sys.stderr)
        return 1
    if not args.judgment.exists():
        print(f"# Missing judgment file: {args.judgment}", file=sys.stderr)
        return 1

    results = json.loads(args.results.read_text(encoding="utf-8"))
    judgment = json.loads(args.judgment.read_text(encoding="utf-8"))
    md = render_report(
        results, judgment,
        cycle_start=args.cycle_start,
        cycle_end=args.cycle_end,
    )
    if args.dry_run:
        sys.stdout.write(md)
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(f"# Wrote {args.out} ({len(md)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
