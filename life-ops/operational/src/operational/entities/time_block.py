"""TimeBlock entity (PRD-01 §2).

A :class:`TimeBlock` is the **calendar-aware time interval** used by the
daily handler and weekly report generators to bucket ad-hoc activities
(focus sessions, errands, meetings) into the canonical PAV periods.

The entity is intentionally minimal — it carries a label, start/end
datetimes, the period it belongs to, and an optional link to a
:class:`Routine`. Two computed properties provide the most common
derived values:

* :attr:`duration_minutes` — whole-minute duration (matches
  :attr:`Routine.duration_minutes`).
* :attr:`overlaps_period` — whether the block lies inside the canonical
  hour range of its assigned period (PAV §3 hour windows).

Source of truth:

* **PRD-01 §2** — entity contract for the time-block table.
* **PAV §3** — canonical hour windows per period (3-5 / 8-17 / 18-21).
"""
from __future__ import annotations

from datetime import datetime  # noqa: TC003  (used as Pydantic field type at runtime)
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from operational.constants import DEFAULT
from operational.enums import Period  # noqa: TC001
from operational.types import UEID  # noqa: TC001  (used as Pydantic field type at runtime)

__all__ = ["TimeBlock"]


# ---------------------------------------------------------------------------
# TimeBlock
# ---------------------------------------------------------------------------


class TimeBlock(BaseModel):
    """A time interval for ad-hoc activity tracking (PRD-01 §2).

    Time blocks are how the daily handler records "this is what I did
    between 14:00 and 14:50 on a Tuesday". They are not the same as
    :class:`Routine` instances: routines are **scheduled** in advance;
    time blocks are **recorded** after the fact. The optional
    :attr:`routine_id` field lets a block be linked to a planned routine
    (e.g. a Pomodoro block tied to a routine's planned window).

    Attributes:
        id: :data:`UEID` (e.g. ``"blk_2026_06_07_1410"``).
        label: Human-readable label, 1-100 characters.
        start: Block start (timezone-aware in production; naive in
            tests). Must be strictly before :attr:`end`.
        end: Block end.
        period: :class:`Period` (MANHA / TARDE / NOITE).
        routine_id: Optional :data:`UEID` referencing the
            :class:`Routine` this block realises. ``None`` for ad-hoc
            blocks.
        notes: Free-form notes, 0-500 characters.
        created_at: Wall-clock timestamp of construction.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    label: Annotated[str, Field(min_length=0, max_length=100)] = ""
    start: datetime
    end: datetime
    period: Period
    routine_id: UEID | None = None
    energia_nivel: Annotated[int | None, Field(ge=1, le=10)] = None
    foco_nivel: Annotated[int | None, Field(ge=1, le=10)] = None
    notes: Annotated[str, Field(default="", max_length=500)]
    created_at: datetime

    @model_validator(mode="after")
    def _validate_times(self) -> TimeBlock:
        """Verify ``end`` is strictly after ``start``.

        Returns:
            The model instance (unchanged on success).

        Raises:
            ValueError: If ``end <= start`` (overnight blocks are allowed
                as long as ``end`` is later in absolute time).
        """
        if self.end <= self.start:
            msg = (
                f"end ({self.end.isoformat()}) must be strictly after "
                f"start ({self.start.isoformat()})"
            )
            raise ValueError(msg)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_minutes(self) -> int:
        """Duration of the block in whole minutes (computed).

        Computed as ``(end - start).total_seconds() // 60``. The result
        is always strictly positive because :meth:`_validate_times`
        guarantees ``end > start``.

        Returns:
            Duration in whole minutes (rounded toward zero).
        """
        return int((self.end - self.start).total_seconds() // 60)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def overlaps_period(self) -> bool:
        """Whether the block lies inside the canonical period hours.

        Uses the period's :attr:`Period.default_start_hour` and
        :attr:`Period.default_end_hour` properties — these come from the
        enum module, which is the **single source of truth** for the
        canonical PAV §3 windows (3-5 / 8-17 / 18-21).

        Returns:
            ``True`` iff ``start.hour`` is in ``[lo, hi)`` AND
            ``end.hour`` is in ``(lo, hi]`` (i.e. the block is fully
            contained in the period's canonical window, with the upper
            boundary treated as half-open to allow a block ending exactly
            at 17:00 to count as a TARDE block).

        Note:
            The :data:`operational.constants.DEFAULT` instance is
            referenced here only for backward compatibility with the
            PAV constants module. The actual hour windows are resolved
            through the :class:`Period` enum, which is the canonical
            source.
        """
        lo: int = self.period.default_start_hour
        hi: int = self.period.default_end_hour
        start_h: int = self.start.hour
        end_h: int = self.end.hour
        return lo <= start_h < hi and lo < end_h <= hi

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_routine_link(self) -> bool:
        """Whether the block is tied to a :class:`Routine`.

        Returns:
            ``True`` when :attr:`routine_id` is not ``None``.
        """
        return self.routine_id is not None


# Silence linters — DEFAULT is part of the public surface and we want any
# import-time breakage of the constants module to be flagged.
_ = DEFAULT
