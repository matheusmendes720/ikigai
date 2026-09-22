"""M119 tests — LLM-judge drift tracking.

Verifies:
  - archive_llm_baseline creates <DATE>.llm.json (first-wins same-day)
  - list_baselines still excludes .llm.json files (only <DATE>.json shown)
  - _llm_score extracts 5 dimensions from M116 judgment JSON
  - _llm_score returns None when aggregate is missing
  - weekly_trend merges .llm.json into the per-week aggregate
  - trend_report_markdown adds the `llm` column when ANY week has llm data
  - trend_report_markdown omits the column when NO week has llm data
  - trend_report_markdown shows `—` for weeks without llm data
  - trend_report_markdown adds "Trend (LLM-judge overall)" line when 2+ weeks have data
  - trend_report_markdown's include_llm=False flag suppresses the column
  - CLI archive-llm subcommand works
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest import baseline_archive as ba  # noqa: E402
from tools.backtest.baseline_archive import (  # noqa: E402
    _llm_score,
    archive_llm_baseline,
    list_baselines,
    main,
    trend_report_markdown,
    weekly_trend,
)


@pytest.fixture
def bdir(tmp_path: Path) -> Path:
    return tmp_path / "baselines"


def _rule_judgment(total: float = 90.0) -> dict[str, Any]:
    return {
        "scores": {
            "total_score": total,
            "tool_coverage_pct": 95.0,
            "anchor_pass_rate_pct": 95.0,
            "scenario_pass_rate_pct": 89.0,
            "schema_valid_pct": 100.0,
        },
        "n_judged": 73,
        "generated_at": "2026-09-22T12:00:00Z",
    }


def _llm_judgment(overall: float = 0.751) -> dict[str, Any]:
    return {
        "aggregate": {
            "argument_quality": 0.667,
            "sequence_coherence": 0.825,
            "cultural_fit": 0.567,
            "tool_selection": 0.945,
            "overall": overall,
            "n_scenarios": 73,
            "modes": {"stub": 73},
        },
        "mode_requested": "stub",
    }


# === archive_llm_baseline ===

def test_archive_llm_creates_first_run(bdir: Path, tmp_path: Path) -> None:
    src = tmp_path / "llm.json"
    src.write_text(json.dumps(_llm_judgment()), encoding="utf-8")
    dest = archive_llm_baseline(src, bdir, "2026-09-22")
    assert dest.name == "2026-09-22.llm.json"
    assert dest.exists()


def test_archive_llm_first_wins_same_day(bdir: Path, tmp_path: Path) -> None:
    src1 = tmp_path / "l1.json"
    src1.write_text(json.dumps(_llm_judgment(overall=0.5)), encoding="utf-8")
    src2 = tmp_path / "l2.json"
    src2.write_text(json.dumps(_llm_judgment(overall=0.9)), encoding="utf-8")
    archive_llm_baseline(src1, bdir, "2026-09-22")
    initial = (bdir / "2026-09-22.llm.json").read_bytes()
    archive_llm_baseline(src2, bdir, "2026-09-22")
    assert (bdir / "2026-09-22.llm.json").read_bytes() == initial


def test_list_baselines_excludes_llm_files(bdir: Path) -> None:
    bdir.mkdir()
    (bdir / "2026-09-22.json").write_text("{}", encoding="utf-8")
    (bdir / "2026-09-22.llm.json").write_text("{}", encoding="utf-8")
    paths = list_baselines(bdir, since_days=0)
    names = [p.name for p in paths]
    assert "2026-09-22.json" in names
    assert "2026-09-22.llm.json" not in names


# === _llm_score ===

def test_llm_score_extracts_5_dimensions() -> None:
    s = _llm_score(_llm_judgment(overall=0.812))
    assert s is not None
    assert s["llm_overall"] == 0.812
    assert s["llm_arg_quality"] == 0.667
    assert s["llm_seq_coherence"] == 0.825
    assert s["llm_cultural_fit"] == 0.567
    assert s["llm_tool_selection"] == 0.945


def test_llm_score_returns_none_for_rule_judgment() -> None:
    assert _llm_score(_rule_judgment()) is None


def test_llm_score_returns_none_when_aggregate_missing() -> None:
    assert _llm_score({"scores": {}}) is None


# === weekly_trend merging llm data ===

def test_weekly_trend_picks_up_llm_data(bdir: Path) -> None:
    bdir.mkdir()
    (bdir / "2026-09-22.json").write_text(json.dumps(_rule_judgment(total=94.6)), encoding="utf-8")
    (bdir / "2026-09-22.llm.json").write_text(json.dumps(_llm_judgment(overall=0.751)), encoding="utf-8")
    weeks = weekly_trend(bdir, since_days=365)
    assert len(weeks) == 1
    assert weeks[0]["avg"]["llm_overall"] == 0.751
    assert weeks[0]["avg"]["llm_n_runs"] == 1


def test_weekly_trend_handles_missing_llm(bdir: Path) -> None:
    bdir.mkdir()
    (bdir / "2026-09-22.json").write_text(json.dumps(_rule_judgment(total=94.6)), encoding="utf-8")
    weeks = weekly_trend(bdir, since_days=365)
    assert weeks[0]["avg"]["llm_overall"] is None
    assert weeks[0]["avg"]["llm_n_runs"] == 0


def test_weekly_trend_separate_weeks_independent_llm(bdir: Path) -> None:
    bdir.mkdir()
    # Week 39: has llm. Week 40: doesn't.
    (bdir / "2026-09-22.json").write_text(json.dumps(_rule_judgment(total=94.6)), encoding="utf-8")
    (bdir / "2026-09-22.llm.json").write_text(json.dumps(_llm_judgment(overall=0.751)), encoding="utf-8")
    (bdir / "2026-10-01.json").write_text(json.dumps(_rule_judgment(total=92.0)), encoding="utf-8")
    weeks = weekly_trend(bdir, since_days=365)
    by_label = {w["week_label"]: w for w in weeks}
    assert by_label["2026-W39"]["avg"]["llm_overall"] == 0.751
    assert by_label["2026-W40"]["avg"]["llm_overall"] is None


# === trend_report_markdown column logic ===

def test_trend_report_omits_column_when_no_llm() -> None:
    md = trend_report_markdown([
        {"week_label": "2026-W39", "week_start": "2026-09-22", "n_runs": 1,
         "avg": {"total_score": 94.6, "anchor_pass": 95.8, "tool_coverage": 95.0,
                 "scenario_pass": 89.0, "llm_overall": None, "llm_n_runs": 0},
         "latest_run": "2026-09-22"},
    ])
    # No `| llm |` column header
    assert "| llm |" not in md


def test_trend_report_adds_column_when_any_llm_present() -> None:
    md = trend_report_markdown([
        {"week_label": "2026-W39", "week_start": "2026-09-22", "n_runs": 1,
         "avg": {"total_score": 94.6, "anchor_pass": 95.8, "tool_coverage": 95.0,
                 "scenario_pass": 89.0, "llm_overall": 0.751, "llm_n_runs": 1},
         "latest_run": "2026-09-22"},
    ])
    assert "| llm |" in md
    assert "0.751" in md


def test_trend_report_shows_dash_for_missing_llm_week() -> None:
    md = trend_report_markdown([
        {"week_label": "2026-W39", "week_start": "2026-09-22", "n_runs": 1,
         "avg": {"total_score": 94.6, "anchor_pass": 95.8, "tool_coverage": 95.0,
                 "scenario_pass": 89.0, "llm_overall": 0.751, "llm_n_runs": 1},
         "latest_run": "2026-09-22"},
        {"week_label": "2026-W40", "week_start": "2026-10-01", "n_runs": 1,
         "avg": {"total_score": 92.0, "anchor_pass": 95.0, "tool_coverage": 95.0,
                 "scenario_pass": 89.0, "llm_overall": None, "llm_n_runs": 0},
         "latest_run": "2026-10-01"},
    ])
    assert "|" in md  # sanity
    # The W40 row should contain — for the llm cell
    w40_rows = [line for line in md.splitlines() if "2026-W40" in line]
    assert any("—" in row for row in w40_rows)


def test_trend_report_adds_llm_trend_line_when_two_weeks() -> None:
    md = trend_report_markdown([
        {"week_label": "2026-W39", "week_start": "2026-09-22", "n_runs": 1,
         "avg": {"total_score": 94.6, "anchor_pass": 95.8, "tool_coverage": 95.0,
                 "scenario_pass": 89.0, "llm_overall": 0.700, "llm_n_runs": 1},
         "latest_run": "2026-09-22"},
        {"week_label": "2026-W40", "week_start": "2026-10-01", "n_runs": 1,
         "avg": {"total_score": 92.0, "anchor_pass": 95.0, "tool_coverage": 95.0,
                 "scenario_pass": 89.0, "llm_overall": 0.800, "llm_n_runs": 1},
         "latest_run": "2026-10-01"},
    ])
    assert "Trend (LLM-judge overall)" in md
    assert "📈" in md
    assert "+0.100" in md


def test_trend_report_include_llm_false_suppresses() -> None:
    md = trend_report_markdown(
        [{"week_label": "2026-W39", "week_start": "2026-09-22", "n_runs": 1,
          "avg": {"total_score": 94.6, "anchor_pass": 95.8, "tool_coverage": 95.0,
                  "scenario_pass": 89.0, "llm_overall": 0.751, "llm_n_runs": 1},
          "latest_run": "2026-09-22"}],
        include_llm=False,
    )
    assert "| llm |" not in md


# === CLI ===

def test_main_archive_llm(tmp_path: Path, capsys) -> None:
    src = tmp_path / "llm.json"
    src.write_text(json.dumps(_llm_judgment()), encoding="utf-8")
    bdir = tmp_path / "baselines"
    rc = main(["archive-llm", "--source", str(src), "--baselines-dir", str(bdir), "--date", "2026-10-15"])
    assert rc == 0
    assert (bdir / "2026-10-15.llm.json").exists()
