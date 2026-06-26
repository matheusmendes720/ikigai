"""Unit tests for PeriodReport entity + parser.

Source: .omo/plans/period-reports-sync.md T5
"""
from __future__ import annotations

import warnings
from datetime import date, timedelta
from pathlib import Path

import pytest

import sys
VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from models.period_report import (
    PeriodReport,
    PeriodReportParser,
    PeriodSyncStats,
    _PERIOD_DAYS,
    _PERIOD_VERDICTS,
)


def make_valid_kw(period="daily", **overrides):
    """Factory for valid PeriodReport kwargs."""
    base = dict(
        id="test-1",
        entity_type="period_report",
        period=period,
        date_start=date(2026, 6, 26),
        date_end=date(2026, 6, 26),
        verdict="PASS",
        verdict_score=0.85,
        vault_path="/test.md",
        vault_hash="a" * 16,
    )
    # Adjust dates for non-daily periods
    period_days = _PERIOD_DAYS.get(period)
    if period_days and period != "daily":
        base["date_end"] = base["date_start"] + timedelta(days=period_days - 1)
    if period == "sonho":
        # sonho has no fixed length — override dates
        base["date_end"] = base["date_start"] + timedelta(days=180)
        base["verdict"] = "ACTIVE"
        base["verdict_score"] = 0.65
    if period == "onda":
        base["verdict"] = "CONTINUE_WAVE"
    base.update(overrides)
    return base


