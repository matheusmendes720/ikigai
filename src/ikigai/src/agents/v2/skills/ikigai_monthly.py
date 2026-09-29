"""M162 — ikigai-monthly skill.

Aggregate last 4 weekly reviews into a monthly review.
Emits Proposal with WRITE_FILE change to vault/monthly/{yyyy-mm}.md.

Cron: 0 10 1 * *
Slash: /ikigai-monthly
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from agents.v2.proposals import Proposal
from agents.v2.skills.cadence import (
    list_vault_notes_in_range,
    monthly_path,
    render_monthly_review,
    weekly_path,
)


SKILL_NAME = "ikigai-monthly"


def propose(today: date | None = None) -> Proposal:
    today = today or date.today()
    # Last 28 days covers 4 weekly reviews
    window_start = today - timedelta(days=28)

    weekly_reviews = list_vault_notes_in_range(weekly_path, window_start, today)

    md = render_monthly_review(today=today, weekly_reviews=weekly_reviews)

    out_path = monthly_path(today)
    return Proposal(
        skill=SKILL_NAME,
        reasoning=(
            f"monthly review for {today.year}-{today.month:02d} "
            f"({len(weekly_reviews)} weekly reviews aggregated)"
        ),
        changes=[
            {
                "action": "WRITE_FILE",
                "ueid": f"vault:monthly:{today.year}-{today.month:02d}",
                "fields": {
                    "path": str(out_path),
                    "content": md,
                },
                "rationale": "monthly aggregation; user reviews before --approve",
            }
        ],
        approval_state="pending",
    )


def run_skill(today: date | None = None) -> Proposal:
    return propose(today=today)
