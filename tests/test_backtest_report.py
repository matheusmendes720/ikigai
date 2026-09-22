"""M114g tests — backtest_report.py.

Verifies the markdown report renders correctly given harness + judgment JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest.backtest_report import render_report  # noqa: E402


# === Fixtures ===

@pytest.fixture
def sample_results() -> dict:
    return {
        "n_total": 5,
        "n_pass": 4,
        "n_skip": 1,
        "n_error": 0,
        "elapsed_seconds": 1.234,
        "by_tool": {
            "taskdog_create_task": 2,
            "taskdog_list_tasks": 3,
        },
        "outcomes": [],
    }


@pytest.fixture
def sample_judgment() -> dict:
    return {
        "scores": {
            "anchor_pass_rate_pct": 95.0,
            "tool_coverage_pct": 100.0,
            "schema_valid_pct": 100.0,
            "scenario_pass_rate_pct": 80.0,
            "total_score": 94.0,
        },
        "anchors": {
            1: {"name": "constitutional_sot", "n_scenarios": 3, "n_pass": 3, "n_skip": 0, "n_error": 0, "pass_rate": 1.0},
            2: {"name": "dual_frame_temporal", "n_scenarios": 2, "n_pass": 1, "n_skip": 1, "n_error": 0, "pass_rate": 0.75},
        },
        "tools": {
            "expected_total": 3,
            "actual_total": 3,
            "expected_unique_tools": 2,
            "actual_unique_tools": 2,
            "missing_tools": [],
            "by_tool": {
                "taskdog_create_task": {"expected": 2, "actual": 2, "covered": True},
                "taskdog_list_tasks": {"expected": 1, "actual": 1, "covered": True},
            },
        },
        "schema": {"schema_valid": True, "unknown_tools_referenced": [], "known_tools_count": 26},
        "gaps": [],
        "weights": {"anchor_pass_rate": 0.4, "tool_coverage": 0.3, "schema_valid": 0.1, "scenario_pass_rate": 0.2},
    }


# === Render ===

def test_render_report_contains_score(sample_results, sample_judgment) -> None:
    md = render_report(sample_results, sample_judgment)
    assert "**94.0 / 100**" in md or "**94 / 100**" in md or "94.0" in md


def test_render_report_contains_tl_dr(sample_results, sample_judgment) -> None:
    md = render_report(sample_results, sample_judgment)
    assert "## TL;DR" in md


def test_render_report_contains_anchor_table(sample_results, sample_judgment) -> None:
    md = render_report(sample_results, sample_judgment)
    assert "constitutional_sot" in md
    assert "dual_frame_temporal" in md


def test_render_report_contains_tool_table(sample_results, sample_judgment) -> None:
    md = render_report(sample_results, sample_judgment)
    assert "`taskdog_create_task`" in md
    assert "`taskdog_list_tasks`" in md


def test_render_report_with_gaps(sample_results) -> None:
    judgment = {
        "scores": {
            "anchor_pass_rate_pct": 80.0,
            "tool_coverage_pct": 50.0,
            "schema_valid_pct": 100.0,
            "scenario_pass_rate_pct": 70.0,
            "total_score": 75.0,
        },
        "anchors": {
            1: {"name": "test_anchor", "n_scenarios": 10, "n_pass": 3, "n_skip": 0, "n_error": 7, "pass_rate": 0.3},
        },
        "tools": {
            "expected_total": 4, "actual_total": 2,
            "expected_unique_tools": 2, "actual_unique_tools": 2,
            "missing_tools": ["taskdog_search_tasks", "taskdog_bulk_complete"],
            "by_tool": {
                "taskdog_search_tasks": {"expected": 2, "actual": 0, "covered": False},
                "taskdog_create_task": {"expected": 2, "actual": 2, "covered": True},
            },
        },
        "schema": {"schema_valid": True, "unknown_tools_referenced": [], "known_tools_count": 26},
        "gaps": [
            {"kind": "anchor_low_pass", "anchor": "test_anchor",
             "detail": "pass_rate=30% < 70%"},
            {"kind": "tool_server_missing", "tool": "taskdog_search_tasks",
             "detail": "spec drift"},
            {"kind": "tool_under_exercised", "tool": "taskdog_bulk_complete",
             "detail": "harness didn't call"},
        ],
        "weights": {"anchor_pass_rate": 0.4, "tool_coverage": 0.3, "schema_valid": 0.1, "scenario_pass_rate": 0.2},
    }
    md = render_report(sample_results, judgment)
    assert "## Gaps identified" in md
    assert "tool_server_missing" in md
    assert "tool_under_exercised" in md
    assert "anchor_low_pass" in md
    assert "## Next steps" in md


def test_render_report_empty_gaps(sample_results, sample_judgment) -> None:
    md = render_report(sample_results, sample_judgment)
    assert "No gaps." in md


def test_render_report_uses_cycle_dates(sample_results, sample_judgment) -> None:
    md = render_report(
        sample_results, sample_judgment,
        cycle_start="2026-08-01",
        cycle_end="2026-08-28",
    )
    assert "2026-08-01 → 2026-08-28" in md


def test_render_report_includes_methodology(sample_results, sample_judgment) -> None:
    md = render_report(sample_results, sample_judgment)
    assert "## Methodology" in md
    assert "Anchor pass rate" in md or "anchor" in md.lower()


# === CLI integration ===

def test_report_main_writes_file(tmp_path: Path, sample_results, sample_judgment) -> None:
    """Run the CLI end-to-end with temp JSON inputs."""
    import yaml
    from tools.backtest.backtest_report import main

    results_path = tmp_path / "results.json"
    judgment_path = tmp_path / "judgment.json"
    out_path = tmp_path / "report.md"
    results_path.write_text(json.dumps(sample_results), encoding="utf-8")
    judgment_path.write_text(json.dumps(sample_judgment), encoding="utf-8")

    rc = main([
        "--results", str(results_path),
        "--judgment", str(judgment_path),
        "--out", str(out_path),
    ])
    assert rc == 0
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "# Backtest Q1" in content
    assert "TL;DR" in content


def test_report_main_handles_missing_files(tmp_path: Path) -> None:
    from tools.backtest.backtest_report import main
    rc = main(["--results", str(tmp_path / "missing.json"),
               "--judgment", str(tmp_path / "missing2.json"),
               "--out", str(tmp_path / "report.md")])
    assert rc == 1
