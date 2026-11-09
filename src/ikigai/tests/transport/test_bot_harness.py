"""The bot, as the client's door to the agent (ADR-037 D7).

The bot is a client of the api (ADR-037 D6) and it now has a SECOND door: the
harness, which runs the cadences. This file proves that door end to end —
the wire contract, the non-blocking behaviour, and the two ways it may fail
closed.

**Why a real server and not a double.** The client's whole job is to speak
the harness's contract, and the contract is HTTP + JSON. A double of the
client's own methods would pass whether the client were right or wrong — it
would only prove that the bot calls what it thinks it calls. So the double
here is a REAL server on a REAL socket, serving the harness's contract, and
the client talks to it exactly as it talks to the container.

**Why the non-blocking behaviour is a test and not a comment.** A routine
takes minutes. A bot that waited for it would stop answering the phone for
the length of every cadence, and the owner would read that as a dead bot
rather than as a slow routine. The test measures the dispatch: it must
return while the run is still in flight.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from src.bot.harness_client import HarnessClient, HarnessError
from src.bot.main import ROUTINES, Bot, McpClient

#: The repository root. This file lives one level deeper than the suite root
#: (``tests/transport/``), so the root is four parents up.
REPO_ROOT = Path(__file__).resolve().parents[4]

#: The cadences the bot may run — PINNED here, and not read from the bot.
#:
#: The expectation is written out so it cannot move with the defect it
#: exists to catch: a test that read the list from the thing under test
#: would pass whatever the bot declared.
CADENCES = {
    "daily-note",
    "weekly-review",
    "monthly-review",
    "quarterly-plan",
}

#: Every skill the projection publishes — the harness's whitelist, and what
#: the fake server answers when the client asks what the agent can run.
PUBLISHED = {
    "daily-note",
    "monthly-review",
    "quarterly-plan",
    "store-read",
    "store-write",
    "vault-sync",
    "weekly-review",
}

#: The report a routine comes back with — the shape the harness publishes.
REPORT: dict[str, Any] = {
    "ok": True,
    "routine": "daily-note",
    "session_id": "tg-42",
    "text": "A nota do dia foi escrita: nota:nota-do-dia:a1b2c3d4:0123456789abcdef",
    "bytes": 66,
    "events": 22,
    "memory_entry_id": 1,
    "duration_ms": 9446,
}


class _Handler(BaseHTTPRequestHandler):
    """The harness's answers, over HTTP."""

    protocol_version = "HTTP/1.1"

    def log_message(self, *args: Any) -> None:
        """Quiet: the access log is noise in a test."""

    @property
    def harness(self) -> _HarnessServer:
        return self.server.harness  # type: ignore[attr-defined]

    def _reply(self) -> None:
        harness = self.harness
        if harness.delay_s:
            time.sleep(harness.delay_s)
        body = json.dumps(harness.payload_for(self.path)).encode("utf-8")
        self.send_response(harness.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            self.harness.received.append(json.loads(raw or b"{}"))
        except json.JSONDecodeError:
            self.harness.received.append({"__unparsed__": raw.decode("utf-8", "replace")})
        self._reply()

    def do_GET(self) -> None:
        self.harness.gets.append(self.path)
        self._reply()


class _HarnessServer:
    """A real server speaking the harness's contract."""

    def __init__(self) -> None:
        self.received: list[dict[str, Any]] = []
        self.gets: list[str] = []
        self.status = 200
        self.payload: dict[str, Any] = dict(REPORT)
        self.delay_s = 0.0
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server.harness = self  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def payload_for(self, path: str) -> dict[str, Any]:
        """The harness answers each door with its own shape."""
        if path.startswith("/v1/routines"):
            return {"routines": [{"id": name} for name in sorted(PUBLISHED)]}
        if path.startswith("/v1/memory"):
            return {
                "session_id": "tg-42",
                "entries": [
                    {
                        "id": 1,
                        "kind": "routine",
                        "key": "daily-note",
                        "content": "a nota do dia foi escrita",
                        "session": "tg-42",
                        "created_at": "2026-11-08T12:00:00Z",
                    }
                ],
                "events": [],
            }
        return self.payload

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


class _RecordingTelegram:
    """The Telegram side, recorded instead of sent."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        #: The PREVIEWS, kept apart from the messages. A draft is not an
        #: answer: it is the live state of a run that is still going. A
        #: recorder that counted the two together could not tell "the answer
        #: came before the run finished" from "the preview was opened".
        self.drafts: list[dict[str, Any]] = []

    async def post(self, url: str, json: dict[str, Any]) -> None:
        # The parameter is named `json` because httpx names it that, and the
        # bot calls it by keyword.
        if "sendMessageDraft" in url:
            self.drafts.append(json)
            return
        self.sent.append(json)

    async def get(self, url: str, params: dict[str, Any]) -> Any:
        raise AssertionError("the bot must not poll in this test")


class _NoStore(McpClient):
    """A client double that writes nothing — the bot is not testing the store."""

    def __init__(self) -> None:
        super().__init__("http://unused.invalid/mcp")
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        return {}


@pytest.fixture
def harness_server() -> Any:
    server = _HarnessServer()
    try:
        yield server
    finally:
        server.close()


def _bot(harness: HarnessClient | None) -> tuple[Bot, _RecordingTelegram]:
    telegram = _RecordingTelegram()
    bot = Bot("token", _NoStore(), {"42"}, "owner", harness=harness)
    bot._http = telegram  # type: ignore[assignment]
    return bot, telegram


# ---------------------------------------------------------------------------
# What the bot may run
# ---------------------------------------------------------------------------


def test_the_routines_the_bot_exposes_are_the_published_cadences() -> None:
    """The bot may run the cadences, and only the cadences.

    Both ends are held. The set is pinned here, so a routine added to the bot
    without a decision fails. And every routine is checked against the
    published projection on disk, so a skill renamed in the repository fails
    too — the harness's whitelist IS that projection, and a routine the
    projection does not carry does not run there either.
    """
    published = {
        path.parent.name for path in (REPO_ROOT / "specs" / "harness" / "skills").glob("*/SKILL.md")
    }
    assert published, "the published projection is missing — the harness would run nothing"

    assert set(ROUTINES) == CADENCES, (
        f"the bot's routines are not the cadences: {sorted(set(ROUTINES) ^ CADENCES)}"
    )
    assert CADENCES <= published, (
        f"the cadences the bot exposes are not published: {sorted(CADENCES - published)}"
    )
    # The other published skills are the ROLES — what the agent does inside a
    # routine. The owner does not call them by hand.
    assert not (set(ROUTINES) & (published - CADENCES)), (
        "the bot exposes a role as if it were a cadence"
    )


async def test_the_catalogue_lists_every_routine() -> None:
    """A routine the owner cannot see is a routine the owner does not have.

    The command is the published skill id, so the name the owner types is the
    name the agent knows — and there is no second list to drift.
    """
    catalogue = await Bot("token", _NoStore(), {"42"}, "owner")._dispatch("/help", "", "1")

    for routine in ROUTINES:
        assert f"/{routine}" in catalogue, f"/help does not list /{routine}"


# ---------------------------------------------------------------------------
# The wire
# ---------------------------------------------------------------------------


async def test_a_routine_reaches_the_harness_over_http(harness_server: _HarnessServer) -> None:
    """The client's whole job: speak the harness's contract.

    The routine, the session, the chat and the owner's own words travel as
    the harness publishes them, and the answer comes back as the agent's
    report.
    """
    client = HarnessClient(harness_server.url)

    result = await client.run_routine(
        "daily-note",
        session_id="tg:42",
        chat_id="42",
        message="hoje o dia foi assim",
    )

    assert result["text"] == REPORT["text"]
    assert result["memory_entry_id"] == 1

    assert len(harness_server.received) == 1
    sent = harness_server.received[0]
    assert sent["routine"] == "daily-note"
    assert sent["session_id"] == "tg:42"
    assert sent["chat_id"] == "42"
    assert sent["message"] == "hoje o dia foi assim"
    assert sent["timeout_ms"] > 0, "the run was not bounded"


async def test_a_refusal_from_the_harness_is_an_error_with_its_reason(
    harness_server: _HarnessServer,
) -> None:
    """The harness answers a refusal with a body, and the reason is kept.

    A status code alone would tell the owner "something went wrong"; the
    harness says WHICH routine it does not know, and that is the difference
    between a fixable mistake and a mystery.
    """
    harness_server.status = 400
    harness_server.payload = {
        "ok": False,
        "error": "unknown routine: daily-nota",
        "detail": "known routines: daily-note, weekly-review",
    }
    client = HarnessClient(harness_server.url)

    with pytest.raises(HarnessError) as raised:
        await client.run_routine("daily-nota", session_id="tg:42", chat_id="42")

    message = str(raised.value)
    assert "unknown routine" in message
    assert "known routines" in message


async def test_a_closed_door_is_an_error_and_not_a_silence(
    harness_server: _HarnessServer,
) -> None:
    """A harness that is not there is a message, not a hang.

    The client waits for the harness's own ceiling, but a door that is
    closed answers immediately — and the owner hears about it.
    """
    harness_server.close()
    client = HarnessClient(harness_server.url)

    with pytest.raises(HarnessError):
        await client.run_routine("daily-note", session_id="tg:42", chat_id="42")


# ---------------------------------------------------------------------------
# The bot
# ---------------------------------------------------------------------------


async def test_a_routine_command_does_not_block_the_bot(harness_server: _HarnessServer) -> None:
    """The dispatch returns while the run is still in flight.

    A routine takes minutes. A bot that waited for it would stop answering
    the phone for the length of every cadence, and the owner would read that
    as a dead bot rather than as a slow routine. The agent's report lands as
    a SECOND message.
    """
    harness_server.delay_s = 1.5
    harness = HarnessClient(harness_server.url)
    bot, telegram = _bot(harness)

    started = time.monotonic()
    answer = await bot._dispatch("/daily-note", "hoje", "1", "42")
    elapsed = time.monotonic() - started

    assert elapsed < 1.0, f"the bot waited {elapsed:.2f}s for the agent"
    assert answer == "", (
        "the dispatch still had something to say — a message would replace the preview"
    )
    assert telegram.sent == [], "the answer came before the run finished"
    # The PREVIEW is the answer now: it says which routine started, and it
    # carries the Stop button. A message sent here would replace it — and
    # with it the button the owner needs.
    assert telegram.drafts, "the run opened no preview — the owner watches a silent chat"
    assert "daily-note" in telegram.drafts[0]["text"]

    tasks = list(bot._running)
    assert tasks, "the routine did not start"
    await asyncio.gather(*tasks)

    assert len(telegram.sent) == 1, "the owner never got the agent's report"
    report = telegram.sent[0]["text"]
    assert REPORT["text"] in report
    assert "9.4s" in report, "the receipt does not say how long the run took"


async def test_a_routine_is_asked_for_with_the_owner_s_own_words(
    harness_server: _HarnessServer,
) -> None:
    """The chat is the session, and the words travel with the request.

    One chat is one conversation with the agent, and two chats cannot share
    a context — so the session is the chat, and the owner says what he wants
    in the message that asked for it.
    """
    harness = HarnessClient(harness_server.url)
    bot, _ = _bot(harness)

    await bot._dispatch("/daily-note", "hoje fechei o plano", "7", "42")
    await asyncio.gather(*list(bot._running))

    sent = harness_server.received[0]
    assert sent["session_id"] == "tg:42"
    assert sent["chat_id"] == "42"
    assert sent["message"] == "hoje fechei o plano"


async def test_a_failing_routine_is_reported_to_the_owner(
    harness_server: _HarnessServer,
) -> None:
    """A routine that dies in the background is a routine that never happened.

    The owner is told, and told why. A run that failed silently would leave
    the agent's state and the owner's belief about it in different worlds.
    """
    harness_server.status = 502
    harness_server.payload = {
        "ok": False,
        "error": "the routine failed: the model did not answer",
    }
    harness = HarnessClient(harness_server.url)
    bot, telegram = _bot(harness)

    await bot._dispatch("/daily-note", "hoje", "1", "42")
    await asyncio.gather(*list(bot._running))

    assert len(telegram.sent) == 1
    message = telegram.sent[0]["text"]
    assert "falhou" in message
    assert "the model did not answer" in message


async def test_a_bot_without_the_agent_refuses_the_routines() -> None:
    """No door, no routine — and it says so instead of pretending.

    The bot does not fail closed here: it fails closed on the ALLOWLIST,
    which is what decides who may write at all. Without the agent the bot
    still writes, searches and reads.
    """
    bot, telegram = _bot(None)

    answer = await bot._dispatch("/daily-note", "hoje", "1", "42")

    assert "agente" in answer.lower()
    assert not bot._running, "a routine ran with no agent to run it"
    assert telegram.sent == []


async def test_the_memory_command_reads_what_the_agent_remembered(
    harness_server: _HarnessServer,
) -> None:
    """The agent's memory is readable from the phone, and it is the agent's.

    The session key is the raw chat id on both ends — the harness sanitises
    it on the way in and on the way out — so the same key finds the same
    memory.
    """
    harness_server.payload = {
        "session_id": "tg-42",
        "entries": [
            {
                "id": 1,
                "kind": "routine",
                "key": "daily-note",
                "content": "a nota do dia foi escrita",
                "session": "tg-42",
                "created_at": "2026-11-08T12:00:00Z",
            }
        ],
        "events": [],
    }
    harness = HarnessClient(harness_server.url)
    bot, _ = _bot(harness)

    answer = await bot._dispatch("/memoria", "", "1", "42")

    assert "daily-note" in answer
    assert "a nota do dia foi escrita" in answer
    assert harness_server.gets, "the memory was not read"
    assert "session=tg%3A42" in harness_server.gets[0]


# ---------------------------------------------------------------------------
# The handshake
# ---------------------------------------------------------------------------


async def test_the_start_command_says_what_is_connected(
    harness_server: _HarnessServer,
) -> None:
    """`/start` is the greeting, and the greeting is a report.

    The owner asks the bot "are you there" and the answer has to be about
    the SYSTEM, not about the bot's manners: the store answers, the agent
    answers, and the memory answers. A greeting that says "everything is
    fine" while the agent is closed would be the one lie this bot must not
    tell.
    """
    harness = HarnessClient(harness_server.url)
    bot, _ = _bot(harness)

    answer = await bot._dispatch("/start", "", "1", "42")

    assert "store: ok" in answer
    assert f"agente: ok — {len(PUBLISHED)} rotinas" in answer
    assert "memória: 1 entrada" in answer


async def test_the_handshake_reports_a_closed_agent_instead_of_pretending(
    harness_server: _HarnessServer,
) -> None:
    """The agent is down ⇒ the greeting says so, and says why."""
    harness_server.close()
    harness = HarnessClient(harness_server.url)
    bot, _ = _bot(harness)

    answer = await bot._dispatch("/start", "", "1", "42")

    assert "agente: falhou" in answer
    assert "agente: ok" not in answer


async def test_a_bot_without_the_agent_says_so_in_the_greeting() -> None:
    """No door, no agent — and the greeting says that too."""
    bot, _ = _bot(None)

    answer = await bot._dispatch("/start", "", "1", "42")

    assert "agente: sem porta" in answer
    assert "store: ok" in answer


async def test_the_bot_greets_the_owner_when_it_comes_up(
    harness_server: _HarnessServer,
) -> None:
    """The greeting goes out on its own, to the owner, and to nobody else.

    A bot that comes up silently is a bot the owner cannot tell from a dead
    one. The allowlist is the boundary: an unlisted chat gets nothing —
    not even a greeting.
    """
    harness = HarnessClient(harness_server.url)
    telegram = _RecordingTelegram()
    bot = Bot("token", _NoStore(), {"42"}, "owner", harness=harness)
    bot._http = telegram  # type: ignore[assignment]

    await bot._handshake()

    assert len(telegram.sent) == 1
    assert telegram.sent[0]["chat_id"] == "42"
    assert "Ligado" in telegram.sent[0]["text"]


async def test_the_greeting_never_reaches_an_unlisted_chat() -> None:
    """The boundary is the allowlist, and the greeting goes through it."""
    telegram = _RecordingTelegram()
    bot = Bot("token", _NoStore(), {"42"}, "owner", harness=None)
    bot._http = telegram  # type: ignore[assignment]
    bot._allowed = {"42"}

    await bot._handshake()

    assert {message["chat_id"] for message in telegram.sent} == {"42"}
