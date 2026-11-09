"""The client and the server, talking to each other over a real socket.

Every other test in this package holds ONE half. The unit tests of the service
hold the replay logic with a fake repository; the unit tests of the client hold
the resume logic with a fake socket. Neither of them holds the thing that
actually breaks: the WIRE — the shape of the frames, the ids that pair a
request with its answer, and the order in which the gap and the live feed meet.

So this test starts the real Starlette app on a real port, connects the real
client to it, and drops the connection on purpose to make the gap real. The
repositories are fakes; nothing else is.
"""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator
from typing import Any

import pytest
from src.bot.ws_client import WebSocketClient
from src.contracts.dom import SearchResult
from src.services.changes import ChangeFeed
from src.transport import mcp_server, ws_server


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class EventsRepo:
    """The events the store would have kept."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def append(self, seq: int, uid: str = "kpi:x:aabbccdd:0123456789abcdef") -> None:
        self.rows.append({"seq": seq, "uid": uid, "op": "UPDATE"})

    async def events_since(self, since: int, limit: int) -> list[dict[str, Any]]:
        return [row for row in self.rows if int(row["seq"]) > since][:limit]

    async def event_tip(self) -> int:
        return max((int(row["seq"]) for row in self.rows), default=0)

    async def event_floor(self) -> int:
        return min((int(row["seq"]) for row in self.rows), default=0)

    async def prune_events(self, keep: int) -> int:
        return 0

    async def artifact_events(self) -> AsyncIterator[dict[str, Any]]:
        # A feed with nothing to say, that never ends: the pump is a task.
        while True:
            await asyncio.sleep(3600)
            yield {}  # pragma: no cover


class Artifacts:
    async def search(self, query: Any) -> SearchResult:
        return SearchResult(artifacts=())


class Drafts:
    """The draft service, in the shape the transport expects."""

    async def save(self, draft: Any, *, expected_revision: Any = None, idempotency_key: str) -> Any:
        from src.contracts.drafts import DraftOutcome

        return DraftOutcome(
            client_id=draft.client_id,
            draft_id=draft.draft_id,
            revision=1,
            outcome="created",
        )

    async def get(self, client_id: str, draft_id: str) -> Any:
        return None

    async def open_drafts(self, client_id: str, limit: int = 50) -> list[Any]:
        return []

    async def discard(self, client_id: str, draft_id: str, *, expected_revision: Any = None) -> Any:
        from src.contracts.drafts import DraftOutcome

        return DraftOutcome(client_id=client_id, draft_id=draft_id, revision=1, outcome="discarded")


@pytest.fixture
async def server() -> AsyncIterator[tuple[int, EventsRepo]]:
    """The real app, on a real port, with fake repositories."""
    import uvicorn

    events = EventsRepo()
    services = mcp_server.Services(
        artifacts=Artifacts(),  # type: ignore[arg-type]
        relations=object(),  # type: ignore[arg-type]
        embeddings=object(),  # type: ignore[arg-type]
        changes=ChangeFeed(events),  # type: ignore[arg-type]
        drafts=Drafts(),  # type: ignore[arg-type]
    )
    port = _free_port()
    config = uvicorn.Config(
        ws_server.build_app(services),
        host="127.0.0.1",
        port=port,
        log_level="warning",
        lifespan="on",
    )
    running = uvicorn.Server(config)
    task = asyncio.create_task(running.serve())
    for _ in range(100):
        if running.started:
            break
        await asyncio.sleep(0.05)
    try:
        yield port, events
    finally:
        running.should_exit = True
        await asyncio.wait_for(task, timeout=10)


async def _open(port: int) -> WebSocketClient:
    client = WebSocketClient(f"ws://127.0.0.1:{port}/sync")
    # A tool call is what a real client does first, and it is also what opens
    # the socket: there is no other public way in.
    await client.call("search_artifacts", {"query": {}})
    return client


async def test_the_handshake_says_where_the_feed_stands(
    server: tuple[int, EventsRepo],
) -> None:
    port, events = server
    events.append(7)
    client = await _open(port)
    try:
        assert client.sequence == 7, "the client did not take the tip from the hello"
    finally:
        await client.close()


async def test_a_reconnection_gets_what_it_missed(server: tuple[int, EventsRepo]) -> None:
    """The whole point: a write made while the client was down is not lost."""
    port, events = server
    events.append(1)
    client = await _open(port)
    try:
        assert client.sequence == 1

        # The store changes while the client is away.
        events.append(2)
        events.append(3)

        # Drop the connection on purpose.
        await client._connection.close()  # type: ignore[attr-defined]
        for _ in range(50):
            if client._connection is None:  # type: ignore[attr-defined]
                break
            await asyncio.sleep(0.02)

        incoming = asyncio.create_task(client._events.get())  # type: ignore[attr-defined]
        await client.call("search_artifacts", {"query": {}})
        first = await asyncio.wait_for(incoming, timeout=10)

        assert first["type"] == "event"
        assert first["data"]["seq"] == 2, "the gap did not come back"
        second = await asyncio.wait_for(client._events.get(), timeout=10)  # type: ignore[attr-defined]
        assert second["data"]["seq"] == 3
        assert client.sequence == 3
    finally:
        await client.close()


async def test_a_draft_round_trip_over_the_wire(server: tuple[int, EventsRepo]) -> None:
    """A draft is a frame of its own, and the answer carries the revision."""
    port, _ = server
    client = await _open(port)
    try:
        answer = await client.draft(
            "save", draft_id="nota-1", kind="nota", title="Uma nota", body="a meio"
        )
        assert answer["outcome"] == "created"
        assert answer["draft_id"] == "nota-1"

        discarded = await client.draft("discard", draft_id="nota-1")
        assert discarded["outcome"] == "discarded"
    finally:
        await client.close()


async def test_a_draft_that_names_no_id_is_refused_over_the_wire(
    server: tuple[int, EventsRepo],
) -> None:
    port, _ = server
    client = await _open(port)
    try:
        with pytest.raises(RuntimeError) as raised:
            await client.draft("save", body="sem id")
        assert "validation" in str(raised.value)
    finally:
        await client.close()
