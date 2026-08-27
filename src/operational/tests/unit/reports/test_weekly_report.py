"""Unit tests for :mod:`operational.reports.weekly_report`."""
from __future__ import annotations

from datetime import date

from operational.reports.weekly_report import generate_weekly_report


class TestGenerateWeeklyReport:
    def test_minimal_output(self) -> None:
        report = generate_weekly_report(
            week_start=date(2026, 6, 1),
            week_end=date(2026, 6, 7),
        )
        assert "Weekly Report" in report
        assert "2026-06-01" in report
        assert report.startswith("---")

    def test_with_data(self) -> None:
        report = generate_weekly_report(
            week_start=date(2026, 6, 1),
            week_end=date(2026, 6, 7),
            days_with_course=5,
            days_without_course=2,
            hardwork_total_minutes=1800,
            hardwork_budget_minutes=1980,
            pomodoros_total=45,
            pomodoros_budget=55,
            sleep_hours_list=[7.5, 8.0, 6.0, 7.0, 8.5, 9.0, 7.0],
            workout_days=6,
            meditation_days=5,
        )
        assert "5 / 7" in report
        assert "1800min" in report
        assert "7.6" in report
        assert "6 / 7" in report

    def test_with_quadrants(self) -> None:
        report = generate_weekly_report(
            week_start=date(2026, 6, 1),
            week_end=date(2026, 6, 7),
            daily_quadrants=[
                (80, 85), (70, 60), (30, 40), (20, 80), (90, 90), (50, 50), (40, 30),
            ],
        )
        assert "Quadrant Distribution" in report
        assert "Q1" in report
        assert "Q2" in report
        assert "Q3" in report
        assert "Q4" in report

    def test_with_reflections(self) -> None:
        report = generate_weekly_report(
            week_start=date(2026, 6, 1),
            week_end=date(2026, 6, 7),
            reflections=["Great focus on Tuesday", "Need to improve sleep on Thursday"],
        )
        assert "Great focus" in report

    def test_sleep_calculations(self) -> None:
        report = generate_weekly_report(
            week_start=date(2026, 6, 1),
            week_end=date(2026, 6, 7),
            sleep_hours_list=[5.5, 8.0, 7.5, 4.0, 9.5, 7.0, 8.5],
        )
        assert "5.5" in report or "5" in report
        assert "4.0" in report or "4" in report
