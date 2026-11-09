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
import unicodedata
from datetime import UTC, datetime
from typing import Any

import httpx

from src.bot.harness_client import DEFAULT_TIMEOUT_S, HarnessClient
from src.bot.ws_client import WebSocketClient
from src.contracts.dom import ArtifactKind, make_uid
from src.contracts.dom_kinds import KIND_MODELS

TELEGRAM_API = "https://api.telegram.org"

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
        # The agent's door. Without it the bot still writes, searches and
        # reads — it just cannot run a routine, and it says so.
        self._harness = harness
        # The routines in flight. The task is HELD on purpose: a task nobody
        # references may be collected mid-run, and the owner's answer would
        # never arrive.
        self._running: set[asyncio.Task[None]] = set()

    async def _send(self, chat_id: str, text: str) -> None:
        await self._http.post(
            f"{TELEGRAM_API}/bot{self._token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4000]},
        )

    async def _handle(self, message: dict[str, Any]) -> None:
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if chat_id not in self._allowed:
            # Fail closed and stay silent: an unlisted chat gets no answer and
            # no trace of what this bot can do.
            return

        text = str(message.get("text") or "")
        message_id = str(message.get("message_id", "0"))
        command, _, argument = text.partition(" ")
        argument = argument.strip()

        try:
            answer = await self._dispatch(command, argument, message_id, chat_id)
        except Exception as exc:  # the bot reports, it does not crash
            answer = f"Não consegui completar isso: {exc}"

        await self._send(chat_id, answer)

    async def _dispatch(
        self, command: str, argument: str, message_id: str, chat_id: str = ""
    ) -> str:
        """Route one command to its answer.

        ``chat_id`` is where the answer goes. The deterministic commands do
        not need it — they answer in the message they are handling. The
        routines do: the agent's answer arrives later, in another message, to
        the chat that asked for it.
        """
        if command == "/help":
            return _catalogue()

        routine = command[1:] if command.startswith("/") else ""
        if routine in ROUTINES:
            return await self._start_routine(chat_id, routine, argument)

        if command == "/memoria":
            return await self._memory(chat_id)

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
                session_id=f"tg:{chat_id}",
                chat_id=chat_id,
                message=argument,
            )
        except Exception as exc:
            # A routine that dies in the background is a routine that never
            # happened. The owner is told WHY.
            await self._send(chat_id, f"A rotina {routine} falhou: {exc}")
            return
        await self._send(chat_id, _render_routine(routine, result))

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
        """Both halves of the loop: what arrives, and what changes.

        The poll asks Telegram for commands; the event stream carries the
        changes the store announces. A transport without events simply has
        nothing to listen to, and the second half returns at once.
        """
        await asyncio.gather(self._poll_loop(), self._event_loop())

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
    lines.append("/memoria — o que o agente lembra desta conversa")
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

    bot = Bot(token, client, allowed, client_id, events=events, harness=harness)
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
