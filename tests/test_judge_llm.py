"""M114c tests — judge_llm.py.

Verifies scoring dimensions: per-scenario coverage, anchor scores, tool coverage,
schema validation, gap identification, total-score math.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest.judge_llm import (  # noqa: E402
    judge_anchor,
    judge_run,
    judge_scenario,
    judge_schema,
    judge_tool_coverage,
    identify_gaps,
    compute_total_score,
)
from tools.backtest.seed_q3_scenarios import TASKDOG_TOOLS  # noqa: E402


# === Fixtures ===

def _sample_judgment(day: int, anchors: list[int], expected: list[str], actual: list[str], status: str = "PASS"):
    from tools.backtest.judge_llm import ScenarioJudgment
    return ScenarioJudgment(
        day=day, category="add-task", anchors=anchors,
        expected_tools=expected, actual_tools=actual,
        status=status,
    )


# === judge_scenario ===

def test_judge_scenario_full_match() -> None:
    j = judge_scenario(
        {"day": 1, "category": "add-task", "expected_tools": ["taskdog_create_task"]},
        {"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"},
        anchor_map={1: [4]},
    )
    assert j.tool_coverage == 1.0
    assert j.status == "PASS"
    assert j.anchors == [4]


def test_judge_scenario_partial_match() -> None:
    j = judge_scenario(
        {"day": 2, "category": "decompose", "expected_tools": ["taskdog_create_task", "taskdog_add_dependency"]},
        {"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"},
        anchor_map={2: [3]},
    )
    assert j.tool_coverage == 0.5


def test_judge_scenario_no_expected_tools() -> None:
    """No expected_tools → vacuously covered."""
    j = judge_scenario(
        {"day": 3, "category": "add-task"},
        {"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"},
        anchor_map={},
    )
    assert j.tool_coverage == 1.0


# === judge_anchor ===

def test_judge_anchor_aggregates() -> None:
    js = [
        _sample_judgment(1, [4], [], [], status="PASS"),
        _sample_judgment(2, [4], [], [], status="PASS"),
        _sample_judgment(3, [4], [], [], status="SKIP"),
    ]
    scores = judge_anchor(js)
    assert 4 in scores
    assert scores[4]["n_scenarios"] == 3
    assert scores[4]["n_pass"] == 2
    assert scores[4]["n_skip"] == 1
    # 2 PASS + 0.5*1 SKIP = 2.5 / 3 ≈ 0.833
    assert scores[4]["pass_rate"] == pytest.approx(0.833, abs=0.01)


def test_judge_anchor_zero_scenarios() -> None:
    js = [_sample_judgment(1, [4], [], [])]
    scores = judge_anchor(js)
    # anchor #5 has no scenarios
    assert scores[5]["n_scenarios"] == 0
    assert scores[5]["pass_rate"] == 0.0


# === judge_tool_coverage ===

def test_judge_tool_coverage_identifies_missing() -> None:
    js = [
        _sample_judgment(1, [], ["taskdog_create_task"], ["taskdog_create_task"]),
        _sample_judgment(2, [], ["taskdog_bulk_complete"], []),
    ]
    cov = judge_tool_coverage(js)
    assert "taskdog_bulk_complete" in cov["missing_tools"]
    assert "taskdog_create_task" in cov["by_tool"]
    assert cov["by_tool"]["taskdog_create_task"]["covered"] is True
    assert cov["by_tool"]["taskdog_bulk_complete"]["covered"] is False


def test_judge_tool_coverage_unexpected() -> None:
    """Tools called but not in any expected list."""
    js = [
        _sample_judgment(1, [], [], ["taskdog_create_task"]),
    ]
    cov = judge_tool_coverage(js)
    assert "taskdog_create_task" in cov["unexpected_tools"]


# === judge_schema ===

def test_judge_schema_valid() -> None:
    js = [_sample_judgment(1, [], ["taskdog_create_task"], [])]
    s = judge_schema(js)
    assert s["schema_valid"] is True
    assert s["unknown_tools_referenced"] == []


def test_judge_schema_invalid_tool() -> None:
    js = [_sample_judgment(1, [], ["taskdog_NOT_REAL"], [])]
    s = judge_schema(js)
    assert s["schema_valid"] is False
    assert (1, "taskdog_NOT_REAL") in s["unknown_tools_referenced"]


def test_judge_schema_knows_26_tools() -> None:
    js = []
    s = judge_schema(js)
    assert s["known_tools_count"] == 26
    assert len(TASKDOG_TOOLS) == 26


# === identify_gaps ===

def test_identify_gaps_marks_server_missing() -> None:
    cov = {
        "missing_tools": ["taskdog_bulk_complete", "taskdog_create_task"],
        "by_tool": {},
        "expected_total": 4,
        "actual_total": 1,
    }
    sch = {"schema_valid": True, "unknown_tools_referenced": []}
    gaps = identify_gaps({}, cov, sch)
    kinds = {g["kind"] for g in gaps}
    assert "tool_server_missing" in kinds
    assert "tool_under_exercised" in kinds


def test_identify_gaps_anchor_low_pass() -> None:
    anchor_scores = {
        1: {"name": "x", "n_scenarios": 10, "n_pass": 3, "n_skip": 0, "n_error": 7, "pass_rate": 0.3},
    }
    cov = {"missing_tools": [], "by_tool": {}}
    sch = {"schema_valid": True, "unknown_tools_referenced": []}
    gaps = identify_gaps(anchor_scores, cov, sch)
    assert any(g["kind"] == "anchor_low_pass" for g in gaps)


# === compute_total_score ===

def test_total_score_perfect() -> None:
    # 1 anchor with 100% pass rate; 1 tool covered; valid schema; 100% pass.
    anchor_scores = {
        1: {"name": "x", "n_scenarios": 1, "n_pass": 1, "n_skip": 0, "n_error": 0, "pass_rate": 1.0},
    }
    cov = {"missing_tools": [], "by_tool": {"taskdog_create_task": {"expected": 1, "actual": 1, "covered": True}}}
    sch = {"schema_valid": True, "unknown_tools_referenced": []}
    js = [_sample_judgment(1, [], [], [], status="PASS")]
    total = compute_total_score(anchor_scores, cov, sch, js)
    assert total["total_score"] == 100.0


def test_total_score_zero_when_all_fail() -> None:
    anchor_scores = {
        1: {"name": "x", "n_scenarios": 1, "n_pass": 0, "n_skip": 0, "n_error": 1, "pass_rate": 0.0},
    }
    cov = {"missing_tools": ["taskdog_create_task"], "by_tool": {"taskdog_create_task": {"expected": 1, "actual": 0, "covered": False}}}
    sch = {"schema_valid": False, "unknown_tools_referenced": []}
    js = [_sample_judgment(1, [], [], [], status="ERROR")]
    total = compute_total_score(anchor_scores, cov, sch, js)
    assert total["total_score"] == 0.0


def test_total_score_excludes_server_missing_tools() -> None:
    """Tools in spec but no HTTP endpoint should not penalize."""
    anchor_scores = {
        1: {"name": "x", "n_scenarios": 1, "n_pass": 1, "n_skip": 0, "n_error": 0, "pass_rate": 1.0},
    }
    cov = {
        "missing_tools": ["taskdog_bulk_complete"],
        "by_tool": {
            "taskdog_bulk_complete": {"expected": 3, "actual": 0, "covered": False},
            "taskdog_create_task": {"expected": 1, "actual": 1, "covered": True},
        },
    }
    sch = {"schema_valid": True, "unknown_tools_referenced": []}
    js = [_sample_judgment(1, [], [], [], status="PASS")]
    total = compute_total_score(anchor_scores, cov, sch, js)
    # bulk_complete excluded from denominator; only create_task counted → 100%.
    assert total["tool_coverage_pct"] == 100.0


# === judge_run (integration) ===

def test_judge_run_end_to_end() -> None:
    scenarios = [
        {"day": 1, "category": "add-task", "expected_tools": ["taskdog_create_task"]},
        {"day": 2, "category": "list-tasks", "expected_tools": ["taskdog_list_tasks"]},
        {"day": 3, "category": "daily-plan", "expected_tools": ["taskdog_list_tasks"]},
        {"day": 4, "category": "weekly-review", "expected_tools": ["taskdog_get_metrics"]},
    ]
    anchor_map_doc = {"scenarios": {1: [4], 2: [4], 3: [2], 4: [10]}}
    harness = {
        "outcomes": [
            {"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"},
            {"status": "PASS", "tools_called": ["taskdog_list_tasks"], "detail": "ok"},
            {"status": "PASS", "tools_called": ["taskdog_list_tasks"], "detail": "ok"},
            {"status": "PASS", "tools_called": ["taskdog_get_metrics"], "detail": "ok"},
        ],
    }
    result = judge_run(scenarios, harness, anchor_map_doc)
    # 4 PASS, valid schema, 100% tool coverage on expected — score should be high.
    assert result["scores"]["total_score"] > 70
    assert "anchors" in result
    assert "tools" in result
    assert "schema" in result
    assert "gaps" in result


def test_judge_run_with_yaml_input(tmp_path: Path) -> None:
    """Run judge against actual YAML + JSON files (regression: shape compat)."""
    import yaml
    scenarios_yaml = tmp_path / "scenarios.yaml"
    scenarios_yaml.write_text(yaml.safe_dump({
        "scenarios": [
            {"day": 1, "category": "add-task", "expected_tools": ["taskdog_create_task"]},
        ],
        "anchor_map": {"scenarios": {1: [4]}},
    }), encoding="utf-8")
    results_json = tmp_path / "results.json"
    results_json.write_text(json.dumps({
        "outcomes": [
            {"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"},
        ],
    }), encoding="utf-8")
    # Run via the CLI-equivalent path:
    src = yaml.safe_load(scenarios_yaml.read_text(encoding="utf-8"))
    harness = json.loads(results_json.read_text(encoding="utf-8"))
    result = judge_run(src["scenarios"], harness, src.get("anchor_map", {}))
    assert result["scores"]["total_score"] > 0
