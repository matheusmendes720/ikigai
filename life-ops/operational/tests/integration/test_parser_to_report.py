"""Integration: parser output → report generation."""
from __future__ import annotations

from operational.parsers.frontmatter import parse_journal_frontmatter
from operational.reports.daily_summary import generate_daily_summary


def test_parsed_frontmatter_feeds_daily_report() -> None:
    md = """---
id: day_2026_06_07
date: 2026-06-07
energia_nivel: 8
pomodoros_completos: 6
periods_covered: [MANHA, TARDE]
---
Good day of focused work.
"""
    entry = parse_journal_frontmatter(md)
    report = generate_daily_summary(
        report_date=entry.date,
        energia=entry.energia_nivel,
        pomodoros_completed=entry.pomodoros_completos,
    )
    assert str(entry.date) in report
    assert "8" in report
    assert "6" in report


def test_empty_frontmatter_generates_report() -> None:
    md = "---\nid: day_empty\ndate: 2026-06-07\n---\n\nJust a note."
    entry = parse_journal_frontmatter(md)
    report = generate_daily_summary(report_date=entry.date)
    assert "Daily Summary" in report
