"""The Telegram bot — the owner-facing client of the canonical service.

ADR-037 D8: a client is a PROJECTION of the DOM, not a fork of it. This bot
therefore:

* speaks MCP to the api — it never opens a database connection (D6);
* writes through ``upsert_artifact`` — the service layer is the only writer
  (D5), and every write carries a revision and an idempotency key;
* reads through ``search_artifacts`` — the store is queried by index, not by
  grepping markdown (D4).

It has TWO transports, and the same interface on both. The MCP call asks the
store a question. The websocket (``src/bot/ws_client.py``) asks the same
questions AND receives what the store changed — the writes made by the vault
ingestion, by another device, by the harness. A bot that only ever learns
about its own writes is a bot that is perpetually behind, so the websocket is
used whenever ``IKIGAI_WS_URL`` names one.

And it has a THIRD door, to the AGENT (ADR-037 D7): the harness
(``src/bot/harness_client.py``) is an external process that runs the
cadences. The bot asks for a routine, waits, and reports what the agent
said — it does not orchestrate. The agent writes through the api like every
other client, so there is still one writer per store. The door is optional:
without ``IKIGAI_HARNESS_URL`` the bot still writes, searches and reads, and
the routines say that the agent is not configured.

Owner-only, and it FAILS CLOSED: if the allowlist is missing or empty, the
bot refuses to start rather than answering anyone who finds the token.

Commands
--------
``/nota <texto>``       write a NOTA (the daily report)
``/sonho <texto>``      write a SONHO (a dream — the top of the pyramid)
``/revisao <texto>``    write a REVISAO (the weekly review)
``/plano <texto>``      write a PLANO (the quarterly plan)
``/onda <texto>``       write an ONDA (a 15-day cycle)
``/fase <texto>``       write a FASE (a phase row of the plan)
``/desc <decisão>``     write a DESC — TWO lines: the decision, then why
``/okr <objetivo>``     write an OKR — TWO lines: the objective, then the KR
``/busca <texto>``      search the store
``/uid <uid>``          read one artifact and its edges
``/memoria``            what the agent remembers about this chat
``/start``              the handshake — what is connected, and what is not
``/help``               the catalogue

And the ROUTINES — the cadences the agent runs, named after the published
skills they invoke:

``/daily-note [texto]``     the agent records the day
``/weekly-review [texto]``  the agent consolidates the week
``/monthly-review [texto]`` the agent reviews the month
``/quarterly-plan [texto]`` the agent plans the quarter

A routine takes minutes, not milliseconds, so the bot answers at once and
delivers the agent's report as a second message. The bot's poll loop never
waits for the agent: a phone that goes silent for the length of a routine is
a phone that looks broken.

The two structured kinds — a decision and an OKR — carry fields of their own,
and the contract will not take them without those fields. They read them from
the message: the first line is the head, the second is what the kind also
needs. A decision without a rationale is not a decision, so the bot asks for
the second line instead of sending a payload the contract would refuse.

Run::

    python -m src.bot.main

Environment
-----------
``IKIGAI_BOT_TOKEN``            the Telegram bot token (never in the repo)
``IKIGAI_MCP_URL``              the api's MCP endpoint
``IKIGAI_WS_URL``               the websocket endpoint (optional; when set, the
                                bot uses it and receives the store's changes)
``IKIGAI_WS_TOKEN``             the token the websocket asks for
``IKIGAI_CLIENT_ID``            the identity written on every write
``IKIGAI_BOT_ALLOWED_CHAT_IDS`` comma-separated owner chat ids (required)
``IKIGAI_HARNESS_URL``          the agent's door (optional; without it the
                                routines are refused)
``IKIGAI_HARNESS_TIMEOUT_S``    the ceiling of a routine, in seconds
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import UTC, datetime, timezone
from typing import Any

import httpx

from src.bot.cadence import Cadence, cadence_from_env
from src.bot.channel import (
    Question,
    answer_buttons,
    parse_question,
    question_keyboard,
    question_text,
)
from src.bot.harness_client import DEFAULT_TIMEOUT_S, HarnessClient
from src.bot.rich import markdown_table, plain_table, report_markdown, rich_payload
from src.bot.router import callback_data, parse_callback, route
from src.bot.ws_client import WebSocketClient
from src.contracts.dom import ArtifactKind, make_uid
from src.contracts.dom_kinds import KIND_MODELS

TELEGRAM_API = "https://api.telegram.org"

#: One row of buttons: (label, verb, argument). The verb is what
#: `parse_callback` gives back, and the argument is what the verb acts on —
#: a routine id, or nothing for a decision that is already in the chat.
Button = tuple[str, str, str]
Keyboard = list[list[Button]]

#: What a handler may answer. Most answer with a string; the ones that offer a
#: decision answer with the string AND the buttons, and `_handle` is the one
#: place that sends either.
Answer = str | tuple[str, Keyboard]

#: The routines the owner may run from the phone, and what each one does.
#:
#: The key IS the published skill id: the harness's whitelist is the
#: published projection (``specs/harness/skills/<id>/SKILL.md``), so the name
#: the owner types is the name the agent knows. A second spelling would be a
#: second list, and a second list drifts.
#:
#: The four cadences are the router's (``specs/harness/router.md`` §3): the
#: daily note, the weekly review, the monthly review and the quarterly plan.
#: The other three published skills — ``store-read``, ``store-write`` and
#: ``vault-sync`` — are the ROLES, not the cadences: they are what the agent
#: does inside a routine, and the owner does not call them by hand.
ROUTINES: dict[str, str] = {
    "daily-note": "corrige o dia — classifica as tarefas com a evidência",
    "weekly-review": "consolida a semana",
    "monthly-review": "revê o mês e as decisões",
    "quarterly-plan": "planeja o trimestre — fases, OKRs e ondas",
}

#: The door to the agent, and the ceiling of a routine.
HARNESS_URL_ENV = "IKIGAI_HARNESS_URL"
HARNESS_TIMEOUT_ENV = "IKIGAI_HARNESS_TIMEOUT_S"

#: The Mini App's public address. It is a URL, not a port: the page is
#: served by this bot and reached through the proxy that owns the
#: certificate, and Telegram will only open an HTTPS address.
MINIAPP_URL_ENV = "IKIGAI_MINIAPP_URL"

#: The port the Mini App's HTTP surface listens on. Zero means the panel is
#: NOT served — the bot without a panel is the bot as it was, and a
#: deployment that does not want the page does not open the door.
MINIAPP_PORT_ENV = "IKIGAI_MINIAPP_PORT"

#: The ceiling of ONE probe of the handshake, in seconds. The greeting has to
#: arrive: an agent that is slow, or down, must produce a line that says so
#: — not a greeting that never comes.
HANDSHAKE_TIMEOUT_S = 10.0

#: How often the bot looks at the agent's log for a question the agent asked.
#: It is a poll, not a push: the harness is a process behind a socket, and a
#: poll is the simplest thing that cannot lose an event. Two seconds is fast
#: enough that the owner does not watch a spinner, and slow enough that the
#: harness is not asked for nothing sixty times a minute.
RUNTIME_POLL_S = 2.0

#: The kinds the bot may write. It is a projection of the owner's day, not
#: an editor of the whole pyramid.
#:
#: The six that came with the pivot are the cadence kinds: what the daily,
#: weekly, monthly and quarterly routines produce. The pi harness runs those
#: routines, but the owner is the one holding the phone at the moment the
#: decision is taken — so the client writes them too, in the same kinds the
#: skills write.
WRITABLE: dict[str, ArtifactKind] = {
    "/nota": ArtifactKind.NOTA,
    "/sonho": ArtifactKind.SONHO,
    "/revisao": ArtifactKind.REVISAO,
    "/plano": ArtifactKind.PLANO,
    "/onda": ArtifactKind.ONDA,
    "/fase": ArtifactKind.FASE,
    "/desc": ArtifactKind.DESC,
    "/okr": ArtifactKind.OKR,
}

#: The kinds whose contract carries fields of their own, and the order those
#: fields appear in the message. The first line is the head; the second is
#: what the kind also needs.
#:
#: ``decision`` and ``rationale`` for a DESC, ``objective`` and
#: ``key_result`` for an OKR. The monthly-review skill says it plainly: a
#: decision without a rationale is not a decision. So the rationale is not
#: optional here even though the model leaves it nullable — the bot asks for
#: it rather than sending a decision with no reason behind it.
HEAD_FIELDS: dict[ArtifactKind, tuple[str, ...]] = {
    ArtifactKind.DESC: ("decision", "rationale"),
    ArtifactKind.OKR: ("objective", "key_result"),
}

#: What the bot asks for when the message is short of what the kind needs.
_MISSING_HEAD: dict[ArtifactKind, str] = {
    ArtifactKind.DESC: (
        "A decisão precisa do porquê.\nDuas linhas: a primeira é a decisão, a segunda é o racional."
    ),
    ArtifactKind.OKR: (
        "O objetivo precisa do key result.\n"
        "Duas linhas: a primeira é o objetivo, a segunda é o key result."
    ),
}

#: The catalogue the owner reads. It is built FROM ``WRITABLE``, so a command
#: that can be written is a command the help lists — and a command that is
#: listed is a command that can be written.
_COMMANDS: dict[str, tuple[str, str]] = {
    "/nota": ("<texto>", "registra a nota do dia"),
    "/sonho": ("<texto>", "registra um sonho"),
    "/revisao": ("<texto>", "registra a revisão da semana"),
    "/plano": ("<texto>", "registra o plano do trimestre"),
    "/onda": ("<texto>", "registra a onda"),
    "/fase": ("<texto>", "registra a fase do plano"),
    "/desc": ("<decisão>", "registra a decisão e o porquê — duas linhas"),
    "/okr": ("<objetivo>", "registra o objetivo e o key result — duas linhas"),
}

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def _slugify(text: str, limit: int = 60) -> str:
    """Lowercase, ascii-folded, dash-separated. The UEID slug segment is strict."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = _SLUG_STRIP.sub("-", folded.lower()).strip("-")
    if len(slug) < 2:
        # The UEID slug segment wants a character at both ends, so a one-letter
        # title would be rejected at the boundary instead of being written.
        slug = (slug or "nota").ljust(2, "x")
    return slug[:limit].strip("-")


