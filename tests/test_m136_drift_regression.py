"""M136 tests — drift_regression.py.

Verifies week-over-week drift regression detection. Uses synthetic
JSON snapshots so tests are hermetic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest import drift_regression as dr  # noqa: E402
from tools.backtest.drift_regression import (  # noqa: E402
    _is_regression,
    _load_two_snapshots,
    check,
    main,
)


def _write_snapshot(bdir: Path, date: str, summary: dict[str, int]) -> Path:
    """Write a synthetic drift snapshot."""
    p = bdir / f"{date}.drift.json"
    p.write_text(
        json.dumps({"date": date, "summary": summary, "total": sum(summary.values())}),
        encoding="utf-8",
    )
    return p


@pytest.fixture
def two_snapshots(tmp_path: Path) -> Path:
    """Two snapshots: prior with low counts, current with higher counts."""
    _write_snapshot(tmp_path, "2026-09-15", {
        "unmarked_done": 5, "unmarked_open": 2, "phantom_task": 10,
        "planned_orphan": 100, "priority_mismatch": 3, "tag_mismatch": 1,
        "due_date_mismatch": 0,
    })
    _write_snapshot(tmp_path, "2026-09-22", {
        "unmarked_done": 5, "unmarked_open": 2, "phantom_task": 12,
        "planned_orphan": 200, "priority_mismatch": 3, "tag_mismatch": 1,
        "due_date_mismatch": 5,
    })
    return tmp_path


@pytest.fixture
def identical_snapshots(tmp_path: Path) -> Path:
    """Two snapshots with identical counts."""
    counts = {
        "unmarked_done": 5, "unmarked_open": 2, "phantom_task": 10,
        "planned_orphan": 100, "priority_mismatch": 3, "tag_mismatch": 1,
        "due_date_mismatch": 0,
    }
    _write_snapshot(tmp_path, "2026-09-15", counts)
    _write_snapshot(tmp_path, "2026-09-22", counts)
    return tmp_path


@pytest.fixture
def single_snapshot(tmp_path: Path) -> Path:
    """Only one snapshot — insufficient for comparison."""
    _write_snapshot(tmp_path, "2026-09-22", {
        "unmarked_done": 5, "unmarked_open": 2, "phantom_task": 10,
        "planned_orphan": 100, "priority_mismatch": 3, "tag_mismatch": 1,
        "due_date_mismatch": 0,
    })
    return tmp_path


# === _is_regression ===

def test_is_regression_no_change() -> None:
    """Identical counts → no regression."""
    summary = {"unmarked_done": 5, "phantom_task": 10}
    assert _is_regression(summary, summary, 0.10) == []


def test_is_regression_growth_above_threshold() -> None:
    """Growth > threshold → regression."""
    prior = {"phantom_task": 100}
    current = {"phantom_task": 200}  # 100% growth
    regs = _is_regression(prior, current, 0.10)
    assert len(regs) == 1
    assert regs[0]["kind"] == "phantom_task"
    assert regs[0]["reason"] == "growth>10%"
    assert regs[0]["delta"] == 100
    assert regs[0]["delta_pct"] == 1.0


def test_is_regression_growth_below_threshold() -> None:
    """Growth <= threshold → no regression."""
    prior = {"phantom_task": 100}
    current = {"phantom_task": 105}  # 5% growth
    assert _is_regression(prior, current, 0.10) == []


def test_is_regression_shrinkage_ok() -> None:
    """Drift decreasing → not a regression (good!)."""
    prior = {"phantom_task": 100}
    current = {"phantom_task": 50}
    assert _is_regression(prior, current, 0.10) == []


def test_is_regression_new_kind() -> None:
    """New drift kind appearing (0 → >0) → regression."""
    prior = {"due_date_mismatch": 0}
    current = {"due_date_mismatch": 5}
    regs = _is_regression(prior, current, 0.10)
    assert len(regs) == 1
    assert regs[0]["kind"] == "due_date_mismatch"
    assert regs[0]["reason"] == "new_kind"


def test_is_regression_zero_to_zero_ok() -> None:
    """Both 0 → not a regression."""
    prior = {"due_date_mismatch": 0}
    current = {"due_date_mismatch": 0}
    assert _is_regression(prior, current, 0.10) == []


def test_is_regression_multiple() -> None:
    """Multiple kinds regressing → all reported."""
    prior = {"phantom_task": 100, "planned_orphan": 50, "unmarked_done": 10}
    current = {"phantom_task": 200, "planned_orphan": 100, "unmarked_done": 10}
    regs = _is_regression(prior, current, 0.10)
    assert len(regs) == 2
    kinds = {r["kind"] for r in regs}
    assert kinds == {"phantom_task", "planned_orphan"}


def test_is_regression_custom_threshold() -> None:
    """Threshold is configurable."""
    prior = {"phantom_task": 100}
    current = {"phantom_task": 105}  # 5% growth
    # With 1% threshold → regression.
    regs = _is_regression(prior, current, 0.01)
    assert len(regs) == 1
    assert regs[0]["reason"] == "growth>1%"


# === _load_two_snapshots ===

def test_load_two_snapshots(two_snapshots: Path) -> None:
    """Loads newer + older."""
    newer, older = _load_two_snapshots(two_snapshots)
    assert newer is not None
    assert older is not None
    assert newer["date"] == "2026-09-22"
    assert older["date"] == "2026-09-15"


def test_load_two_snapshots_insufficient(single_snapshot: Path) -> None:
    """Only 1 snapshot → newer only, older is None."""
    newer, older = _load_two_snapshots(single_snapshot)
    assert newer is not None
    assert older is None


def test_load_two_snapshots_empty(tmp_path: Path) -> None:
    """No snapshots → both None."""
    newer, older = _load_two_snapshots(tmp_path)
    assert newer is None
    assert older is None


def test_load_two_snapshots_malformed(tmp_path: Path) -> None:
    """Malformed JSON is skipped (returns None)."""
    (tmp_path / "2026-09-22.drift.json").write_text("not json", encoding="utf-8")
    newer, older = _load_two_snapshots(tmp_path)
    assert newer is None
    assert older is None


# === check ===

def test_check_no_regression(identical_snapshots: Path) -> None:
    """Identical snapshots → ok=True, no regressions."""
    result = check(identical_snapshots)
    assert result["ok"] is True
    assert result["regressions"] == []
    assert result["insufficient_data"] is False


def test_check_with_regression(two_snapshots: Path) -> None:
    """Growth + new kind → ok=False, 3 regressions."""
    result = check(two_snapshots)
    assert result["ok"] is False
    # planned_orphan 100→200 (100% growth), phantom_task 10→12 (20% growth),
    # due_date_mismatch 0→5 (new kind).
    assert len(result["regressions"]) == 3
    kinds = {r["kind"] for r in result["regressions"]}
    assert "phantom_task" in kinds
    assert "planned_orphan" in kinds
    assert "due_date_mismatch" in kinds


def test_check_insufficient_data(single_snapshot: Path) -> None:
    """1 snapshot only → insufficient_data=True, ok=True (don't fail CI)."""
    result = check(single_snapshot)
    assert result["ok"] is True
    assert result["insufficient_data"] is True


def test_check_empty_dir(tmp_path: Path) -> None:
    """No snapshots at all → ok=True (no regression possible)."""
    result = check(tmp_path)
    assert result["ok"] is True


def test_check_threshold_override(two_snapshots: Path) -> None:
    """threshold=2.0 (200%) → only mega-growth regresses.

    With prior=100, current=200 → 100% growth, not > 200%.
    phantom_task 10→12 → 20%, not > 200%.
    due_date_mismatch 0→5 → still flagged as new_kind regardless of threshold.
    """
    result = check(two_snapshots, threshold=2.0)
    # Only the new-kind regression remains (new_kind isn't gated by threshold).
    assert len(result["regressions"]) == 1
    assert result["regressions"][0]["kind"] == "due_date_mismatch"
    assert result["regressions"][0]["reason"] == "new_kind"
    assert result["ok"] is False


def test_check_returns_dates(two_snapshots: Path) -> None:
    """result includes current_date and prior_date."""
    result = check(two_snapshots)
    assert result["current_date"] == "2026-09-22"
    assert result["prior_date"] == "2026-09-15"


# === CLI: check ===

def test_main_check_ok(identical_snapshots: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["check", "--drift-dir", str(identical_snapshots)])
    assert rc == 0
    assert "no regressions" in capsys.readouterr().out


def test_main_check_regression(two_snapshots: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["check", "--drift-dir", str(two_snapshots)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "REGRESSION" in out
    assert "phantom_task" in out


def test_main_check_insufficient(
    single_snapshot: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["check", "--drift-dir", str(single_snapshot)])
    assert rc == 0
    assert "Insufficient" in capsys.readouterr().out


def test_main_check_json(two_snapshots: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["check", "--drift-dir", str(two_snapshots), "--json"])
    assert rc == 1
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ok"] is False
    assert len(parsed["regressions"]) >= 2


# === CLI: report ===

def test_main_report_markdown(two_snapshots: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["report", "--drift-dir", str(two_snapshots)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# Drift regression check" in out
    assert "| Kind | Prior | Current |" in out
    assert "phantom_task" in out
    assert "🚨 REGRESSION" in out  # kind that grew


def test_main_report_insufficient(
    single_snapshot: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["report", "--drift-dir", str(single_snapshot)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Insufficient data" in out


def test_main_report_json(two_snapshots: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["report", "--drift-dir", str(two_snapshots), "--json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert "report" in parsed
    assert "ok" in parsed


def test_main_invalid_cmd(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["bogus", "--drift-dir", str(tmp_path)])
