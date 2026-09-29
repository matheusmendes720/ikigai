"""M162 — ikigai-weekly skill.

Aggregate 7 daily reports + taskdog state into a weekly review.
Emits Proposal with WRITE_FILE change to vault/weekly/{iso}.md.

Cron: 0 9 * * 1
Slash: /ikigai-weekly
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from agents.v2.proposals import Proposal
from agents.v2.skills.cadence import (
    daily_path,
    list_vault_notes_in_range,
    render_weekly_review,
    weekly_path,
    was_created_in_window,
    was_done_in_window,
)


SKILL_NAME = "ikigai-weekly"


def propose(today: date | None = None) -> Proposal:
    today = today or date.today()
    week_start = today - timedelta(days=7)

    # Aggregate 7 daily reports
    daily_reports = list_vault_notes_in_range(daily_path, week_start, today)

    # Aggregate taskdog state
    try:
        from src.mesh.adapters.taskdog import TaskdogAdapter

        adapter = TaskdogAdapter()
        tasks = adapter.list_all()
    except Exception:  # noqa: BLE001
        tasks = []

    done_week = [t for t in tasks if was_done_in_window(t, week_start, today)]
    created_week = [t for t in tasks if was_created_in_window(t, week_start, today)]

    # Render markdown
    md = render_weekly_review(
        today=today,
        daily_reports=daily_reports,
        done_tasks=done_week,
        created_tasks=created_week,
    )

    # Build WRITE_FILE change proposal
    review_path = weekly_path(today)
    return Proposal(
        skill=SKILL_NAME,
        reasoning=(
            f"weekly review for week ending {today.isoformat()} "
            f"({len(daily_reports)} daily reports, "
            f"{len(done_week)} done, {len(created_week)} created)"
        ),
        changes=[
            {
                "action": "WRITE_FILE",
                "ueid": f"vault:weekly:{today.isocalendar().year}-W{today.isocalendar().week:02d}",
                "fields": {
                    "path": str(review_path),
                    "content": md,
                },
                "rationale": "weekly aggregation; user reviews before --approve",
            }
        ],
        approval_state="pending",
    )


def run_skill(today: date | None = None) -> Proposal:
    return propose(today=today)