class TestPeriodReportValidation:
    """Tests for all Pydantic validators."""

    def test_valid_daily(self):
        r = PeriodReport(**make_valid_kw("daily"))
        assert r.period == "daily"
        assert r.verdict == "PASS"
        assert r.verdict_score == 0.85

    def test_valid_weekly(self):
        r = PeriodReport(**make_valid_kw("weekly"))
        assert r.period == "weekly"
        assert r.verdict == "PASS"

    def test_valid_onda(self):
        r = PeriodReport(**make_valid_kw("onda"))
        assert r.verdict == "CONTINUE_WAVE"
        assert r.verdict_score == 0.85

    def test_valid_quarterly(self):
        r = PeriodReport(**make_valid_kw("quarterly"))
        assert r.period == "quarterly"
        assert r.verdict_score == 0.85

    def test_valid_sonho(self):
        r = PeriodReport(**make_valid_kw("sonho"))
        assert r.verdict == "ACTIVE"
        assert r.verdict_score == 0.65

    def test_invalid_verdict_for_daily(self):
        with pytest.raises(ValueError, match="not allowed"):
            PeriodReport(**make_valid_kw("daily", verdict="KILL_WAVE"))

    def test_invalid_verdict_for_weekly(self):
        with pytest.raises(ValueError, match="not allowed"):
            PeriodReport(**make_valid_kw("weekly", verdict="ACTIVE"))

    def test_invalid_verdict_for_sonho(self):
        with pytest.raises(ValueError, match="not allowed"):
            PeriodReport(**make_valid_kw("sonho", verdict="PASS"))

    def test_sonho_cannot_have_parent(self):
        with pytest.raises(ValueError, match="sonho reports cannot have parent_period"):
            PeriodReport(**make_valid_kw("sonho", parent_period="forbidden"))

    def test_sonho_with_parent_other_period_ok(self):
        # Non-sonho can have parent_period
        r = PeriodReport(**make_valid_kw("weekly", parent_period="sonho-1"))
        assert r.parent_period == "sonho-1"

    def test_date_end_before_start_raises(self):
        with pytest.raises(ValueError, match="date_end.*< date_start"):
            PeriodReport(**make_valid_kw("daily", date_end=date(2026, 6, 25)))

    def test_weekly_too_long_raises(self):
        # Override date_end to be 30 days out — should fail weekly (~7 days) validation
        with pytest.raises(ValueError, match="expected ~7 days"):
            PeriodReport(**make_valid_kw(
                "weekly",
                date_end=date(2026, 6, 26) + timedelta(days=30),
            ))

    def test_daily_one_day_exact(self):
        r = PeriodReport(**make_valid_kw("daily"))
        assert r.period == "daily"
        assert r.date_end == r.date_start

    def test_weekly_exact_seven_days(self):
        r = PeriodReport(**make_valid_kw("weekly"))
        assert r.period == "weekly"
        assert (r.date_end - r.date_start).days == 6  # 7 days inclusive

    def test_verdict_score_out_of_range_raises(self):
        with pytest.raises(ValueError):
            PeriodReport(**make_valid_kw("daily", verdict_score=1.5))
        with pytest.raises(ValueError):
            PeriodReport(**make_valid_kw("daily", verdict_score=-0.1))

    def test_verdict_score_consistency_fail_high_score_warns(self):
        """FAIL verdict with high score should warn."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            r = PeriodReport(**make_valid_kw("daily", verdict="FAIL", verdict_score=0.8))
            assert len(w) == 1
            assert "verdict=FAIL but verdict_score=0.8" in str(w[0].message)

    def test_verdict_score_consistency_kill_wave_warns(self):
        """KILL_WAVE verdict with high score should warn."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            r = PeriodReport(**make_valid_kw("onda", verdict="KILL_WAVE", verdict_score=0.9))
            assert len(w) == 1
            assert "verdict=KILL_WAVE but verdict_score=0.9" in str(w[0].message)

    def test_no_warning_for_fail_low_score(self):
        """FAIL verdict with low score should NOT warn."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            r = PeriodReport(**make_valid_kw("daily", verdict="FAIL", verdict_score=0.2))
            fail_warnings = [x for x in w if "verdict=" in str(x.message)]
            assert len(fail_warnings) == 0

    def test_extra_fields_allowed(self):
        """extra='allow' preserves unknown fields."""
        r = PeriodReport(**make_valid_kw("daily", custom_field="x", another=42))
        assert r.model_dump()["custom_field"] == "x"
        assert r.model_dump()["another"] == 42

    def test_optional_defaults(self):
        """Optional fields have correct defaults."""
        r = PeriodReport(**make_valid_kw("daily"))
        assert r.sonho_id is None
        assert r.ikigai_vector is None
        assert r.xp_gained is None
        assert r.policy_recommendation is None
        assert r.parent_period is None
        assert r.status == "active"
        assert r.tags == []
        assert r.template_version == "1.0"
        assert r.ikigai_cluster == "plan"

    def test_auto_id_from_vault_path(self):
        """id defaults to vault_path stem when empty."""
        r = PeriodReport(**make_valid_kw("daily", id="", vault_path="/foo/bar/my-report.md"))
        assert r.id == "my-report"

    def test_explicit_id_preserved(self):
        """Explicit id is not overridden."""
        r = PeriodReport(**make_valid_kw("daily", id="explicit-id"))
        assert r.id == "explicit-id"

    def test_all_period_types_in_verdicts_map(self):
        """_PERIOD_VERDICTS covers all period types."""
        for period in ["daily", "weekly", "onda", "quarterly", "sonho"]:
            assert period in _PERIOD_VERDICTS, f"Missing verdicts for {period}"
            assert isinstance(_PERIOD_VERDICTS[period], set)
            assert len(_PERIOD_VERDICTS[period]) > 0

    def test_all_period_types_in_days_map(self):
        """_PERIOD_DAYS covers all period types."""
        for period in ["daily", "weekly", "onda", "quarterly", "sonho"]:
            assert period in _PERIOD_DAYS, f"Missing days for {period}"


class TestPeriodReportParser:
    """Tests for PeriodReportParser.parse_file."""

    def test_parse_valid_daily_file(self, tmp_path: Path):
        md = tmp_path / "daily.md"
        md.write_text(
            "---\n"
            "type: period_report\n"
            "entity_type: period_report\n"
            "period: daily\n"
            "date_start: 2026-06-26\n"
            "date_end: 2026-06-26\n"
            "verdict: PASS\n"
            "verdict_score: 0.85\n"
            "---\n\n"
            "# Body\n",
            encoding="utf-8",
        )
        r = PeriodReportParser.parse_file(str(md))
        assert r is not None
        assert r.period == "daily"
        assert r.verdict == "PASS"
        assert len(r.vault_hash) == 16
        assert r.vault_path == str(md)

    def test_parse_returns_none_for_non_period(self, tmp_path: Path):
        md = tmp_path / "other.md"
        md.write_text(
            "---\n"
            "type: project\n"
            "title: Something\n"
            "---\n"
            "# body\n",
            encoding="utf-8",
        )
        assert PeriodReportParser.parse_file(str(md)) is None

    def test_parse_returns_none_for_missing_type(self, tmp_path: Path):
        md = tmp_path / "incomplete.md"
        md.write_text(
            "---\n"
            "entity_type: period_report\n"
            "period: daily\n"
            "date_start: 2026-06-26\n"
            "date_end: 2026-06-26\n"
            "verdict: PASS\n"
            "verdict_score: 0.85\n"
            "---\n",
            encoding="utf-8",
        )
        assert PeriodReportParser.parse_file(str(md)) is None

    def test_parse_returns_none_for_invalid_yaml(self, tmp_path: Path):
        md = tmp_path / "bad.md"
        md.write_text(
            "---\n"
            "type: period_report\n"
            "entity_type: period_report\n"
            "period: daily\n"
            "date_start: not-a-date\n"
            "date_end: 2026-06-26\n"
            "verdict: PASS\n"
            "verdict_score: 0.85\n"
            "---\n",
            encoding="utf-8",
        )
        assert PeriodReportParser.parse_file(str(md)) is None

    def test_parse_returns_none_for_bad_verdict(self, tmp_path: Path):
        """Invalid verdict raises during model validation, parse_file returns None."""
        md = tmp_path / "bad-verdict.md"
        md.write_text(
            "---\n"
            "type: period_report\n"
            "entity_type: period_report\n"
            "period: daily\n"
            "date_start: 2026-06-26\n"
            "date_end: 2026-06-26\n"
            "verdict: ACTIVE\n"  # not valid for daily
            "verdict_score: 0.85\n"
            "---\n",
            encoding="utf-8",
        )
        assert PeriodReportParser.parse_file(str(md)) is None

    def test_parse_vault_hash_is_deterministic(self, tmp_path: Path):
        md = tmp_path / "daily.md"
        md.write_text(
            "---\n"
            "type: period_report\n"
            "entity_type: period_report\n"
            "period: daily\n"
            "date_start: 2026-06-26\n"
            "date_end: 2026-06-26\n"
            "verdict: PASS\n"
            "verdict_score: 0.85\n"
            "---\n",
            encoding="utf-8",
        )
        r1 = PeriodReportParser.parse_file(str(md))
        r2 = PeriodReportParser.parse_file(str(md))
        assert r1 is not None
        assert r2 is not None
        assert r1.vault_hash == r2.vault_hash

    def test_parse_different_content_different_hash(self, tmp_path: Path):
        md1 = tmp_path / "d1.md"
        md1.write_text(
            "---\n"
            "type: period_report\n"
            "entity_type: period_report\n"
            "period: daily\n"
            "date_start: 2026-06-26\n"
            "date_end: 2026-06-26\n"
            "verdict: PASS\n"
            "verdict_score: 0.85\n"
            "---\n",
            encoding="utf-8",
        )
        md2 = tmp_path / "d2.md"
        md2.write_text(
            "---\n"
            "type: period_report\n"
            "entity_type: period_report\n"
            "period: daily\n"
            "date_start: 2026-06-27\n"
            "date_end: 2026-06-27\n"
            "verdict: PASS\n"
            "verdict_score: 0.85\n"
            "---\n",
            encoding="utf-8",
        )
        r1 = PeriodReportParser.parse_file(str(md1))
        r2 = PeriodReportParser.parse_file(str(md2))
        assert r1 is not None
        assert r2 is not None
        assert r1.vault_hash != r2.vault_hash

    def test_parse_returns_none_for_wrong_entity_type(self, tmp_path: Path):
        """type=period_report but entity_type=something_else should return None."""
        md = tmp_path / "wrong-entity.md"
        md.write_text(
            "---\n"
            "type: period_report\n"
            "entity_type: project\n"
            "period: daily\n"
            "date_start: 2026-06-26\n"
            "date_end: 2026-06-26\n"
            "verdict: PASS\n"
            "verdict_score: 0.85\n"
            "---\n",
            encoding="utf-8",
        )
        assert PeriodReportParser.parse_file(str(md)) is None

    def test_parse_corrupt_file_returns_none(self, tmp_path: Path):
        md = tmp_path / "corrupt.md"
        md.write_text("\xff\xfe\0\0", encoding="utf-8")
        assert PeriodReportParser.parse_file(str(md)) is None


class TestPeriodSyncStats:
    """Tests for PeriodSyncStats (frozen=True)."""

    def test_defaults(self):
        s = PeriodSyncStats()
        assert s.ingested == 0
        assert s.skipped == 0
        assert s.updated == 0
        assert s.errors == 0
        assert s.orphans == 0
        assert s.conflicts == 0
        assert s.file_errors == []

    def test_custom_values(self):
        s = PeriodSyncStats(ingested=5, skipped=2, updated=3, errors=1)
        assert s.ingested == 5
        assert s.skipped == 2
        assert s.updated == 3
        assert s.errors == 1

    def test_frozen_cannot_mutate(self):
        s = PeriodSyncStats()
        with pytest.raises(Exception):  # ValidationError from frozen config
            s.ingested = 5  # type: ignore

    def test_file_errors_list(self):
        s = PeriodSyncStats(file_errors=[{"path": "/foo.md", "error": "parse failed"}])
        assert len(s.file_errors) == 1
        assert s.file_errors[0]["path"] == "/foo.md"
