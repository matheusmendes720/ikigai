"""M134 tests — drift_baseline.py.

Verifies daily snapshots + ISO-week trend + markdown rendering.
Uses synthetic snapshots so tests are hermetic.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest import drift_baseline as db  # noqa: E402
from tools.backtest.drift_baseline import (  # noqa: E402
    ALL_KINDS,
    FILENAME_RE,
    _iso_week_key,
    list_snapshots,
    main,
    snapshot,
    trend_report_markdown,
    weekly,
)


# === _iso_week_key ===

def test_iso_week_key_january() -> None:
    """ISO week of 2026-01-01 is 2026-W01."""
    assert _iso_week_key("2026-01-01") == "2026-W01"


def test_iso_week_key_december() -> None:
    """ISO week of 2026-12-31 is 2026-W53."""
    assert _iso_week_key("2026-12-31") == "2026-W53"


def test_iso_week_key_mid_year() -> None:
    """ISO week of 2026-09-22 is 2026-W39."""
    assert _iso_week_key("2026-09-22") == "2026-W39"


# === FILENAME_RE ===

def test_filename_re_matches() -> None:
    """Matches YYYY-MM-DD.drift.json."""
    m = FILENAME_RE.match("2026-09-22.drift.json")
    assert m is not None
    assert m.group(1) == "2026-09-22"


def test_filename_re_rejects_other_files() -> None:
    """Doesn't match other files."""
    assert FILENAME_RE.match("2026-09-22.json") is None
    assert FILENAME_RE.match("SHA256SUMS") is None
    assert FILENAME_RE.match("2026-9-22.drift.json") is None  # not zero-padded


# === snapshot ===

def test_snapshot_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """snapshot writes <DATE>.drift.json with summary + total."""
    fake_summary = {
        "unmarked_done": 1, "unmarked_open": 2, "phantom_task": 3,
        "planned_orphan": 4, "priority_mismatch": 0, "tag_mismatch": 0,
        "due_date_mismatch": 0,
    }
    monkeypatch.setattr(db, "_audit_drift_summary", lambda: fake_summary)
    target = snapshot(tmp_path, day=date(2026, 9, 22))
    assert target is not None
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["date"] == "2026-09-22"
    assert data["total"] == 10
    assert data["summary"]["planned_orphan"] == 4