def _hash8(text: str) -> str:
    """Eight hex chars — the width the UEID hash segments accept."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def _artifact_payload(
    kind: ArtifactKind,
    title: str,
    body: str,
    uuid_short: str,
    head: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the Artifact the transport expects.

    The uid is derived from the OPERATION, not from the clock: the uuid half
    comes from the Telegram message id and the hash half from the body. Two
    sends of the same message are the same intent, which is what makes the
    write idempotent (ADR-037 D5).

    `head` carries the fields the kind has of its own — the decision and its
    rationale, the objective and its key result. They are part of the body
    too: the body is the prose, the typed fields are the structured reading
    of the same prose.
    """
    now = datetime.now(UTC).isoformat()
    artifact: dict[str, Any] = {
        "uid": str(make_uid(kind, _slugify(title), uuid_short, _hash8(body))),
        "kind": kind.value,
        "title": title,
        "body": body,
        "body_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "created_at": now,
        "updated_at": now,
    }
    if head:
        artifact.update(head)
    return artifact


def _write_arguments(
    kind: ArtifactKind,
    title: str,
    body: str,
    uuid_short: str,
    client_id: str,
    head: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The arguments for `upsert_artifact` — ONE place, so the client and the
    transport cannot drift apart.

    These names are the wire contract: the transport's tool takes exactly
    these four arguments, and the drift test compares the two. They disagreed
    once — the transport wanted a nested `req` envelope and the bot sent the
    fields flat — and every write from Telegram failed with a validation
    error that nothing in the suite noticed.
    """
    artifact = _artifact_payload(kind, title, body, uuid_short, head)
    return {
        "artifact": artifact,
        "expected_revision": None,
        "idempotency_key": f"{artifact['uid']}:{artifact['body_hash']}",
        "client_id": client_id,
    }


def _head_fields(
    kind: ArtifactKind,
    argument: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """The kind's own fields, taken from the lines of the message.

    Returns ``(fields, complaint)``. A complaint means the message was short
    of what the kind needs, and the bot asks for it instead of sending a
    payload the contract would refuse. A kind with no fields of its own
    returns ``(None, None)``.
    """
    fields = HEAD_FIELDS.get(kind)
    if fields is None:
        return None, None
    lines = argument.splitlines()
    if len(lines) < len(fields):
        return None, _MISSING_HEAD[kind]
    return dict(zip(fields, lines[: len(fields)], strict=True)), None


def _validate_artifact(kind: ArtifactKind, artifact: dict[str, Any]) -> None:
    """The payload must satisfy the kind's OWN model before it leaves the bot.

    The api would refuse it anyway — but the refusal arrives as a transport
    error, after the message was typed. Validating here names the missing
    field at the moment the owner is reading the answer, and it is the same
    model the transport validates against, so the two cannot drift.
    """
    KIND_MODELS[kind].model_validate(artifact)


class McpClient:
    """A thin MCP client over streamable HTTP.

    The api is the only thing this process talks to. If the api is down, the
    bot says so — it does not fall back to the database, because a fallback
    would be a second writer (ADR-037 D5).
    """

    def __init__(self, url: str) -> None:
        self._url = url

    async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        from mcp import ClientSession

        try:
            from mcp.client.streamable_http import streamable_http_client
        except ImportError:  # pragma: no cover — mcp < 1.3 only had the old spelling
            # mypy: the two spellings carry different signatures, so it calls
            # the alias an incompatible import. It is the same client, and the
            # lock pins mcp 1.30 — the fallback is for the older spelling only.
            from mcp.client.streamable_http import (  # type: ignore[assignment]
                streamablehttp_client as streamable_http_client,
            )

        async with streamable_http_client(self._url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
        if getattr(result, "isError", False):
            raise RuntimeError(f"{tool} failed: {result.content}")
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            return structured
        for block in result.content:
            text = getattr(block, "text", None)
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
        return None


class Bot:
    """The Telegram loop. One command per message, one answer per command.

    A routine is the exception: it is one command and TWO answers — "it
    started" now, and the agent's report when the agent is done.
    """

    def __init__(
        self,
        token: str,
        client: Any,
        allowed: set[str],
        client_id: str,
        events: Any | None = None,
        harness: HarnessClient | None = None,
        cadence: Cadence | None = None,
    ) -> None:
        self._token = token
        self._client = client
        self._allowed = allowed
        self._client_id = client_id
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=60.0))
        self._offset = 0
        # The stream of pushed events, when the transport carries them.
        self._events = events
        # The uids this bot just wrote. A write is announced by the store
        # like any other, and the owner does not need to be told about the
        # note they just dictated.
        self._own_writes: set[str] = set()
        # The draft each chat has open, and the revision it was last saved at.
        # It is a CACHE of the store, never the truth: `_list_drafts` reads the
        # store, because a draft that only exists in this dictionary dies with
        # the process — which is the thing drafts exist to avoid.
        self._open: dict[str, dict[str, Any]] = {}
        # The agent's door. Without it the bot still writes, searches and
        # reads — it just cannot run a routine, and it says so.
        self._harness = harness
        # The routines in flight. The task is HELD on purpose: a task nobody
        # references may be collected mid-run, and the owner's answer would
        # never arrive.
        self._running: set[asyncio.Task[None]] = set()
        # The question each chat is ANSWERING: the id of the question the
        # agent is suspended on, waiting for prose.
        #
        # It is a CACHE, and it is a cache of the RUNTIME's state, not of
        # the store's: the question itself lives in the harness (so a restart
        # does not lose it), and this dictionary only says "the next message
        # in this chat is the answer". The harness refuses an answer to a
        # question that is not open, so a stale entry here costs one
        # complaint, not a wrong answer.
        self._awaiting: dict[str, str] = {}
        # The event cursor of each chat's session: what the bot has already
        # seen of the agent's log. The same shape as the store's change feed
        # (ADR-039) — the client says what it has and gets what it does not.
        self._cursors: dict[str, int] = {}
        # The clock. `None` is a bot that runs exactly as it did before the
        # cadence existed: a deployment that does not set a time is not a
        # deployment that wanted one.
        self._cadence = cadence

    def _client_key(self, chat_id: str) -> str:
        """The routing key of a chat: `tg:<chat_id>`.

        It is the key the harness routes on AND the key the session is
        named after, which is why it is written in ONE place: two spellings
        of the same key is one key that finds nothing.
        """
        return f"tg:{chat_id}"

    async def _send(
        self,
        chat_id: str,
        text: str,
        buttons: Keyboard | None = None,
        web_app: tuple[str, str] | None = None,
    ) -> None:
        """One message, optionally with a decision under it.

        `reply_markup` is what makes the chat a UI instead of a prompt: the
        button carries the verb, and the owner does not type `/guardar` to
        agree with what they just read.

        `web_app` is the Mini App's door: a button that opens a page INSIDE
        the chat, with Telegram's own identity attached. It is a different
        kind of button because it is a different kind of thing — a surface,
        not a verb — and Telegram's payload for the two is not the same.
        """
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text[:4000]}
        rows: list[list[dict[str, Any]]] = []
        if buttons:
            rows = [
                [
                    {"text": label, "callback_data": callback_data(verb, argument)}
                    for label, verb, argument in row
                ]
                for row in buttons
            ]
        if web_app:
            label, url = web_app
            rows.append([{"text": label, "web_app": {"url": url}}])
        if rows:
            payload["reply_markup"] = {"inline_keyboard": rows}
        await self._http.post(f"{TELEGRAM_API}/bot{self._token}/sendMessage", json=payload)

    async def _answer_callback(self, callback_id: str, text: str = "") -> None:
        """Stop the spinner.

        An unanswered callback query spins on the owner's screen until it
        times out, whatever the bot is doing — so this is called on every
        path, including the one that refuses the button.
        """
        payload: dict[str, Any] = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text[:200]
        await self._http.post(f"{TELEGRAM_API}/bot{self._token}/answerCallbackQuery", json=payload)

    async def _handle(self, message: dict[str, Any]) -> None:
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if chat_id not in self._allowed:
            # Fail closed and stay silent: an unlisted chat gets no answer and
            # no trace of what this bot can do.
            return

        text = str(message.get("text") or "")
        message_id = str(message.get("message_id", "0"))

        try:
            answer: Answer
            if text.startswith("/"):
                command, _, argument = text.partition(" ")
                if command == "/painel":
                    # The Mini App is a SURFACE, not an answer: it is sent on
                    # its own, with its own button, and the chat carries on.
                    await self._send_panel(chat_id)
                    return
                answer = await self._dispatch(command, argument.strip(), message_id, chat_id)
            else:
                # A message that is NOT a command is prose, and prose belongs to
                # the draft that is open. The command path splits on the first
                # space, which would throw the first word of the paragraph away.
                answer = await self._append(chat_id, text.strip(), message_id)
        except Exception as exc:  # the bot reports, it does not crash
            answer = f"Não consegui completar isso: {exc}"

        if isinstance(answer, tuple):
            body, buttons = answer
        else:
            body, buttons = answer, None
        # Two positional arguments when there is no decision to offer: a
        # transport that only knows `(chat_id, text)` keeps working, and the
        # signature grows only where it has to.
        if buttons:
            await self._send(chat_id, body, buttons)
        else:
            await self._send(chat_id, body)

    async def _dispatch(
        self,
        command: str,
        argument: str,
        message_id: str,
        chat_id: str = "",
    ) -> Answer:
        """Route one command to its answer.

        ``chat_id`` is where the answer goes. The deterministic commands do
        not need it — they answer in the message they are handling. The
        routines do: the agent's answer arrives later, in another message, to
        the chat that asked for it.
        """
        if command == "/help":
            return _catalogue()

        if command == "/start":
            # The greeting, on demand: the same handshake the bot sends when
            # it comes up — what is connected, and what is not.
            return await self._handshake_text(chat_id)

        routine = command[1:] if command.startswith("/") else ""
        if routine in ROUTINES:
            return await self._start_routine(chat_id, routine, argument)

        if command == "/memoria":
            return await self._memory(chat_id)

        if command == "/rascunho":
            return await self._start_draft(chat_id, argument)

        if command == "/guardar":
            return await self._commit_draft(chat_id, message_id)

        if command == "/descartar":
            return await self._discard_draft(chat_id)

        if command == "/rascunhos":
            return await self._list_drafts()

        if command in WRITABLE:
            if not argument:
                return "Diz o que é, em uma linha."
            kind = WRITABLE[command]
            head, complaint = _head_fields(kind, argument)
            if complaint is not None:
                return complaint
            title = argument.splitlines()[0][:120]
            body = argument
            arguments = _write_arguments(
                kind, title, body, _hash8(message_id), self._client_id, head
            )
            _validate_artifact(kind, arguments["artifact"])
            await self._client.call("upsert_artifact", arguments)
            uid = str(arguments["artifact"]["uid"])
            self._own_writes.add(uid)
            return f"Registado ({kind.value}).\n{uid}"

        if command == "/busca":
            if not argument:
                return "O que procuro?"
            result = await self._client.call(
                "search_artifacts",
                {"query": {"text": argument, "limit": 10}},
            )
            return _render_search(result)

        if command == "/uid":
            if not argument:
                return "Qual o uid?"
            bundle = await self._client.call("get_artifact", {"uid": argument, "depth": 1})
            return _render_bundle(bundle)

        return "Não conheço esse comando. /help"

    # -- the draft flow ----------------------------------------------------
    #
    # A paragraph is not a message. The owner thinks in several sends, and
    # before this the second send of the same thought was either a new artifact
    # or "Não conheço esse comando". The draft is the state a conversation
    # needs: prose in progress, in the store, so it survives the bot restarting
    # or the phone losing signal (ADR-040).
    #
    # The draft is reached with `client.draft(...)`, which exists only on the
    # websocket client. A bot on the MCP transport has no drafts and says so
    # rather than pretending the command worked.

    def _draft_key(self, chat_id: str) -> str:
        """One open draft per chat. Two chats composing are two drafts."""
        return f"telegram-{chat_id or 'ninguem'}"

    def _speaks_drafts(self) -> bool:
        return callable(getattr(self._client, "draft", None))

    async def _read_draft(self, chat_id: str) -> dict[str, Any] | None:
        """The open draft, or None when there is none.

        A missing draft is not an error in a conversation — it is the answer
        to "what was I writing?" when the answer is "nothing". The transport
        reports it as `not_found`, which is right for a caller that asked for
        a specific thing, and wrong for a bot that is asking whether one
        exists.
        """
        try:
            found = await self._client.draft(
                "get", client_id=self._client_id, draft_id=self._draft_key(chat_id)
            )
        except RuntimeError as exc:
            if "not_found" in str(exc):
                self._open.pop(chat_id, None)
                return None
            raise
        return found if isinstance(found, dict) else None

    async def _start_draft(self, chat_id: str, argument: str) -> Answer:
        if not self._speaks_drafts():
            return (
                "Sem rascunhos neste transporte: eles viajam pelo websocket.\n"
                "Configure IKIGAI_WS_URL e eu volto a guardar o que fica a meio."
            )
        if not argument:
            return await self._show_draft(chat_id)

        kinds = {command.lstrip("/"): kind for command, kind in WRITABLE.items()}
        kind = kinds.get(argument.strip().lower())
        if kind is None:
            return "Que tipo? " + ", ".join(sorted(kinds))

        # Resuming an open draft keeps what was already written; starting one
        # over it would silently throw the paragraph away. After a restart the
        # bot has no revision in memory, so the save comes back as a CONFLICT —
        # and the conflict is the correct answer, not a failure: it means
        # "there is already a draft here". It is reread and resumed.
        key = self._draft_key(chat_id)
        try:
            answer = await self._client.draft(
                "save",
                client_id=self._client_id,
                draft_id=key,
                kind=kind.value,
                title="",
                body="",
                expected_revision=self._open.get(chat_id, {}).get("revision"),
            )
        except RuntimeError as exc:
            if "conflict" not in str(exc):
                raise
            current = await self._read_draft(chat_id)
            if current is None:  # pragma: no cover — a conflict means it exists
                raise
            self._open[chat_id] = {
                "kind": str(current.get("kind")),
                "revision": int(current["revision"]),
            }
            return (
                f"Já havia um rascunho de {current.get('kind')} aberto — retomei-o.\n"
                "Manda o texto. /rascunho sozinho mostra o que está lá; /guardar fecha."
            )
        self._open[chat_id] = {"kind": kind.value, "revision": int(answer["revision"])}
        return (
            f"Rascunho de {kind.value} aberto.\n"
            "Manda o texto em quantas mensagens quiseres. /guardar fecha, /descartar deita fora.",
            [[("Guardar", "draft.guardar", ""), ("Descartar", "draft.descartar", "")]],
        )

    async def _append(self, chat_id: str, text: str, message_id: str) -> Answer:
        """A message that is not a command: it is prose, and it grows the draft."""
        if not text:
            return ""
        # A QUESTION the agent asked takes the message first. While the agent
        # is suspended on it, the owner's prose IS the answer — and a draft
        # that swallowed it would be a draft holding a reply to the agent.
        awaiting = self._awaiting.get(chat_id)
        if awaiting:
            return await self._deliver_answer(chat_id, awaiting, text)
        if not self._speaks_drafts():
            return "Não conheço esse comando. /help"
        state = self._open.get(chat_id)

        current = await self._read_draft(chat_id)
        if current is None:
            # No draft is open, so this sentence is not prose waiting to be
            # kept — it is either a routine the owner named in their own words
            # or an instruction the bot does not understand.
            return await self._route_or_ask(chat_id, text)
        if state is None:
            # The cache is cold — this process may have just started. The STORE
            # is the truth, so a paragraph typed after a restart joins the draft
            # that is still open instead of being refused. A conversation that
            # has to be reopened by hand after every restart loses the sentence
            # in between.
            state = {"kind": str(current.get("kind"))}
            self._open[chat_id] = state
        body = str(current.get("body") or "")
        grown = f"{body}\n{text}".strip() if body else text
        answer = await self._client.draft(
            "save",
            client_id=self._client_id,
            draft_id=self._draft_key(chat_id),
            kind=state["kind"],
            title=grown.splitlines()[0][:120],
            body=grown,
            expected_revision=int(current["revision"]),
        )
        self._open[chat_id] = {"kind": state["kind"], "revision": int(answer["revision"])}
        lines = len(grown.splitlines())
        return f"Anotado. {lines} linha(s) no rascunho. /guardar quando estiver."

    async def _route_or_ask(self, chat_id: str, text: str) -> Answer:
        """A sentence with no draft open: a routine, or a question back.

        The deterministic table answers first, because it is the half that
        cannot invent a routine id — and the harness refuses an id it does not
        know, so a confident guess is a 400 in the owner's face.

        When the table abstains, the answer is a question with the four
        routines as buttons. That is strictly better than the old answer
        ("there is no open draft"), which was true and described a feature the
        owner was not using.
        """
        routed = route(text, ROUTINES)
        if routed is not None:
            return await self._start_routine(chat_id, routed.routine, routed.slots.get("when", ""))

        rows: Keyboard = [[(f"/{routine}", "run", routine)] for routine in ROUTINES]
        return (
            "Não há rascunho aberto, e não percebi se é uma rotina.\n"
            "Escolhe uma, ou começa um rascunho com /rascunho <tipo>.",
            rows,
        )

    async def _on_callback(self, callback: dict[str, Any]) -> None:
        """A button was pressed. Answer it, then do what it says.

        Every path answers the callback query: an unanswered one spins on the
        owner's screen for the whole timeout, and a spinner is the client
        telling the owner the bot is thinking when it is not.
        """
        callback_id = str(callback.get("id", ""))
        message = callback.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        message_id = str(message.get("message_id", "0"))
        parsed = parse_callback(str(callback.get("data") or ""))

        if parsed is None:
            await self._answer_callback(callback_id, "Não conheço esse botão.")
            return
        if chat_id not in self._allowed:
            # Fail closed, like every other door: an unlisted chat learns
            # nothing about what the button would have done.
            await self._answer_callback(callback_id)
            return

        verb, argument = parsed
        text: Answer
        try:
            if verb == "draft.guardar":
                text = await self._commit_draft(chat_id, message_id)
            elif verb == "draft.descartar":
                text = await self._discard_draft(chat_id)
            elif verb == "run":
                await self._answer_callback(callback_id)
                await self._send(chat_id, await self._start_routine(chat_id, argument, ""))
                return
            elif verb.startswith("ask."):
                # The agent asked something, and the owner pressed a button.
                text = await self._answer_question(chat_id, verb, argument)
            else:
                text = "Não conheço esse botão."
        except Exception as exc:  # the bot reports, it does not crash
            text = f"Não consegui completar isso: {exc}"

        await self._answer_callback(callback_id)
        if isinstance(text, tuple):
            body, buttons = text
            await self._send(chat_id, body, buttons)
        else:
            await self._send(chat_id, text)

    # -- the questions the agent asked --------------------------------------
    #
    # The agent, in the middle of a turn, calls `ask` and WAITS. This is the
    # client's half of that wait: the question is drawn as buttons, the
    # owner's answer is carried back to the runtime, and the agent's call
    # returns with it.
    #
    # The question lives in the RUNTIME, not here. That is the whole reason
    # this works when the bot restarts: the agent is suspended on a question
    # the harness holds, and the bot is only the surface it is shown on.

    async def _answer_question(self, chat_id: str, verb: str, argument: str) -> str:
        """The owner pressed a button of a question the agent asked."""
        harness = self._harness
        if harness is None:
            return "O agente não está configurado neste bot (IKIGAI_HARNESS_URL)."
        parsed = answer_buttons(verb, argument)
        if parsed is None:
            return "Não conheço esse botão."
        question_id, choice = parsed
        if choice == "#type":
            # The answer is prose: the button does not carry it, it ARMS the
            # chat, and the next message the owner writes IS the answer.
            self._awaiting[chat_id] = question_id
            return (
                "Escreve a resposta — a próxima mensagem é a resposta ao agente.\n"
                "O agente está à espera dela."
            )
        try:
            await harness.answer(question_id, option_index=int(choice.lstrip("#")))
        except Exception as exc:
            return f"Não consegui entregar a resposta: {exc}"
        self._awaiting.pop(chat_id, None)
        return "Resposta entregue. O agente continua."

    async def _deliver_answer(self, chat_id: str, question_id: str, text: str) -> str:
        """The owner TYPED the answer to a question the agent asked."""
        harness = self._harness
        if harness is None:
            return "O agente não está configurado neste bot (IKIGAI_HARNESS_URL)."
        try:
            await harness.answer(question_id, value=text)
        except Exception as exc:
            # The question may have expired while the owner was writing. The
            # arming is dropped either way: keeping it would swallow the
            # NEXT message into a question nobody is waiting for.
            self._awaiting.pop(chat_id, None)
            return f"Não consegui entregar a resposta: {exc}"
        self._awaiting.pop(chat_id, None)
        return "Resposta entregue. O agente continua."

    async def _runtime_loop(self) -> None:
        """Watch the agent's own log, and draw what it asks.

        The questions arrive as events on the session's log — the same
        forward feed the store has (ADR-039), and the same cursor. The bot
        polls it: the harness is a process behind a socket, and a poll is
        the simplest thing that cannot lose an event.
        """
        if self._harness is None:
            return
        while True:
            for chat_id in list(self._allowed):
                try:
                    await self._drain_runtime(chat_id)
                except Exception as exc:  # a feed failure is not fatal
                    print(f"runtime feed failed: {exc}", file=sys.stderr)
            await asyncio.sleep(RUNTIME_POLL_S)

    async def _drain_runtime(self, chat_id: str) -> None:
        """Read what the agent did since the last time, and draw it."""
        harness = self._harness
        if harness is None:
            return
        since = self._cursors.get(chat_id, 0)
        page = await harness.events(self._client_key(chat_id), since=since)
        events = page.get("events") or []
        tip = int(page.get("tip") or 0)
        if events:
            self._cursors[chat_id] = tip or since
        for event in events:
            if event.get("kind") != "question.asked":
                continue
            question = parse_question(event.get("payload") or {})
            if question is None:
                continue
            # A question the owner already answered is not a question any
            # more: the runtime says so, and the bot does not re-ask it.
            if await self._already_answered(question):
                continue
            await self._send(chat_id, question_text(question), question_keyboard(question))

    async def _already_answered(self, question: Question) -> bool:
        """Has this question already been answered (or has it expired)?

        The runtime is the truth: it holds the question, and it says what
        happened to it. The bot asks, because a question that was answered
        must not be drawn again — a second copy of the same question is the
        client pretending not to have listened.
        """
        harness = self._harness
        if harness is None:
            return False
        try:
            state = await harness.question(question.id)
        except Exception:
            # The runtime did not answer: draw the question rather than hide
            # it. A question that is hidden is a question nobody can answer.
            return False
        return str(state.get("state") or "") != "pending"

    async def _send_panel(self, chat_id: str) -> None:
        """Open the Mini App: the session's panel, inside the chat.

        The URL is the deployment's: the panel is served by the bot itself
        (it holds the token that authenticates the page), behind the proxy
        that owns the certificate. The button opens it INSIDE the chat, with
        Telegram's identity attached — which is what makes the page able to
        prove who is asking.
        """
        url = (os.environ.get(MINIAPP_URL_ENV) or "").strip()
        if not url:
            await self._send(
                chat_id,
                "O painel não está configurado neste bot (IKIGAI_MINIAPP_URL).",
            )
            return
        await self._send(
            chat_id,
            "O painel da sessão: a rotina em curso, as perguntas à espera e o que o agente fez.",
            web_app=("📊 Abrir painel", url),
        )

    async def _show_draft(self, chat_id: str) -> str:
        draft = await self._read_draft(chat_id)
        if draft is None:
            return "Nenhum rascunho aberto."
        body = str(draft.get("body") or "")
        if not body:
            return f"Rascunho de {draft.get('kind')} vazio. Manda o texto."
        return f"{draft.get('kind')} · rev {draft.get('revision')}\n\n{body}"

    async def _commit_draft(self, chat_id: str, message_id: str) -> str:
        """Close the draft as an artifact, through the SAME write path as always.

        The draft never commits itself: it is state. Turning it into an
        artifact is `upsert_artifact`, with its own envelope and its own
        revision guard — a draft that committed on its own would be a second
        writer of the DOM wearing the draft's name.
        """
        if not self._speaks_drafts():
            return "Sem rascunhos neste transporte."
        draft = await self._read_draft(chat_id)
        if draft is None:
            return "Nenhum rascunho para guardar."
        body = str(draft.get("body") or "").strip()
        if not body:
            return "O rascunho está vazio — não há o que guardar."

        kind = ArtifactKind(str(draft.get("kind")))
        head, complaint = _head_fields(kind, body)
        if complaint is not None:
            return complaint
        title = body.splitlines()[0][:120]
        arguments = _write_arguments(
            kind,
            title,
            body,
            _hash8(f"{self._draft_key(chat_id)}:{message_id}"),
            self._client_id,
            head,
        )
        _validate_artifact(kind, arguments["artifact"])
        await self._client.call("upsert_artifact", arguments)
        uid = str(arguments["artifact"]["uid"])
        self._own_writes.add(uid)
        try:
            await self._client.draft(
                "discard",
                client_id=self._client_id,
                draft_id=self._draft_key(chat_id),
                expected_revision=int(draft["revision"]),
            )
        except RuntimeError as exc:
            if "conflict" not in str(exc):
                raise
            # The write LANDED. Only the CLOSE was refused, because the draft
            # moved under the bot — another session edited it between the read
            # and the discard. The guard is right to refuse it: discarding that
            # draft would throw the other session's edit away.
            #
            # Saying "I could not do it" would be a lie about the store — the
            # artifact IS there. And saying nothing about the draft would
            # leave it open, swallowing the next paragraph the owner writes.
            self._open.pop(chat_id, None)
            return (
                f"Guardado ({kind.value}), mas o rascunho ficou aberto — "
                f"outra sessão mudou-o entretanto.\n{uid}"
            )
        self._open.pop(chat_id, None)
        return f"Guardado ({kind.value}).\n{uid}"

    async def _discard_draft(self, chat_id: str) -> str:
        if not self._speaks_drafts():
            return "Sem rascunhos neste transporte."
        draft = await self._read_draft(chat_id)
        if draft is None:
            return "Nenhum rascunho para descartar."
        await self._client.draft(
            "discard",
            client_id=self._client_id,
            draft_id=self._draft_key(chat_id),
            expected_revision=int(draft["revision"]),
        )
        self._open.pop(chat_id, None)
        return "Descartado."

    async def _list_drafts(self) -> str:
        """What was left half-written — the answer after a restart.

        It reads the STORE and not the memory on purpose: a draft that only
        exists in this process's dictionary is a draft that dies with the
        process, which is the thing drafts exist to avoid.
        """
        if not self._speaks_drafts():
            return "Sem rascunhos neste transporte."
        answer = await self._client.draft("list", client_id=self._client_id)
        drafts = (answer or {}).get("drafts") or []
        if not drafts:
            return "Nenhum rascunho aberto."
        lines = ["Rascunhos abertos:"]
        for item in drafts:
            body = str(item.get("body") or "")
            first = body.splitlines()[0][:60] if body else "(vazio)"
            lines.append(f"• {item.get('kind')} · rev {item.get('revision')} — {first}")
        return "\n".join(lines)

    async def _handshake(self) -> None:
        """Greet the owner, and say what is connected.

        A bot that comes up silently is a bot the owner cannot tell from a
        dead one. So the FIRST thing it says is what it can reach — the
        store, the agent, the agent's memory — and it says it only to the
        allowed chats: the allowlist is the boundary, and this message goes
        through it like every other one.

        It runs BESIDE the poll loop, not in front of it: a greeting that
        waits for a slow agent must never stop the bot from answering.
        """
        for chat_id in self._allowed:
            try:
                await self._send(chat_id, await self._handshake_text(chat_id))
            except Exception as exc:  # a greeting that fails is not a crash
                print(f"handshake failed: {exc}", file=sys.stderr)

    async def _handshake_text(self, chat_id: str) -> str:
        """The handshake: the store, the agent, and the agent's memory.

        Each probe is BOUNDED, and each failure is REPORTED rather than
        hidden: a greeting that says "everything is fine" while the agent is
        closed would be the one lie this bot must not tell.
        """
        lines = ["🔌 Ligado."]

        started = time.monotonic()
        try:
            await self._client.call("search_artifacts", {"query": {"limit": 1}})
            elapsed = int((time.monotonic() - started) * 1000)
            lines.append(f"• store: ok ({elapsed} ms)")
        except Exception as exc:
            lines.append(f"• store: falhou — {exc}")

        harness = self._harness
        if harness is None:
            lines.append("• agente: sem porta (IKIGAI_HARNESS_URL)")
        else:
            try:
                routines = await harness.routines(timeout_s=HANDSHAKE_TIMEOUT_S)
                lines.append(f"• agente: ok — {len(routines)} rotinas")
            except Exception as exc:
                lines.append(f"• agente: falhou — {exc}")
            if chat_id:
                try:
                    memory = await harness.memory(f"tg:{chat_id}", timeout_s=HANDSHAKE_TIMEOUT_S)
                    entries = len(memory.get("entries") or [])
                    lines.append(f"• memória: {entries} entrada(s) nesta conversa")
                except Exception as exc:
                    lines.append(f"• memória: falhou — {exc}")

        lines.append("Comandos: /help")
        return "\n".join(lines)

    async def _start_routine(self, chat_id: str, routine: str, argument: str) -> str:
        """Ask the agent to run a routine, and answer NOW.

        A routine is the agent's work — it reads the store, classifies, writes
        and reports — and it takes minutes, not milliseconds. The bot's poll
        loop must not wait for it, or the phone goes silent for the whole run
        and the owner cannot tell a slow routine from a dead bot. So the
        routine runs in its own task and the report lands as a second message.
        """
        if self._harness is None:
            return "O agente não está configurado neste bot (IKIGAI_HARNESS_URL)."
        if not chat_id:
            return "Não sei a quem devolver a rotina."

        task = asyncio.create_task(self._run_routine(chat_id, routine, argument))
        self._running.add(task)
        task.add_done_callback(self._running.discard)
        return f"A rotina {routine} começou. Aviso quando terminar."

    async def _run_routine(self, chat_id: str, routine: str, argument: str) -> None:
        """Run the routine and deliver the agent's report to the chat.

        The session is the chat: one Telegram chat is one conversation with
        the agent, and two chats cannot share a context. The key is the raw
        chat id — the harness sanitises it on the way in and on the way out,
        so the same raw key finds the same memory.
        """
        harness = self._harness
        if harness is None:
            return
        try:
            result = await harness.run_routine(
                routine,
                session_id=self._client_key(chat_id),
                chat_id=chat_id,
                message=argument,
                # The ROUTING key: the harness decides which agentic runtime
                # answers this client. It is sent apart from the session
                # because the two are different things — the session is the
                # conversation, the client is the door.
                client=self._client_key(chat_id),
            )
        except Exception as exc:
            # A routine that dies in the background is a routine that never
            # happened. The owner is told WHY.
            await self._send(chat_id, f"A rotina {routine} falhou: {exc}")
            return
        await self._send(chat_id, _render_routine(routine, result))

    async def _cadence_loop(self) -> None:
        """Sleep until the clock says it is time, run, and schedule again.

        The wait is recomputed from the wall clock on every pass rather than
        decremented, so a machine that suspends for an hour does not fire at
        the wrong hour — and a restart needs no state to recover, because the
        next occurrence is a function of the current time.

        A cadence that dies is a cadence that never happened, so the failure
        is reported to the chat that was supposed to receive the report.
        """
        cadence = self._cadence
        if cadence is None:
            return

        while True:
            now = datetime.now(UTC)
            target = cadence.next_run(now)
            wait = (target - now).total_seconds()
            print(
                f"cadence: {cadence.routine} in {wait / 3600:.1f}h (at {target.isoformat()})",
                file=sys.stderr,
            )
            await asyncio.sleep(max(wait, 1.0))
            try:
                await self._run_cadence(cadence)
            except Exception as exc:  # a nightly failure must not be silent
                print(f"cadence failed: {exc}", file=sys.stderr)
                await self._send(cadence.chat_id, f"A rotina {cadence.routine} falhou: {exc}")

    async def _run_cadence(self, cadence: Cadence) -> None:
        """Run the routine, then send what it produced as a rich message."""
        harness = self._harness
        if harness is None:
            # No agent, no cadence. Repeating that every night would be noise
            # about a configuration the handshake already reports.
            return

        result = await harness.run_routine(
            cadence.routine,
            session_id=f"tg:{cadence.chat_id}",
            chat_id=cadence.chat_id,
            message="",
        )

        zone = cadence.zone or timezone(cadence.offset)
        day = datetime.now(UTC).astimezone(zone).strftime("%Y-%m-%d")
        rows = await self._touched_today(cadence)
        headers = ("Tipo", "Título", "Hora")

        title = f"{cadence.routine} — {day}"
        body = str(result.get("text") or "").strip()
        duration = result.get("duration_ms")
        footer = f"{len(rows)} artefato(s) hoje"
        if isinstance(duration, int):
            footer = f"{footer} · {duration / 1000:.1f}s"

        markdown = report_markdown(
            title, markdown_table(headers, rows, ("left", "left", "right")), body, footer
        )
        fallback = "\n\n".join(
            block for block in (title, plain_table(headers, rows), body) if block
        )
        await self._send_rich(cadence.chat_id, markdown, fallback)

    async def _touched_today(self, cadence: Cadence) -> list[tuple[str, str, str]]:
        """What the store says was written today, newest first.

        The date filter is CLIENT-side on purpose: `SearchQuery` has no
        `since`, and the structured search already orders by `updated_at`
        descending — so the newest rows are the ones a day can contain, and a
        day that wrote more than the limit reports what it asked for.

        A store that does not answer is not a cadence that fails: the report
        the agent wrote is still worth sending.
        """
        try:
            result = await self._client.call("search_artifacts", {"query": {"limit": 20}})
        except Exception as exc:
            print(f"cadence: the store did not answer ({exc})", file=sys.stderr)
            return []

        items = result.get("artifacts") if isinstance(result, dict) else None
        zone = cadence.zone or timezone(cadence.offset)
        today = datetime.now(UTC).astimezone(zone).date()

        rows: list[tuple[str, str, str]] = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            stamp = str(item.get("updated_at") or "")
            try:
                when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except ValueError:
                continue
            local = when.astimezone(zone)
            if local.date() != today:
                continue
            rows.append(
                (
                    str(item.get("kind") or "?"),
                    str(item.get("title") or item.get("uid") or "?"),
                    local.strftime("%H:%M"),
                )
            )
        return rows

    async def _send_rich(self, chat_id: str, markdown: str, fallback: str) -> None:
        """`sendRichMessage`, and an honest fallback.

        The rich API is new, and a client that cannot render it answers with
        an error rather than a message. The bot sends the plain table instead
        of losing the report — and it says so on stderr, because a fallback
        that has become permanent is a bug that looks like a style choice.
        """
        try:
            response = await self._http.post(
                f"{TELEGRAM_API}/bot{self._token}/sendRichMessage",
                json=rich_payload(chat_id, markdown),
            )
            body = response.json()
            if body.get("ok"):
                return
            print(f"sendRichMessage refused: {body.get('description')}", file=sys.stderr)
        except Exception as exc:
            print(f"sendRichMessage failed: {exc}", file=sys.stderr)
        await self._send(chat_id, fallback)

    async def _memory(self, chat_id: str) -> str:
        """What the agent remembers about this chat."""
        harness = self._harness
        if harness is None:
            return "O agente não está configurado neste bot (IKIGAI_HARNESS_URL)."
        if not chat_id:
            return "Não sei de que sessão ler."
        result = await harness.memory(f"tg:{chat_id}")
        return _render_memory(result)

    async def run(self) -> None:
        """Every half of the loop: what arrives, what changes, and the clock.

        The poll asks Telegram for commands; the event stream carries the
        changes the store announces. A transport without events simply has
        nothing to listen to, and that half returns at once.

        The third is the AGENT's own log: the questions the agent asked while
        a routine was running, and the report it produced. It is polled, not
        pushed, and it is a separate half so that a slow agent never stops
        the bot from answering a command.

        The handshake is the fourth: the greeting that says what is
        connected. It runs beside the other three, so a slow agent delays the
        greeting and nothing else.

        The cadence is the fourth, and the only one with no input: it sleeps
        until the wall clock says it is time, and the loop dies with the
        process. Nothing is lost that a clock can reconstruct.
        """
        await asyncio.gather(
            self._poll_loop(),
            self._event_loop(),
            self._runtime_loop(),
            self._handshake(),
            self._cadence_loop(),
        )

    async def _poll_loop(self) -> None:
        while True:
            try:
                response = await self._http.get(
                    f"{TELEGRAM_API}/bot{self._token}/getUpdates",
                    params={"offset": self._offset, "timeout": 30},
                )
                payload = response.json()
            except Exception as exc:  # a poll failure is not fatal
                print(f"poll failed: {exc}", file=sys.stderr)
                await asyncio.sleep(5)
                continue

            for update in payload.get("result", []):
                self._offset = update["update_id"] + 1
                callback = update.get("callback_query")
                if callback:
                    await self._on_callback(callback)
                    continue
                message = update.get("message") or update.get("edited_message")
                if message:
                    await self._handle(message)

    async def _event_loop(self) -> None:
        """Forward the store's changes to the owner."""
        if self._events is None:
            return
        async for frame in self._events:
            try:
                await self._announce(frame)
            except Exception as exc:  # an event failure is not fatal
                print(f"event failed: {exc}", file=sys.stderr)

    async def _announce(self, frame: dict[str, Any]) -> None:
        """Tell the owner that something changed — unless it was our own write."""
        data = frame.get("data") or {}
        uid = str(data.get("uid") or "")
        if not uid:
            return
        if uid in self._own_writes:
            self._own_writes.discard(uid)
            return

        title = uid
        try:
            bundle = await self._client.call("get_artifact", {"uid": uid, "depth": 0})
            if isinstance(bundle, dict):
                title = str((bundle.get("artifact") or {}).get("title") or uid)
        except Exception:
            # The artifact may be gone by the time we look. The uid still
            # names what changed, so the owner is told something useful.
            pass

        for chat_id in self._allowed:
            await self._send(chat_id, f"• {title}\n  {uid}")


def _catalogue() -> str:
    """The catalogue of what the bot does.

    It is built FROM ``WRITABLE``, so it cannot drift: a command that can be
    written is a command the owner is told about, and a command the owner is
    told about exists in ``WRITABLE``. The two dictionaries are the same
    length — the catalogue would raise on a command without a description,
    and the drift test holds them together.

    The routines are listed from ``ROUTINES``, the same way: a routine the
    owner cannot run is a routine he does not need to be told about.
    """
    lines = ["O que eu faço:"]
    for command in WRITABLE:
        usage, description = _COMMANDS[command]
        lines.append(f"{command} {usage} — {description}")
    lines.append("/busca <texto> — procura no store")
    lines.append("/uid <uid> — lê um artefato e suas arestas")
    lines.append("/rascunho <tipo> — abre um rascunho; sem argumento, mostra o que está lá")
    lines.append("/guardar — fecha o rascunho como artefato")
    lines.append("/descartar — deita fora o rascunho")
    lines.append("/rascunhos — o que ficou a meio, lido do store")
    lines.append("/memoria — o que o agente lembra desta conversa")
    lines.append("/painel — o painel da sessão, dentro do chat")
    lines.append("/start — o handshake: o que está ligado")
    lines.append("")
    lines.append("Rotinas (o agente corre o ciclo e responde quando acabar):")
    for routine, description in ROUTINES.items():
        lines.append(f"/{routine} [texto] — {description}")
    return "\n".join(lines)


def _render_routine(routine: str, result: dict[str, Any]) -> str:
    """The agent's report, as the owner reads it.

    The harness returns what the agent said — the report the skill asks for:
    the uid it wrote, the counts per class, the tools that ran. That is the
    answer, and it comes first. The receipt (how long it took, what the
    agent remembered) follows it, because the owner asked a question and the
    answer is the agent's, not the receipt's.
    """
    text = str(result.get("text") or "").strip()
    lines = [f"✔ {routine}"]
    if text:
        lines.append(text)
    receipt: list[str] = []
    duration = result.get("duration_ms")
    if isinstance(duration, int):
        receipt.append(f"{duration / 1000:.1f}s")
    entry = result.get("memory_entry_id")
    if entry is not None:
        receipt.append(f"memória #{entry}")
    if receipt:
        lines.append("(" + " · ".join(receipt) + ")")
    return "\n".join(lines)


def _render_memory(result: dict[str, Any]) -> str:
    """What the agent remembers, as the owner reads it.

    The entries are the agent's own words. The memory is the AGENT's state —
    the DOM is the store's — so this is a reading of the agent's notebook,
    not of the canonical record.
    """
    entries = result.get("entries") or []
    if not isinstance(entries, list):
        return "O agente não lembra de nada."
    if not entries:
        return "O agente ainda não guardou nada desta conversa."
    lines: list[str] = []
    for entry in entries[-5:]:
        if not isinstance(entry, dict):
            continue
        content = str(entry.get("content") or "").strip()
        key = str(entry.get("key") or "?")
        stamp = str(entry.get("created_at") or "")
        lines.append(f"• {key}" + (f" · {stamp}" if stamp else ""))
        if content:
            lines.append(f"  {content[:400]}")
    if not lines:
        return "O agente ainda não guardou nada desta conversa."
    return "\n".join(lines)


def _render_search(result: Any) -> str:
    """Render a search result.

    The field is the CONTRACT's field: `SearchResult.artifacts`. The renderer
    used to look for "items" and "results" — names the transport has never
    sent — so every search answered "Nada encontrado" however many rows it
    had. Nothing noticed, because nothing exercised the renderer.
    """
    if not isinstance(result, dict):
        return "Nada encontrado."
    items = result.get("artifacts") or []
    if not items:
        return "Nada encontrado."
    lines = []
    for item in items[:10]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("uid") or "?"
        lines.append(f"• {title}\n  {item.get('uid', '')}")
    return "\n".join(lines)


def _render_bundle(bundle: Any) -> str:
    if not isinstance(bundle, dict):
        return str(bundle)
    artifact = bundle.get("artifact") or {}
    relations = bundle.get("relations") or []
    lines = [f"{artifact.get('title', '?')}\n{artifact.get('uid', '')}"]
    if artifact.get("body"):
        lines.append(str(artifact["body"])[:800])
    if relations:
        lines.append("arestas: " + ", ".join(str(r.get("rel", "?")) for r in relations[:10]))
    return "\n".join(lines)


def _harness_timeout_s() -> float:
    """The ceiling of a routine, in seconds.

    The harness bounds the run with the same number, so the two agree on who
    gives up first: the agent, not the socket. A value that is not a number
    falls back to the harness's own default rather than failing the bot at
    boot — a typo in a timeout must not take the owner offline.
    """
    raw = (os.environ.get(HARNESS_TIMEOUT_ENV) or "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_S
    try:
        return max(30.0, float(raw))
    except ValueError:
        return DEFAULT_TIMEOUT_S


def _miniapp_port() -> int:
    """The port the Mini App listens on, or zero when there is none.

    A value that is not a number is zero, not a crash: a typo in a port
    must not take the bot offline — the chat is the product, and the panel
    is a surface on top of it.
    """
    raw = (os.environ.get(MINIAPP_PORT_ENV) or "").strip()
    if not raw:
        return 0
    try:
        port = int(raw)
    except ValueError:
        return 0
    return port if 1 <= port <= 65535 else 0


async def _serve(bot: Bot) -> None:
    """The chat's loop, and the panel's surface, in ONE process.

    The Mini App is served by the bot because the bot is the only holder of
    the token the page's identity is made of. A separate service would need
    the token too, and a token in two places is a token that leaks from the
    place nobody remembered.
    """
    port = _miniapp_port()
    if not port:
        await bot.run()
        return

    import uvicorn

    from src.bot.miniapp import create_app

    server = uvicorn.Server(
        uvicorn.Config(
            create_app(bot),
            host="0.0.0.0",  # the container's network, not the host's
            port=port,
            log_level="warning",
        )
    )
    await asyncio.gather(bot.run(), server.serve())


def main() -> None:
    token = os.environ.get("IKIGAI_BOT_TOKEN")
    if not token:
        raise SystemExit("IKIGAI_BOT_TOKEN is not set")

    allowed_raw = os.environ.get("IKIGAI_BOT_ALLOWED_CHAT_IDS", "")
    allowed = {part.strip() for part in allowed_raw.split(",") if part.strip()}
    if not allowed:
        raise SystemExit(
            "IKIGAI_BOT_ALLOWED_CHAT_IDS is empty — the bot refuses to start, "
            "because an open bot is a public write channel (contract C-4)"
        )

    url = os.environ.get("IKIGAI_MCP_URL", "http://localhost:8000/mcp")
    client_id = os.environ.get("IKIGAI_CLIENT_ID", "owner")

    # The agent's door. It is OPTIONAL: without it the bot still writes,
    # searches and reads, and the routines are refused with a reason. The
    # bot does not fail closed here — it fails closed on the ALLOWLIST,
    # because that is what decides who may write at all.
    harness: HarnessClient | None = None
    harness_url = (os.environ.get(HARNESS_URL_ENV) or "").strip()
    if harness_url:
        harness = HarnessClient(harness_url, timeout_s=_harness_timeout_s())

    # Two transports, one interface. The websocket carries the changes the
    # store announces — the writes made elsewhere — and the MCP call does not.
    # A bot that only ever learns about its own writes is a bot that is
    # perpetually behind, so the websocket is preferred when it is configured.
    ws_url = (os.environ.get("IKIGAI_WS_URL") or "").strip()
    events: Any | None = None
    if ws_url:
        client: Any = WebSocketClient(
            ws_url, (os.environ.get("IKIGAI_WS_TOKEN") or "").strip() or None
        )
        events = client.events()
    else:
        client = McpClient(url)

    # The clock. A time that is SET and malformed raises here, on purpose: a
    # bot that boots with a cadence it silently ignores looks exactly like a
    # bot with no cadence at all, and nobody finds out until a report is
    # missing at the end of the day.
    cadence = cadence_from_env(os.environ, allowed)

    bot = Bot(
        token,
        client,
        allowed,
        client_id,
        events=events,
        harness=harness,
        cadence=cadence,
    )
    # `_serve` runs the chat's loop AND the Mini App's surface, in one
    # process: the panel is served by the bot because the bot is the only
    # holder of the token its identity is made of.
    asyncio.run(_serve(bot))


if __name__ == "__main__":
    main()
