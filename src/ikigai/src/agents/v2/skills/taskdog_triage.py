"""M161 — taskdog-triage skill.

Proactive daily scan that detects:
- Tasks with deadline within 48h and not done
- Tasks where planned_start is in the past and status is still planned
  (overdue)
- Tasks missing or with too-short descriptions

Emits a Proposal (NEVER executes directly). User approves via --approve.

Cron: 0 9 * * *
Slash: /triage
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from agents.v2.proposals import Proposal


# Configurable thresholds
DEADLINE_WINDOW_DAYS = 2
DESCRIPTION_MIN_LEN = 10


def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def detect_changes(
    tasks: list[dict[str, Any]], today: date | None = None
) -> list[dict[str, Any]]:
    """Detect triage-worthy changes in a list of task dicts.

    Each task is expected to have: ueid, status, priority, deadline,
    planned_start, description (all optional except ueid).
    """
    today = today or date.today()
    changes: list[dict[str, Any]] = []

    for t in tasks:
        ueid = t.get("ueid")
        if not ueid:
            continue  # skip malformed tasks

        status = t.get("status", "")
        priority = t.get("priority")
        deadline = _parse_iso_date(t.get("deadline"))
        planned_start = _parse_iso_date(t.get("planned_start"))
        description = (t.get("description") or "").strip()

        # 1. Deadline within window, not done → bump priority
        if deadline is not None:
            days_until = (deadline - today).days
            if 0 <= days_until <= DEADLINE_WINDOW_DAYS and status != "done":
                if priority is None or priority > 1:
                    changes.append(
                        {
                            "action": "UPDATE",
                            "ueid": ueid,
                            "fields": {"priority": 1},
                            "rationale": (
                                f"deadline in {days_until} day(s) "
                                f"({deadline.isoformat()}), status={status}"
                            ),
                        }
                    )

        # 2. Overdue: planned_start in past, still planned → in_progress
        if planned_start is not None and planned_start < today and status == "planned":
            changes.append(
                {
                    "action": "UPDATE",
                    "ueid": ueid,
                    "fields": {"status": "in_progress"},
                    "rationale": (
                        f"planned_start {planned_start.isoformat()} "
                        f"is in the past, status was 'planned'"
                    ),
                }
            )

        # 3. Missing or too-short description
        if len(description) < DESCRIPTION_MIN_LEN:
            changes.append(
                {
                    "action": "UPDATE",
                    "ueid": ueid,
                    "fields": {
                        "description": (
                            f"(auto-flagged {today.isoformat()}: "
                            "needs human description)"
                        )
                    },
                    "rationale": (
                        f"description is {len(description)} chars "
                        f"(min {DESCRIPTION_MIN_LEN})"
                    ),
                }
            )

    return changes


def propose(
    tasks: list[dict[str, Any]],
    today: date | None = None,
    source_fork: str = "taskdog-triage",
) -> Proposal:
    """Build a Proposal from triage analysis.

    The Proposal has approval_state="pending". Caller must ask user
    and only then apply via review_queue.
    """
    today = today or date.today()
    changes = detect_changes(tasks, today=today)
    reasoning = (
        f"taskdog-triage scanned {len(tasks)} task(s) for {today.isoformat()}: "
        f"deadline < {DEADLINE_WINDOW_DAYS}d, overdue planned, missing description. "
        f"Found {len(changes)} candidate change(s)."
    )
    return Proposal(
        skill=source_fork,
        reasoning=reasoning,
        changes=changes,
    )


# Skill registry hook (for /skill taskdog-triage in td chat)
SKILL_NAME = "taskdog-triage"


def run_skill(tasks: list[dict[str, Any]] | None = None) -> Proposal:
    """Entry point invoked by /skill taskdog-triage.

    If `tasks` is None, the skill would normally fetch from the
    TaskdogAdapter. We don't import the adapter here to keep this module
    dependency-free and easy to test.
    """
    if tasks is None:
        tasks = []  # caller should fetch
    return propose(tasks)
