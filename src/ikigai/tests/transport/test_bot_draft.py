"""The Stop: the draft that carries it, and the update that fires it.

Gate G7 of the chain (`specs/harness/CHAINED-ROUTINES.md` §11): *Stop stops
— the Stop button cancels the run within 2 s, and no artifact is written.*

Telegram's streaming replies give a bot a surface that is not a message: a
DRAFT, with a Stop button, that the owner watches while the work happens.
The button does not stop anything by itself — it produces an update
(`stopped_message_generation`) — so the bot has to do the stopping.

These tests are the bot's half of the gate:

- the draft opens, with the button, and it IS the "it started" message (a
  message there would replace the preview, and with it the button);
- the stop finds the run it belongs to, cancels it, and asks the harness to
  stop the AGENT — because a bot that only stops waiting leaves an agent
  working, and an agent that keeps working keeps writing;
- a stop for nothing, from nobody, or too late, does nothing at all.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import src.bot.main as bot_main
from src.bot.main import Bot


class FakeHttp:
    """Telegram's HTTP surface: what was sent, and what it answers."""

    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, Any]]] = []
        #: What `sendMessageDraft` answers. `{"ok": False}` is how Telegram
        #: refuses a draft — a chat that is not private, for instance.
        self.draft_ok = True

    async def post(self, url: str, json: dict[str, Any]) -> Any:
        self.posts.append((url, json))

        class _Response:
            def __init__(self, body: dict[str, Any]) -> None:
                self._body = body

            def json(self) -> dict[str, Any]:
                return self._body

        if "sendMessageDraft" in url:
            return _Response({"ok": self.draft_ok})
        return _Response({"ok": True})

    async def get(self, url: str, params: dict[str, Any]) -> Any:
        raise AssertionError("the bot must not poll in this test")

    def drafts(self) -> list[dict[str, Any]]:
        """The `sendMessageDraft` payloads, in order."""
        return [payload for url, payload in self.posts if "sendMessageDraft" in url]

    def messages(self) -> list[dict[str, Any]]:
        return [payload for url, payload in self.posts if url.endswith("/sendMessage")]


class FakeHarness:
    """The agent's door: a routine that never ends, until it is stopped."""

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled: list[str] = []
        self.result: dict[str, Any] = {"text": "o relatório", "duration_ms": 1234}

    async def run_routine(self, routine: str, **kwargs: Any) -> dict[str, Any]:
        self.started.set()
        await self.release.wait()
        return self.result

    async def cancel_routine(
        self, session_id: str, timeout_s: float | None = None
    ) -> dict[str, Any]:
        self.cancelled.append(session_id)
        return {"ok": True, "cancelled": True}


class RecordingBot(Bot):
    """The real bot, with Telegram's send replaced by a recorder."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.outbox: list[str] = []
        self.http = FakeHttp()
        self._http = self.http

    async def _send(self, chat_id: str, text: str, buttons: Any = None) -> None:
        self.outbox.append(text)


def _bot(harness: Any = None, allowed: set[str] | None = None) -> RecordingBot:
    return RecordingBot(
        "token",
        object(),
        allowed if allowed is not None else {"2115322359"},
        "owner",
        harness=harness,
    )


async def _stop(bot: RecordingBot, draft_id: int, chat_id: str = "2115322359") -> None:
    """The update Telegram sends when the owner presses Stop."""
    await bot._on_generation_stopped({"chat": {"id": chat_id}, "draft_id": draft_id})


# ---------------------------------------------------------------------------
# The draft
# ---------------------------------------------------------------------------


async def test_a_routine_opens_a_draft_with_the_stop_button() -> None:
    """The preview is what carries the button — and there is no button
    without a preview."""
    harness = FakeHarness()
    bot = _bot(harness)

    await bot._start_routine("2115322359", "daily-note", "")

    drafts = bot.http.drafts()
    assert len(drafts) == 1, "the routine opened no preview"
    payload = drafts[0]
    assert payload["can_stop"] is True, "the preview has no Stop button"
    assert payload["draft_id"], "the draft id must not be zero"
    assert isinstance(payload["chat_id"], int), "the chat id must be a number"
    assert "daily-note" in payload["text"]


async def test_the_draft_replaces_the_started_message() -> None:
    """A message while the preview is open REPLACES the preview — and with it
    the button the owner needs."""
    harness = FakeHarness()
    bot = _bot(harness)

    answer = await bot._start_routine("2115322359", "daily-note", "")

    assert answer == "", "the bot sent a message that would replace the preview"
    assert not bot.outbox, "a message was sent next to the preview"


async def test_a_draft_telegram_refuses_falls_back_to_the_message() -> None:
    """A preview is a private-chat surface. A chat that cannot have one gets
    the message it always got, and the run works the same way."""
    harness = FakeHarness()
    bot = _bot(harness)
    bot.http.draft_ok = False

    answer = await bot._start_routine("2115322359", "daily-note", "")

    assert "daily-note" in answer
    assert "começou" in answer
    assert bot.http.drafts(), "the bot did not even try"


async def test_the_draft_is_refreshed_with_the_same_id() -> None:
    """The preview is a thirty-second thing. A routine is not — so the
    preview is refreshed, with the SAME id, which is what makes Telegram
    animate the new text into the old one."""
    harness = FakeHarness()
    bot = _bot(harness)
    await bot._start_routine("2115322359", "daily-note", "")
    first = bot.http.drafts()[0]["draft_id"]

    await bot._drafts.refresh(bot._drafts.find(first))  # type: ignore[arg-type]

    drafts = bot.http.drafts()
    assert len(drafts) == 2, "the preview was not refreshed"
    assert drafts[1]["draft_id"] == first, "the refresh used another id: it would not animate"


async def test_the_refresh_tick_is_below_the_preview_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Stop button must not disappear from under the owner's thumb."""
    monkeypatch.setattr(bot_main, "REFRESH_S", 0.01)
    harness = FakeHarness()
    bot = _bot(harness)

    await bot._start_routine("2115322359", "daily-note", "")
    await harness.started.wait()
    await asyncio.sleep(0.05)

    assert len(bot.http.drafts()) > 1, "the preview was never refreshed"


