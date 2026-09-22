"""M114d — taskdog_exhaustiveness.py

Tool coverage mapper for backtesting. Given the 28-scenario YAML from M114a,
ensures each of the 26 taskdog-mcp tools is exercised at least N times across
the cycle. Tools with under-coverage get synthetic supplemental scenarios
appended; tools over-covered keep their natural distribution.

Outputs:
  vault/drafts/q3-scenarios.exhaustive.yaml  (coverage-padded scenario list)

CLI:
    python tools/backtest/taskdog_exhaustiveness.py [--invocations-per-tool N] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Re-use canonical 26-tool enum from M114a.
from tools.backtest.seed_q3_scenarios import (  # noqa: E402
    CATEGORY_COUNTS,
    CATEGORY_EXPECTED_TOOLS,
    TASKDOG_TOOLS,
)

DEFAULT_SCENARIOS = REPO_ROOT / "vault" / "drafts" / "q3-scenarios.yaml"
DEFAULT_OUT = REPO_ROOT / "vault" / "drafts" / "q3-scenarios.exhaustive.yaml"


# Category authoring hints — for synthetic scenarios that exercise a specific
# tool, this picks a category whose CATEGORY_EXPECTED_TOOLS contains that tool.
# Result: synthetic scenarios look real, not arbitrary.
CATEGORY_TOOL_HINTS: dict[str, str] = {
    # Realistic user-prompt fragments per category.
    "add-task": (
        "User asks to add a single new task — 'Add a leaf task for the "
        "{topic} cluster with priority 5 and tag {tag}.'"
    ),
    "list-tasks": (
        "User wants to list today's PENDING tasks filtered by status and "
        "{tag} tag — exercise of list/search tooling."
    ),
    "update-task": (
        "User wants to bump priority on task {task_id} from 5 to 8 and "
        "add tag {tag} — update/set_priority/set_tags exercise."
    ),
    "complete-task": (
        "User marks task {task_id} as complete — exercise of complete_task."
    ),
    "decompose": (
        "User wants a 3-step decomposition of '{topic}' with dependencies — "
        "exercise of create_task + add_dependency."
    ),
    "daily-plan": (
        "User asks for today's daily plan — exercise of list_tasks + "
        "get_daily_allocations."
    ),
    "weekly-review": (
        "User asks for last week's burndown + executive summary — exercise "
        "of get_burndown + get_executive_summary + get_metrics."
    ),
}


def _build_current_coverage(scenarios: list[dict[str, Any]]) -> Counter[str]:
    """Count current tool invocations across the scenarios list."""
    coverage: Counter[str] = Counter()
    for sc in scenarios:
        for tool in sc.get("expected_tools", []):
            coverage[tool] += 1
    return coverage


def _pick_category_for_tool(tool: str) -> str:
    """Choose the natural category for an under-covered tool."""
    for cat, tools in CATEGORY_EXPECTED_TOOLS.items():
        if tool in tools:
            return cat
    # Fallback: most-common category (daily-plan), produces a generic synthetic.
    return "daily-plan"


def _make_synthetic_scenario(
    day: int,
    date: str,
    category: str,
    tool: str,
    topic: str,
    tag: str,
) -> dict[str, Any]:
    """Forge a plausible scenario whose expected_tools includes `tool`."""
    template = CATEGORY_TOOL_HINTS.get(category, "Generic scenario for {tool}.")
    prompt = template.format(topic=topic, tag=tag, task_id=f"tsk:{tool[:4]}-{day:02d}", tool=tool)
    return {
        "day": day,
        "date": date,
        "category": category,
        "prompt": prompt,
        "expected_tools": [tool],
        "expected_args": {
            "cluster": "ikigai/plan",
            "tags_any": [tag],
            "synthetic": True,  # marker so M114b backtest harness can flag.
        },
        "synthetic_for_tool": tool,
    }


def _pad_coverage(
    scenarios: list[dict[str, Any]],
    target_invocations: int,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int]]:
    """Pad scenarios so every tool has >= target_invocations coverage.

    Returns: (padded, added_per_tool, before_coverage)
    """
    coverage = _build_current_coverage(scenarios)
    before = dict(coverage)

    # Synthetic topics / tags — deterministic per tool for stable tests.
    synth_topics = {
        "taskdog_create_task": ("vault-sync", "deep-agent"),
        "taskdog_list_tasks": ("today-pending", "p0"),
        "taskdog_get_task": ("trace-evt-001", "ops"),
        "taskdog_update_task": ("mission-critical", "ops"),
        "taskdog_complete_task": ("smoke-cycle-finish", "ops"),
        "taskdog_reopen": ("reopen-regression-test", "ops"),
        "taskdog_pause": ("context-switch-pause", "ops"),
        "taskdog_archive": ("archive-old-cycle", "archive"),
        "taskdog_cancel": ("cancel-deferred-idea", "ops"),
        "taskdog_search_tasks": ("priority-floor", "ops"),
        "taskdog_set_priority": ("bump-priority-test", "ops"),
        "taskdog_set_deadline": ("deadline-tighten", "deadline-this-week"),
        "taskdog_set_tags": ("tag-retro", "ops"),
        "taskdog_add_dependency": ("dep-blocker-unblock", "ops"),
        "taskdog_remove_dependency": ("dep-cleanup", "ops"),
        "taskdog_create_note": ("postmortem-note", "ops"),
        "taskdog_list_notes": ("trace-notes-week", "ops"),
        "taskdog_get_metrics": ("weekly-metrics", "ops"),
        "taskdog_get_burndown": ("burndown-week", "ops"),
        "taskdog_get_executive_summary": ("exec-summary-week", "ops"),
        "taskdog_get_cognitive_debt_metrics": ("cog-debt", "ops"),
        "taskdog_get_q_high_e_low_metrics": ("q-h-e-l", "ops"),
        "taskdog_get_execution_rate": ("exec-rate", "ops"),
        "taskdog_get_daily_allocations": ("alloc-today", "ops"),
        "taskdog_bulk_archive": ("bulk-archive-cleanup", "archive"),
        "taskdog_bulk_complete": ("bulk-finish-cycle", "ops"),
    }

    synthetic_day = 1000  # synthetic days numbered 1000+ to not collide with 1..28.
    added: dict[str, int] = defaultdict(int)
    padded: list[dict[str, Any]] = list(scenarios)

    for tool in TASKDOG_TOOLS:
        while coverage[tool] < target_invocations:
            cat = _pick_category_for_tool(tool)
            topic, tag = synth_topics.get(tool, (tool.replace("_", "-"), "ops"))
            sc = _make_synthetic_scenario(
                day=synthetic_day,
                date=f"2026-cycle-synth-{synthetic_day:04d}",
                category=cat,
                tool=tool,
                topic=topic,
                tag=tag,
            )
            padded.append(sc)
            coverage[tool] += 1
            added[tool] += 1
            synthetic_day += 1

    return padded, dict(added), before


def build_coverage_report(
    scenarios: list[dict[str, Any]],
    target_invocations: int = 3,
) -> dict[str, Any]:
    """Build the full padded-scenarios + coverage-matrix report."""
    padded, added_per_tool, before = _pad_coverage(scenarios, target_invocations)
    after = _build_current_coverage(padded)

    tools_under = {
        t: target_invocations - after[t] for t in TASKDOG_TOOLS if after[t] < target_invocations
    }
    tools_meeting = {
        t: after[t] for t in TASKDOG_TOOLS if after[t] >= target_invocations
    }
    return {
        "scenarios": padded,
        "cycle_start": scenarios[0]["date"] if scenarios else None,
        "anchor_count": len(padded) - len(scenarios),
        "coverage": {
            "target_invocations_per_tool": target_invocations,
            "before": before,
            "added": added_per_tool,
            "after": dict(after),
            "tools_under_target": tools_under,
            "tools_meeting_target": tools_meeting,
            "max_invocation_count": max(after.values()) if after else 0,
            "min_invocation_count": min(after[t] for t in TASKDOG_TOOLS),
            "total_tools": len(TASKDOG_TOOLS),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pad 28-day scenarios so every taskdog tool meets minimum invocation count."
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=DEFAULT_SCENARIOS,
        help=f"Input YAML (default: {DEFAULT_SCENARIOS.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output YAML (default: {DEFAULT_OUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--invocations-per-tool",
        type=int,
        default=3,
        help="Minimum invocations per tool (default: 3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print coverage matrix to stdout, do not write YAML",
    )
    args = parser.parse_args(argv)

    if not args.scenarios.exists():
        print(f"# Missing input: {args.scenarios}. Run seed_q3_scenarios first.", file=sys.stderr)
        return 1

    src = yaml.safe_load(args.scenarios.read_text(encoding="utf-8"))
    scenarios = src.get("scenarios", [])
    if not scenarios:
        print("# Input scenarios list is empty.", file=sys.stderr)
        return 1

    report = build_coverage_report(scenarios, args.invocations_per_tool)
    cov = report["coverage"]

    if args.dry_run:
        print(f"# Cycle start: {report['cycle_start']}")
        print(f"# Tools: {cov['total_tools']}")
        print(f"# Target invocations/tool: {cov['target_invocations_per_tool']}")
        print(f"# Min invocations: {cov['min_invocation_count']}")
        print(f"# Max invocations: {cov['max_invocation_count']}")
        print(f"# Synthetic scenarios added: {report['anchor_count']}")
        print("# Coverage (added → final count per tool):")
        for t in TASKDOG_TOOLS:
            added = cov["added"].get(t, 0)
            after = cov["after"].get(t, 0)
            flag = " ✓" if after >= cov["target_invocations_per_tool"] else " ✗"
            print(f"  {t:<48} +{added} → {after}{flag}")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    print(
        f"# Wrote {len(report['scenarios'])} scenarios "
        f"(+{report['anchor_count']} synthetic) → {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
