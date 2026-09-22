"""M114c — judge_llm.py

Rule-based scoring of harness outcomes against expected scenario intent.

The judge does NOT need an LLM. It evaluates:
  1. Per-scenario: did the harness call the right tool? (expected_tools coverage)
  2. Per-anchor: how many scenarios for each anchor PASS vs SKIP vs ERROR?
  3. Per-tool coverage: did the corpus actually exercise the expected tools?
  4. Schema validation: do all expected_tools have a real implementation?

Output: a 0-100 score per dimension + total + actionable gaps.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest.role_anchors import ROLE_ANCHORS  # noqa: E402
from tools.backtest.seed_q3_scenarios import TASKDOG_TOOLS  # noqa: E402


# === Dimension 1: per-scenario expected_tools coverage ===

@dataclass
class ScenarioJudgment:
    day: int
    category: str
    anchors: list[int]
    expected_tools: list[str]
    actual_tools: list[str]
    status: str
    tool_coverage: float = 0.0  # expected ∩ actual / expected
    details: str = ""


def judge_scenario(
    sc: dict[str, Any],
    outcome: dict[str, Any],
    anchor_map: dict[int, list[int]],
) -> ScenarioJudgment:
    day = sc.get("day", 0)
    expected = set(sc.get("expected_tools", []))
    actual = set(outcome.get("tools_called", []))
    if expected:
        covered = expected & actual
        cov = len(covered) / len(expected)
    else:
        cov = 1.0  # No expected tool → vacuously satisfied.

    status = outcome.get("status", "PENDING")
    return ScenarioJudgment(
        day=day,
        category=sc.get("category", ""),
        anchors=anchor_map.get(day, []),
        expected_tools=sorted(expected),
        actual_tools=sorted(actual),
        status=status,
        tool_coverage=cov,
        details=outcome.get("detail", ""),
    )


# === Dimension 2: anchor score ===

def judge_anchor(judgments: list[ScenarioJudgment]) -> dict[int, dict[str, Any]]:
    """For each anchor: count scenarios that touched it, % PASS, % SKIP, % ERROR."""
    by_anchor: dict[int, list[ScenarioJudgment]] = {}
    for j in judgments:
        for aid in j.anchors:
            by_anchor.setdefault(aid, []).append(j)

    out: dict[int, dict[str, Any]] = {}
    for a in ROLE_ANCHORS:
        items = by_anchor.get(a.id, [])
        if not items:
            out[a.id] = {
                "name": a.name,
                "n_scenarios": 0,
                "n_pass": 0, "n_skip": 0, "n_error": 0,
                "pass_rate": 0.0,
            }
            continue
        n_pass = sum(1 for j in items if j.status == "PASS")
        n_skip = sum(1 for j in items if j.status == "SKIP")
        n_error = sum(1 for j in items if j.status == "ERROR")
        # Treat SKIP as partial credit: SKIP is "world harder than harness",
        # not a harness bug. Half credit.
        n_eff = n_pass + 0.5 * n_skip
        rate = n_eff / len(items) if items else 0.0
        out[a.id] = {
            "name": a.name,
            "n_scenarios": len(items),
            "n_pass": n_pass, "n_skip": n_skip, "n_error": n_error,
            "pass_rate": round(rate, 3),
        }
    return out


# === Dimension 3: tool coverage ===

def judge_tool_coverage(judgments: list[ScenarioJudgment]) -> dict[str, Any]:
    """Did the corpus actually exercise the tools it expected to?"""
    expected_all: Counter[str] = Counter()
    actual_all: Counter[str] = Counter()
    expected_only: set[str] = set()
    for j in judgments:
        for t in j.expected_tools:
            expected_all[t] += 1
        for t in j.actual_tools:
            actual_all[t] += 1
        expected_only.update(j.expected_tools)
    missing = sorted(expected_only - set(actual_all.keys()))
    unexpected = sorted(set(actual_all.keys()) - expected_only)
    return {
        "expected_total": sum(expected_all.values()),
        "actual_total": sum(actual_all.values()),
        "expected_unique_tools": len(expected_all),
        "actual_unique_tools": len(actual_all),
        "missing_tools": missing,
        "unexpected_tools": unexpected,
        "by_tool": {
            t: {
                "expected": expected_all[t],
                "actual": actual_all[t],
                "covered": expected_all[t] > 0 and actual_all[t] > 0,
            }
            for t in sorted(set(expected_all) | set(actual_all))
        },
    }


# === Dimension 4: schema validation ===

def judge_schema(judgments: list[ScenarioJudgment]) -> dict[str, Any]:
    """Validate that expected_tools names follow taskdog-mcp naming convention."""
    known = set(TASKDOG_TOOLS)
    bad: list[tuple[int, str]] = []
    for j in judgments:
        for t in j.expected_tools:
            if t not in known:
                bad.append((j.day, t))
    return {
        "known_tools_count": len(known),
        "unknown_tools_referenced": bad,
        "schema_valid": len(bad) == 0,
    }


# === Overall score ===

WEIGHTS = {
    "anchor_pass_rate": 0.40,
    "tool_coverage": 0.30,
    "schema_valid": 0.10,
    "scenario_pass_rate": 0.20,
}


def compute_total_score(
    anchor_scores: dict[int, dict[str, Any]],
    tool_cov: dict[str, Any],
    schema: dict[str, Any],
    judgments: list[ScenarioJudgment],
) -> dict[str, Any]:
    if not anchor_scores:
        anchor_overall = 0.0
    else:
        anchor_overall = sum(v["pass_rate"] for v in anchor_scores.values()) / len(anchor_scores)
    # Tools in MCP spec but no HTTP endpoint — excluded from coverage denominator.
    SERVER_MISSING_TOOLS = {
        "taskdog_search_tasks", "taskdog_bulk_archive", "taskdog_bulk_complete",
        "taskdog_get_cognitive_debt_metrics", "taskdog_get_q_high_e_low_metrics",
        "taskdog_get_execution_rate", "taskdog_get_executive_summary",
    }
    expected_in_harness = {
        t for t in tool_cov["by_tool"]
        if t not in SERVER_MISSING_TOOLS and tool_cov["by_tool"][t]["expected"] > 0
    }
    if expected_in_harness:
        coverage = (
            len(expected_in_harness) - len(set(tool_cov["missing_tools"]) & expected_in_harness)
        ) / len(expected_in_harness)
    else:
        coverage = 1.0
    schema_score = 1.0 if schema["schema_valid"] else 0.0
    if judgments:
        pass_rate = sum(1 for j in judgments if j.status == "PASS") / len(judgments)
    else:
        pass_rate = 0.0

    total = (
        WEIGHTS["anchor_pass_rate"] * anchor_overall
        + WEIGHTS["tool_coverage"] * coverage
        + WEIGHTS["schema_valid"] * schema_score
        + WEIGHTS["scenario_pass_rate"] * pass_rate
    ) * 100

    return {
        "anchor_pass_rate_pct": round(anchor_overall * 100, 1),
        "tool_coverage_pct": round(coverage * 100, 1),
        "schema_valid_pct": round(schema_score * 100, 1),
        "scenario_pass_rate_pct": round(pass_rate * 100, 1),
        "total_score": round(total, 1),
    }


# === Gaps report ===

def identify_gaps(
    anchor_scores: dict[int, dict[str, Any]],
    tool_cov: dict[str, Any],
    schema: dict[str, Any],
) -> list[dict[str, str]]:
    # Tools that exist in the MCP spec but have no corresponding HTTP endpoint
    # on the live taskdog-server. Coverage gaps here are spec/server drift, not
    # harness bugs. Surfaced separately so the report can call them out.
    SERVER_MISSING_TOOLS = {
        "taskdog_search_tasks", "taskdog_bulk_archive", "taskdog_bulk_complete",
        "taskdog_get_cognitive_debt_metrics", "taskdog_get_q_high_e_low_metrics",
        "taskdog_get_execution_rate", "taskdog_get_executive_summary",
    }
    gaps: list[dict[str, str]] = []
    for aid, v in anchor_scores.items():
        if v["n_scenarios"] == 0:
            gaps.append({
                "kind": "anchor_no_scenarios",
                "anchor": v["name"],
                "detail": "No scenarios map to this anchor; harness can't evaluate it.",
            })
        elif v["pass_rate"] < 0.7:
            gaps.append({
                "kind": "anchor_low_pass",
                "anchor": v["name"],
                "detail": f"pass_rate={v['pass_rate']:.0%} < 70%; review scenarios or harness.",
            })
    for t in tool_cov["missing_tools"]:
        if t in SERVER_MISSING_TOOLS:
            gaps.append({
                "kind": "tool_server_missing",
                "tool": t,
                "detail": (
                    "Tool is in MCP spec but no HTTP endpoint on live taskdog-server. "
                    "Either add endpoint, or mark tool as retired in spec."
                ),
            })
        else:
            gaps.append({
                "kind": "tool_under_exercised",
                "tool": t,
                "detail": "Harness did not call this expected tool; add action coverage.",
            })
    for day, tool in schema["unknown_tools_referenced"]:
        gaps.append({
            "kind": "schema_invalid",
            "scenario_day": str(day),
            "tool": tool,
            "detail": "Tool name not in known taskdog-mcp toolset; check spelling.",
        })
    return gaps


# === Driver ===

def judge_run(
    scenarios: list[dict[str, Any]],
    harness_results: dict[str, Any],
    anchor_map_doc: dict[str, Any],
) -> dict[str, Any]:
    anchor_map: dict[int, list[int]] = {}
    if isinstance(anchor_map_doc, dict) and "scenarios" in anchor_map_doc:
        anchor_map = {int(k): list(v) for k, v in anchor_map_doc["scenarios"].items()}

    outcomes = harness_results.get("outcomes", [])
    judgments = [
        judge_scenario(sc, oc, anchor_map)
        for sc, oc in zip(scenarios, outcomes)
    ]
    anchor_scores = judge_anchor(judgments)
    tool_cov = judge_tool_coverage(judgments)
    schema = judge_schema(judgments)
    total = compute_total_score(anchor_scores, tool_cov, schema, judgments)
    gaps = identify_gaps(anchor_scores, tool_cov, schema)

    return {
        "scores": total,
        "weights": WEIGHTS,
        "anchors": anchor_scores,
        "tools": tool_cov,
        "schema": schema,
        "gaps": gaps,
        "n_judged": len(judgments),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rule-based judge for backtest harness results.",
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=REPO_ROOT / "vault" / "drafts" / "q3-scenarios.with-anchors.yaml",
    )
    parser.add_argument(
        "--harness-results",
        type=Path,
        default=REPO_ROOT / "reports" / "backtest-Q1-results.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "backtest-Q1-judgment.json",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    import yaml  # noqa: E402

    if not args.scenarios.exists() or not args.harness_results.exists():
        print("# Missing inputs.", file=sys.stderr)
        return 1

    src = yaml.safe_load(args.scenarios.read_text(encoding="utf-8"))
    scenarios = src.get("scenarios", []) if isinstance(src, dict) else src
    anchor_map_doc = src.get("anchor_map", {}) if isinstance(src, dict) else {}
    harness_results = json.loads(args.harness_results.read_text(encoding="utf-8"))

    result = judge_run(scenarios, harness_results, anchor_map_doc)
    print(json.dumps(result["scores"], indent=2))
    if args.dry_run:
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"# Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
