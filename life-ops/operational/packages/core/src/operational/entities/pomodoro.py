"""Pomodoro entities (PAV §9, PRD-01).

The Pomodoro state machine is one of the load-bearing parts of the PAV
operational system: it tracks focused work in **rounds** of
``POMODORO_WORK_MIN`` minutes interleaved with short and long breaks.
This module declares three entities that compose the full machine:

* :class:`PomodoroConfig` — the **configuration** of a Pomodoro session
  (work / break / long-break / round counts). A typical day has one
  config; a single session binds to one config by ``config_id``.
* :class:`PomodoroRound` — a **single round** within a session, with
  its own start / completion timestamps and pause tracking.
* :class:`PomodoroSession` — the **full session** (sequence of rounds)
  with the lifecycle state, total focus / break minute aggregates and
  completion ratio.

State machine references:

* The seven :class:`PomodoroState` enum values (IDLE, WORK, BREAK,
  LONG_BREAK, PAUSED, SKIPPED, COMPLETE) and the
  :meth:`PomodoroState.can_transition_to` graph are defined in
  :mod:`operational.enums`.
* The state of a :class:`PomodoroSession` and of each
  :class:`PomodoroRound` are typed :class:`PomodoroState` values, but
  the **orchestrator** (not this module) is responsible for advancing
  the machine. The entities are pure data containers.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from operational.constants import DEFAULT
from operational.enums import PomodoroState
from operational.types import UEID  # noqa: TC001  (used as Pydantic field type at runtime)

__all__ = ["PomodoroConfig", "PomodoroRound", "PomodoroSession"]


# ---------------------------------------------------------------------------
# PomodoroConfig
# ---------------------------------------------------------------------------


class PomodoroConfig(BaseModel):
    """Configuration for a Pomodoro session (PAV §9, PRD-01).

    A config is a **named recipe** for a Pomodoro session: how long each
    work block runs, how long the breaks are, and how many rounds are
    expected. The canonical values come from
    :data:`operational.constants.DEFAULT` — use
    :meth:`from_pav_defaults` to build a production-ready config without
    having to repeat the magic numbers.

    Attributes:
        id: :data:`UEID` (e.g. ``"pmo_focus_deep"``).
        name: Human-readable name, 1-100 characters.
        work_minutes: Length of a single work block in minutes.
            Clamped to ``[10, 120]`` (PAV §1 default ``50``).
        break_minutes: Length of a short break in minutes. Clamped to
            ``[1, 30]`` and **must be strictly less** than
            :attr:`work_minutes` (validated).
        long_break_minutes: Length of a long break in minutes (taken
            every ``rounds_max`` rounds). Clamped to ``[10, 60]``.
        rounds_min: Minimum expected number of rounds. Clamped to
            ``[1, 10]``.
        rounds_max: Maximum expected number of rounds. Clamped to
            ``[1, 10]`` and **must be greater than or equal to**
            :attr:`rounds_min` (validated).
        routine_id: Optional :data:`UEID` of a :class:`Routine` that
            this config is bound to. ``None`` for free-standing configs.
        created_at: Wall-clock timestamp of construction.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    name: Annotated[str, Field(min_length=1, max_length=100)]
    work_minutes: Annotated[int, Field(ge=10, le=120)]
    break_minutes: Annotated[int, Field(ge=1, le=30)]
    long_break_minutes: Annotated[int, Field(ge=10, le=60)]
    rounds_min: Annotated[int, Field(ge=1, le=10)]
    rounds_max: Annotated[int, Field(ge=1, le=10)]
    routine_id: UEID | None = None
    created_at: datetime

    @model_validator(mode="after")
    def _validate_invariants(self) -> PomodoroConfig:
        """Cross-field invariants enforced at construction time.

        Returns:
            The model instance (unchanged on success).

        Raises:
            ValueError: If ``rounds_max < rounds_min`` or
                ``break_minutes >= work_minutes``.
        """
        if self.rounds_max < self.rounds_min:
            msg = (
                f"rounds_max ({self.rounds_max}) must be >= "
                f"rounds_min ({self.rounds_min})"
            )
            raise ValueError(msg)
        if self.break_minutes >= self.work_minutes:
            msg = (
                f"break_minutes ({self.break_minutes}) must be strictly "
                f"< work_minutes ({self.work_minutes})"
            )
            raise ValueError(msg)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def session_duration_minutes(self) -> int:
        """Total expected session duration in minutes (computed).

        The estimate assumes the session runs for :attr:`rounds_max`
        rounds with a long break at the end. Round work and short
        breaks alternate; the long break replaces the last short break.

        Returns:
            ``rounds_max * work_minutes + (rounds_max - 1) * break_minutes
            + long_break_minutes``.
        """
        work_total: int = self.rounds_max * self.work_minutes
        short_breaks: int = max(0, self.rounds_max - 1) * self.break_minutes
        return work_total + short_breaks + self.long_break_minutes

    @classmethod
    def from_pav_defaults(
        cls,
        name: str,
        **overrides: Any,  # noqa: ANN401
    ) -> PomodoroConfig:
        """Build a :class:`PomodoroConfig` from PAV canonical defaults.

        Reads the constants from :data:`operational.constants.DEFAULT`
        (single source of truth) and produces a validated instance. Any
        field can be overridden through keyword arguments.

        Args:
            name: Human-readable name (1-100 characters).
            **overrides: Field overrides. Allowed keys: ``id``,
                ``work_minutes``, ``break_minutes``, ``long_break_minutes``,
                ``rounds_min``, ``rounds_max``, ``routine_id``,
                ``created_at``. Unknown keys raise :class:`ValueError`
                (Pydantic ``extra="forbid"``).

        Returns:
            A fully-validated :class:`PomodoroConfig`.

        Example:
            >>> cfg = PomodoroConfig.from_pav_defaults("Deep Focus")
            >>> cfg.work_minutes
            50
        """
        base: dict[str, object] = {
            "id": f"pmo_{uuid4().hex[:12]}",
            "name": name,
            "work_minutes": DEFAULT.POMODORO_WORK_MIN,
            "break_minutes": DEFAULT.POMODORO_BREAK_MIN,
            "long_break_minutes": DEFAULT.POMODORO_LONG_BREAK_MIN,
            "rounds_min": DEFAULT.POMODORO_ROUNDS_MIN,
            "rounds_max": DEFAULT.POMODORO_ROUNDS_MAX,
            "created_at": datetime.now(tz=UTC),
        }
        base.update(overrides)
        return cls(**base)


