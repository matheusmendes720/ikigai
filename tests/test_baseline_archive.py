"""M118 tests — baseline_archive.py.

Verifies the daily archive rotation, weekly trend computation, and markdown
rendering. All tests use tmp_path to keep state isolated.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest import baseline_archive as ba  # noqa: E402
from tools.backtest.baseline_archive import (  # noqa: E402
    _score,
    archive_baseline,
    list_baselines,
    main,
    trend_report_markdown,
    weekly_trend,
)


@pytest.fixture
def tmp_baselines(tmp_path: Path) -> Path:
    return tmp_path / "baselines"


def _fake_judgment(total: float = 90.0, tool: float = 90.0, anchor: float = 95.0) -> dict[str, Any]:
    return {
        "scores": {
            "total_score": total,
            "tool_coverage_pct": tool,
            "anchor_pass_rate_pct": anchor,
            "scenario_pass_rate_pct": 88.0,
            "schema_valid_pct": 100.0,
        },
        "n_judged": 73,
        "generated_at": "2026-09-22T12:00:00Z",
    }


# === archive_baseline ===

def test_archive_creates_first_run(tmp_path: Path) -> None:
    src = tmp_path / "judgment.json"
    src.write_text(json.dumps(_fake_judgment()), encoding="utf-8")
    dest = archive_baseline(src, baselines_dir=tmp_path / "baselines", date_str="2026-09-22")
    assert dest.exists()
    assert dest.name == "2026-09-22.json"


def test_archive_first_wins_same_day(tmp_path: Path) -> None:
    src1 = tmp_path / "j1.json"
    src1.write_text(json.dumps(_fake_judgment(total=80.0)), encoding="utf-8")
    src2 = tmp_path / "j2.json"
    src2.write_text(json.dumps(_fake_judgment(total=99.0)), encoding="utf-8")
    dest = archive_baseline(src1, baselines_dir=tmp_path / "baselines", date_str="2026-09-22")
    initial_size = dest.read_bytes()
    archive_baseline(src2, baselines_dir=tmp_path / "baselines", date_str="2026-09-22")
    # First-wins: content unchanged.
    assert dest.read_bytes() == initial_size


def test_archive_invalid_date_raises(tmp_path: Path) -> None:
    src = tmp_path / "j.json"
    src.write_text(json.dumps(_fake_judgment()), encoding="utf-8")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        archive_baseline(src, baselines_dir=tmp_path / "baselines", date_str="bad-date")


# === list_baselines ===

def test_list_baselines_filters_by_age(tmp_path: Path) -> None:
    bdir = tmp_path / "baselines"
    bdir.mkdir()
    today = dt.date.today().isoformat()
    old = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    (bdir / f"{old}.json").write_text("{}", encoding="utf-8")
    (bdir / f"{today}.json").write_text("{}", encoding="utf-8")
    (bdir / "garbage.json").write_text("{}", encoding="utf-8")
    paths = list_baselines(bdir, since_days=7)
    names = [p.name for p in paths]
    assert f"{today}.json" in names
    assert f"{old}.json" not in names
    assert "garbage.json" not in names


def test_list_baselines_zero_since_returns_all(tmp_path: Path) -> None:
    bdir = tmp_path / "baselines"
    bdir.mkdir()
    (bdir / "2025-01-01.json").write_text("{}", encoding="utf-8")
    (bdir / "2026-01-01.json").write_text("{}", encoding="utf-8")
    paths = list_baselines(bdir, since_days=0)
    assert len(paths) == 2


def test_list_baselines_missing_dir(tmp_path: Path) -> None:
    assert list_baselines(tmp_path / "missing", since_days=0) == []


# === _score ===

def test_score_extracts_four_dimensions() -> None:
    s = _score(_fake_judgment(total=88.5, tool=92.3, anchor=96.1))
    assert s["total_score"] == 88.5
    assert s["tool_coverage"] == 92.3
    assert s["anchor_pass"] == 96.1


def test_score_handles_missing_fields() -> None:
    s = _score({})
    assert all(s[k] == 0.0 for k in s)


# === weekly_trend ===

def test_weekly_trend_groups_by_iso_week(tmp_path: Path) -> None:
    bdir = tmp_path / "baselines"
    bdir.mkdir()
    # 2 days in same ISO week (39), 1 day in week 40
    (bdir / "2026-09-22.json").write_text(json.dumps(_fake_judgment(total=90.0)), encoding="utf-8")
    (bdir / "2026-09-23.json").write_text(json.dumps(_fake_judgment(total=92.0)), encoding="utf-8")
    (bdir / "2026-10-01.json").write_text(json.dumps(_fake_judgment(total=95.0)), encoding="utf-8")
    weeks = weekly_trend(bdir, since_days=365)
    labels = [w["week_label"] for w in weeks]
    assert labels == ["2026-W39", "2026-W40"]
    assert weeks[0]["n_runs"] == 2
    assert weeks[0]["avg"]["total_score"] == 91.0  # (90+92)/2
    assert weeks[1]["n_runs"] == 1
    assert weeks[1]["avg"]["total_score"] == 95.0


def test_weekly_trend_skips_invalid_json(tmp_path: Path) -> None:
    bdir = tmp_path / "baselines"
    bdir.mkdir()
    (bdir / "2026-09-22.json").write_text("not valid json", encoding="utf-8")
    (bdir / "2026-09-23.json").write_text(json.dumps(_fake_judgment()), encoding="utf-8")
    weeks = weekly_trend(bdir, since_days=365)
    assert len(weeks) == 1
    assert weeks[0]["n_runs"] == 1


def test_weekly_trend_empty(tmp_path: Path) -> None:
    assert weekly_trend(tmp_path / "missing", since_days=0) == []


# === trend_report_markdown ===

def test_trend_report_empty() -> str:
    md = trend_report_markdown([])
    assert "No baselines" in md


def test_trend_report_single_week() -> str:
    md = trend_report_markdown([{
        "week_label": "2026-W39",
        "week_start": "2026-09-22",
        "n_runs": 1,
        "avg": {"total_score": 94.6, "anchor_pass": 95.8, "tool_coverage": 95.0, "scenario_pass": 89.0},
        "latest_run": "2026-09-22",
    }])
    assert "W39" in md
    assert "94.6" in md
    assert "Trend" not in md  # no delta computed with single week


def test_trend_report_multiple_weeks_emoji() -> str:
    md = trend_report_markdown([
        {"week_label": "2026-W39", "week_start": "2026-09-22", "n_runs": 1,
         "avg": {"total_score": 90.0, "anchor_pass": 95.0, "tool_coverage": 90.0, "scenario_pass": 85.0},
         "latest_run": "2026-09-22"},
        {"week_label": "2026-W40", "week_start": "2026-10-01", "n_runs": 1,
         "avg": {"total_score": 95.0, "anchor_pass": 96.0, "tool_coverage": 96.0, "scenario_pass": 90.0},
         "latest_run": "2026-10-01"},
    ])
    assert "📈" in md
    assert "+5.00" in md


def test_trend_report_regression_emoji() -> str:
    md = trend_report_markdown([
        {"week_label": "2026-W39", "week_start": "2026-09-22", "n_runs": 1,
         "avg": {"total_score": 95.0, "anchor_pass": 96.0, "tool_coverage": 96.0, "scenario_pass": 90.0},
         "latest_run": "2026-09-22"},
        {"week_label": "2026-W40", "week_start": "2026-10-01", "n_runs": 1,
         "avg": {"total_score": 88.0, "anchor_pass": 90.0, "tool_coverage": 90.0, "scenario_pass": 85.0},
         "latest_run": "2026-10-01"},
    ])
    assert "📉" in md


# === CLI ===

def test_main_archive(tmp_path: Path, capsys) -> None:
    src = tmp_path / "j.json"
    src.write_text(json.dumps(_fake_judgment()), encoding="utf-8")
    rc = main(["archive", "--source", str(src), "--baselines-dir", str(tmp_path / "baselines"), "--date", "2026-10-01"])
    assert rc == 0
    assert (tmp_path / "baselines" / "2026-10-01.json").exists()


def test_main_list(tmp_path: Path, capsys) -> None:
    bdir = tmp_path / "baselines"
    bdir.mkdir()
    (bdir / "2026-09-22.json").write_text("{}", encoding="utf-8")
    rc = main(["list", "--baselines-dir", str(bdir)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "2026-09-22.json" in captured.out


def test_main_weekly(tmp_path: Path) -> None:
    bdir = tmp_path / "baselines"
    bdir.mkdir()
    (bdir / "2026-09-22.json").write_text(json.dumps(_fake_judgment(total=94.6)), encoding="utf-8")
    out = tmp_path / "trend.md"
    rc = main(["weekly", "--baselines-dir", str(bdir), "--out", str(out)])
    assert rc == 0
    assert out.exists()
    assert "W39" in out.read_text(encoding="utf-8")


def test_main_invalid_cmd(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["bogus", "--baselines-dir", str(tmp_path / "b")])
