"""M114a tests — seed_q3_scenarios.

Verifies:
- Vault parsing pulls events with frontmatter `date` field
- Coverage target sums to 28 days (4 weeks)
- Each scenario has expected_tools + expected_args
- Output YAML is well-formed and re-parses cleanly
- Daily anchor rotation is deterministic across runs
- Per-category count matches CATEGORY_COUNTS
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest.seed_q3_scenarios import (  # noqa: E402
    CATEGORY_COUNTS,
    CATEGORY_EXPECTED_TOOLS,
    TASKDOG_TOOLS,
    _gather_anchors,
    _rotation_for_anchors,
    _select_anchors_per_day,
    build_scenarios,
)


def test_rotation_sums_to_28() -> None:
    rotation = _rotation_for_anchors()
    assert len(rotation) == 28, f"expected 28-day rotation, got {len(rotation)}"
    counts = {cat: rotation.count(cat) for cat in CATEGORY_COUNTS}
    assert counts == CATEGORY_COUNTS, f"counts mismatch: {counts}"


def test_build_scenarios_returns_28_dicts() -> None:
    out = build_scenarios("2026-09-22", 28)
    assert "scenarios" in out
    assert len(out["scenarios"]) == 28
    for i, sc in enumerate(out["scenarios"], 1):
        assert sc["day"] == i
        assert sc["category"] in CATEGORY_COUNTS
        assert isinstance(sc["expected_tools"], list)
        assert isinstance(sc["expected_args"], dict)
        assert "cluster" in sc["expected_args"]
        assert "tags_any" in sc["expected_args"]


def test_cycle_end_is_cycle_start_plus_27_days() -> None:
    out = build_scenarios("2026-09-22", 28)
    from datetime import date

    start = date.fromisoformat(out["cycle_start"])
    end = date.fromisoformat(out["cycle_end"])
    assert (end - start).days == 27, f"expected 27-day span, got {(end - start).days}"


def test_tools_per_category_valid_subset() -> None:
    """Each CATEGORY_EXPECTED_TOOLS list contains only known taskdog tools."""
    for cat, tools in CATEGORY_EXPECTED_TOOLS.items():
        for t in tools:
            assert t in TASKDOG_TOOLS, f"{cat!r} uses unknown tool {t!r}"


def test_taskdog_tools_list_size_26() -> None:
    """M113 spec: 26 taskdog-mcp tools exhaustively covered."""
    assert len(TASKDOG_TOOLS) == 26


def test_yaml_roundtrip(tmp_path: Path) -> None:
    """Build → write → re-parse YAML yields the same scenarios."""
    out_path = tmp_path / "scenarios.yaml"
    out = build_scenarios("2026-09-22", 28)
    out_path.write_text(
        yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    reloaded = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert reloaded["cycle_start"] == out["cycle_start"]
    assert reloaded["scenarios"] == out["scenarios"]


def test_anchor_selection_is_deterministic() -> None:
    """Same cycle_start + same anchor pool → same per-day picks."""
    anchors = _gather_anchors()
    pick_a = _select_anchors_per_day(anchors, 28, "2026-09-22")
    pick_b = _select_anchors_per_day(anchors, 28, "2026-09-22")
    assert pick_a == pick_b


def test_gather_anchors_handles_missing_vault(tmp_path: Path) -> None:
    """If VAULT_DIR is empty, anchors list is empty (no crash)."""
    # Make a Vault stand-in by monkey-patching the module.
    import tools.backtest.seed_q3_scenarios as mod

    empty_vault = tmp_path / "empty_vault"
    empty_vault.mkdir()
    mod.VAULT_DIR = empty_vault
    anchors = mod._gather_anchors()
    assert anchors == []


def test_scenario_prompts_include_category() -> None:
    """Every scenario prompt mentions its category."""
    out = build_scenarios("2026-09-22", 28)
    for sc in out["scenarios"]:
        assert sc["category"] in sc["prompt"]


def test_yaml_coverage_target_block() -> None:
    """Output contains coverage_target with 26 tools + per-category counts."""
    out = build_scenarios("2026-09-22", 28)
    ct = out["coverage_target"]
    assert ct["scenarios_per_category"] == CATEGORY_COUNTS
    assert ct["tool_invocation_count_per_tool"] == 3
    assert ct["target_tools"] == TASKDOG_TOOLS
