"""M162 — ikigai-quarterly skill.

Aggregate 3 monthly + 13 weekly reviews into a quarterly review.
Emits Proposal with WRITE_FILE change to vault/quarterly/{yyyy-Qn}.md
PLUS CREATE OKRs as taskdog tasks.

Cron: 0 11 1 1,4,7,10 *
Slash: /ikigai-quarterly
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from agents.v2.proposals import Proposal
from agents.v2.skills.cadence import (
    extract_okrs_from_review,
    list_vault_notes_in_range,
    monthly_path,
    quarterly_path,
    render_quarterly_review,
    weekly_path,
)


SKILL_NAME = "ikigai-quarterly"


def propose(today: date | None = None) -> Proposal:
    today = today or date.today()
    quarter = (today.month - 1) // 3 + 1

    # Last 95 days covers 3 monthly + 13 weekly
    window_start = today - timedelta(days=95)

    monthly_reviews = list_vault_notes_in_range(monthly_path, window_start, today)
    weekly_reviews = list_vault_notes_in_range(weekly_path, window_start, today)

    md = render_quarterly_review(
        today=today,
        monthly_reviews=monthly_reviews,
        weekly_reviews=weekly_reviews,
    )

    # Extract OKRs from rendered review
    okrs = extract_okrs_from_review(md)

    out_path = quarterly_path(today)
    changes: list[dict[str, Any]] = [
        {
            "action": "WRITE_FILE",
            "ueid": f"vault:quarterly:{today.year}-Q{quarter}",
            "fields": {
                "path": str(out_path),
                "content": md,
            },
            "rationale": "quarterly aggregation; user reviews before --approve",
        }
    ]
    # Append OKR CREATE tasks
    for i, okr in enumerate(okrs):
        changes.append(
            {
                "action": "CREATE",
                "ueid": f"tsk:okr:{today.isoformat()}:{i:04d}",
                "fields": {
                    "title": okr["title"],
                    "priority": okr.get("priority", 2),
                },
                "rationale": f"OKR extracted from quarterly review",
            }
        )

    return Proposal(
        skill=SKILL_NAME,
        reasoning=(
            f"quarterly review for {today.year}-Q{quarter} "
            f"({len(monthly_reviews)} monthly + {len(weekly_reviews)} weekly, "
            f"{len(okrs)} OKRs proposed)"
        ),
        changes=changes,
        approval_state="pending",
    )


def run_skill(today: date | None = None) -> Proposal:
    return propose(today=today)
