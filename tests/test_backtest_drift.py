"""M115 tests — backtest_drift.py.

Verifies that the drift detector correctly identifies score changes, anchor
regressions, tool coverage changes, and gap emergence/resolution.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest.backtest_drift import (  # noqa: E402
    diff_anchors,
    diff_gaps,
    diff_scores,
    diff_tools,
    main,
    render_drift_report,
)


# === diff_scores ===

def test_diff_scores_positive() -> None:
    cur = {"total_score": 95.0, "anchor_pass_rate_pct": 90.0}
    base = {"total_score": 90.0, "anchor_pass_rate_pct": 85.0}
    d = diff_scores(cur, base)
    assert d["total_score"] == 5.0
    assert d["anchor_pass_rate_pct"] == 5.0


def test_diff_scores_negative() -> None:
    cur = {"total_score": 80.0}
    base = {"total_score": 90.0}
    d = diff_scores(cur, base)
    assert d["total_score"] == -10.0


def test_diff_scores_zero_when_missing() -> None:
    """Missing dimension is treated as 0."""
    d = diff_scores({}, {})
    assert d["total_score"] == 0.0


# === diff_anchors ===

def test_diff_anchors_sorts_regressions_first() -> None:
    cur = {
        1: {"name": "a", "pass_rate": 0.9, "n_scenarios": 10},
        2: {"name": "b", "pass_rate": 0.7, "n_scenarios": 10},
    }
    base = {
        1: {"name": "a", "pass_rate": 0.95, "n_scenarios": 10},
        2: {"name": "b", "pass_rate": 0.6, "n_scenarios": 10},
    }
    rows = diff_anchors(cur, base)
    # Anchor 1 has delta = -0.05 (regression), 2 has +0.10 (improvement).
    # Sorted by delta ascending: 1 should come first.
    assert rows[0]["anchor_id"] == 1
    assert rows[0]["delta"] == pytest.approx(-0.05)
    assert rows[1]["anchor_id"] == 2


def test_diff_anchors_handles_new_anchor() -> None:
    """Anchor in current but not baseline."""
    cur = {1: {"name": "new_anchor", "pass_rate": 1.0, "n_scenarios": 5}}
    rows = diff_anchors(cur, {})
    assert len(rows) == 1
    assert rows[0]["baseline_rate"] == 0.0
    assert rows[0]["current_rate"] == 1.0
    assert rows[0]["delta"] == pytest.approx(1.0)


# === diff_tools ===

def test_diff_tools_newly_covered() -> None:
    cur = {"a": {"covered": True}, "b": {"covered": False}}
    base = {"a": {"covered": False}, "b": {"covered": False}}
    d = diff_tools(cur, base)
    assert d["newly_covered"] == ["a"]
    assert d["newly_missing"] == []


def test_diff_tools_newly_missing() -> None:
    cur = {"a": {"covered": False}, "b": {"covered": True}}
    base = {"a": {"covered": True}, "b": {"covered": True}}
    d = diff_tools(cur, base)
    assert d["newly_covered"] == []
    assert d["newly_missing"] == ["a"]


def test_diff_tools_unchanged() -> None:
    cur = {"a": {"covered": True}, "b": {"covered": False}}
    base = {"a": {"covered": True}, "b": {"covered": False}}
    d = diff_tools(cur, base)
    assert sorted(d["unchanged"]) == ["a", "b"]


# === diff_gaps ===

def test_diff_gaps_emerges_new() -> None:
    cur = [{"kind": "tool_under_exercised", "tool": "taskdog_x"}]
    base = []
    d = diff_gaps(cur, base)
    assert d["n_delta"] == 1
    assert len(d["new"]) == 1
    assert d["new"][0]["kind"] == "tool_under_exercised"


def test_diff_gaps_resolved() -> None:
    cur = []
    base = [{"kind": "tool_under_exercised", "tool": "taskdog_x"}]
    d = diff_gaps(cur, base)
    assert d["n_delta"] == -1
    assert len(d["resolved"]) == 1


def test_diff_gaps_persistent() -> None:
    gap = {"kind": "tool_server_missing", "tool": "taskdog_search"}
    d = diff_gaps([gap], [gap])
    assert d["n_delta"] == 0
    assert len(d["persistent"]) == 1


# === render_drift_report ===

def _sample_judgment(score: float = 94.5, anchor_rate: float = 0.95) -> dict:
    return {
        "scores": {
            "anchor_pass_rate_pct": anchor_rate * 100,
            "tool_coverage_pct": 100.0,
            "schema_valid_pct": 100.0,
            "scenario_pass_rate_pct": 90.0,
            "total_score": score,
        },
        "anchors": {
            1: {"name": "a", "pass_rate": 1.0, "n_scenarios": 10, "n_pass": 10, "n_skip": 0, "n_error": 0},
            2: {"name": "b", "pass_rate": anchor_rate, "n_scenarios": 10, "n_pass": int(10*anchor_rate), "n_skip": 0, "n_error": 0},
        },
        "tools": {
            "by_tool": {
                "taskdog_create_task": {"covered": True, "expected": 1, "actual": 1},
            },
        },
        "gaps": [],
    }


def test_render_improving_trend() -> None:
    score_delta = {"total_score": 3.0, "anchor_pass_rate_pct": 2.0}
    md = render_drift_report(
        score_delta,
        diff_anchors(_sample_judgment(95.0)["anchors"], _sample_judgment(92.0)["anchors"]),
        diff_tools({}, {}),
        diff_gaps([], []),
    )
    assert "IMPROVING" in md


def test_render_regressing_trend() -> None:
    score_delta = {"total_score": -5.0, "anchor_pass_rate_pct": -3.0}
    md = render_drift_report(
        score_delta,
        diff_anchors(_sample_judgment(85.0)["anchors"], _sample_judgment(90.0)["anchors"]),
        diff_tools({}, {}),
        diff_gaps([], []),
    )
    assert "REGRESSING" in md


def test_render_stable_trend() -> None:
    md = render_drift_report(
        {"total_score": 0.2, "anchor_pass_rate_pct": 0.1},
        diff_anchors(_sample_judgment(94.5)["anchors"], _sample_judgment(94.3)["anchors"]),
        diff_tools({}, {}),
        diff_gaps([], []),
    )
    assert "STABLE" in md


def test_render_includes_methodology() -> None:
    md = render_drift_report(
        {"total_score": 0.0},
        diff_anchors({}, {}),
        diff_tools({}, {}),
        diff_gaps([], []),
    )
    assert "## Interpretation" in md
    assert "Anchor regressions" in md


# === CLI integration ===

def test_main_handles_missing_baseline(tmp_path: Path) -> None:
    cur = tmp_path / "current.json"
    cur.write_text(json.dumps(_sample_judgment()), encoding="utf-8")
    rc = main(["--current", str(cur), "--baseline", str(tmp_path / "missing.json"),
               "--out", str(tmp_path / "drift.md")])
    assert rc == 1


def test_main_snapshot_creates_baseline(tmp_path: Path) -> None:
    cur = tmp_path / "current.json"
    bak = tmp_path / "baseline.json"
    cur.write_text(json.dumps(_sample_judgment()), encoding="utf-8")
    rc = main(["--current", str(cur), "--baseline", str(bak),
               "--out", str(tmp_path / "drift.md"),
               "--snapshot"])
    assert rc == 0
    assert bak.exists()
    assert json.loads(bak.read_text())["scores"]["total_score"] == 94.5


def test_main_writes_drift_report(tmp_path: Path) -> None:
    cur = tmp_path / "current.json"
    bak = tmp_path / "baseline.json"
    cur.write_text(json.dumps(_sample_judgment(96.0)), encoding="utf-8")
    bak.write_text(json.dumps(_sample_judgment(90.0)), encoding="utf-8")
    out = tmp_path / "drift.md"
    rc = main(["--current", str(cur), "--baseline", str(bak), "--out", str(out)])
    assert rc == 0
    md = out.read_text(encoding="utf-8")
    assert "Backtest Drift Report" in md
    assert "IMPROVING" in md


def test_main_handles_missing_current(tmp_path: Path) -> None:
    rc = main(["--current", str(tmp_path / "missing.json"),
               "--baseline", str(tmp_path / "baseline.json"),
               "--out", str(tmp_path / "drift.md")])
    assert rc == 1
