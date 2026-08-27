"""Hypothesis property tests for PeriodReport.

Source: .omo/plans/period-reports-sync.md T7

Properties tested:
1. Verdict x Period: PeriodReport validates iff verdict is in _PERIOD_VERDICTS[period]
2. Score range: verdict_score always in [0, 1]
3. Date range: date_end >= date_start
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

VIBE_OPS_SRC = Path(__file__).resolve().parents[2] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from models.period_report import (
    PeriodReport,
    _PERIOD_DAYS,
    _PERIOD_VERDICTS,
)


# Strategies
periods_st = st.sampled_from(["daily", "weekly", "onda", "quarterly", "sonho"])

# All valid verdicts across all periods
all_verdicts_st = st.sampled_from(
    sorted(set().union(*_PERIOD_VERDICTS.values()))
)

verdict_score_st = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

date_st = st.dates(
    min_value=date(2024, 1, 1),
    max_value=date(2030, 12, 31),
)


def period_verdicts_st():
    """Strategy yielding (period, valid_verdict) tuples."""
    def _inner(period):
        return st.sampled_from(sorted(_PERIOD_VERDICTS[period]))
    return _inner


def _make_valid_kwargs(period: str, verdict: str, verdict_score: float,
                     date_start: date, date_end: date) -> dict:
    """Build valid PeriodReport kwargs for given inputs."""
    base = dict(
        id="prop-test",
        period=period,
        verdict=verdict,
        verdict_score=verdict_score,
        vault_path="/test.md",
        vault_hash="a" * 16,
        date_start=date_start,
        date_end=date_end,
    )
    return base


class TestVerdictPeriodMatrix:
    """Property: Verdict validates iff in allowed set for period."""

    @given(period=periods_st, valid_verdict=st.sampled_from(sorted(_PERIOD_VERDICTS["daily"])))
    @settings(max_examples=100)
    def test_daily_valid_verdict_always_validates(self, period, valid_verdict):
        # daily accepts PASS, PARTIAL, FAIL only
        # For other periods, use the appropriate verdict set
        # Property: for each period, pick a verdict from ITS set and verify it validates
        valid_set = _PERIOD_VERDICTS[period]
        v = valid_verdict if valid_verdict in valid_set else next(iter(valid_set))
        d = date(2026, 6, 26)
        # Adjust dates for period
        days = _PERIOD_DAYS.get(period) or 180
        d_end = d + timedelta(days=days - 1)
        r = PeriodReport(**_make_valid_kwargs(period, v, 0.5, d, d_end))
        assert r.verdict == v

    @given(
        period=periods_st,
        invalid_verdict=st.sampled_from(
            ["INVALID_X", "not_a_verdict", "xxx", "passing", "fail_test"]
        ),
    )
    @settings(max_examples=100)
    def test_invalid_verdict_strings_always_rejected(self, period, invalid_verdict):
        """Property: any string NOT in the allowed set is rejected."""
        valid_set = _PERIOD_VERDICTS[period]
        if invalid_verdict in valid_set:
            # Skip if it happens to be valid
            return
        # Use dates appropriate for the period
        d = date(2026, 6, 26)
        days = _PERIOD_DAYS.get(period) or 180
        d_end = d + timedelta(days=days - 1)
        with pytest.raises(ValueError):
            PeriodReport(**_make_valid_kwargs(period, invalid_verdict, 0.5, d, d_end))


class TestScoreRange:
    """Property: verdict_score must be in [0, 1]."""

    @given(
        period=periods_st,
        score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_score_in_valid_range_validates(self, period, score):
        """Any score in [0, 1] should be accepted."""
        v = next(iter(_PERIOD_VERDICTS[period]))
        d = date(2026, 6, 26)
        days = _PERIOD_DAYS.get(period) or 180
        d_end = d + timedelta(days=days - 1)
        r = PeriodReport(**_make_valid_kwargs(period, v, score, d, d_end))
        assert r.verdict_score == score

    @given(
        period=periods_st,
        score=st.floats(min_value=1.01, max_value=1000.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_score_above_one_rejected(self, period, score):
        """Property: score > 1.0 always rejected."""
        v = next(iter(_PERIOD_VERDICTS[period]))
        d = date(2026, 6, 26)
        days = _PERIOD_DAYS.get(period) or 180
        d_end = d + timedelta(days=days - 1)
        with pytest.raises(ValueError):
            PeriodReport(**_make_valid_kwargs(period, v, score, d, d_end))

    @given(
        period=periods_st,
        score=st.floats(min_value=-1000.0, max_value=-0.01, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_score_below_zero_rejected(self, period, score):
        """Property: score < 0 always rejected."""
        v = next(iter(_PERIOD_VERDICTS[period]))
        d = date(2026, 6, 26)
        days = _PERIOD_DAYS.get(period) or 180
        d_end = d + timedelta(days=days - 1)
        with pytest.raises(ValueError):
            PeriodReport(**_make_valid_kwargs(period, v, score, d, d_end))


class TestDateRange:
    """Property: date_end >= date_start always."""

    @given(
        period=periods_st,
        d_start=date_st,
        d_offset=st.integers(min_value=0, max_value=365),
    )
    @settings(max_examples=100)
    def test_date_end_after_start_validates(self, period, d_start, d_offset):
        v = next(iter(_PERIOD_VERDICTS[period]))
        d_end = d_start + timedelta(days=d_offset)
        # Need to handle the period day constraint
        days = _PERIOD_DAYS.get(period)
        if days is None:
            # sonho: any date range up to 365 days
            if (d_end - d_start).days > 365:
                return
        else:
            # Other periods: ~days +/- 1
            actual = (d_end - d_start).days + 1
            if abs(actual - days) > 1:
                return
        r = PeriodReport(**_make_valid_kwargs(period, v, 0.5, d_start, d_end))
        assert r.date_start == d_start
        assert r.date_end == d_end

    @given(
        period=periods_st,
        d_start=date_st,
        d_offset=st.integers(min_value=1, max_value=365),
    )
    @settings(max_examples=100)
    def test_date_end_before_start_rejected(self, period, d_start, d_offset):
        """Property: date_end < date_start always rejected."""
        v = next(iter(_PERIOD_VERDICTS[period]))
        d_end = d_start - timedelta(days=d_offset)
        with pytest.raises(ValueError):
            PeriodReport(**_make_valid_kwargs(period, v, 0.5, d_start, d_end))


class TestHierarchy:
    """Property: sonho cannot have parent_period."""

    @given(
        parent_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("L", "N"), max_codepoint=0x7e
        )),
    )
    @settings(max_examples=50)
    def test_sonho_with_any_parent_rejected(self, parent_id):
        """Property: any parent_period on a sonho is rejected."""
        # sonho + any parent
        with pytest.raises(ValueError, match="sonho reports cannot have parent_period"):
            PeriodReport(**_make_valid_kwargs(
                "sonho", "ACTIVE", 0.65,
                date(2026, 1, 1), date(2026, 12, 31),
                # parent_period="any-id"
            ) | {"parent_period": parent_id})

    @given(
        parent_id=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_non_sonho_with_parent_accepted(self, parent_id):
        """Property: non-sonho periods can have any parent_period."""
        v = next(iter(_PERIOD_VERDICTS["weekly"]))
        r = PeriodReport(**_make_valid_kwargs(
            "weekly", v, 0.7,
            date(2026, 6, 1), date(2026, 6, 7),
        ) | {"parent_period": parent_id})
        assert r.parent_period == parent_id