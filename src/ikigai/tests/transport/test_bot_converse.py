"""Conversation mode: the owner talks to the agent in prose, threaded.

The L1 door (`store-read`) answers a free sentence as a read-only report. L2
adds a mode the owner turns on with `/conversa`: a free sentence then goes to
`converse`, a published role that answers in prose, grounds itself in the store
and writes nothing. The harness keeps one session per chat (`tg:<chat_id>`), so
the thread survives across turns — the bot carries no conversation state.

These guards pin the mode, not the prose: toggling routes prose to `converse`
verbatim and writes nothing; toggling off restores the `store-read` door; a
cadence phrase still wins mid-conversation; the toggle is honest without the
agent or without the skill published; two turns share one session; `converse`
is a published skill disjoint from the cadences; the catalogue and the command
palette list the conversation surfaces.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest

from src.bot.harness_client import HarnessClient
from src.bot.main import AGENT_ROLES, ROUTINES, Bot, _catalogue
from src.ikigai.tests.transport.test_bot_drafts import FakeClient
from src.ikigai.tests.transport.test_bot_harness import (
    PUBLISHED,
    REPO_ROOT,
    _HarnessServer,
    _RecordingTelegram,
)

#: A sentence no cadence phrase matches — the router abstains on it.
QUESTION = "o que sabes sobre o pivot de carreira?"


@pytest.fixture
def harness_server() -> Iterator[_HarnessServer]:
    server = _HarnessServer()
    try:
        yield server
    finally:
        server.close()


def _bot(harness: HarnessClient | None) -> tuple[Bot, _RecordingTelegram, FakeClient]:
    store = FakeClient()
    bot = Bot("token", store, {"42"}, "owner", harness=harness)
    telegram = _RecordingTelegram()
    bot._http = telegram
    return bot, telegram, store


def _say(bot: Bot, text: str) -> Any:
    return bot._handle({"chat": {"id": "42"}, "text": text, "message_id": "1"})


async def _turn_on(bot: Bot) -> str:
    answer = await bot._dispatch("/conversa", "", "1", "42")
    assert isinstance(answer, str)
    return answer


async def test_conversation_mode_routes_prose_to_converse(
    harness_server: _HarnessServer,
) -> None:
    harness = HarnessClient(harness_server.url)
    bot, telegram, _ = _bot(harness)
    await _turn_on(bot)
    assert "42" in bot._converse

    await _say(bot, QUESTION)
    assert bot._running, "the prose was not handed to the agent"
    await asyncio.gather(*list(bot._running))

    runs = [r for r in harness_server.received if "routine" in r]
    assert len(runs) == 1
    assert runs[0]["routine"] == "converse"
    assert runs[0]["message"] == QUESTION, "the owner's sentence was not carried verbatim"
    assert telegram.sent, "the owner never got the agent's answer"
    assert "converse" in telegram.drafts[0]["text"], "no preview was opened"


async def test_converse_writes_nothing(harness_server: _HarnessServer) -> None:
    harness = HarnessClient(harness_server.url)
    bot, _, store = _bot(harness)
    await _turn_on(bot)

    await _say(bot, QUESTION)
    await asyncio.gather(*list(bot._running))

    writes = [c for c in store.calls if c[0] in ("upsert_artifact", "draft.save")]
    assert writes == [], "a read-only conversation wrote to the store"


async def test_toggling_off_restores_the_store_read_door(
    harness_server: _HarnessServer,
) -> None:
    harness = HarnessClient(harness_server.url)
    bot, _, _ = _bot(harness)
    await _turn_on(bot)
    off = await bot._dispatch("/conversa", "", "1", "42")
    assert "desligado" in off
    assert "42" not in bot._converse

    await _say(bot, QUESTION)
    await asyncio.gather(*list(bot._running))

    runs = [r for r in harness_server.received if "routine" in r]
    assert runs[0]["routine"] == "store-read", "the default door was not restored"


async def test_a_cadence_phrase_still_wins_in_conversation_mode(
    harness_server: _HarnessServer,
) -> None:
    harness = HarnessClient(harness_server.url)
    bot, _, _ = _bot(harness)
    await _turn_on(bot)

    await _say(bot, "fecha o dia")
    await asyncio.gather(*list(bot._running))

    runs = [r for r in harness_server.received if "routine" in r]
    assert runs[0]["routine"] == "daily-note", "the table did not answer first"


async def test_the_toggle_without_the_agent_is_honest() -> None:
    bot, _, _ = _bot(None)
    answer = await bot._dispatch("/conversa", "", "1", "42")
    assert "42" not in bot._converse, "the mode was set with no agent to talk to"
    assert "converse" in answer


async def test_the_toggle_requires_converse_published(
    harness_server: _HarnessServer,
) -> None:
    original = harness_server.payload_for

    def without_converse(path: str) -> dict[str, Any]:
        answer = original(path)
        if path.startswith("/v1/routines"):
            answer["routines"] = [r for r in answer["routines"] if r["id"] != "converse"]
        return answer

    harness_server.payload_for = without_converse  # type: ignore[method-assign]
    harness = HarnessClient(harness_server.url)
    bot, _, _ = _bot(harness)

    answer = await bot._dispatch("/conversa", "", "1", "42")
    assert "42" not in bot._converse, "the mode was set for an unpublished skill"
    assert "converse" in answer


async def test_two_turns_share_one_session(harness_server: _HarnessServer) -> None:
    harness = HarnessClient(harness_server.url)
    bot, _, _ = _bot(harness)
    await _turn_on(bot)

    await _say(bot, "primeira frase sobre o pivot de carreira")
    await asyncio.gather(*list(bot._running))
    await _say(bot, "e quanto ao segundo ponto?")
    await asyncio.gather(*list(bot._running))

    runs = [r for r in harness_server.received if "routine" in r]
    assert len(runs) == 2
    assert all(r["routine"] == "converse" for r in runs)
    assert runs[0]["session_id"] == runs[1]["session_id"], "the thread was not carried"


def test_converse_is_a_published_skill_disjoint_from_cadences() -> None:
    projection = {
        path.parent.name for path in (REPO_ROOT / "specs" / "harness" / "skills").glob("*/SKILL.md")
    }
    assert "converse" in projection, "the converse skill is not projected"
    assert "converse" in AGENT_ROLES
    assert "converse" in PUBLISHED
    assert "converse" not in ROUTINES, "a role and a cadence share an id"


def test_the_catalogue_lists_conversation() -> None:
    catalogue = _catalogue()
    assert "/converse" in catalogue, "/help does not list the converse role"
    assert "/conversa" in catalogue, "/help does not list the conversation toggle"


async def test_the_palette_lists_conversation() -> None:
    bot, telegram, _ = _bot(None)
    await bot._command_palette()
    payloads = [p for p in telegram.sent if "commands" in p]
    names = {c["command"] for c in payloads[0]["commands"]}
    assert "converse" in names, "the palette does not autocomplete the converse role"
    assert "conversa" in names, "the palette does not autocomplete the conversation toggle"
