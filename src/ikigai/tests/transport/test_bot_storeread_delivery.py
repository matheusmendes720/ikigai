"""The manual door renders the agent's Markdown — whole, short or long.

2026-11-24 — the owner chose FULL RICH on the manual door: every routine
report (store-read and the rest) is delivered through ``sendRichMessage`` so
the agent's Markdown renders — headers, lists, tables, code — exactly like the
cadence already delivers. Before, the completion branch sent the framed report
as ONE plain ``sendMessage``: the Markdown arrived as literal raw text, and a
report over the ceiling was clipped at ``text[:4000]`` — the tail silently
dropped. Now ``_send_chunked`` renders and splits it: a short report is one rich
message, a long one is a few chunks each under ``MAX_CHUNK``, the ``✔ routine``
frame in the first and the receipt in the last, and nothing is thrown away. If
``sendRichMessage`` is refused, ``_send_rich`` falls back to the plain chunk, so
the report still arrives whole.

This pins that delivery on the real HTTP surface, with a Telegram double that
ACCEPTS ``sendRichMessage``. The harness guard
``test_a_routine_command_does_not_block_the_bot`` keeps its invariant — the
report arrives whole, in one message, with the receipt, without blocking — and
its double now accepts the rich send too, so it reads the report off the rich
payload rather than a plain fallback. The rich FORMAT is pinned here: long →
chunks whole, short → one rich message, the ceiling splits not clips, and a
refused rich send still delivers. This is a NEW guard; the sibling harness and
draft guards were adapted to the rich channel with every invariant intact —
none was weakened.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.bot.harness_client import HarnessClient
from src.bot.main import Bot, _render_routine
from src.bot.rich import MAX_CHUNK
from src.ikigai.tests.transport.test_bot_harness import (
    _HarnessServer,
    _NoStore,
)
from src.ikigai.tests.transport.test_bot_harness import (
    _RecordingTelegram as _BaseTelegram,
)

pytestmark = pytest.mark.asyncio

QUESTION = "/store-read o que sei sobre o alvo"
DURATION_MS = 9400
MEMORY_ENTRY_ID = 7
RECEIPT = "(9.4s · memória #7)"


class _OkResponse:
    def json(self) -> dict[str, Any]:
        return {"ok": True, "result": {"message_id": 1}}


class _RefusedResponse:
    """The Bot API refusing the rich send — the fallback must still deliver."""

    def json(self) -> dict[str, Any]:
        return {"ok": False, "description": "rich messages are unsupported here"}


class _RecordingTelegram(_BaseTelegram):
    """The harness's double, plus a record of WHICH kind each message was.

    ``rich_ok=False`` makes ``sendRichMessage`` answer a refusal, so the
    fallback path is exercised on the real ``_send_rich`` code.
    """

    def __init__(self, *, rich_ok: bool = True) -> None:
        super().__init__()
        self.rich: list[dict[str, Any]] = []
        self.plain: list[dict[str, Any]] = []
        self._rich_ok = rich_ok

    async def post(self, url: str, json: dict[str, Any]) -> Any:
        if "sendMessageDraft" in url:
            self.drafts.append(json)
            return _OkResponse()
        self.sent.append(json)
        if "sendRichMessage" in url:
            self.rich.append(json)
            return _OkResponse() if self._rich_ok else _RefusedResponse()
        self.plain.append(json)
        return _OkResponse()


@pytest.fixture
def harness_server():
    server = _HarnessServer()
    try:
        yield server
    finally:
        server.close()


def _bot(
    harness: HarnessClient, telegram: _RecordingTelegram | None = None
) -> tuple[Bot, _RecordingTelegram]:
    telegram = telegram if telegram is not None else _RecordingTelegram()
    bot = Bot("token", _NoStore(), {"42"}, "owner", harness=harness)
    bot._http = telegram  # type: ignore[assignment]
    return bot, telegram


def _result(text: str) -> dict[str, Any]:
    return {
        "ok": True,
        "routine": "store-read",
        "text": text,
        "duration_ms": DURATION_MS,
        "memory_entry_id": MEMORY_ENTRY_ID,
    }


async def _ask(harness_server: _HarnessServer, bot: Bot, prose: str) -> None:
    harness_server.payload = _result(prose)
    await bot._handle({"chat": {"id": "42"}, "text": QUESTION, "message_id": "1"})
    await asyncio.gather(*list(bot._running))


#: The frame and the receipt the renderer wraps around the agent's prose, so a
#: test can ask for a FRAMED report of an exact length instead of guessing.
_FRAME_OVERHEAD = len(_render_routine("store-read", _result("x"))) - 1


def _prose_of(length: int) -> str:
    """Prose whose FRAMED report is exactly ``length`` characters."""
    return "x" * (length - _FRAME_OVERHEAD)


async def test_a_long_store_read_report_arrives_whole_in_rich_chunks(
    harness_server: _HarnessServer,
) -> None:
    """A store-read that found a lot is worth more than its first 4000 chars.

    The framed report is well over the ceiling, so it must arrive in readable
    rich chunks — the frame in the first, the receipt in the last, every
    paragraph of the agent's answer present, nothing clipped. The old plain
    ``sendMessage`` dropped the tail at 4000 and showed the Markdown raw; this
    is the regression that ends both.
    """
    harness = HarnessClient(harness_server.url)
    bot, telegram = _bot(harness)
    paragraphs = [f"paragrafo {i} " + "x" * 750 for i in range(12)]
    prose = "\n\n".join(paragraphs)
    await _ask(harness_server, bot, prose)

    chunks = [p["rich_message"]["markdown"] for p in telegram.rich]
    assert len(chunks) >= 2, "a long report was not chunked — it would have been clipped"
    assert telegram.plain == [], "the long report took the plain (clipping) path"
    assert all(len(c) <= MAX_CHUNK for c in chunks), "a chunk exceeds Telegram's rich ceiling"
    assert chunks[0].startswith("✔ store-read"), "the routine frame is not in the first chunk"
    assert RECEIPT in chunks[-1], "the receipt is not in the last chunk"
    assert all(any(p in c for c in chunks) for p in paragraphs), "a paragraph was lost"
    # The whole prose is reconstructable from the chunks: nothing was thrown away.
    assert not any(all(p in c for p in paragraphs) for c in chunks), (
        "the report fit in one chunk — the test no longer exercises the long path"
    )


async def test_a_short_store_read_report_is_one_rich_message(
    harness_server: _HarnessServer,
) -> None:
    """A short report renders rich too — the owner chose full Markdown.

    Even a one-line answer is the agent's Markdown, so it goes through
    ``sendRichMessage``: one rich message carrying the frame, the prose and the
    receipt, nothing plain. The old short-plain path showed the Markdown as
    literal raw text; this is the door the owner asked to render.
    """
    harness = HarnessClient(harness_server.url)
    bot, telegram = _bot(harness)
    prose = "uma resposta curta"
    await _ask(harness_server, bot, prose)

    assert len(telegram.rich) == 1, "a short report is one rich message"
    assert telegram.plain == [], "the short report did not take the plain path"
    markdown = telegram.rich[0]["rich_message"]["markdown"]
    assert prose in markdown
    assert markdown.startswith("✔ store-read"), "the frame is missing"
    assert RECEIPT in markdown, "the receipt is missing"


async def test_a_report_that_fits_in_one_chunk_is_delivered_whole_rich(
    harness_server: _HarnessServer,
) -> None:
    """A report under the chunk ceiling is one rich message, complete."""
    harness = HarnessClient(harness_server.url)
    bot, telegram = _bot(harness)
    prose = _prose_of(MAX_CHUNK)
    await _ask(harness_server, bot, prose)

    assert len(telegram.rich) == 1, "a report that fits is not split"
    assert telegram.plain == [], "a fitting report did not take the plain path"
    markdown = telegram.rich[0]["rich_message"]["markdown"]
    assert prose in markdown, "the prose was clipped"
    assert markdown.startswith("✔ store-read")
    assert RECEIPT in markdown


async def test_one_character_over_the_chunk_ceiling_is_not_clipped(
    harness_server: _HarnessServer,
) -> None:
    """The ceiling splits, it does not clip: one char over MAX_CHUNK is whole.

    The framed report is one character over the rich chunk ceiling, so it
    splits into two rich chunks — and every character of the prose survives.
    A naive ``text[:MAX_CHUNK]`` would have dropped the last character; the
    chunked path keeps it.
    """
    harness = HarnessClient(harness_server.url)
    bot, telegram = _bot(harness)
    prose = _prose_of(MAX_CHUNK + 1)
    await _ask(harness_server, bot, prose)

    chunks = [p["rich_message"]["markdown"] for p in telegram.rich]
    assert len(chunks) >= 2, "a report over the ceiling was not split"
    assert telegram.plain == [], "the report was clipped to a plain send"
    assert all(len(c) <= MAX_CHUNK for c in chunks)
    delivered = sum(c.count("x") for c in chunks)
    assert delivered == len(prose), f"{len(prose) - delivered} chars lost"


async def test_a_refused_rich_message_still_delivers_the_report_whole(
    harness_server: _HarnessServer,
) -> None:
    """If sendRichMessage is refused, the report still arrives — plain, whole.

    Full rich makes every report depend on ``sendRichMessage``. The safety net
    is ``_send_rich``'s fallback: a refused rich send delivers the same chunk as
    plain text, so the owner still reads the frame, the prose and the receipt.
    Nothing is lost because the renderer was unavailable.
    """
    harness = HarnessClient(harness_server.url)
    bot, telegram = _bot(harness, _RecordingTelegram(rich_ok=False))
    prose = "uma resposta curta"
    await _ask(harness_server, bot, prose)

    assert telegram.rich, "the rich path was not attempted"
    assert len(telegram.plain) == 1, "the refused rich send did not fall back"
    text = telegram.plain[0]["text"]
    assert prose in text
    assert text.startswith("✔ store-read"), "the frame is missing from the fallback"
    assert RECEIPT in text, "the receipt is missing from the fallback"
