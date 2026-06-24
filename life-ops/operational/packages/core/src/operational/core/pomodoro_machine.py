"""Pomodoro plugin contract + default in-memory implementation.

This module provides the **pluggable interface** for fine-grained task-time
recording. The user's architecture decision (2026-06-07) is:

* **NO pomodoro engine between time blocks** — only gross entry/exit
  registration is captured by the time-blocks layer.
* **Pomodoro is a plug-in contract** that will eventually connect to
  **Timewarrior** for sub-block task-level time tracking
  (presupposing roadmap cards, which are out of scope for now).
* The current package implements the **default in-memory plugin** as a
  reference / test fixture. Real production use will require a
  Timewarrior-backed plugin implementing :class:`PomodoroPlugin`.

The default implementation here preserves the original PAV §9 state
machine (7 states, 11 transitions) as a **self-contained reference**.
It is intentionally *not* wired into the :class:`TimeBlock` capture
pipeline; it is offered as a building block for future integrations.

See Also:
* :class:`operational.entities.time_block.TimeBlock` — the gross
  entry/exit primitive that the time-blocks layer DOES use.
* :mod:`operational.core.break_calculator` — break minutes between
  TimeBlocks.
* :mod:`operational.core.context_switch` — PAV context-switch
  overhead estimation between periods.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final, Protocol, runtime_checkable

from operational.enums import PomodoroState
from operational.types import UEID  # noqa: TC001  (UEID is a string type alias at runtime)

__all__ = [
    "DEFAULT_TRANSITIONS",
    "InMemoryPomodoroPlugin",
    "PomodoroEvent",
    "PomodoroPlugin",
    "PomodoroSession",
    "PomodoroSessionEvent",
    "PomodoroTracker",
    "default_transition_table",
    "get_default_plugin",
]


# Default transition table (PAV §9 stateDiagram-v2)
DEFAULT_TRANSITIONS: Final[dict[PomodoroState, frozenset[PomodoroState]]] = {
    PomodoroState.IDLE: frozenset({PomodoroState.WORK, PomodoroState.COMPLETE}),
    PomodoroState.WORK: frozenset({PomodoroState.BREAK, PomodoroState.LONG_BREAK, PomodoroState.PAUSED}),
    PomodoroState.BREAK: frozenset({PomodoroState.WORK, PomodoroState.SKIPPED}),
    PomodoroState.LONG_BREAK: frozenset({PomodoroState.IDLE}),
    PomodoroState.PAUSED: frozenset({PomodoroState.WORK, PomodoroState.IDLE}),
    PomodoroState.SKIPPED: frozenset({PomodoroState.WORK}),
    PomodoroState.COMPLETE: frozenset(),  # terminal
}


# ---------------------------------------------------------------------------
# Plugin contract
# ---------------------------------------------------------------------------


@runtime_checkable
class PomodoroPlugin(Protocol):
    """Pluggable interface for fine-grained (sub-block) task-time recording.

    This protocol is the **pluggable boundary** between the operational
    package and a future Timewarrior (or other) integration. The
    time-blocks layer does **NOT** depend on a pomodoro plugin; the
    plugin is only consulted for sub-block, task-card-level time
    tracking.

    The default in-memory implementation lives in
    :class:`InMemoryPomodoroPlugin`. A future Timewarrior-backed
    implementation will satisfy the same protocol.
    """

    def start_session(self, session_id: UEID, *, rounds_max: int = 4) -> PomodoroSession:
        """Start a new pomodoro session.

        Args:
            session_id: UEID of the session to start.
            rounds_max: Maximum number of work rounds in this session.

        Returns:
            A new PomodoroSession in IDLE state.
        """
        ...

    def get_session(self, session_id: UEID) -> PomodoroSession | None:
        """Retrieve a session by ID, or None if not found."""
        ...

    def list_sessions(self) -> list[PomodoroSession]:
        """List all known sessions."""
        ...

    def delete_session(self, session_id: UEID) -> bool:
        """Delete a session. Returns True if removed, False if not found."""
        ...

    def record_event(self, session_id: UEID, event: PomodoroSessionEvent) -> None:
        """Record a state transition event for a session.

        Used by the underlying tracking implementation (e.g. Timewarrior
        hook) to push events into the operational package.
        """
        ...


@dataclass(frozen=True, slots=True)
class PomodoroEvent:
    """An event in the default in-memory state machine.

    Attributes:
        timestamp: When the event occurred.
        from_state: Previous state.
        to_state: New state.
        round_number: Current round (1-based).
        reason: Why the transition happened.
    """
    timestamp: datetime
    from_state: PomodoroState
    to_state: PomodoroState
    round_number: int
    reason: str = ""


@dataclass(frozen=True, slots=True)
class PomodoroSessionEvent:
    """A session-level event pushed by a plugin (e.g. Timewarrior).

    Distinct from :class:`PomodoroEvent` (which is internal to the
    default in-memory machine). The plugin contract uses this type to
    feed external state changes into the operational layer.
    """
    session_id: UEID
    timestamp: datetime
    state: PomodoroState
    round_number: int = 0
    note: str = ""


@dataclass
class PomodoroSession:
    """A pomodoro session (plugin-agnostic data record).

    Held by the plugin to track the high-level state of a session.
    The actual state-machine logic lives in the plugin; this
    record is just the data shape.
    """
    session_id: UEID
    rounds_max: int
    state: PomodoroState = PomodoroState.IDLE
    current_round: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    events: list[PomodoroSessionEvent] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default in-memory reference implementation
# ---------------------------------------------------------------------------


class InMemoryPomodoroPlugin:
    """Default in-memory reference implementation of :class:`PomodoroPlugin`.

    Implements the PAV §9 state machine (7 states, 11 transitions).
    Used as a test fixture and as a fallback when no Timewarrior
    plugin is registered.

    NOTE: This implementation is **not** wired into the time-blocks
    capture pipeline. The time-blocks layer captures only gross
    entry/exit times; pomodoros are a separate, opt-in
    sub-block-tracking concern that will be wired in via a future
    Timewarrior plugin.
    """

    def __init__(self) -> None:
        self._sessions: dict[UEID, PomodoroSession] = {}

    def start_session(self, session_id: UEID, *, rounds_max: int = 4) -> PomodoroSession:
        """Start a new session in IDLE state."""
        if rounds_max < 1:
            msg = f"rounds_max must be >= 1, got {rounds_max}"
            raise ValueError(msg)
        if session_id in self._sessions:
            msg = f"Session {session_id} already exists"
            raise ValueError(msg)
        session = PomodoroSession(
            session_id=session_id,
            rounds_max=rounds_max,
            state=PomodoroState.IDLE,
            current_round=0,
            started_at=datetime.now(UTC),
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: UEID) -> PomodoroSession | None:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[PomodoroSession]:
        return list(self._sessions.values())

    def delete_session(self, session_id: UEID) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def record_event(self, session_id: UEID, event: PomodoroSessionEvent) -> None:
        """Record an externally-pushed event (e.g. from Timewarrior hook)."""
        session = self._sessions.get(session_id)
        if session is None:
            msg = f"Session {session_id} not found"
            raise KeyError(msg)
        # Validate transition
        if event.state not in DEFAULT_TRANSITIONS[session.state]:
            msg = f"Invalid transition: {session.state.value} → {event.state.value}"
            raise ValueError(
                msg
            )
        session.state = event.state
        session.current_round = event.round_number
        if event.state == PomodoroState.COMPLETE:
            session.completed_at = event.timestamp
        session.events.append(event)


class PomodoroTracker:
    """Stateful reference state machine for the default plugin.

    Implements the PAV §9 transition table for fine-grained round
    tracking. Mirrors the original in-memory state machine from
    Sprint 3B but is **explicitly a reference implementation** of
    the plugin contract (not an active engine wired into the
    time-blocks pipeline).

    Usage (e.g. for tests or future Timewarrior integration):

    >>> tracker = PomodoroTracker(session_id="pmo_abc", rounds_max=4)
    >>> tracker.start()
    >>> tracker.complete_round()
    """

    def __init__(
        self,
        session_id: UEID,
        rounds_max: int = 4,
        work_minutes: int = 50,
        break_minutes: int = 10,
        long_break_minutes: int = 30,
        transitions: dict[PomodoroState, frozenset[PomodoroState]] | None = None,
    ) -> None:
        if rounds_max < 1:
            msg = f"rounds_max must be >= 1, got {rounds_max}"
            raise ValueError(msg)
        self._session_id = session_id
        self._rounds_max = rounds_max
        self._work_minutes = work_minutes
        self._break_minutes = break_minutes
        self._long_break_minutes = long_break_minutes
        self._transitions = transitions or DEFAULT_TRANSITIONS
        self._current_state = PomodoroState.IDLE
        self._current_round = 0
        self._events: list[PomodoroEvent] = []
        self._started_at: datetime | None = None

    @property
    def session_id(self) -> UEID:
        return self._session_id

    @property
    def current_state(self) -> PomodoroState:
        return self._current_state

    @property
    def current_round(self) -> int:
        return self._current_round

    @property
    def events(self) -> list[PomodoroEvent]:
        return list(self._events)

    @property
    def is_running(self) -> bool:
        return self._current_state not in (PomodoroState.IDLE, PomodoroState.COMPLETE)

    @property
    def is_complete(self) -> bool:
        return self._current_state == PomodoroState.COMPLETE

    def can_transition_to(self, target: PomodoroState) -> bool:
        return target in self._transitions[self._current_state]

    def transition(
        self,
        target: PomodoroState,
        reason: str = "",
        when: datetime | None = None,
    ) -> PomodoroEvent:
        if self._current_state == PomodoroState.COMPLETE:
            msg = "Cannot transition from terminal state COMPLETE"
            raise RuntimeError(msg)
        if not self.can_transition_to(target):
            valid = sorted(s.value for s in self._transitions[self._current_state])
            msg_0 = (
                f"Invalid transition: {self._current_state.value} → {target.value}. "
                f"Valid targets: {valid}"
            )
            raise ValueError(
                msg_0
            )
        event = PomodoroEvent(
            timestamp=when or datetime.now(UTC),
            from_state=self._current_state,
            to_state=target,
            round_number=self._current_round,
            reason=reason,
        )
        self._events.append(event)
        self._current_state = target
        return event

    def start(self, when: datetime | None = None) -> PomodoroEvent:
        if self._current_state != PomodoroState.IDLE:
            msg = f"Cannot start from state {self._current_state.value}"
            raise RuntimeError(msg)
        self._started_at = when or datetime.now(UTC)
        self._current_round = 1
        return self.transition(PomodoroState.WORK, reason="session start", when=when)

    def complete_round(self, when: datetime | None = None) -> PomodoroEvent:
        if self._current_state != PomodoroState.WORK:
            msg = f"complete_round requires WORK state, got {self._current_state.value}"
            raise RuntimeError(msg)
        if self._current_round >= self._rounds_max:
            return self.transition(
                PomodoroState.LONG_BREAK,
                reason=f"round {self._current_round} complete (last)",
                when=when,
            )
        return self.transition(
            PomodoroState.BREAK, reason=f"round {self._current_round} complete", when=when
        )

    def complete_break(self, when: datetime | None = None) -> PomodoroEvent:
        if self._current_state != PomodoroState.BREAK:
            msg = f"complete_break requires BREAK state, got {self._current_state.value}"
            raise RuntimeError(msg)
        self._current_round += 1
        return self.transition(
            PomodoroState.WORK, reason=f"break complete, starting round {self._current_round}", when=when
        )

    def complete_long_break(self, when: datetime | None = None) -> PomodoroEvent:
        if self._current_state != PomodoroState.LONG_BREAK:
            msg = f"complete_long_break requires LONG_BREAK state, got {self._current_state.value}"
            raise RuntimeError(
                msg
            )
        return self.transition(PomodoroState.IDLE, reason="long break complete", when=when)

    def interrupt(self, when: datetime | None = None) -> PomodoroEvent:
        return self.transition(PomodoroState.PAUSED, reason="user interrupt", when=when)

    def resume(self, when: datetime | None = None) -> PomodoroEvent:
        return self.transition(PomodoroState.WORK, reason="user resume", when=when)

    def abort(self, when: datetime | None = None) -> PomodoroEvent:
        return self.transition(PomodoroState.IDLE, reason="user abort", when=when)

    def skip_break(self, when: datetime | None = None) -> PomodoroEvent:
        self.transition(PomodoroState.SKIPPED, reason="user skip", when=when)
        return self.transition(PomodoroState.WORK, reason="continue after skip", when=when)

    def finish(self, when: datetime | None = None) -> PomodoroEvent:
        if self._current_state != PomodoroState.IDLE:
            msg = f"finish requires IDLE state, got {self._current_state.value}"
            raise RuntimeError(msg)
        return self.transition(PomodoroState.COMPLETE, reason="session done", when=when)

    def get_state_duration_minutes(self, state: PomodoroState) -> int:
        if state == PomodoroState.WORK:
            return self._work_minutes
        if state in (PomodoroState.BREAK, PomodoroState.SKIPPED):
            return self._break_minutes
        if state == PomodoroState.LONG_BREAK:
            return self._long_break_minutes
        return 0


# ---------------------------------------------------------------------------
# Module-level plugin registry
# ---------------------------------------------------------------------------


_DEFAULT_PLUGIN: PomodoroPlugin | None = None


def get_default_plugin() -> PomodoroPlugin:
    """Return the default :class:`PomodoroPlugin`.

    On first call, instantiates an :class:`InMemoryPomodoroPlugin`.
    Subsequent calls return the same instance (singleton).

    A future Timewarrior plugin will register itself here via
    :func:`set_default_plugin` at application startup.
    """
    global _DEFAULT_PLUGIN
    if _DEFAULT_PLUGIN is None:
        _DEFAULT_PLUGIN = InMemoryPomodoroPlugin()
    return _DEFAULT_PLUGIN


def set_default_plugin(plugin: PomodoroPlugin) -> None:
    """Register a custom :class:`PomodoroPlugin` (e.g. Timewarrior-backed).

    The time-blocks layer is *not* coupled to this registry; it is
    consulted only by callers that opt into sub-block time tracking
    (i.e. when roadmap cards are present).
    """
    global _DEFAULT_PLUGIN
    _DEFAULT_PLUGIN = plugin


def default_transition_table() -> dict[PomodoroState, frozenset[PomodoroState]]:
    """Return a copy of the default transition table (PAV §9)."""
    return {k: frozenset(v) for k, v in DEFAULT_TRANSITIONS.items()}
