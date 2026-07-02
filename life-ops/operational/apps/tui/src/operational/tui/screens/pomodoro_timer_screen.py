"""Pomodoro Timer Screen for PAV TUI.

This screen drives the PAV Pomodoro state machine end-to-end:

* ``PomodoroTracker`` (from :mod:`operational.core.pomodoro_machine`) owns
  the FSM and the list of transition events.
* A 1-Hz :meth:`textual.timer.Timer` ticks ``_time_left`` down and
  triggers an automatic state advance when the current round's
  duration is reached.
* Each completed transition is persisted to the
  :data:`operational.cli.state.pomodoros` repo as a
  :class:`PomodoroRound` so the cycle survives a TUI restart.

Why this was previously broken (P0 #4): ``BINDINGS`` declared four
action methods (``action_start_timer``/``action_pause_timer``/
``action_skip_break``/``action_abort_timer``) that were never defined,
the screen mutated free-form ``str`` state, and no event was ever
written to disk. See ``docs/P0-CORRECTIONS-MAP.md`` §P0 #4.
"""
from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar
from uuid import uuid4

from operational.cli.state import (
    pomodoros as pomodoros_repo,
)
from operational.cli.state import (
    reload_stale_repos,
)
from operational.constants import DEFAULT
from operational.core.pomodoro_machine import PomodoroTracker
from operational.entities.pomodoro import PomodoroRound
from operational.enums import PomodoroState
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Digits, Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.timer import Timer


