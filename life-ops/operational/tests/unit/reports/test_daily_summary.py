"""Unit tests for :mod:`operational.reports.daily_summary`."""
from __future__ import annotations

from datetime import date

import pytest

from operational.reports.daily_summary import (
    calculate_efficiency,
    generate_daily_summary,
    render_cartesian_ascii,
)


class TestGenerateDailySummary:
    def test_minimal_output(self) -> None:
        report = generate_daily_summary(
            report_date=date(2026, 6, 7),
        )
        assert "Daily Summary" in report
        assert "2026-06-07" in report
        assert report.startswith("---")

    def test_with_data(self) -> None:
        report = generate_daily_summary(
            report_date=date(2026, 6, 7),
            wake_hour=4,
            wake_minute=0,
            sleep_hour=20,
            sleep_minute=30,
            sleep_hours=7.5,
            sleep_quality="bom",
            workout_done=True,
            workout_minutes=60,
            meditation_done=True,
            meditation_minutes=15,
            energia=8,
            day_type="curso",
            hardwork_budget_minutes=240,
            hardwork_actual_minutes=220,
            pomodoros_completed=8,
            pomodoros_budget=10,
            lunch_eat_minutes=5,
            lunch_rest_minutes=30,
            dinner_before_18=True,
            transitions_completed=8,
            desvios=["Acordei 30min tarde"],
            licoes=["Preparar café na noite anterior"],
            ajustes=["Pausa extra de 5min no período da tarde"],
        )
        assert "Hardwork" in report
        assert "220min" in report
        assert "8/10" in report
        assert "Acordei 30min tarde" in report
        assert "Preparar café" in report

    def test_includes_cartesian(self) -> None:
        report = generate_daily_summary(
            report_date=date(2026, 6, 7),
            hardwork_budget_minutes=480,
            hardwork_actual_minutes=360,
        )
        assert "Cartesian" in report
        assert "Q1" in report or "Q2" in report or "Q3" in report or "Q4" in report


class TestRenderCartesianAscii:
    def test_origin_point(self) -> None:
        out = render_cartesian_ascii(0, 0)
        assert "X=0%" in out
        assert "Y=0%" in out
        assert "Q3" in out

    def test_maximum_point(self) -> None:
        out = render_cartesian_ascii(100, 100)
        assert "X=100%" in out
        assert "Q1" in out

    def test_midpoint(self) -> None:
        out = render_cartesian_ascii(50, 50)
        assert "X=50%" in out

    def test_quadrant_q2(self) -> None:
        out = render_cartesian_ascii(30, 80)
        assert "Q2" in out

    def test_quadrant_q4(self) -> None:
        out = render_cartesian_ascii(70, 30)
        assert "Q4" in out


class TestCalculateEfficiency:
    def test_normal_case(self) -> None:
        assert calculate_efficiency(240, 220) == pytest.approx(91.67, rel=0.01)

    def test_exceeds_budget(self) -> None:
        assert calculate_efficiency(240, 300) == 100.0

    def test_zero_budget(self) -> None:
        assert calculate_efficiency(0, 100) == 0.0

    def test_exact_match(self) -> None:
        assert calculate_efficiency(240, 240) == 100.0

    def test_half_of_budget(self) -> None:
        assert calculate_efficiency(240, 120) == 50.0
