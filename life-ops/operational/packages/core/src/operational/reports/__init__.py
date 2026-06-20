"""Reports — generate daily summaries and weekly reports.

Public API
----------
- :func:`generate_daily_summary` — Markdown daily summary (PAV §10)
- :func:`generate_weekly_report` — Markdown weekly report (PAV 🔟)
- :func:`render_cartesian_ascii` — Cartesian plane visualisation
- :func:`calculate_efficiency` — Productivity (X) and efficiency (Y)
"""
from __future__ import annotations

from operational.reports.daily_summary import (
    calculate_efficiency,
    generate_daily_summary,
    render_cartesian_ascii,
)
from operational.reports.weekly_report import generate_weekly_report

__all__ = [
    "calculate_efficiency",
    "generate_daily_summary",
    "generate_weekly_report",
    "render_cartesian_ascii",
]
