"""Unit tests for ``PomodoroTimerScreen._maybe_reload`` (P2 #4).

Mirrors the pattern shipped for the dashboard in P0 #8: every TUI
screen that touches persistent repos must call
``reload_stale_repos()`` on its refresh path so peer-process writes
(``pav pomodoro round create`` from another terminal) become visible
to the live TUI without a restart.

These tests verify the *contract* on the new method directly rather
than spinning up a full ``App`` — keeps the test fast, deterministic,
and free of Textual's run-loop scheduling.
"""

from __future__ import annotations

from unittest.mock import patch

from operational.tui.screens.pomodoro_timer_screen import PomodoroTimerScreen


def test_screen_has_maybe_reload_method() -> None:
    """``_maybe_reload`` exists and is callable (P2 #4 entry point)."""
    assert hasattr(PomodoroTimerScreen, "_maybe_reload"), (
        "PomodoroTimerScreen must define _maybe_reload (P2 #4 fix)"
    )
    assert callable(PomodoroTimerScreen._maybe_reload)


def test_screen_has_reload_handle_attribute() -> None:
    """``on_mount`` registers the reload timer as ``_reload_handle``."""
    # Source-level check via the ``__init_subclass__`` machinery is too
    # heavy for a smoke test. The attribute is initialized inside
    # ``on_mount`` (Textual lifecycle hook), so we just confirm the
    # source declares the type annotation as ``Timer | None``.
    import inspect

    src = inspect.getsource(PomodoroTimerScreen.on_mount)
    assert "_reload_handle" in src, (
        "on_mount must initialize self._reload_handle for P2 #4"
    )
    assert "self.set_interval(2.0, self._maybe_reload)" in src, (
        "on_mount must wire _reload_handle to a 2.0-second interval"
    )


def test_screen_on_unmount_stops_reload_handle() -> None:
    """``on_unmount`` must stop the reload handle to prevent zombie timers."""
    import inspect

    src = inspect.getsource(PomodoroTimerScreen.on_unmount)
    assert "_reload_handle.stop()" in src, (
        "on_unmount must call _reload_handle.stop() to release the timer"
    )


def test_maybe_reload_invokes_reload_stale_repos() -> None:
    """``_maybe_reload`` calls the shared reload helper on every tick."""
    with patch(
        "operational.tui.screens.pomodoro_timer_screen.reload_stale_repos"
    ) as mocked:
        # Construct a bare instance — we never call ``on_mount`` so the
        # handle attribute is irrelevant; we're driving ``_maybe_reload``
        # directly to assert its single-statement contract.
        screen = PomodoroTimerScreen.__new__(PomodoroTimerScreen)
        screen._maybe_reload()
        assert mocked.call_count == 1, (
            "_maybe_reload must call reload_stale_repos() exactly once"
        )


def test_maybe_reload_swallows_transient_errors() -> None:
    """A reload failure must NEVER propagate — the timer loop must survive.

    If ``reload_stale_repos`` raises (e.g. malformed JSON, IOError on a
    transient filesystem glitch), the 1-Hz tick handler would inherit
    the exception and the countdown would stop. The ``try/except
    Exception: pass`` guard in ``_maybe_reload`` prevents this.
    """
    with patch(
        "operational.tui.screens.pomodoro_timer_screen.reload_stale_repos",
        side_effect=RuntimeError("simulated transient failure"),
    ):
        screen = PomodoroTimerScreen.__new__(PomodoroTimerScreen)
        # Must NOT raise.
        screen._maybe_reload()