# ---------------------------------------------------------------------------
# PomodoroRound
# ---------------------------------------------------------------------------


class PomodoroRound(BaseModel):
    """A single Pomodoro round (PAV §9 state machine).

    A round is one cycle of the state machine: a work block followed by
    a (short or long) break, or a single work block if the round was
    skipped or paused. The round carries its own start / completion
    timestamps and pause accounting; the
    :attr:`actual_duration_minutes` computed property subtracts paused
    time.

    Attributes:
        id: :data:`UEID` (e.g. ``"pmor_session_001_round_1"``).
        round_number: 1-based round index. Clamped to ``[1, 20]``.
        state: :class:`PomodoroState` of this round.
        started_at: Wall-clock time when the round started. ``None``
            for never-started rounds.
        completed_at: Wall-clock time when the round ended. ``None``
            for in-progress or never-started rounds.
        paused_duration_seconds: Total seconds the round spent in
            :attr:`PomodoroState.PAUSED`. Clamped to ``>= 0``.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    id: UEID
    round_number: Annotated[int, Field(ge=1, le=20)]
    state: PomodoroState
    started_at: datetime | None = None
    completed_at: datetime | None = None
    paused_duration_seconds: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def _validate_timestamps(self) -> PomodoroRound:
        """Ensure ``completed_at`` is not before ``started_at``.

        Returns:
            The model instance (unchanged on success).

        Raises:
            ValueError: If both timestamps are set and
                ``completed_at < started_at``.
        """
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            msg = (
                f"completed_at ({self.completed_at.isoformat()}) must be "
                f">= started_at ({self.started_at.isoformat()})"
            )
            raise ValueError(msg)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def actual_duration_minutes(self) -> float:
        """Effective round duration in minutes (computed).

        Equals ``(completed_at - started_at) - paused_duration_seconds``
        when both timestamps are present, else ``0.0``. The result is a
        ``float`` because pauses are tracked in seconds.

        Returns:
            Effective duration in minutes (may be fractional).
        """
        if self.started_at is None or self.completed_at is None:
            return 0.0
        elapsed_seconds: float = (
            self.completed_at - self.started_at
        ).total_seconds() - float(self.paused_duration_seconds)
        return elapsed_seconds / 60.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_focus_round(self) -> bool:
        """Whether this round counts as focus work.

        Returns:
            ``True`` when :attr:`state` is :attr:`PomodoroState.WORK`
            or :attr:`PomodoroState.COMPLETE`. Break / pause / skip
            rounds are not focus rounds.
        """
        return self.state in {PomodoroState.WORK, PomodoroState.COMPLETE}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_break_round(self) -> bool:
        """Whether this round is a break (short or long).

        Returns:
            ``True`` when :attr:`state` is :attr:`PomodoroState.BREAK`
            or :attr:`PomodoroState.LONG_BREAK`.
        """
        return self.state in {PomodoroState.BREAK, PomodoroState.LONG_BREAK}


# ---------------------------------------------------------------------------
# PomodoroSession
# ---------------------------------------------------------------------------


class PomodoroSession(BaseModel):
    """A full Pomodoro session (PAV §9, PRD-01).

    A session aggregates the rounds run under a single
    :class:`PomodoroConfig` (referenced by :attr:`config_id`). The
    session's own :attr:`state` reflects the **current** machine state;
    the list of :attr:`rounds` retains the historical record.

    Computed properties aggregate the round-level data into session-level
    metrics (total focus minutes, total break minutes, completion ratio).

    Attributes:
        id: :data:`UEID` (e.g. ``"pms_2026_06_07_morning"``).
        config_id: :data:`UEID` of the bound :class:`PomodoroConfig`.
        state: :class:`PomodoroState` of the session as a whole.
        rounds: Ordered list of :class:`PomodoroRound` records.
        started_at: Wall-clock time when the session started.
        completed_at: Wall-clock time when the session reached a
            terminal state. ``None`` while the session is in progress.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    id: UEID
    config_id: UEID
    state: PomodoroState
    rounds: list[PomodoroRound] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_terminal_state(self) -> PomodoroSession:
        """Ensure ``completed_at`` is set only for terminal states.

        Returns:
            The model instance (unchanged on success).

        Raises:
            ValueError: If ``completed_at`` is set but the state is not
                terminal (IDLE, SKIPPED, COMPLETE).
        """
        if self.completed_at is not None and not self.state.is_terminal:
            msg = (
                f"completed_at is set but state is {self.state.value!r}, "
                f"which is not terminal"
            )
            raise ValueError(msg)
        if (
            self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            msg = (
                f"completed_at ({self.completed_at.isoformat()}) must be "
                f">= started_at ({self.started_at.isoformat()})"
            )
            raise ValueError(msg)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_focus_minutes(self) -> int:
        """Sum of focus minutes across all rounds (computed).

        Focus minutes are taken from rounds whose state is
        :attr:`PomodoroState.WORK` or :attr:`PomodoroState.COMPLETE`.
        The aggregated value is truncated to whole minutes.

        Returns:
            Whole focus minutes (always ``>= 0``).
        """
        total: float = sum(
            r.actual_duration_minutes
            for r in self.rounds
            if r.state in {PomodoroState.WORK, PomodoroState.COMPLETE}
        )
        return int(total)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_break_minutes(self) -> int:
        """Sum of break minutes across all rounds (computed).

        Break minutes are taken from rounds whose state is
        :attr:`PomodoroState.BREAK` or :attr:`PomodoroState.LONG_BREAK`.
        The aggregated value is truncated to whole minutes.

        Returns:
            Whole break minutes (always ``>= 0``).
        """
        total: float = sum(
            r.actual_duration_minutes
            for r in self.rounds
            if r.state in {PomodoroState.BREAK, PomodoroState.LONG_BREAK}
        )
        return int(total)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_minutes(self) -> int:
        """Total elapsed minutes in the session (focus + break).

        Returns:
            Sum of :attr:`total_focus_minutes` and
            :attr:`total_break_minutes`.
        """
        return self.total_focus_minutes + self.total_break_minutes

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completion_ratio(self) -> float:
        """Ratio of completed rounds to total rounds in the session.

        A round counts as "completed" when its state is
        :attr:`PomodoroState.COMPLETE`. The denominator is
        ``len(self.rounds)`` (not the configured ``rounds_max``) so that
        partial sessions are not penalised: a session that was abandoned
        after 2 rounds shows ``2/2 = 1.0`` (or ``1/2 = 0.5`` if only
        one of them completed).

        Returns:
            Float in ``[0.0, 1.0]``. Returns ``0.0`` for an empty
            session.
        """
        if not self.rounds:
            return 0.0
        completed: int = sum(
            1 for r in self.rounds if r.state == PomodoroState.COMPLETE
        )
        return completed / len(self.rounds)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def focus_ratio(self) -> float:
        """Ratio of focus minutes to total session minutes (computed).

        Returns ``0.0`` if the session has no recorded minutes. Used by
        the daily handler to detect "all breaks, no work" sessions.

        Returns:
            Float in ``[0.0, 1.0]``.
        """
        total: int = self.total_minutes
        if total == 0:
            return 0.0
        return self.total_focus_minutes / total


# Silence linters — DEFAULT is part of the public surface and we want any
# import-time breakage of the constants module to be flagged.
_ = DEFAULT
