"""The bot's websocket transport: calls out, events in, and a gap it can close.

The Telegram bot is a CLIENT of the store (ADR-037 D6): it speaks to the
transport and never opens a database. It used to have exactly one way to do
that — a request/response MCP call, per command.

That is enough to ASK. It is not enough to stay in sync: the writes it cares
about happen in other processes — the vault ingestion, another device, the
harness — and a bot that only learns about its own writes is a bot that is
perpetually behind.

So the bot speaks the websocket. The interface is the same one the MCP client
has — ``call(tool, arguments)`` — so the bot's dispatch code does not know or
care which transport it is on. What the websocket adds is three things:

- **the other direction** — the server pushes what the store changed, and the
  bot forwards it to the owner;
- **a gap it can close** — every event carries the store's sequence, and a
  client that reconnects asks for what came after the last one it delivered.
  A channel reaches whoever is listening at that instant and nobody else, so
  without this the writes made while the bot was down are lost in silence;
- **the drafts** — the prose the owner is writing that is not an artifact yet,
  which is why it has to outlive the socket.

Two properties the consumer gets for free, and neither is free to implement:

- **no duplicates.** The gap and the live feed overlap by construction — an
  event can arrive on the wire while the replay is still being answered — so
  anything at or below the last delivered sequence is dropped.
- **no reordering.** While a replay is in flight, live events are BUFFERED and
  flushed after it, so the consumer never sees a later event before it sees
  the earlier one.

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


def _event_frame(uid: str, op: str, seq: int | None) -> dict[str, Any]:
    """One frame shape for an event, whether it came live or from the gap.

    The live feed and the replay carry the same fact in two shapes — the live
    one is already a frame, the replay is a row. A consumer that had to know
    which is which is a consumer that will get it wrong, so they are normalised
    here and nowhere else.
    """
    data: dict[str, Any] = {"uid": uid, "op": str(op).upper()}
    if seq is not None:
        data["seq"] = seq
    return {"type": "event", "event": f"artifact.{str(op).lower()}", "data": data}


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
    """A websocket client with the MCP client's shape, and a resumable feed.

    ``call`` returns what the tool returned and raises what the tool raised —
    the domain error, with its code, so the bot's message says "conflict" and
    not "something went wrong".
    """

    def __init__(
        self,
        url: str,
        token: str | None = None,
        *,
        auto_resume: bool = True,
        replay_limit: int = 500,
    ) -> None:
        self._url = url
        self._token = token
        self._auto_resume = auto_resume
        self._replay_limit = replay_limit
        self._connection: Any | None = None
        self._pending: dict[str, asyncio.Future[Any]] = {}
        self._events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._reader: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        #: The last sequence the CONSUMER was given. The whole point of the
        #: resume is that this survives a connection.
        self._sequence: int | None = None
        self._resuming = False
        self._buffer: list[dict[str, Any]] = []
        # A task with no reference can be garbage-collected mid-flight, and a
        # resume that disappears halfway is worse than one that never started:
        # the client would believe it is current.
        self._resume_task: asyncio.Task[None] | None = None

    @property
    def sequence(self) -> int | None:
        """The last change sequence this client delivered, or None before the first."""
        return self._sequence

    async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        """Call a tool and wait for its answer."""
        return await self._request({"type": "call", "tool": tool, "arguments": arguments})

    async def draft(self, op: str, **fields: Any) -> Any:
        """Save, read, list or discard a draft.

        It is not a tool and it is not shaped like one: a draft is state, and
        the transport gives it its own frame (ADR-040). Keeping it a separate
        method is what stops a caller from reaching for ``call("save_draft")``
        and finding out at runtime that there is no such tool.
        """
        return await self._request({"type": "draft", "op": op, **fields})

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """The frames the server pushes, as they arrive — gap first, then live."""
        while True:
            yield await self._events.get()

    async def close(self) -> None:
        """Close the connection and stop the reader."""
        if self._reader is not None:
            self._reader.cancel()
            self._reader = None
        if self._resume_task is not None:
            self._resume_task.cancel()
            self._resume_task = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def _request(self, frame: dict[str, Any]) -> Any:
        """Send one frame and wait for the answer with its id."""
        async with self._lock:
            if self._connection is None:
                await self._connect()
            connection = self._connection
            if connection is None:  # pragma: no cover — _connect raises first
                raise RuntimeError("the websocket is not connected")

            request_id = uuid4().hex
            future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
            self._pending[request_id] = future
            await connection.send(json.dumps({**frame, "id": request_id}))
        try:
            return await future
        finally:
            self._pending.pop(request_id, None)

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
            pass
        finally:
            # The connection ended. The pending calls are failed here rather
            # than left waiting for an answer that will never come, and the
            # handle is cleared so the NEXT call reconnects instead of writing
            # into a socket that is already closed.
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(RuntimeError("the websocket closed"))
            self._pending.clear()
            self._connection = None

    def _dispatch(self, raw: Any) -> None:
        try:
            frame = json.loads(raw)
        except (TypeError, ValueError):
            return
        if not isinstance(frame, dict):
            return

        kind = frame.get("type")
        if kind == "hello":
            # The tip is here, and it is what says whether a gap exists.
            #
            # The state is updated SYNCHRONOUSLY and only the replay is a
            # task: a caller that reads `sequence` right after the handshake
            # must see where the feed stands, and a value that appears a tick
            # later is a value that races its own reader.
            tip = frame.get("sequence")
            if not isinstance(tip, int):
                return
            if self._sequence is None:
                self._sequence = tip
                return
            if not self._auto_resume or tip <= self._sequence:
                return
            self._resume_task = asyncio.create_task(self._replay(self._sequence, tip))
            return
        if kind == "result":
            self._settle(frame)
            return
        if kind == "event":
            self._incoming(frame)

    def _settle(self, frame: dict[str, Any]) -> None:
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

    async def _replay(self, since: int, tip: int) -> None:
        """Ask for what came after `since`, and deliver it before anything new.

        Live events that land while the answer is in flight are BUFFERED: a
        consumer that saw sequence 10 before sequences 6 to 9 would not be able
        to tell a reordering from a change of mind.
        """
        self._resuming = True
        try:
            data = await self._request(
                {"type": "resume", "since": since, "limit": self._replay_limit}
            )
        except Exception:
            # The gap could not be closed. The live feed is still usable, and a
            # client that refuses to work because it missed something is a
            # client that stops working for the wrong reason.
            self._resuming = False
            self._flush()
            return

        for row in _rows(data):
            self._deliver(
                _event_frame(str(row.get("uid")), str(row.get("op") or "UPDATE"), _seq(row))
            )
        self._resuming = False
        self._flush()
        if isinstance(data, dict) and (data.get("truncated") or data.get("lost")):
            # The gap was bigger than one page, OR the cursor was older than
            # what the log still keeps. Both mean "you are not current", and
            # the consumer is told so it can reread what it cares about
            # instead of believing a silence is a sign of being up to date.
            self._events.put_nowait(
                {
                    "type": "gap",
                    "truncated": bool(data.get("truncated")),
                    "lost": bool(data.get("lost")),
                    "floor": data.get("floor"),
                    "tip": tip,
                }
            )

    def _flush(self) -> None:
        buffered, self._buffer = self._buffer, []
        for frame in buffered:
            self._deliver(frame)

    def _incoming(self, frame: dict[str, Any]) -> None:
        if self._resuming:
            self._buffer.append(frame)
            return
        self._deliver(frame)

    def _deliver(self, frame: dict[str, Any]) -> None:
        """Hand an event to the consumer, once."""
        data = frame.get("data")
        seq = _seq(data if isinstance(data, dict) else {})
        if seq is not None:
            if self._sequence is not None and seq <= self._sequence:
                # The gap and the live feed overlap by construction.
                return
            self._sequence = seq
        self._events.put_nowait(frame)


def _seq(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    raw = payload.get("seq")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return None


def _rows(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    events = data.get("events")
    if not isinstance(events, list):
        return []
    return [row for row in events if isinstance(row, dict)]
