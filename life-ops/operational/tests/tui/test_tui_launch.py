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