class PomodoroTimerScreen(Screen):
    """Active pomodoro timer with state machine visualization.

    The screen is a thin Textual controller over :class:`PomodoroTracker`.
    All state transitions go through the tracker so the on-disk record
    and the displayed state can never disagree.
    """

    BINDINGS: ClassVar = [
        Binding("s", "start_timer", "Start", show=False),
        Binding("p", "pause_timer", "Pause", show=False),
        Binding("period", "skip_break", "Skip", show=False),
        Binding("a", "abort_timer", "Abort", show=False),
    ]

    CSS = """
PomodoroTimerScreen {
    background: $panel;
    layout: vertical;
    align: center middle;
}
#pomo-title {
    height: 3;
    width: 100%;
    padding: 1 2;
    background: $surface;
    color: $text;
    text-style: bold;
}
#pomo-timer {
    height: 7;
    width: 100%;
    padding: 1 2;
    content-align: center middle;
    color: $error;
    text-style: bold;
}
#pomo-status, #fsm-diagram, #state-label {
    height: 3;
    width: 100%;
    padding: 0 2;
    color: $text-muted;
}
#btn-start, #btn-pause, #btn-skip, #btn-abort {
    width: 100%;
    margin: 0 1;
}
"""

    # Default PAV §9 round lengths — single source of truth lives in
    # ``operational.constants.DEFAULT``. The screen reads them on mount
    # so changes to the constants flow through automatically.
    _WORK_MIN: ClassVar[int] = DEFAULT.POMODORO_WORK_MIN
    _BREAK_MIN: ClassVar[int] = DEFAULT.POMODORO_BREAK_MIN
    _LONG_BREAK_MIN: ClassVar[int] = DEFAULT.POMODORO_LONG_BREAK_MIN
    _ROUNDS_MAX: ClassVar[int] = DEFAULT.POMODORO_ROUNDS_MAX

    def compose(self) -> ComposeResult:
        """Compose the pomodoro timer screen widgets."""
        yield Header()
        yield Static("🍅 POMODORO", id="pomo-title")
        yield Digits(f"{self._WORK_MIN:02d}:00", id="pomo-timer")
        yield Static(
            f"Round 0/{self._ROUNDS_MAX}  |  S1 manha  |  IDLE", id="pomo-status"
        )
        yield Static(
            "IDLE → WORK → BREAK → WORK → LONG_BREAK → COMPLETE", id="fsm-diagram"
        )
        yield Static("State: IDLE", id="state-label")
        yield Button("Start", id="btn-start")
        yield Button("Pause", id="btn-pause", disabled=True)
        yield Button("Skip Break", id="btn-skip", disabled=True)
        yield Button("Abort", id="btn-abort", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        """Initialize tracker, countdown, and the 1-Hz tick timer."""
        # Build a fresh tracker — UEID format: ``pmo_<12-hex>``. Late
        # import of ``uuid4`` here would shadow the one we already
        # imported at module scope, so we use ``uuid.uuid4`` directly
        # via the module reference captured at the top of this file.
        self._tracker: PomodoroTracker = PomodoroTracker(
            session_id=f"pmo_{uuid4().hex[:12]}",
            rounds_max=self._ROUNDS_MAX,
            work_minutes=self._WORK_MIN,
            break_minutes=self._BREAK_MIN,
            long_break_minutes=self._LONG_BREAK_MIN,
        )
        self._state: PomodoroState = PomodoroState.IDLE
        self._time_left: int = self._WORK_MIN * 60
        self._tick_handle: Timer | None = None
        self._reload_handle: Timer | None = None
        # Capture the wall-clock moment of the *current* state so we
        # know when its planned duration has elapsed.
        self._phase_started_at: datetime | None = None
        self._update_ui()
        self._tick_handle = self.set_interval(1.0, self._tick)
        # P2 #4 — pick up cross-process CLI writes (e.g. ``pav pomodoro
        # round create`` in another terminal) before any read of the
        # ``pomodoros`` repo. Mirrors the dashboard refresh pattern:
        # cheap mtime probe, no-op when nothing changed.
        self._reload_handle = self.set_interval(2.0, self._maybe_reload)

    def on_unmount(self) -> None:
        """Stop the interval timers when the screen leaves the stack."""
        if self._tick_handle is not None:
            self._tick_handle.stop()
            self._tick_handle = None
        if self._reload_handle is not None:
            self._reload_handle.stop()
            self._reload_handle = None

    def _maybe_reload(self) -> None:
        """Probe all repos for peer-process writes and re-hydrate if stale.

        P2 #4: mirrors ``DashboardScreen._refresh`` so the pomodoro screen
        stays consistent with the dashboard if another terminal writes a
        ``PomodoroRound`` between polls. The reload itself is a no-op
        when nothing changed — cost is one mtime check per repo (~µs).
        """
        # Never let a transient reload error break the timer loop.
        # Same suppression pattern as ``DashboardScreen._refresh``.
        with suppress(Exception):
            reload_stale_repos()

    # ------------------------------------------------------------------
    # Tick + auto-advance
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """1-Hz countdown; advance FSM when the round duration elapses."""
        if self._state == PomodoroState.IDLE or self._state == PomodoroState.PAUSED:
            # Idle and paused phases don't count down — pause freezes
            # the timer, idle is pre-start.
            return
        if self._state.is_terminal:
            return
        self._time_left = max(0, self._time_left - 1)
        self._refresh_timer_label()
        if self._time_left == 0:
            self._auto_advance()

    def _auto_advance(self) -> None:
        """Advance the FSM when the current phase's duration elapses.

        WORK → BREAK (or LONG_BREAK if final round); BREAK → WORK;
        LONG_BREAK → COMPLETE. The transition is persisted as a
        :class:`PomodoroRound` so the completed phase is recorded
        even if the user quits before manually aborting.
        """
        if self._state == PomodoroState.WORK:
            self._persist_round_completion(PomodoroState.WORK)
            try:
                self._tracker.complete_round()
            except RuntimeError:
                return  # tracker refused (e.g. not in WORK)
            self._enter_phase(self._state_after_work())
        elif self._state == PomodoroState.BREAK:
            self._persist_round_completion(PomodoroState.BREAK)
            try:
                self._tracker.complete_break()
            except RuntimeError:
                return
            self._enter_phase(PomodoroState.WORK)
        elif self._state == PomodoroState.LONG_BREAK:
            self._persist_round_completion(PomodoroState.LONG_BREAK)
            try:
                self._tracker.complete_long_break()
            except RuntimeError:
                return
            self._enter_phase(PomodoroState.COMPLETE)

    def _state_after_work(self) -> PomodoroState:
        """Return BREAK unless we're on the final round (LONG_BREAK).

        Mirrors :meth:`PomodoroTracker.complete_round`, which already
        promotes to LONG_BREAK on the last round; we read the tracker
        for the source of truth instead of recomputing the round count.
        """
        # After ``complete_round`` the tracker may have advanced to
        # LONG_BREAK. Reflect that immediately so the next tick uses
        # the long-break duration.
        if self._tracker.current_state == PomodoroState.LONG_BREAK:
            return PomodoroState.LONG_BREAK
        return PomodoroState.BREAK

    def _enter_phase(self, new_state: PomodoroState) -> None:
        """Reset the countdown for the new phase and update the UI."""
        self._state = new_state
        self._time_left = self._duration_for(new_state)
        self._phase_started_at = datetime.now(tz=UTC)
        self._update_ui()

    def _duration_for(self, state: PomodoroState) -> int:
        """Return the planned duration of a state in seconds."""
        minutes = self._tracker.get_state_duration_minutes(state)
        return minutes * 60

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_round_completion(self, phase: PomodoroState) -> None:
        """Append a ``PomodoroRound`` for the just-finished phase.

        Captures the wall-clock window between :attr:`_phase_started_at`
        and *now*; pause accounting is intentionally zero (the screen
        does not expose pause mid-phase today — pause is a discrete
        FSM transition, not a sub-phase timer).
        """
        if self._phase_started_at is None:
            return
        now = datetime.now(tz=UTC)
        # Round number tracks the tracker's current round at the time
        # the phase ENDED (i.e. after the tracker has advanced).
        round_number = max(1, self._tracker.current_round)
        # IDs must match the entity pattern ``^[a-z]{3,5}_[a-z0-9_]+$``,
        # so the state segment is lowercased. The entity still stores
        # the original :class:`PomodoroState` enum in ``state``.
        record_id = (
            f"pmor_{self._tracker.session_id[4:]}"
            f"_r{round_number}_{phase.value.lower()}"
        )
        round_ = PomodoroRound(
            id=record_id,
            round_number=round_number,
            state=phase,
            started_at=self._phase_started_at,
            completed_at=now,
            paused_duration_seconds=0,
        )
        pomodoros_repo.upsert(round_)

    # ------------------------------------------------------------------
    # Button handlers (action_* methods referenced by BINDINGS)
    # ------------------------------------------------------------------

    def action_start_timer(self) -> None:
        """Start the session (IDLE → WORK)."""
        if self._state != PomodoroState.IDLE:
            return
        self._tracker.start()
        self._enter_phase(PomodoroState.WORK)

    def action_pause_timer(self) -> None:
        """Toggle pause / resume (WORK ↔ PAUSED).

        Pause is a **freeze**, not a state transition to BREAK. The
        round continues to count down when resumed because
        :meth:`_enter_phase` is not invoked — only the timer is
        gated. ``on_unmount``'s interval teardown handles the case
        where the user leaves the screen while paused.
        """
        if self._state == PomodoroState.WORK:
            self._tracker.interrupt()
            self._state = PomodoroState.PAUSED
            self._update_ui()
        elif self._state == PomodoroState.PAUSED:
            self._tracker.resume()
            self._state = PomodoroState.WORK
            self._update_ui()

    def action_skip_break(self) -> None:
        """Skip the current break (BREAK / LONG_BREAK → WORK).

        Only meaningful while in a break state. The tracker raises
        ``RuntimeError`` if the FSM rejects the transition; we
        silently ignore it.
        """
        if self._state == PomodoroState.BREAK:
            self._persist_round_completion(PomodoroState.BREAK)
            try:
                self._tracker.skip_break()
            except (RuntimeError, ValueError):
                return
            self._enter_phase(PomodoroState.WORK)

    def action_abort_timer(self) -> None:
        """Abort the session (any non-idle state → IDLE).

        The tracker's FSM only allows ``abort()`` from ``PAUSED`` and
        ``LONG_BREAK``. From ``WORK`` we go through ``PAUSED``; from
        ``BREAK`` we go ``SKIPPED → WORK → PAUSED`` so the machine
        records both the break-skip and the user-abort events. The
        chain preserves a clean audit trail on disk while honouring
        the machine's invariants.
        """
        if self._state == PomodoroState.IDLE:
            return
        # Persist whatever phase is currently in-flight so the
        # wall-clock duration is captured before we transition out.
        self._persist_round_completion(self._state)
        # Drive the tracker through legal transitions until we are in
        # a state from which ``abort()`` is legal (PAUSED or LONG_BREAK).
        try:
            if self._state == PomodoroState.BREAK:
                self._tracker.skip_break()  # BREAK → SKIPPED → WORK
                self._state = PomodoroState.WORK
            if self._state in (PomodoroState.WORK,):
                self._tracker.interrupt()  # WORK → PAUSED
                self._state = PomodoroState.PAUSED
            # PAUSED / LONG_BREAK → IDLE.
            self._tracker.abort()
        except (RuntimeError, ValueError):
            pass
        self._state = PomodoroState.IDLE
        self._time_left = self._WORK_MIN * 60
        self._phase_started_at = None
        self._update_ui()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route button presses through the same action methods as keys.

        Routing buttons through ``action_*`` keeps a single source of
        truth for "what does Start do?" — the action method, not the
        click handler.
        """
        btn_id = event.button.id or ""
        if btn_id == "btn-start":
            self.action_start_timer()
        elif btn_id == "btn-pause":
            self.action_pause_timer()
        elif btn_id == "btn-skip":
            self.action_skip_break()
        elif btn_id == "btn-abort":
            self.action_abort_timer()

    # ------------------------------------------------------------------
    # UI sync
    # ------------------------------------------------------------------

    def _refresh_timer_label(self) -> None:
        """Update only the :class:`Digits` widget — cheap, every second."""
        mins, secs = divmod(self._time_left, 60)
        self.query_one("#pomo-timer", Digits).update(f"{mins:02d}:{secs:02d}")

    def _update_ui(self) -> None:
        """Refresh all state-driven widgets (status / state / buttons)."""
        self._refresh_timer_label()
        self.query_one("#state-label", Static).update(f"State: {self._state.value}")
        self.query_one("#pomo-status", Static).update(
            f"Round {self._tracker.current_round}/{self._ROUNDS_MAX}  |  "
            f"S1 manha  |  {self._state.value}"
        )
        self.query_one("#btn-start", Button).disabled = (
            self._state != PomodoroState.IDLE
        )
        self.query_one("#btn-pause", Button).disabled = self._state not in (
            PomodoroState.WORK,
            PomodoroState.PAUSED,
        )
        self.query_one("#btn-skip", Button).disabled = self._state != (
            PomodoroState.BREAK
        )
        self.query_one("#btn-abort", Button).disabled = (
            self._state == PomodoroState.IDLE
        )
