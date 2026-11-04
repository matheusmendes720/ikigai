"""The Telegram bot — the owner-facing client of the canonical service.

ADR-037 D8: a client is a PROJECTION of the DOM, not a fork of it. This bot
therefore:

* speaks MCP to the api — it never opens a database connection (D6);
* writes through ``upsert_artifact`` — the service layer is the only writer
  (D5), and every write carries a revision and an idempotency key;
* reads through ``search_artifacts`` — the store is queried by index, not by
  grepping markdown (D4).

Owner-only, and it FAILS CLOSED: if the allowlist is missing or empty, the
bot refuses to start rather than answering anyone who finds the token.

Commands
--------
``/nota <texto>``   write a NOTA (the daily report)
``/sonho <texto>``  write a SONHO (a dream — the top of the pyramid)
``/busca <texto>``  search the store
``/uid <uid>``      read one artifact and its edges
``/help``           the catalogue

Run::

    python -m src.bot.main

Environment
-----------
``IKIGAI_BOT_TOKEN``            the Telegram bot token (never in the repo)
``IKIGAI_MCP_URL``              the api's MCP endpoint
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

from src.contracts.dom import ArtifactKind, make_uid

TELEGRAM_API = "https://api.telegram.org"

#: The kinds the bot may write. It is a projection of the owner's day, not
#: an editor of the whole pyramid.
WRITABLE: dict[str, ArtifactKind] = {
    "/nota": ArtifactKind.NOTA,
    "/sonho": ArtifactKind.SONHO,
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
) -> dict[str, Any]:
    """Build the Artifact the transport expects.

    The uid is derived from the OPERATION, not from the clock: the uuid half
    comes from the Telegram message id and the hash half from the body. Two
    sends of the same message are the same intent, which is what makes the
    write idempotent (ADR-037 D5).
    """
    now = datetime.now(UTC).isoformat()
    return {
        "uid": str(make_uid(kind, _slugify(title), uuid_short, _hash8(body))),
        "kind": kind.value,
        "title": title,
        "body": body,
        "body_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "created_at": now,
        "updated_at": now,
    }


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
            from mcp.client.streamable_http import (
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

    def __init__(self, token: str, client: McpClient, allowed: set[str], client_id: str) -> None:
        self._token = token
        self._client = client
        self._allowed = allowed
        self._client_id = client_id
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=60.0))
        self._offset = 0

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
            answer = await self._dispatch(command, argument, message_id)
        except Exception as exc:  # noqa: BLE001 — the bot reports, it does not crash
            answer = f"Não consegui completar isso: {exc}"

        await self._send(chat_id, answer)

    async def _dispatch(self, command: str, argument: str, message_id: str) -> str:
        if command == "/help":
            return (
                "O que eu faço:\n"
                "/nota <texto> — registra a nota do dia\n"
                "/sonho <texto> — registra um sonho\n"
                "/busca <texto> — procura no store\n"
                "/uid <uid> — lê um artefato e suas arestas\n"
            )

        if command in WRITABLE:
            if not argument:
                return "Diz o que é, em uma linha."
            kind = WRITABLE[command]
            title = argument.splitlines()[0][:120]
            body = argument
            artifact = _artifact_payload(kind, title, body, _hash8(message_id))
            outcome = await self._client.call(
                "upsert_artifact",
                {
                    "artifact": artifact,
                    "expected_revision": None,
                    "idempotency_key": f"{artifact['uid']}:{artifact['body_hash']}",
                    "client_id": self._client_id,
                },
            )
            return f"Registado ({kind.value}).\n{artifact['uid']}"

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

    async def run(self) -> None:
        while True:
            try:
                response = await self._http.get(
                    f"{TELEGRAM_API}/bot{self._token}/getUpdates",
                    params={"offset": self._offset, "timeout": 30},
                )
                payload = response.json()
            except Exception as exc:  # noqa: BLE001 — a poll failure is not fatal
                print(f"poll failed: {exc}", file=sys.stderr)
                await asyncio.sleep(5)
                continue

            for update in payload.get("result", []):
                self._offset = update["update_id"] + 1
                message = update.get("message") or update.get("edited_message")
                if message:
                    await self._handle(message)


def _render_search(result: Any) -> str:
    if isinstance(result, dict):
        items = result.get("items") or result.get("results") or []
    else:
        items = []
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

    bot = Bot(token, McpClient(url), allowed, client_id)
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