def test_snapshot_first_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same date → skip (don't overwrite)."""
    fake_summary = {"unmarked_done": 1, "unmarked_open": 0, "phantom_task": 0,
                    "planned_orphan": 0, "priority_mismatch": 0, "tag_mismatch": 0,
                    "due_date_mismatch": 0}
    monkeypatch.setattr(db, "_audit_drift_summary", lambda: fake_summary)
    s1 = snapshot(tmp_path, day=date(2026, 9, 22))
    s2 = snapshot(tmp_path, day=date(2026, 9, 22))
    assert s1 == s2
    assert s1.exists()


def test_snapshot_ensures_all_kinds_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Even if audit_drift returns partial summary, snapshot has all 7 kinds."""
    # Patch the underlying audit_drift so _audit_drift_summary's normalization runs.
    from tools.backtest import vault_propagation as vp

    def fake_audit_drift():
        return {"summary": {"unmarked_done": 5}}  # Only 1 of 7 kinds

    monkeypatch.setattr(vp, "audit_drift", fake_audit_drift)
    target = snapshot(tmp_path, day=date(2026, 9, 22))
    data = json.loads(target.read_text(encoding="utf-8"))
    for kind in ALL_KINDS:
        assert kind in data["summary"]
        if kind != "unmarked_done":
            assert data["summary"][kind] == 0


# === list_snapshots ===

def test_list_snapshots_returns_newest_first(tmp_path: Path) -> None:
    """list_snapshots returns newest first."""
    for d in ("2026-09-20", "2026-09-22", "2026-09-21"):
        (tmp_path / f"{d}.drift.json").write_text("{}", encoding="utf-8")
    files = list_snapshots(tmp_path)
    assert [f.stem.replace(".drift", "") for f in files] == [
        "2026-09-22", "2026-09-21", "2026-09-20",
    ]


def test_list_snapshots_ignores_other_files(tmp_path: Path) -> None:
    """Doesn't return SHA256SUMS or other files."""
    (tmp_path / "2026-09-22.drift.json").write_text("{}", encoding="utf-8")
    (tmp_path / "SHA256SUMS").write_text("hash", encoding="utf-8")
    (tmp_path / "2026-09-22.json").write_text("{}", encoding="utf-8")
    files = list_snapshots(tmp_path)
    assert len(files) == 1
    assert files[0].name == "2026-09-22.drift.json"


def test_list_snapshots_empty_dir(tmp_path: Path) -> None:
    """Empty / non-existent dir returns []."""
    assert list_snapshots(tmp_path / "empty") == []
    assert list_snapshots(tmp_path) == []


# === weekly ===

def test_weekly_groups_by_iso_week(tmp_path: Path) -> None:
    """Multiple dates in same week → grouped."""
    # All 3 in 2026-W39 (Sep 21-27).
    for d in ("2026-09-21", "2026-09-22", "2026-09-23"):
        payload = {
            "date": d,
            "summary": {k: (1 if k == "planned_orphan" else 0) for k in ALL_KINDS},
            "total": 1,
        }
        (tmp_path / f"{d}.drift.json").write_text(json.dumps(payload), encoding="utf-8")
    weeks = weekly(tmp_path)
    assert len(weeks) == 1
    assert weeks[0]["week"] == "2026-W39"
    assert weeks[0]["snapshot_count"] == 3
    assert weeks[0]["totals"]["planned_orphan"] == 3


def test_weekly_aggregates_kinds_across_snapshots(tmp_path: Path) -> None:
    """Aggregates same kind across multiple snapshots in same week."""
    for d, count in (("2026-09-21", 2), ("2026-09-22", 5), ("2026-09-23", 1)):
        payload = {
            "date": d,
            "summary": {k: (count if k == "planned_orphan" else 0) for k in ALL_KINDS},
            "total": count,
        }
        (tmp_path / f"{d}.drift.json").write_text(json.dumps(payload), encoding="utf-8")
    weeks = weekly(tmp_path)
    assert weeks[0]["totals"]["planned_orphan"] == 8  # 2+5+1


def test_weekly_since_days_filters(tmp_path: Path) -> None:
    """since_days filter excludes old snapshots."""
    # Old (90+ days ago) + recent.
    for d in ("2026-01-01", "2026-09-22"):
        payload = {"date": d, "summary": {k: 1 for k in ALL_KINDS}, "total": 7}
        (tmp_path / f"{d}.drift.json").write_text(json.dumps(payload), encoding="utf-8")
    # since_days=30 only keeps 2026-09-22.
    weeks = weekly(tmp_path, since_days=30)
    total_count = sum(w["snapshot_count"] for w in weeks)
    assert total_count == 1
    # since_days=0 means all-time.
    weeks_all = weekly(tmp_path, since_days=0)
    total_count_all = sum(w["snapshot_count"] for w in weeks_all)
    assert total_count_all == 2


def test_weekly_no_snapshots(tmp_path: Path) -> None:
    """Empty dir → empty list."""
    assert weekly(tmp_path) == []


# === trend_report_markdown ===

def test_trend_report_markdown_empty() -> None:
    """Empty weeks list → 'no snapshots' message."""
    md = trend_report_markdown([])
    assert "# Drift trend" in md
    assert "no snapshots" in md.lower()


def test_trend_report_markdown_with_data() -> None:
    """Single week → markdown table with all columns."""
    weeks = [{
        "week": "2026-W39",
        "snapshot_count": 3,
        "totals": {k: (i + 1) for i, k in enumerate(ALL_KINDS)},
    }]
    md = trend_report_markdown(weeks)
    assert "# Drift trend" in md
    assert "2026-W39" in md
    assert "unmarked_done" in md
    assert "due_date_mismatch" in md
    # Total column = sum of all kinds.
    total = sum(i + 1 for i in range(len(ALL_KINDS)))
    assert str(total) in md


def test_trend_report_markdown_missing_kind() -> None:
    """Totals dict missing a kind → 0 in that column."""
    weeks = [{
        "week": "2026-W39",
        "snapshot_count": 1,
        "totals": {"planned_orphan": 5},  # only 1 of 7 kinds
    }]
    md = trend_report_markdown(weeks)
    # All 7 kinds should still appear in header.
    for kind in ALL_KINDS:
        assert kind in md
    # The 6 missing kinds → "0" in the row.
    assert "| 0 |" in md


# === CLI ===

def test_main_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    fake_summary = {k: 0 for k in ALL_KINDS}
    fake_summary["planned_orphan"] = 7
    monkeypatch.setattr(db, "_audit_drift_summary", lambda: fake_summary)
    rc = main(["snapshot", "--drift-dir", str(tmp_path), "--date", "2026-09-22"])
    assert rc == 0
    assert (tmp_path / "2026-09-22.drift.json").exists()


def test_main_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for d in ("2026-09-21", "2026-09-22"):
        (tmp_path / f"{d}.drift.json").write_text("{}", encoding="utf-8")
    rc = main(["list", "--drift-dir", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "2026-09-22.drift.json" in captured.out
    assert "2026-09-21.drift.json" in captured.out


def test_main_weekly_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    payload = {"date": "2026-09-22", "summary": {k: 1 for k in ALL_KINDS}, "total": 7}
    (tmp_path / "2026-09-22.drift.json").write_text(json.dumps(payload), encoding="utf-8")
    rc = main(["weekly", "--drift-dir", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "2026-W39" in captured.out


def test_main_weekly_to_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    payload = {"date": "2026-09-22", "summary": {k: 1 for k in ALL_KINDS}, "total": 7}
    (tmp_path / "2026-09-22.drift.json").write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "trend.md"
    rc = main(["weekly", "--drift-dir", str(tmp_path), "--out", str(out)])
    assert rc == 0
    assert out.exists()
    assert "2026-W39" in out.read_text(encoding="utf-8")


def test_main_invalid_cmd(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["bogus", "--drift-dir", str(tmp_path)])
