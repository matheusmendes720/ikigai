"""Entity modules for the operational domain.

This package groups the **immutable Pydantic v2 models** that represent
the day-to-day building blocks of the PAV operational system. They are
intentionally **leaves** of the package: imports are limited to
:mod:`operational.enums`, :mod:`operational.types` and
:mod:`operational.constants` — no entity imports another entity, no
I/O is performed.

Sprint 2A delivers three entity modules:

* :mod:`operational.entities.routine` — :class:`Routine`, :class:`Ritual`,
  :class:`Transition` (PAV §3, §5).
* :mod:`operational.entities.time_block` — :class:`TimeBlock` (PRD-01 §2).
* :mod:`operational.entities.pomodoro` — :class:`PomodoroConfig`,
  :class:`PomodoroRound`, :class:`PomodoroSession` (PAV §9).
"""
from __future__ import annotations

from operational.entities.pomodoro import (
    PomodoroConfig,
    PomodoroRound,
    PomodoroSession,
)
from operational.entities.routine import (
    VALID_WEEKDAYS,
    Ritual,
    Routine,
    Transition,
    Weekday,
)
from operational.entities.time_block import TimeBlock

__all__ = [
    "VALID_WEEKDAYS",
    "PomodoroConfig",
    "PomodoroRound",
    "PomodoroSession",
    "Ritual",
    "Routine",
    "TimeBlock",
    "Transition",
    "Weekday",
]