# ---------------------------------------------------------------------------
# The stop
# ---------------------------------------------------------------------------


async def test_the_stop_cancels_the_run_and_asks_the_harness_to_stop_the_agent() -> None:
    """Both halves, and the second one is the one that matters.

    The bot's wait is not the work: the agent is a process with the store
    open. A bot that only stops waiting leaves an agent working — and an
    agent that keeps working keeps writing."""
    harness = FakeHarness()
    bot = _bot(harness)
    await bot._start_routine("2115322359", "daily-note", "")
    await harness.started.wait()
    tasks = list(bot._running)
    assert len(tasks) == 1

    await _stop(bot, bot.http.drafts()[0]["draft_id"])

    assert harness.cancelled == ["tg:2115322359"], "the agent was not told to stop"
    await asyncio.wait({tasks[0]}, timeout=1.0)
    assert tasks[0].cancelled(), "the bot kept waiting for a run that was stopped"
    assert "Parada" in bot.outbox[-1], f"the bot answered: {bot.outbox[-1]}"


async def test_a_stopped_run_sends_no_report() -> None:
    """The report belongs to a run that finished. A stopped one has none."""
    harness = FakeHarness()
    bot = _bot(harness)
    await bot._start_routine("2115322359", "daily-note", "")
    await harness.started.wait()

    await _stop(bot, bot.http.drafts()[0]["draft_id"])
    await asyncio.sleep(0.05)

    assert not any("relatório" in text for text in bot.outbox), (
        f"the stopped run still sent its report: {bot.outbox}"
    )


async def test_a_stop_for_a_draft_that_does_not_exist_does_nothing() -> None:
    """A stop for a preview that is gone has nothing to stop."""
    harness = FakeHarness()
    bot = _bot(harness)

    await _stop(bot, 987654)

    assert not harness.cancelled, "the agent was stopped for a run that did not exist"
    assert not bot.outbox, "the bot spoke about a stop that was not its own"


async def test_a_stop_from_an_unlisted_chat_does_nothing() -> None:
    """Fail closed, like every other door."""
    harness = FakeHarness()
    bot = _bot(harness, allowed={"outro-chat"})
    await bot._start_routine("outro-chat", "daily-note", "")
    await harness.started.wait()

    await _stop(bot, bot.http.drafts()[0]["draft_id"], chat_id="2115322359")

    assert not harness.cancelled, "an unlisted chat stopped a run"
    assert not bot.outbox, "an unlisted chat was answered"


async def test_a_stop_after_the_run_finished_does_not_cut_the_report() -> None:
    """The report was already on its way. Cancelling now would cut it in
    half — which is worse than a stop that did nothing."""
    harness = FakeHarness()
    bot = _bot(harness)
    await bot._start_routine("2115322359", "daily-note", "")
    await harness.started.wait()
    draft_id = bot.http.drafts()[0]["draft_id"]

    harness.release.set()
    await asyncio.sleep(0.05)
    assert any("relatório" in text for text in bot.outbox), "the report was not sent"

    await _stop(bot, draft_id)

    assert not harness.cancelled, "a finished run was cancelled"
    assert "já tinha terminado" in bot.outbox[-1]
