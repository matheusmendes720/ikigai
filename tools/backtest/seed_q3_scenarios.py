"""M114a — seed_q3_scenarios.py

Deterministic 28-day backtest scenario generator, vault-anchored (per M113 spec).

Reads `vault/**/*.md`:
- YAML frontmatter `date:` → day index
- `cluster:` → taskdog tag mapping
- `tags:` → reuse as scenario tags
- Inline `> **Status:**` blocks for drafts without frontmatter

Outputs `vault/drafts/q3-scenarios.yaml` (28 scenarios, 1/day × 4 weeks):

  ```yaml
  cycle_start: 2026-09-22
  cycle_end: 2026-10-19
  scenarios:
    - day: 1
      date: 2026-09-22
      category: add-task          # 7 categories: add/list/update/complete/decompose/daily-plan/weekly-review
      prompt: |
        Day 1 — fresh start of the Q4 build cycle.
        Anchor event: [[agentic-markdown-system-completion]] (vault/drafts/).
        Synthesized user utterance: "Add a leaf task for the deep-agent vault sync module under \
        the q4-deep-agent-build cluster with priority 7. Tags: deep-agent, vault-sync."
      expected_tools: [taskdog_create_task]
      expected_args:
        cluster: ikigai/plan
        tags_any: [deep-agent, vault-sync, q4-build]
      anchor_file: vault/drafts/agentic-markdown-system-completion.md
    ...
  coverage_target:
    add-task:          4
    list-tasks:        4
    update-task:       3
    complete-task:     3
    decompose:         4
    daily-plan:        7
    weekly-review:     3
    # total = 28
    tool_invocation_count_per_tool: 3
    target_tools:
      - taskdog_create_task
      - taskdog_list_tasks
      - taskdog_update_task
      - taskdog_complete_task
      - taskdog_reopen
      - taskdog_pause
      - taskdog_archive
      - taskdog_cancel
      - taskdog_get_task
      - taskdog_search_tasks
      - taskdog_get_metrics
      - taskdog_get_burndown
      - taskdog_get_executive_summary
      - taskdog_get_cognitive_debt_metrics
      - taskdog_get_q_high_e_low_metrics
      - taskdog_get_execution_rate
      - taskdog_get_daily_allocations
      - taskdog_set_deadline
      - taskdog_set_priority
      - taskdog_set_tags
      - taskdog_add_dependency
      - taskdog_remove_dependency
      - taskdog_create_note
      - taskdog_list_notes
      - taskdog_bulk_archive
      - taskdog_bulk_complete
  ```

CLI:
    python tools/backtest/seed_q3_scenarios.py [--out PATH] [--days N] [--anchor]
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_DIR = REPO_ROOT / "vault"
DEFAULT_OUT = REPO_ROOT / "vault" / "drafts" / "q3-scenarios.yaml"

# M113 spec: 7 categories with target counts summing to 28 days (4 weeks).
CATEGORY_COUNTS: dict[str, int] = {
    "add-task": 4,
    "list-tasks": 4,
    "update-task": 3,
    "complete-task": 3,
    "decompose": 4,
    "daily-plan": 7,
    "weekly-review": 3,
}

# Per M113 §3: which tool each category should primarily exercise.
# M117: complete-task + weekly-review also exercise taskdog_audit_drift
# (the agent's Routine Inicial/Final drift check from M114f).
CATEGORY_EXPECTED_TOOLS: dict[str, list[str]] = {
    "add-task": ["taskdog_create_task"],
    "list-tasks": ["taskdog_list_tasks", "taskdog_search_tasks"],
    "update-task": ["taskdog_update_task", "taskdog_set_priority", "taskdog_set_tags"],
    "complete-task": ["taskdog_complete_task", "taskdog_audit_drift"],
    "decompose": ["taskdog_create_task", "taskdog_add_dependency"],
    "daily-plan": ["taskdog_list_tasks", "taskdog_get_daily_allocations"],
    "weekly-review": ["taskdog_get_burndown", "taskdog_get_executive_summary", "taskdog_audit_drift"],
}

# M113 spec: 26 taskdog-mcp tools. Listed in taskdog-mcp server's own ordering.
TASKDOG_TOOLS: list[str] = [
    "taskdog_create_task",
    "taskdog_list_tasks",
    "taskdog_get_task",
    "taskdog_update_task",
    "taskdog_complete_task",
    "taskdog_reopen",
    "taskdog_pause",
    "taskdog_archive",
    "taskdog_cancel",
    "taskdog_search_tasks",
    "taskdog_set_priority",
    "taskdog_set_deadline",
    "taskdog_set_tags",
    "taskdog_add_dependency",
    "taskdog_remove_dependency",
    "taskdog_create_note",
    "taskdog_list_notes",
    "taskdog_get_metrics",
    "taskdog_get_burndown",
    "taskdog_get_executive_summary",
    "taskdog_get_cognitive_debt_metrics",
    "taskdog_get_q_high_e_low_metrics",
    "taskdog_get_execution_rate",
    "taskdog_get_daily_allocations",
    # M117: vault_diff audit — exercise via Routine Inicial/Final (anchor #7)
    "taskdog_audit_drift",
    "taskdog_bulk_archive",
    "taskdog_bulk_complete",
]


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse YAML frontmatter if present; empty dict otherwise."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}


def _gather_anchors() -> list[dict[str, Any]]:
    """Walk vault/ and pull every anchored event with date/cluster/tags.

    Returns a sorted list of dicts:
        {date, cluster, level, status, tags, file_path, title, body_excerpt}
    """
    anchors: list[dict[str, Any]] = []
    for md_file in sorted(VAULT_DIR.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        meta = _parse_frontmatter(text)
        if not meta:
            continue
        date = meta.get("date")
        if not date or not isinstance(date, str):
            continue
        # First heading = title candidate.
        title = ""
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        anchors.append(
            {
                "date": str(date),
                "cluster": meta.get("cluster", "ikigai/misc"),
                "level": meta.get("level", ""),
                "status": meta.get("status", ""),
                "tags": meta.get("tags", []) or [],
                "file_path": str(md_file.relative_to(REPO_ROOT)),
                "title": title,
                "type": meta.get("type", ""),
            }
        )
    return sorted(anchors, key=lambda a: a["date"])


def _build_category_rotation() -> list[str]:
    """Return a 28-item rotation following the CATEGORY_COUNTS distribution.

    Pattern: heavy on daily-plan (7), then distribute other categories.
    Deterministic — same input yields same rotation.
    """
    rotation: list[str] = []
    for cat, count in CATEGORY_COUNTS.items():
        rotation.extend([cat] * count)
    return sorted(rotation)  # sort deterministic


def _derive_user_utterance(category: str, anchor: dict[str, Any] | None, day_idx: int) -> str:
    """Synthesize a realistic user prompt from the category + (optional) vault anchor."""
    if anchor is None:
        # Generic scenario, day-only anchored.
        return (
            f"Day {day_idx} — {category}. No specific vault event; "
            "use generic deep-agent build context. Pick reasonable defaults."
        )
    title = anchor["title"] or anchor["file_path"]
    cluster = anchor["cluster"]
    return (
        f"Day {day_idx} — {category}. Anchor: {title} ({anchor['file_path']}, "
        f"cluster={cluster}, status={anchor['status']}, level={anchor['level']}). "
        "Generate a realistic user request that triggers this scenario."
    )


def _rotation_for_anchors() -> list[str]:
    """Sort categories by name + counts → deterministic 28-day order."""
    items = []
    for cat, n in CATEGORY_COUNTS.items():
        items.extend([cat] * n)
    return sorted(items)


def _expected_args_for(category: str, anchor: dict[str, Any] | None) -> dict[str, Any]:
    """Pick expected_args based on category. Anchored when possible."""
    if anchor is None:
        return {"cluster": "ikigai/misc", "tags_any": []}
    return {
        "cluster": anchor["cluster"],
        "tags_any": [
            t.replace(" ", "-") for t in (anchor.get("tags") or []) if isinstance(t, str)
        ][:3]
        or ["deep-agent"],
    }


def _select_anchors_per_day(
    anchors: list[dict[str, Any]],
    n_days: int,
    cycle_start: str,
) -> list[dict[str, Any] | None]:
    """Pick an anchor for each day (day1..dayN). Stable: same anchors → same order.

    Days with no matching-anchor fallback to None (generic scenario).
    """
    from datetime import date, timedelta

    if not anchors:
        return [None] * n_days
    start = date.fromisoformat(cycle_start)
    by_day: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for a in anchors:
        try:
            d = date.fromisoformat(a["date"])
        except (TypeError, ValueError):
            continue
        delta = (d - start).days
        if 0 <= delta < n_days:
            by_day[delta].append(a)
    out: list[dict[str, Any] | None] = []
    for i in range(n_days):
        bucket = by_day.get(i) or by_day.get(min(by_day.keys(), default=0), [])
        if bucket:
            # Deterministic pick via hash(seed+day).
            seed = f"{cycle_start}-{i}".encode()
            idx = int(hashlib.sha256(seed).hexdigest()[:8], 16) % len(bucket)
            out.append(bucket[idx])
        else:
            out.append(None)
    return out


def build_scenarios(cycle_start: str, n_days: int = 28) -> dict[str, Any]:
    """Build the full scenarios dict (the YAML structure above)."""
    anchors = _gather_anchors()
    daily_anchors = _select_anchors_per_day(anchors, n_days, cycle_start)
    rotation = _rotation_for_anchors()
    if len(rotation) != n_days:
        raise ValueError(
            f"CATEGORY_COUNTS must sum to {n_days}: got {sum(CATEGORY_COUNTS.values())}"
        )

    from datetime import date, timedelta

    scenarios: list[dict[str, Any]] = []
    cycle_start_date = date.fromisoformat(cycle_start)
    for i, (cat, anchor) in enumerate(zip(rotation, daily_anchors)):
        day_date = cycle_start_date + timedelta(days=i)
        prompt = _derive_user_utterance(cat, anchor, i + 1)
        scenario: dict[str, Any] = {
            "day": i + 1,
            "date": day_date.isoformat(),
            "category": cat,
            "prompt": prompt,
            "expected_tools": CATEGORY_EXPECTED_TOOLS[cat],
            "expected_args": _expected_args_for(cat, anchor),
        }
        if anchor is not None:
            scenario["anchor_file"] = anchor["file_path"]
        scenarios.append(scenario)

    return {
        "cycle_start": cycle_start,
        "cycle_end": (cycle_start_date + timedelta(days=n_days - 1)).isoformat(),
        "anchor_count": len(anchors),
        "anchor_files_used": sum(1 for a in daily_anchors if a is not None),
        "scenarios": scenarios,
        "coverage_target": {
            "scenarios_per_category": CATEGORY_COUNTS,
            "tool_invocation_count_per_tool": 3,
            "target_tools": TASKDOG_TOOLS,
        },
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    """Tiny YAML loader used only when yaml is missing or sentinel needed."""
    # We import yaml above; this is a safety net for forge-style subloaders.
    import yaml as _y

    return _y.safe_load(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate 28-day backtest scenarios from vault/")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output YAML path (default: {DEFAULT_OUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=28,
        help="Number of days in the cycle (default: 28 = 4 weeks)",
    )
    parser.add_argument(
        "--cycle-start",
        type=str,
        default="2026-09-22",
        help="Cycle start date (ISO YYYY-MM-DD). Defaults to 2026-09-22.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary to stdout instead of writing YAML",
    )
    parser.add_argument(
        "--anchor",
        action="store_true",
        help="Show which vault files were used as anchors and exit.",
    )
    args = parser.parse_args(argv)

    if args.anchor:
        anchors = _gather_anchors()
        print(f"# Total anchored events in vault/: {len(anchors)}")
        for a in anchors:
            print(f"  {a['date']} [{a['cluster']}/{a['type']}] {a['title']!r}  ← {a['file_path']}")
        return 0

    scenarios = build_scenarios(args.cycle_start, args.days)
    cat_counts = Counter(s["category"] for s in scenarios["scenarios"])
    tool_count = sum(len(s["expected_tools"]) for s in scenarios["scenarios"])
    summary = {
        "total_scenarios": len(scenarios["scenarios"]),
        "scenarios_per_category": dict(cat_counts),
        "total_tool_invocations_planned": tool_count,
        "anchor_files_used": scenarios["anchor_files_used"],
        "anchor_files_total": scenarios["anchor_count"],
        "days": args.days,
        "cycle_start": args.cycle_start,
        "cycle_end": scenarios["cycle_end"],
    }
    if args.dry_run:
        import json as _json

        print(_json.dumps(summary, indent=2))
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        yaml.safe_dump(scenarios, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    print(f"# Wrote {len(scenarios['scenarios'])} scenarios → {args.out}")
    print(f"# Summary: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
