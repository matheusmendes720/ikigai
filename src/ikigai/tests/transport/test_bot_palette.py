"""The command palette: the "/" autocomplete the owner actually sees.

Telegram only autocompletes what `setMyCommands` published, and it refuses a
hyphen in a command name. The bot answered twenty-seven commands and registered
none, so typing "/" showed an empty list. These guards pin the registration,
not the prose: the palette carries exactly the commands the bot answers, the
underscore aliases dispatch to the canonical cadence and role ids, startup
wires the registration beside the menu button, and a refusal never crashes.
"""

from __future__ import annotations

import asyncio
import inspect
import re
from collections.abc import Iterator
from typing import Any

import pytest

from src.bot.harness_client import HarnessClient
from src.bot.main import _COMMANDS, _UTILITY_COMMANDS, AGENT_ROLES, ROUTINES, Bot
from src.ikigai.tests.transport.test_bot_drafts import FakeClient
from src.ikigai.tests.transport.test_bot_harness import _HarnessServer, _RecordingTelegram

#: Telegram's own rule for a command name: lowercase, digits, underscore, 1-32.
_NAME = re.compile(r"^[a-z0-9_]{1,32}$")


@pytest.fixture
def harness_server() -> Iterator[_HarnessServer]:
    server = _HarnessServer()
    try:
        yield server
    finally:
        server.close()


def _bot(harness: HarnessClient | None = None) -> tuple[Bot, _RecordingTelegram]:
    bot = Bot("token", FakeClient(), {"42"}, "owner", harness=harness)
    telegram = _RecordingTelegram()
    bot._http = telegram  # type: ignore[assignment]
    return bot, telegram


async def test_the_palette_publishes_every_command_the_bot_answers() -> None:
    bot, telegram = _bot()

    await bot._command_palette()

    payloads = [p for p in telegram.sent if "commands" in p]
    assert len(payloads) == 1, "setMyCommands was not called exactly once"
    commands = payloads[0]["commands"]
    names = {c["command"] for c in commands}
    expected = (
        {n.lstrip("/") for n in _COMMANDS}
        | {n.lstrip("/") for n in _UTILITY_COMMANDS}
        | {n.replace("-", "_") for n in {**ROUTINES, **AGENT_ROLES}}
    )
    assert names == expected, "the palette and the answerable surface drifted apart"
    for entry in commands:
        assert _NAME.match(entry["command"]), f"invalid Telegram command: {entry['command']}"
        assert 1 <= len(entry["description"]) <= 256, "Telegram refuses this description"


async def test_the_underscore_alias_runs_the_canonical_routine(
    harness_server: _HarnessServer,
) -> None:
    bot, _ = _bot(HarnessClient(harness_server.url))

    await bot._dispatch("/daily_note", "", "1", "42")
    await asyncio.gather(*list(bot._running))

    runs = [r for r in harness_server.received if "routine" in r]
    assert runs, "the alias never reached the harness"
    assert runs[0]["routine"] == "daily-note", "the alias missed the cadence"


async def test_the_underscore_alias_runs_the_canonical_role(
    harness_server: _HarnessServer,
) -> None:
    bot, _ = _bot(HarnessClient(harness_server.url))

    await bot._dispatch("/store_read", "o que registrei hoje?", "1", "42")
    await asyncio.gather(*list(bot._running))

    runs = [r for r in harness_server.received if "routine" in r]
    assert runs, "the alias never reached the harness"
    assert runs[0]["routine"] == "store-read", "the alias missed the role"


async def test_startup_wires_the_palette_beside_the_menu_button() -> None:
    source = inspect.getsource(Bot.run)
    assert "self._command_palette()" in source, "startup never registers the palette"
    assert "self._menu_button()" in source, "the menu button wiring was lost"


async def test_a_refused_palette_does_not_crash_the_bot() -> None:
    class _Refusing:
        async def post(self, url: str, json: dict[str, Any]) -> None:
            raise RuntimeError("telegram said no")

    bot, _ = _bot()
    bot._http = _Refusing()  # type: ignore[assignment]

    await bot._command_palette()  # must return, not raise
