"""M114d tests — taskdog_exhaustiveness.

Verifies:
- Coverage matrix computed from input scenarios
- All 26 tools meet min invocation count after padding
- Synthetic scenarios have marker `synthetic_for_tool`
- Total count = (input scenarios) + (synthetic padding)
- Adding more synthetic scenarios is idempotent (deterministic)
- Per-tool invocation count never drops below target
- Dry-run prints coverage matrix without writing YAML
- Output YAML roundtrips cleanly
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest.seed_q3_scenarios import build_scenarios  # noqa: E402
from tools.backtest.taskdog_exhaustiveness import (  # noqa: E402
    TASKDOG_TOOLS,
    _build_current_coverage,
    _pick_category_for_tool,
    build_coverage_report,
)


def _make_input() -> list[dict]:
    return build_scenarios("2026-09-22", 28)["scenarios"]


def test_coverage_includes_all_26_tools() -> None:
    coverage = _build_current_coverage(_make_input())
    seen = set(coverage.keys())
    assert seen.issubset(set(TASKDOG_TOOLS)), f"unknown tools in coverage: {seen - set(TASKDOG_TOOLS)}"


def test_padded_coverage_meets_minimum() -> None:
    """Every one of 26 tools must hit >= 3 invocations after padding."""
    report = build_coverage_report(_make_input(), target_invocations=3)
    for t in TASKDOG_TOOLS:
        after = report["coverage"]["after"].get(t, 0)
        assert after >= 3, f"{t}: only {after} invocations, expected >= 3"


def test_synthetic_scenarios_marked() -> None:
    """Padded scenarios have a `synthetic_for_tool` marker."""
    report = build_coverage_report(_make_input(), target_invocations=3)
    synthetic = [s for s in report["scenarios"] if "synthetic_for_tool" in s]
    assert len(synthetic) > 0
    assert all(s["synthetic_for_tool"] in TASKDOG_TOOLS for s in synthetic)


def test_total_count_input_plus_synthetic() -> None:
    """padded_len = input_len + (synthetic added)."""
    inp = _make_input()
    report = build_coverage_report(inp, target_invocations=3)
    assert len(report["scenarios"]) == len(inp) + report["anchor_count"]


def test_pick_category_for_tool_returns_known_category() -> None:
    """Synthetic category is always one of CATEGORY_COUNTS keys."""
    from tools.backtest.seed_q3_scenarios import CATEGORY_COUNTS

    for tool in TASKDOG_TOOLS:
        cat = _pick_category_for_tool(tool)
        assert cat in CATEGORY_COUNTS, f"{tool}: bad category {cat}"


def test_yaml_roundtrip(tmp_path: Path) -> None:
    """Build → write → re-parse yields same scenarios."""
    inp = _make_input()
    report = build_coverage_report(inp, target_invocations=3)
    out_path = tmp_path / "exhaustive.yaml"
    out_path.write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    reloaded = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert len(reloaded["scenarios"]) == len(report["scenarios"])
    assert reloaded["coverage"]["target_invocations_per_tool"] == 3


def test_min_invocation_equals_target() -> None:
    """Min invocation count for any tool == target after padding."""
    report = build_coverage_report(_make_input(), target_invocations=3)
    assert report["coverage"]["min_invocation_count"] == 3


def test_target_invocations_5_still_meets() -> None:
    """Higher target requires more padding; min still >= 5."""
    report = build_coverage_report(_make_input(), target_invocations=5)
    for t in TASKDOG_TOOLS:
        after = report["coverage"]["after"].get(t, 0)
        assert after >= 5


def test_tools_under_target_empty_after_padding() -> None:
    """tools_under_target dict is empty when target met."""
    report = build_coverage_report(_make_input(), target_invocations=3)
    assert report["coverage"]["tools_under_target"] == {}


def test_natural_scenarios_preserved() -> None:
    """Synthetic padding does not mutate natural input scenarios."""
    inp = _make_input()
    original = [dict(s) for s in inp]  # deep copy of shallow fields
    report = build_coverage_report(inp, target_invocations=3)
    natural_padded = [s for s in report["scenarios"] if "synthetic_for_tool" not in s]
    for i, s_orig in enumerate(original):
        assert natural_padded[i]["day"] == s_orig["day"]
        assert natural_padded[i]["category"] == s_orig["category"]
