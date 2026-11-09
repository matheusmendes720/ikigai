"""The bot's websocket transport: calls out, events in.

The Telegram bot is a CLIENT of the store (ADR-037 D6): it speaks to the
transport and never opens a database. It used to have exactly one way to do
that — a request/response MCP call, per command.

That is enough to ASK. It is not enough to stay in sync: the writes it cares
about happen in other processes — the vault ingestion, another device, the
harness — and a bot that only learns about its own writes is a bot that is
perpetually behind.

So the bot can speak the websocket instead. The interface is the same one the
MCP client has — ``call(tool, arguments)`` — so the bot's dispatch code does
not know or care which transport it is on. What the websocket adds is the
other direction: the server pushes what the store changed, and the bot
forwards it to the owner.

The token is the same one the transport demands. A client with no token is
refused by the handshake, and the bot says so rather than retrying forever.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

__all__ = ["WebSocketClient"]


def _url_complaint(url: str) -> str | None:
    """Why this URL cannot be a websocket, or ``None`` when it can.

    A function of its own because it is the one thing about a connection that
    can be checked with no network at all — and because the port is SHARED
    with the MCP transport: ``http://ws:8001/sync`` names the right host and
    the right port and is still wrong, since the scheme is the protocol.
    Measured on the box before this guard existed: the bot's whole store leg
    failed in 591 ms (*"scheme isn't ws or wss"*) while the container kept
    reporting healthy, and the message it produced sent the reader to
    ``http:8001/sync`` — an address that does not exist.
    """
    if url.startswith(("ws://", "wss://")):
        return None
    return (
        f"the websocket URL must start with ws:// or wss://, and {url!r} does not. "
        "The transport speaks the websocket protocol, and an http:// URL is a "
        "different protocol that happens to share the port — the call fails even "
        "when the service is healthy."
    )


class WebSocketClient:
    """A websocket client with the MCP client's shape.

    ``call`` returns what the tool returned and raises what the tool raised —
    the domain error, with its code, so the bot's message says "conflict" and
    not "something went wrong".
    """

    def __init__(self, url: str, token: str | None = None) -> None:
        self._url = url
        self._token = token
        self._connection: Any | None = None
        self._pending: dict[str, asyncio.Future[Any]] = {}
        self._events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._reader: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        """Call a tool and wait for its answer."""
        async with self._lock:
            if self._connection is None:
                await self._connect()
            connection = self._connection
            if connection is None:  # pragma: no cover — _connect raises first
                raise RuntimeError("the websocket is not connected")

            request_id = uuid4().hex
            future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
            self._pending[request_id] = future
            await connection.send(
                json.dumps(
                    {
                        "type": "call",
                        "id": request_id,
                        "tool": tool,
                        "arguments": arguments,
                    }
                )
            )
        try:
            return await future
        finally:
            self._pending.pop(request_id, None)

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """The frames the server pushes, as they arrive."""
        while True:
            yield await self._events.get()

    async def close(self) -> None:
        """Close the connection and stop the reader."""
        if self._reader is not None:
            self._reader.cancel()
            self._reader = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def _connect(self) -> None:
        complaint = _url_complaint(self._url)
        if complaint is not None:
            raise RuntimeError(complaint)

        from websockets.asyncio.client import connect

        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            self._connection = await connect(self._url, additional_headers=headers)
        except Exception as exc:
            parsed = urlsplit(self._url)
            where = f"{parsed.hostname}:{parsed.port}"
            raise RuntimeError(
                f"the websocket at {self._url} refused the connection: {exc}. "
                f"The bot needs {where} to be reachable and the token to be right."
            ) from exc
        self._reader = asyncio.create_task(self._read())

    async def _read(self) -> None:
        """The reader: answers the calls, queues the events."""
        connection = self._connection
        if connection is None:  # pragma: no cover — _connect sets it first
            return
        try:
            async for raw in connection:
                self._dispatch(raw)
        except asyncio.CancelledError:
            raise
        except Exception:
            # The connection ended. The pending calls are failed here rather
            # than left waiting for an answer that will never come.
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(RuntimeError("the websocket closed"))
            self._pending.clear()

    def _dispatch(self, raw: Any) -> None:
        try:
            frame = json.loads(raw)
        except (TypeError, ValueError):
            return
        if not isinstance(frame, dict):
            return

        kind = frame.get("type")
        if kind == "result":
            future = self._pending.get(str(frame.get("id")))
            if future is None or future.done():
                return
            if frame.get("ok"):
                future.set_result(frame.get("data"))
                return
            error = frame.get("error")
            if not isinstance(error, dict):
                error = {}
            code = str(error.get("code") or "error")
            message = str(error.get("message") or "")
            detail = str(error.get("detail") or "")
            text = f"{code}: {message}"
            if detail:
                text = f"{text} ({detail})"
            future.set_exception(RuntimeError(text))
            return

        if kind == "event":
            self._events.put_nowait(frame)
