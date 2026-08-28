"""Deep Agent propagator: emits approved events to all relevant forks + vault."""
from dataclasses import dataclass

from src.contracts.task_change import TaskChange, PropagationEvent
from src.mesh.agent_consumer import ValidationResult
from src.mesh.adapters.base import ForkAdapter


@dataclass(frozen=True)
class PropagationResult:
    fork_name: str
    success: bool
    error: str = ""


def propagate(
    event: TaskChange,
    validation: ValidationResult,
    adapters: list[ForkAdapter],
) -> list[PropagationResult]:
    """Propagate approved event to all adapters. Per-adapter failures are isolated."""
    if validation.decision.value != "approve":
        return []

    propagation = PropagationEvent(
        event_id=event.event_id,
        ueid=event.ueid,
        action=event.action,
        fields=validation.approved_fields or event.fields,
        approved_at=event.timestamp,
        source_fork=event.source_fork,
    )

    results = []
    for adapter in adapters:
        try:
            adapter.apply_change(propagation)
            results.append(PropagationResult(fork_name=adapter.name, success=True))
        except Exception as e:
            results.append(
                PropagationResult(
                    fork_name=adapter.name,
                    success=False,
                    error=str(e),
                )
            )
    return results
