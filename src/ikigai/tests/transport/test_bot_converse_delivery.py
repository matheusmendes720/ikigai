"""The conversation, delivered to be read — not reported at.

L2 made the owner's free sentence reach `converse`. This guard pins HOW the
answer comes back: the agent's prose is Markdown, rendered through the rich
path, split into a few digestible messages instead of one wall the API
truncates — and with no report frame (`✔ converse`, a receipt) around it,
because the owner asked to talk. The pure splitter (`chunk_markdown`) is held
at its boundaries; the delivery path is held end to end through the harness.

A guard is only worth what its failure proves: put the plain `_send` back on
the converse branch, or drop the splitter, and these fail.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest

from src.bot.harness_client import HarnessClient
from src.bot.main import Bot
from src.bot.rich import MAX_CHUNK, chunk_markdown
from src.ikigai.tests.transport.test_bot_drafts import FakeClient
from src.ikigai.tests.transport.test_bot_harness import _HarnessServer, _RecordingTelegram

#: A sentence no cadence phrase matches — the router abstains on it.
QUESTION = "o que sabes sobre o pivot de carreira?"


# ---------------------------------------------------------------------------
# The splitter, at its boundaries
# ---------------------------------------------------------------------------


def test_empty_prose_is_no_messages() -> None:
    assert chunk_markdown("") == []
    assert chunk_markdown("   \n\n  \n") == []


def test_short_prose_is_one_message() -> None:
    assert chunk_markdown("olá") == ["olá"]
    assert chunk_markdown("primeiro\n\nsegundo") == ["primeiro\n\nsegundo"]


def test_a_long_answer_is_split_under_the_ceiling() -> None:
    prose = "\n\n".join(f"**Ponto {i}.** " + "palavra " * 60 for i in range(8))
    chunks = chunk_markdown(prose)
    assert len(chunks) >= 2, "a long answer was not split"
    assert all(len(chunk) <= MAX_CHUNK for chunk in chunks), "a chunk exceeds the ceiling"
    joined = "\n\n".join(chunks)
    for i in range(8):
        assert f"**Ponto {i}.**" in joined, "a paragraph was lost in the split"


def test_an_oversized_paragraph_is_split_not_truncated() -> None:
    prose = "palavra " * 1200  # one paragraph, far over the ceiling
    chunks = chunk_markdown(prose)
    assert len(chunks) >= 2
    assert all(len(chunk) <= MAX_CHUNK for chunk in chunks)
    assert all(chunk.strip() for chunk in chunks), "an empty piece was emitted"


def test_a_code_fence_that_fits_stays_whole() -> None:
    prose = "antes\n\n```python\nprint('oi')\n```\n\ndepois"
    chunks = chunk_markdown(prose)
    assert len(chunks) == 1
    assert "```python\nprint('oi')\n```" in chunks[0], "the fence was torn"


def test_an_oversized_fence_is_reopened_in_each_piece() -> None:
    block = "```\n" + "x" * 100 + "\n```"
    chunks = chunk_markdown(block, limit=50)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 50
        assert chunk.startswith("```\n"), "a piece left the code block"
        assert chunk.endswith("\n```"), "a piece did not close the code block"


def test_a_non_positive_limit_is_refused() -> None:
    with pytest.raises(ValueError, match="limit must be positive"):
        chunk_markdown("qualquer coisa", limit=0)
    with pytest.raises(ValueError, match="limit must be positive"):
        chunk_markdown("qualquer coisa", limit=-1)


# ---------------------------------------------------------------------------
# The delivery path, end to end
# ---------------------------------------------------------------------------


class _OkResponse:
    """What Telegram answers when the rich message was accepted."""

    def json(self) -> dict[str, Any]:
        return {"ok": True}


class _RichTelegram(_RecordingTelegram):
    """A recorder that accepts the rich API, so the rich path is exercised.

    The base recorder returns nothing, which `_send_rich` reads as a refusal
    and falls back to plain — fine for the mode guards, but it would hide the
    very rendering this file holds. Here every post is accepted.
    """

    async def post(self, url: str, json: dict[str, Any]) -> _OkResponse:
        await super().post(url, json)
        return _OkResponse()


@pytest.fixture
def harness_server() -> Iterator[_HarnessServer]:
    server = _HarnessServer()
    try:
        yield server
    finally:
        server.close()


def _bot(harness: HarnessClient) -> tuple[Bot, _RichTelegram]:
    bot = Bot("token", FakeClient(), {"42"}, "owner", harness=harness)
    telegram = _RichTelegram()
    bot._http = telegram  # type: ignore[assignment]
    return bot, telegram


async def _converse(bot: Bot, prose: str, harness_server: _HarnessServer) -> _RichTelegram:
    harness_server.payload = {"text": prose, "duration_ms": 1200, "memory_entry_id": 7}
    await bot._dispatch("/conversa", "", "1", "42")
    await bot._handle({"chat": {"id": "42"}, "text": QUESTION, "message_id": "1"})
    await asyncio.gather(*list(bot._running))
    return bot._http  # type: ignore[return-value]


async def test_a_long_converse_answer_arrives_as_readable_rich_chunks(
    harness_server: _HarnessServer,
) -> None:
    prose = "\n\n".join(f"**Ponto {i}.** " + "palavra " * 60 for i in range(8))
    bot, _ = _bot(HarnessClient(harness_server.url))
    telegram = await _converse(bot, prose, harness_server)

    answers = telegram.sent
    assert len(answers) >= 2, "a long answer was not split into digestible messages"
    assert all("rich_message" in p for p in answers), "the prose was not rendered as Markdown"
    for payload in answers:
        markdown = payload["rich_message"]["markdown"]
        assert len(markdown) <= MAX_CHUNK, "a message exceeds the readable ceiling"
        assert "✔" not in markdown, "the report frame leaked into the conversation"
    joined = "\n\n".join(p["rich_message"]["markdown"] for p in answers)
    for i in range(8):
        assert f"**Ponto {i}.**" in joined, "the answer was truncated"


async def test_a_short_converse_answer_is_one_rendered_message_without_framing(
    harness_server: _HarnessServer,
) -> None:
    prose = "O pivot está **adiado** para a próxima onda."
    bot, _ = _bot(HarnessClient(harness_server.url))
    telegram = await _converse(bot, prose, harness_server)

    assert len(telegram.sent) == 1, "a short answer was needlessly split"
    payload = telegram.sent[0]
    assert "rich_message" in payload, "the prose was not rendered as Markdown"
    assert payload["rich_message"]["markdown"] == prose, "a report frame was added to the prose"


async def test_an_empty_converse_answer_is_honest(
    harness_server: _HarnessServer,
) -> None:
    bot, _ = _bot(HarnessClient(harness_server.url))
    telegram = await _converse(bot, "   ", harness_server)

    assert len(telegram.sent) == 1
    assert telegram.sent[0].get("text") == "(sem resposta)"
