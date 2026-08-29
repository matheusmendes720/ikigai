"""TaskChange and PropagationEvent models for the review queue.

These models represent events in the fork-agent interaction loop.
Every fork emits TaskChange; agent consumes/produces this and emits
PropagationEvent to downstream forks after approval.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from src.contracts.common import UEID


class TaskAction(str, Enum):
    """Action type for task lifecycle."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    DONE = "done"


TaskStatus = Literal["pending", "approved", "rejected", "propagated", "partial_propagation", "clarified"]


class TaskChange(BaseModel):
    """Event model for the review queue.

    Every fork emits this; agent consumes/produces this.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    ueid: UEID
    action: TaskAction
    fields: dict[str, Any]
    source_fork: str
    timestamp: datetime
    status: TaskStatus = "pending"


class PropagationEvent(BaseModel):
    """Subset emitted by agent to downstream forks after approval."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str  # same as TaskChange.event_id (for idempotency)
    ueid: UEID
    action: TaskAction
    fields: dict[str, Any]
    approved_at: datetime
    source_fork: str  # original source
