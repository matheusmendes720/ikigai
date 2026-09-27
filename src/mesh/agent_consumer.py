"""Deep Agent consumer: validates events against vault context + PAE rules.

M148 refactor: original monolithic `validate()` replaced with an action-
dispatching entry point that delegates to a per-action validator. The
CREATE branch preserves the v1 rules (title-not-vague, due-not-in-past,
UEID collision check). UPDATE, DONE, DELETE get their own focused rules.
"""

import logging
from dataclasses import dataclass
from datetime import date
from enum import Enum

from contracts.task_change import TaskAction, TaskChange

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


def _validate_create(event: TaskChange) -> ValidationResult:
    """CREATE: title-not-vague + due-not-in-past."""
    title = event.fields.get("title", "")
    if not title or title.lower().strip() in VAGUE_TITLES or len(title.strip()) < 5:
        return ValidationResult(
            Decision.CLARIFY,
            "Title too vague. Provide a specific, actionable title "
            "(>=5 chars, not 'todo'/'tbd').",
        )

    if "due" in event.fields:
        try:
            due = date.fromisoformat(event.fields["due"])
            if due < date.today():
                return ValidationResult(
                    Decision.REJECT,
                    f"Due date {due} is in the past. "
                    "Use a future date or remove due field.",
                )
        except (ValueError, TypeError):
            return ValidationResult(
                Decision.REJECT,
                f"Invalid due date format: {event.fields['due']!r}. "
                "Use YYYY-MM-DD.",
            )

    return ValidationResult(Decision.APPROVE, approved_fields=event.fields)


def _validate_update(event: TaskChange) -> ValidationResult:
    """UPDATE: UEID immutable + non-empty fields + coarse type checks."""
    if "ueid" in event.fields:
        return ValidationResult(
            Decision.REJECT,
            "UPDATE cannot change ueid (use CREATE + DELETE if you need "
            "to change identity).",
        )
    if not event.fields:
        return ValidationResult(
            Decision.REJECT,
            "UPDATE requires at least one field to change.",
        )
    if "status" in event.fields and not isinstance(event.fields["status"], str):
        return ValidationResult(
            Decision.REJECT,
            f"status must be a string, got {type(event.fields['status']).__name__}",
        )
    return ValidationResult(Decision.APPROVE, approved_fields=event.fields)


def _validate_done(event: TaskChange) -> ValidationResult:
    """DONE: no fields (status set implicitly by adapter).

    Existence check happens later in the adapter via SQL — if the row
    is missing, the propagator will surface a partial_propagation event.
    """
    if event.fields:
        return ValidationResult(
            Decision.REJECT,
            "DONE takes no fields; status is set implicitly. "
            "Use UPDATE if you need to set other fields.",
        )
    return ValidationResult(Decision.APPROVE, approved_fields=event.fields)


def _validate_delete(event: TaskChange) -> ValidationResult:
    """DELETE: no fields (UEID is on the event)."""
    if event.fields:
        return ValidationResult(
            Decision.REJECT,
            "DELETE takes no fields; use UPDATE to set status='cancelled' "
            "for soft-removal.",
        )
    return ValidationResult(Decision.APPROVE, approved_fields=event.fields)


def _check_ueid_collision(event: TaskChange) -> ValidationResult | None:
    """Cross-action UEID collision check (only on CREATE).

    If a propagated event with this UEID exists and its title differs,
    reject the new event. Returns None if no collision or check skipped.
    """
    try:
        from src.mesh import queue

        for existing in queue.replay_after_restart():
            if (
                existing.ueid == event.ueid
                and existing.status == "propagated"
                and existing.fields.get("title") != event.fields.get("title")
            ):
                return ValidationResult(
                    Decision.REJECT,
                    f"UEID collision: {event.ueid} already exists with "
                    "different content.",
                )
    except (ImportError, AttributeError) as exc:
        # Per B5.0-F6: was a silent pass before; now log a warning so this
        # silent failure mode doesn't slip past code review unnoticed.
        logger.warning(
            "UEID collision check skipped: queue module unavailable (%s: %s)",
            type(exc).__name__,
            exc,
        )
    return None


def validate(event: TaskChange) -> ValidationResult:
    """Validate event. Returns approve/reject/clarify decision.

    M148: dispatches on event.action to a per-action validator.
    """
    action = (
        event.action
        if isinstance(event.action, TaskAction)
        else TaskAction(event.action)
    )

    if action == TaskAction.CREATE:
        result = _validate_create(event)
    elif action == TaskAction.UPDATE:
        result = _validate_update(event)
    elif action == TaskAction.DONE:
        result = _validate_done(event)
    elif action == TaskAction.DELETE:
        result = _validate_delete(event)
    else:
        return ValidationResult(
            Decision.REJECT,
            f"Unknown action: {action!r}. Allowed: create, update, done, delete.",
        )

    # UEID collision check is CREATE-only (other actions mutate, not create)
    if result.decision == Decision.APPROVE and action == TaskAction.CREATE:
        collision = _check_ueid_collision(event)
        if collision is not None:
            return collision

    return result
