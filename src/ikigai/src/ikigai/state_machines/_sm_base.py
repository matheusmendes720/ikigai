"""State machine primitives — must not import from sibling modules to avoid circular imports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


class TransitionError(Exception):
    """Raised when a guarded transition is blocked."""

    pass


@dataclass
class Transition:
    from_state: str
    to_state: str
    trigger: str
    guard: Callable[[dict[str, Any]], bool] | None = None
    audit_message: str = ""

    def is_allowed(self, context: dict[str, Any]) -> bool:
        if self.guard is None:
            return True
        return self.guard(context)


@dataclass
class TransitionRecord:
    timestamp: datetime
    from_state: str
    to_state: str
    trigger: str
    audit_message: str


class StateMachine:
    """Generic state machine with guards and audit log."""

    def __init__(
        self,
        initial_state: str,
        name: str = "",
        states: list[str] | None = None,
    ) -> None:
        self.name = name
        self.current_state = initial_state
        self.states = list(states) if states is not None else [initial_state]
        # Validate initial_state is in the explicit states list, if provided.
        # When `states` is None we derive it from initial_state (and auto-extend
        # in add_transition below), so there is nothing to validate against.
        if states is not None and initial_state not in self.states:
            raise ValueError(
                f"initial_state {initial_state!r} not in declared states {self.states!r}"
            )
        self._transitions: dict[tuple[str, str], Transition] = {}
        self.audit_log: list[TransitionRecord] = []
        self.context: dict[str, Any] = {}

    def add_transition(
        self,
        from_state: str | Transition = "",
        to_state: str = "",
        trigger: str = "",
        guard: Callable[[dict[str, Any]], bool] | None = None,
        audit_message: str = "",
    ) -> None:
        # Two call forms supported:
        #   add_transition(Transition(...))              — single object (factories)
        #   add_transition("idle", "active", "begin")    — positional (tests)
        if isinstance(from_state, Transition):
            t = from_state
        else:
            t = Transition(
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                guard=guard,
                audit_message=audit_message,
            )
        self._transitions[(t.from_state, t.to_state)] = t
        # Auto-extend states from transitions so callers don't have to
        # pre-declare every reachable state up front.
        if t.from_state not in self.states:
            self.states.append(t.from_state)
        if t.to_state not in self.states:
            self.states.append(t.to_state)

    def transition_to(self, target_state: str, trigger: str = "") -> None:
        if target_state not in self.states:
            raise ValueError(f"Unknown state: {target_state!r}")

        key = (self.current_state, target_state)
        if key not in self._transitions:
            raise TransitionError(f"No transition from {self.current_state!r} → {target_state!r}")

        t = self._transitions[key]
        if not t.is_allowed(self.context):
            raise TransitionError(f"Guard blocked {self.current_state} → {target_state}")

        now = datetime.now(timezone.utc)
        self.audit_log.append(
            TransitionRecord(
                timestamp=now,
                from_state=self.current_state,
                to_state=target_state,
                trigger=trigger or t.trigger,
                audit_message=t.audit_message,
            )
        )
        self.current_state = target_state

    def can_transition_to(self, target_state: str) -> bool:
        """True iff a transition is registered from the current state to target_state."""
        key = (self.current_state, target_state)
        return key in self._transitions
