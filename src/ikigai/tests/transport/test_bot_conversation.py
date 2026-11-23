"""The conversation door: a sentence the intent table does not know.

The owner asked to talk to an agent, not to be handed four buttons. The
harness publishes seven skills; three are roles, not cadences. `store-read`
is the one whose trigger is "a text" and which writes nothing — so a sentence
the deterministic table abstains on becomes a question to it, and the answer
comes back through the same preview + Stop guard a cadence uses.

These guards pin the door, not the prose: a free sentence reaches `store-read`
verbatim and writes nothing; without the agent the honest "no open draft"
answer is preserved; a cadence phrase still wins; the door opens only on a
CONFIRMED publication; the roles are commands and published skills, disjoint
from the cadences.
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
    # A draft-capable store: the door is reached through `_append`, which
    # bails before routing when the client cannot speak drafts.
    store = FakeClient()
    bot = Bot("token", store, {"42"}, "owner", harness=harness)
    telegram = _RecordingTelegram()
    bot._http = telegram
    return bot, telegram, store


def _say(bot: Bot, text: str) -> Any:
    return bot._handle({"chat": {"id": "42"}, "text": text, "message_id": "1"})


async def test_a_free_sentence_goes_to_the_agent_as_a_question(
    harness_server: _HarnessServer,
) -> None:
    harness = HarnessClient(harness_server.url)
    bot, telegram, _ = _bot(harness)

    await _say(bot, QUESTION)
    assert bot._running, "the question was not handed to the agent"
    await asyncio.gather(*list(bot._running))

    runs = [r for r in harness_server.received if "routine" in r]
    assert len(runs) == 1
    assert runs[0]["routine"] == "store-read"
    assert runs[0]["message"] == QUESTION, "the owner's sentence was not carried verbatim"
    assert telegram.sent, "the owner never got the agent's answer"
    assert "store-read" in telegram.drafts[0]["text"], "no preview was opened"


async def test_the_question_writes_nothing(harness_server: _HarnessServer) -> None:
    harness = HarnessClient(harness_server.url)
    bot, _, store = _bot(harness)

    await _say(bot, QUESTION)
    await asyncio.gather(*list(bot._running))

    writes = [c for c in store.calls if c[0] in ("upsert_artifact", "draft.save")]
    assert writes == [], "a read-only question wrote to the store"


async def test_without_the_agent_the_honest_answer_is_preserved() -> None:
    bot, telegram, _ = _bot(None)

    await _say(bot, QUESTION)

    assert not bot._running, "a bot with no agent tried to run a routine"
    assert telegram.sent
    assert "Não há rascunho aberto" in telegram.sent[0]["text"]


async def test_a_cadence_phrase_still_wins(harness_server: _HarnessServer) -> None:
    harness = HarnessClient(harness_server.url)
    bot, _, _ = _bot(harness)

    await _say(bot, "fecha o dia")
    await asyncio.gather(*list(bot._running))

    runs = [r for r in harness_server.received if "routine" in r]
    assert runs[0]["routine"] == "daily-note", "the table did not answer first"


async def test_an_unreachable_harness_gets_buttons_not_a_dispatch(
    harness_server: _HarnessServer,
) -> None:
    harness_server.status = 500
    harness = HarnessClient(harness_server.url)
    bot, telegram, _ = _bot(harness)

    await _say(bot, QUESTION)

    assert not bot._running, "a dead harness was sent a routine it may refuse"
    assert harness_server.received == []
    assert "Não há rascunho aberto" in telegram.sent[0]["text"]


async def test_a_harness_without_store_read_gets_buttons(
    harness_server: _HarnessServer,
) -> None:
    original = harness_server.payload_for

    def without_store_read(path: str) -> dict[str, Any]:
        answer = original(path)
        if path.startswith("/v1/routines"):
            answer["routines"] = [r for r in answer["routines"] if r["id"] != "store-read"]
        return answer

    harness_server.payload_for = without_store_read  # type: ignore[method-assign]
    harness = HarnessClient(harness_server.url)
    bot, telegram, _ = _bot(harness)

    await _say(bot, QUESTION)

    assert not bot._running, "an unpublished routine was dispatched"
    rows = telegram.sent[0].get("reply_markup", {}).get("inline_keyboard", [])
    labels = {button["text"] for row in rows for button in row}
    assert "/store-read" not in labels, "a button for an unpublished routine cannot work"


@pytest.mark.parametrize("role", sorted(AGENT_ROLES))
async def test_the_roles_are_commands(harness_server: _HarnessServer, role: str) -> None:
    harness = HarnessClient(harness_server.url)
    bot, _, _ = _bot(harness)

    await bot._dispatch(f"/{role}", "o texto", "1", "42")
    await asyncio.gather(*list(bot._running))

    runs = [r for r in harness_server.received if "routine" in r]
    assert runs[0]["routine"] == role
    assert runs[0]["message"] == "o texto"


def test_the_roles_are_published_skills_and_disjoint_from_cadences() -> None:
    projection = {
        path.parent.name for path in (REPO_ROOT / "specs" / "harness" / "skills").glob("*/SKILL.md")
    }
    assert set(AGENT_ROLES) <= projection, "a role the harness does not publish"
    assert set(AGENT_ROLES) <= PUBLISHED
    assert not (set(AGENT_ROLES) & set(ROUTINES)), "a role and a cadence share an id"


def test_the_catalogue_lists_the_roles() -> None:
    catalogue = _catalogue()
    for role in AGENT_ROLES:
        assert f"/{role}" in catalogue, f"/help does not list the role {role}"
