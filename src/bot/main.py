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
``/help``               the catalogue

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

from src.bot.ws_client import WebSocketClient
from src.contracts.dom import ArtifactKind, make_uid
from src.contracts.dom_kinds import KIND_MODELS

TELEGRAM_API = "https://api.telegram.org"

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
    """The Telegram loop. One command per message, one answer per command."""

    def __init__(
        self,
        token: str,
        client: Any,
        allowed: set[str],
        client_id: str,
        events: Any | None = None,
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

        try:
            if text.startswith("/"):
                command, _, argument = text.partition(" ")
                answer = await self._dispatch(command, argument.strip(), message_id, chat_id)
            else:
                # A message that is NOT a command is prose, and prose belongs to
                # the draft that is open. The command path splits on the first
                # space, which would throw the first word of the paragraph away.
                answer = await self._append(chat_id, text.strip(), message_id)
        except Exception as exc:  # the bot reports, it does not crash
            answer = f"Não consegui completar isso: {exc}"

        await self._send(chat_id, answer)

    async def _dispatch(
        self,
        command: str,
        argument: str,
        message_id: str,
        chat_id: str = "",
    ) -> str:
        if command == "/help":
            return _catalogue()

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

    async def _start_draft(self, chat_id: str, argument: str) -> str:
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
            "Manda o texto em quantas mensagens quiseres. /guardar fecha, /descartar deita fora."
        )

    async def _append(self, chat_id: str, text: str, message_id: str) -> str:
        """A message that is not a command: it is prose, and it grows the draft."""
        if not text:
            return ""
        if not self._speaks_drafts():
            return "Não conheço esse comando. /help"
        state = self._open.get(chat_id)

        current = await self._read_draft(chat_id)
        if current is None:
            return "Não há rascunho aberto.\n/rascunho <tipo> começa um. Ou /help para os comandos."
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
        await self._client.draft(
            "discard",
            client_id=self._client_id,
            draft_id=self._draft_key(chat_id),
            expected_revision=int(draft["revision"]),
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

    bot = Bot(token, client, allowed, client_id, events=events)
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
