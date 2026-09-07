"""Investigation queue contracts — Plan C.

Pre-form tasks that don't fit the 6-level SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA
hierarchy live here as Investigations. They have an inq_id (NOT a UEID — separate
namespace) and a status lifecycle: open → in_progress → resolved | archived.

See docs/superpowers/plans/2026-09-03-investigation-queue-plan-c.md for design.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

InvestigationStatus = Literal["open", "in_progress", "resolved", "archived"]


class Investigation(BaseModel):
    """A pre-form observation parked outside the planning hierarchy.

    Investigations are raw observations, ambiguous research leads, or shadow loops
    that the Deep Agent v2 cannot yet crystallize into the 6-level hierarchy.
    A worker dispatcher (Task 5) reads pending items and may emit them into the
    planning tree once they crystallize.

    Append-only: investigations are never deleted, only transitioned to
    'resolved' or 'archived' (terminal states).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    inq_id: str = Field(
        ...,
        description="Investigation ID. Format: inq-YYYYMMDD-NNN. NOT a UEID.",
        min_length=1,
    )
    source: Literal["agent", "user", "external"] = Field(
        ...,
        description="Who/what created this investigation.",
    )
    payload: str = Field(
        ...,
        description="Free-form description of what needs investigation.",
        min_length=1,
    )
    status: InvestigationStatus = Field(
        default="open",
        description="Lifecycle status. Append-only transitions: open → in_progress → resolved | archived.",
    )
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(),
        description="Last update timestamp. Defaults to creation time.",
    )
    inq_ueid: str | None = Field(
        default=None,
        description="Optional UEID once investigation crystallizes into a hierarchy entry.",
    )
    actor: str = Field(
        default="agent",
        description="Actor who created or last transitioned the investigation.",
    )
    tags: tuple[str, ...] = Field(
        default=(),
        description="Free-form tags for filtering.",
    )
