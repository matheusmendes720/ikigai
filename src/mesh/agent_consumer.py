"""Deep Agent consumer: validates events against vault context + PAE rules."""
import logging
from dataclasses import dataclass
from datetime import date
from enum import Enum

from src.contracts.task_change import TaskChange

logger = logging.getLogger(__name__)


class Decision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    CLARIFY = "clarify"


@dataclass(frozen=True)
class ValidationResult:
    decision: Decision
    reason: str = ""
    approved_fields: dict | None = None


VAGUE_TITLES = {"todo", "tbd", "fix", "work", "task", "stuff", "thing"}


def validate(event: TaskChange) -> ValidationResult:
    """Validate event. Returns approve/reject/clarify decision."""
    title = event.fields.get("title", "")

    # Check 1: title not vague
    if not title or title.lower().strip() in VAGUE_TITLES or len(title.strip()) < 5:
        return ValidationResult(
            Decision.CLARIFY,
            "Title too vague. Provide a specific, actionable title (>=5 chars, not 'todo'/'tbd').",
        )

    # Check 2: due date not in past (for create actions)
    if event.action.value == "create" and "due" in event.fields:
        try:
            due = date.fromisoformat(event.fields["due"])
            if due < date.today():
                return ValidationResult(
                    Decision.REJECT,
                    f"Due date {due} is in the past. Use a future date or remove due field.",
                )
        except (ValueError, TypeError):
            return ValidationResult(
                Decision.REJECT,
                f"Invalid due date format: {event.fields['due']!r}. Use YYYY-MM-DD.",
            )

    # Check 3: UEID collision (existing propagated event with same UEID)
    try:
        from src.mesh import queue

        for existing in queue.replay_after_restart():
            if existing.ueid == event.ueid and existing.status == "propagated":
                if existing.fields.get("title") != event.fields.get("title"):
                    return ValidationResult(
                        Decision.REJECT,
                        f"UEID collision: {event.ueid} already exists with different content.",
                    )
    except (ImportError, AttributeError) as exc:
        # Per B5.0-F6: was a silent pass before; now log a warning so this
        # silent failure mode doesn't slip past code review unnoticed.
        logger.warning(
            "UEID collision check skipped: queue module unavailable (%s: %s)",
            type(exc).__name__,
            exc,
        )

    return ValidationResult(Decision.APPROVE, approved_fields=event.fields)
