"""Integration tests for PAV TUI app launch and screen navigation."""
from __future__ import annotations

import asyncio

from operational.tui.app import PAVApp
from operational.tui.theme import get_tui_theme


def test_app_mounts_without_crash() -> None:
    app = PAVApp()

    async def run() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.is_running

    asyncio.run(run())


def test_on_mount_shows_dashboard() -> None:
    from operational.tui.screens.dashboard_screen import DashboardScreen

    app = PAVApp()

    async def run() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)

    asyncio.run(run())


def test_all_6_non_dashboard_screens_switch_without_crash() -> None:
    app = PAVApp()

    async def run() -> None:
        async with app.run_test() as pilot:
            app.action_switch_daily_flow()
            await pilot.pause()
            app.action_switch_pomodoro_timer()
            await pilot.pause()
            app.action_switch_habits()
            await pilot.pause()
            app.action_switch_metrics()
            await pilot.pause()
            app.action_switch_policy()
            await pilot.pause()
            app.action_switch_journal()
            await pilot.pause()

    asyncio.run(run())


def test_theme_is_registered_before_mount() -> None:
    app = PAVApp()

    async def run() -> None:
        async with app.run_test() as pilot:
            theme = get_tui_theme()
            assert theme.name in app.available_themes

    asyncio.run(run())


def test_switch_to_daily_flow() -> None:
    app = PAVApp()

    async def run() -> None:
        async with app.run_test() as pilot:
            app.action_switch_daily_flow()
            await pilot.pause()

    asyncio.run(run())


def test_switch_to_all_non_dashboard_screens() -> None:
    app = PAVApp()

    async def run() -> None:
        async with app.run_test() as pilot:
            app.action_switch_daily_flow()
            await pilot.pause()
            app.action_switch_pomodoro_timer()
            await pilot.pause()
            app.action_switch_habits()
            await pilot.pause()
            app.action_switch_metrics()
            await pilot.pause()
            app.action_switch_policy()
            await pilot.pause()
            app.action_switch_journal()
            await pilot.pause()

    asyncio.run(run())


def test_quit_binding_works() -> None:
    app = PAVApp()

    async def run() -> None:
        async with app.run_test() as pilot:
            await app.action_quit()
            await pilot.pause()
            assert not app.is_running

    asyncio.run(run())


def test_pomodoro_screen_runs_full_state_machine_cycle() -> None:
    """Drive the Pomodoro screen through IDLE → WORK → PAUSED → WORK → BREAK.

    Regression test for P0 #4: prior to the fix, the four ``action_*``
    handlers were missing so ``BINDINGS`` raised ``NoAttributeError`` and
    the timer never advanced. The screen now wires through
    :class:`PomodoroTracker`, persists rounds to
    :data:`cli_state.pomodoros`, and renders the :class:`PomodoroState`
    enum on the state-label widget.
    """
    from operational.enums import PomodoroState
    from operational.tui.screens.pomodoro_timer_screen import PomodoroTimerScreen

    app = PAVApp()

    async def run() -> None:
        async with app.run_test() as pilot:
            app.action_switch_pomodoro_timer()
            await pilot.pause()
            assert isinstance(app.screen, PomodoroTimerScreen)

            screen: PomodoroTimerScreen = app.screen  # type: ignore[assignment]

            # IDLE — Start button is the only one enabled.
            start_btn = screen.query_one("#btn-start")
            assert not start_btn.disabled, "start must be enabled in IDLE"

            # IDLE → WORK.
            screen.action_start_timer()
            await pilot.pause()
            assert screen._state == PomodoroState.WORK
            assert screen._tracker.current_state == PomodoroState.WORK
            pause_btn = screen.query_one("#btn-pause")
            assert not pause_btn.disabled, "pause must be enabled in WORK"

            # WORK → PAUSED.
            screen.action_pause_timer()
            await pilot.pause()
            assert screen._state == PomodoroState.PAUSED
            assert screen._tracker.current_state == PomodoroState.PAUSED

            # PAUSED → WORK.
            screen.action_pause_timer()
            await pilot.pause()
            assert screen._state == PomodoroState.WORK
            assert screen._tracker.current_state == PomodoroState.WORK

            # WORK → BREAK (force the transition by simulating timer
            # expiry — we don't want to wait 50 minutes of wall time).
            screen._time_left = 1
            screen._phase_started_at = screen._phase_started_at  # keep current
            from datetime import UTC, datetime
            screen._phase_started_at = datetime.now(tz=UTC)
            screen._tick()  # decrement 1 → 0
            await pilot.pause()
            assert screen._state == PomodoroState.BREAK, (
                f"expected BREAK after 1s tick from WORK, got {screen._state}"
            )
            # WORK round was persisted on auto-advance.
            assert screen._tracker.current_round >= 1

            # Now abort the session — should return to IDLE and persist
            # the in-progress BREAK round as SKIPPED.
            screen.action_abort_timer()
            await pilot.pause()
            assert screen._state == PomodoroState.IDLE
            assert screen._tracker.current_state == PomodoroState.IDLE
            # Start button re-enabled, pause/abort disabled.
            assert not screen.query_one("#btn-start").disabled
            assert screen.query_one("#btn-pause").disabled
            assert screen.query_one("#btn-abort").disabled

    asyncio.run(run())
