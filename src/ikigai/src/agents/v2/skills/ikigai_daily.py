"""M162 — ikigai-daily skill.

Replaces the PAV-math-dependent daily reflection with read-only aggregation
of taskdog state + yesterday's vault note. Emits a Proposal with suggestions
in metadata, NO changes (read-only).

Cron: 57 8 * * *
Slash: /ikigai-daily
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from agents.v2.proposals import Proposal
from agents.v2.skills.cadence import (
    daily_path,
    read_vault_note,
    was_done_in_window,
)


SKILL_NAME = "ikigai-daily"


def _generate_suggestions(
    today: date, done_24h: list[dict], pending: list[dict],
    cancelled: list[dict], yesterday_text: str,
) -> list[str]:
    """Build 3-5 pt-BR suggestions based on observable state only."""
    suggestions: list[str] = []
    if done_24h:
        names = ", ".join(t.get("name", "?") for t in done_24h[:3])
        suggestions.append(
            f"Ontem você fechou: {names}. Continue o ritmo."
        )
    if len(pending) > 5:
        suggestions.append(
            f"Você tem {len(pending)} tasks pendentes. "
            "Considere priorizar as 3 mais importantes hoje."
        )
    if len(pending) == 0 and not done_24h:
        suggestions.append(
            "Sem tasks pendentes e nada feito ontem. "
            "Talvez seja hora de planejar a próxima semana."
        )
    if cancelled:
        suggestions.append(
            f"{len(cancelled)} task(s) foram canceladas. "
            "Reveja se algo importante ficou de fora."
        )
    if not yesterday_text and not done_24h:
        suggestions.append(
            "Dia sem registro. Considere escrever em vault/daily/ "
            "antes do fim do dia."
        )
    return suggestions


def propose(today: date | None = None) -> Proposal:
    """Build the daily Proposal. Read-only — no changes."""
    today = today or date.today()
    yesterday = today - timedelta(days=1)

    # Read yesterday's vault note (if exists)
    yesterday_text = read_vault_note(daily_path(yesterday))

    # Aggregate taskdog state (lazy import to avoid circular deps)
    try:
        from src.mesh.adapters.taskdog import TaskdogAdapter

        adapter = TaskdogAdapter()
        tasks = adapter.list_all()
    except Exception:  # noqa: BLE001
        tasks = []

    done_24h = [t for t in tasks if was_done_in_window(t, yesterday, today)]
    pending = [t for t in tasks if t.get("status") == "planned"]
    cancelled = [t for t in tasks if t.get("status") == "cancelled"]

    suggestions = _generate_suggestions(
        today=today,
        done_24h=done_24h,
        pending=pending,
        cancelled=cancelled,
        yesterday_text=yesterday_text,
    )

    # Daily is READ-ONLY: changes=[], suggestions in metadata
    p = Proposal(
        skill=SKILL_NAME,
        reasoning=f"daily reflection for {today.isoformat()}",
        changes=[],
        approval_state="pending",
    )
    # Stash metadata on the proposal
    p.metadata = {  # type: ignore[attr-defined]
        "suggestions": suggestions,
        "stats": {
            "done_24h": len(done_24h),
            "pending": len(pending),
            "cancelled": len(cancelled),
        },
    }
    return p


def run_skill(today: date | None = None) -> Proposal:
    return propose(today=today)
