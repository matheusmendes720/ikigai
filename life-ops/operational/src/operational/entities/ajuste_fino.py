"""AjusteFino entity — fine-grained adjustments between blocks (PAV §2).

PAV §2 explicitly defines:
    ajusteFinos: {periodo: string, minutos: number}[]

These are **structured micro-adjustments** the user logs between
time blocks. They capture small deviations from the canonical
schedule that aren't full desvios:

* "Extended 5min break because I was tired" → +5 min break
* "Reduced S3 from 3 to 2 rounds because of low energy" → -30 min
* "Skipped hydration ritual" → 0 min but negative energia

The ``minutos`` field is **signed**:
* Positive: more time (extended break, longer block)
* Negative: less time (shortened block, skipped ritual)
* Zero: meta-event (e.g., "skipped" without time impact)

AjusteFinos integrate with the break_calculator: the adjusted
net rest between two blocks is
``net_rest + sum(ajustes.minutos for the period)``.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from operational.enums import Period
from operational.types import UEID  # noqa: TC001

__all__ = ["AjusteFino"]


class AjusteFino(BaseModel):
    """A fine-grained adjustment between blocks (PAV §2).

    Attributes:
        id: UEID, e.g., ``aju_manha_extra_break``.
        date: The date of the adjustment.
        period: The period in which the adjustment occurred.
        minutos: Signed adjustment in minutes (positive = added, negative = removed).
        reason: Natural-language explanation of why the adjustment was made.
        block_id_before: Optional reference to the block preceding the adjustment.
        block_id_after: Optional reference to the block following the adjustment.
        created_at: Timestamp of when the adjustment was recorded.
    """
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    date: date
    period: Period
    minutos: Annotated[int, Field(ge=-1440, le=1440)]  # bounded by 24h
    reason: Annotated[str, Field(min_length=1, max_length=500)]
    block_id_before: UEID | None = None
    block_id_after: UEID | None = None
    created_at: datetime

    @field_validator("reason")
    @classmethod
    def _validate_reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            msg = "reason cannot be empty or whitespace"
            raise ValueError(msg)
        return v
