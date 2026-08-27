"""Regression tests for analytics_cmd._window() — P0 #1.

The original bug was module-level `_START`/`_END` constants that froze on first
import. The fix moved the computation into a per-call `_window(days)` function
that re-evaluates `date.today()` on every invocation. These tests anchor that
behaviour against future regressions (e.g. someone optimising by hoisting the
call back to module level).
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from operational.cli.commands import analytics_cmd


class TestAnalyticsWindow:
    def test_default_window_is_180_days(self) -> None:
        """Default 180-day window ends today, starts 180 days ago."""
        end_today = date(2026, 7, 2)
        with patch("operational.cli.commands.analytics_cmd.date") as mock_date:
            mock_date.today.return_value = end_today
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            start, end = analytics_cmd._window()
        assert end == end_today
        assert start == end_today - timedelta(days=180)

    def test_window_recomputes_per_call(self) -> None:
        """Two successive calls return different end-dates when `date.today()` advances.

        This is the load-bearing assertion: if `_window()` is ever rewritten to
        cache (e.g. back to module-level constants), this test fails loudly.
        """
        with patch("operational.cli.commands.analytics_cmd.date") as mock_date:
            mock_date.today.return_value = date(2026, 1, 1)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            _, end_first = analytics_cmd._window()

            mock_date.today.return_value = date(2026, 7, 2)
            _, end_second = analytics_cmd._window()

        assert end_first == date(2026, 1, 1)
        assert end_second == date(2026, 7, 2)
        assert end_second > end_first

    def test_custom_days(self) -> None:
        """Custom day count flows through to start offset; end stays today."""
        end_today = date(2026, 7, 2)
        with patch("operational.cli.commands.analytics_cmd.date") as mock_date:
            mock_date.today.return_value = end_today
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            start, end = analytics_cmd._window(days=30)
        assert end == end_today
        assert start == end_today - timedelta(days=30)

    def test_window_does_not_share_state_between_calls(self) -> None:
        """A regression guard: cached globals would silently freeze the window."""
        fixed_today = date(2026, 7, 2)
        with patch("operational.cli.commands.analytics_cmd.date") as mock_date:
            mock_date.today.return_value = fixed_today
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            # Two calls within the same day should produce identical windows —
            # the function should be deterministic for a frozen "today".
            a = analytics_cmd._window()
            b = analytics_cmd._window()
        assert a == b
        assert a == (fixed_today - timedelta(days=180), fixed_today)
