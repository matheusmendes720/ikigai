"""The bot's client closes the gap, and does it without duplicates or reordering.

Three properties, and none of them is free:

1. **the gap is asked for** — the client remembers the last sequence it gave
   the consumer and asks for what came after it, so a write made while it was
   down is not lost in silence;
2. **no duplicates** — the gap and the live feed overlap by construction, so
   anything at or below the last delivered sequence is dropped;
3. **no reordering** — live events that land while the replay is in flight are
   buffered and flushed after it.

The last two are the ones that make the first one usable. A resume that hands
the consumer sequence 10 before sequences 6 to 9 has replaced a missing event
with a lie about the order.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from src.bot.ws_client import WebSocketClient


class FakeConnection:
    """A socket that records what was sent and can push frames back."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.closed = False

    async def send(self, raw: str) -> None:
        self.sent.append(json.loads(raw))

    async def close(self) -> None:
        self.closed = True

    def pop_sent(self) -> list[dict[str, Any]]:
        sent, self.sent = self.sent, []
        return sent


def _client(connection: FakeConnection) -> WebSocketClient:
    client = WebSocketClient("ws://test/sync", token=None)
    client._connection = connection  # type: ignore[attr-defined]
    return client


def _event(seq: int, op: str = "UPDATE") -> dict[str, Any]:
    return {
        "type": "event",
        "event": f"artifact.{op.lower()}",
        "data": {"uid": "kpi:x:aabbccdd:0123456789abcdef", "op": op, "seq": seq},
    }


def _hello(tip: int) -> dict[str, Any]:
    return {"type": "hello", "tools": [], "drafts": [], "sequence": tip}


async def _drain(client: WebSocketClient, count: int) -> list[dict[str, Any]]:
    return [await asyncio.wait_for(client._events.get(), timeout=2) for _ in range(count)]


async def test_a_first_connection_has_no_gap_to_close() -> None:
    """Everything before the tip happened before this client existed."""
    connection = FakeConnection()
    client = _client(connection)

    client._dispatch(json.dumps(_hello(9)))  # type: ignore[attr-defined]

    assert client.sequence == 9
    assert connection.sent == []


async def test_a_reconnection_asks_for_what_it_missed() -> None:
    connection = FakeConnection()
    client = _client(connection)
    client._sequence = 4  # type: ignore[attr-defined]

    client._dispatch(json.dumps(_hello(9)))  # type: ignore[attr-defined]

    # The hello schedules the resume; let it run.
    for _ in range(5):
        await asyncio.sleep(0)
    sent = connection.pop_sent()
    assert sent, "the client never asked for the gap"
    assert sent[0]["type"] == "resume"
    assert sent[0]["since"] == 4


async def test_the_gap_is_delivered_in_the_stores_order() -> None:
    connection = FakeConnection()
    client = _client(connection)
    client._sequence = 4  # type: ignore[attr-defined]

    client._dispatch(json.dumps(_hello(7)))  # type: ignore[attr-defined]
    for _ in range(5):
        await asyncio.sleep(0)
    request_id = connection.sent[0]["id"]
    client._dispatch(  # type: ignore[attr-defined]
        json.dumps(
            {
                "type": "result",
                "id": request_id,
                "ok": True,
                "data": {
                    "events": [
                        {"uid": "kpi:x:aabbccdd:0123456789abcdef", "op": "UPDATE", "seq": 5},
                        {"uid": "kpi:x:aabbccdd:0123456789abcdef", "op": "INSERT", "seq": 6},
                        {"uid": "kpi:x:aabbccdd:0123456789abcdef", "op": "DELETE", "seq": 7},
                    ],
                    "tip": 7,
                    "truncated": False,
                },
            }
        )
    )

    frames = await _drain(client, 3)
    assert [frame["data"]["seq"] for frame in frames] == [5, 6, 7]
    assert client.sequence == 7


async def test_the_gap_and_the_live_feed_do_not_repeat_an_event() -> None:
    """They overlap by construction: a live event can arrive before the answer."""
    connection = FakeConnection()
    client = _client(connection)
    client._sequence = 4  # type: ignore[attr-defined]

    client._dispatch(json.dumps(_hello(6)))  # type: ignore[attr-defined]
    for _ in range(5):
        await asyncio.sleep(0)
    client._dispatch(json.dumps(_event(6)))  # type: ignore[attr-defined]  # live, buffered
    request_id = connection.sent[0]["id"]
    client._dispatch(  # type: ignore[attr-defined]
        json.dumps(
            {
                "type": "result",
                "id": request_id,
                "ok": True,
                "data": {
                    "events": [
                        {"uid": "kpi:x:aabbccdd:0123456789abcdef", "op": "UPDATE", "seq": 5},
                        {"uid": "kpi:x:aabbccdd:0123456789abcdef", "op": "UPDATE", "seq": 6},
                    ],
                    "tip": 6,
                    "truncated": False,
                },
            }
        )
    )

    frames = await _drain(client, 2)
    assert [frame["data"]["seq"] for frame in frames] == [5, 6]
    assert client._events.empty(), "sequence 6 was delivered twice"


async def test_a_live_event_waits_for_the_gap_it_belongs_after() -> None:
    """A consumer that saw 10 before 6 to 9 could not tell order from opinion."""
    connection = FakeConnection()
    client = _client(connection)
    client._sequence = 5  # type: ignore[attr-defined]

    client._dispatch(json.dumps(_hello(9)))  # type: ignore[attr-defined]
    for _ in range(5):
        await asyncio.sleep(0)
    client._dispatch(json.dumps(_event(9)))  # type: ignore[attr-defined]
    assert client._events.empty(), "a live event overtook the gap"

    request_id = connection.sent[0]["id"]
    client._dispatch(  # type: ignore[attr-defined]
        json.dumps(
            {
                "type": "result",
                "id": request_id,
                "ok": True,
                "data": {
                    "events": [
                        {"uid": "kpi:x:aabbccdd:0123456789abcdef", "op": "UPDATE", "seq": 6},
                        {"uid": "kpi:x:aabbccdd:0123456789abcdef", "op": "UPDATE", "seq": 7},
                    ],
                    "tip": 9,
                    "truncated": False,
                },
            }
        )
    )

    frames = await _drain(client, 3)
    assert [frame["data"]["seq"] for frame in frames] == [6, 7, 9]


async def test_a_gap_bigger_than_a_page_is_said_out_loud() -> None:
    """The client must be able to stop believing it is current."""
    connection = FakeConnection()
    client = _client(connection)
    client._sequence = 1  # type: ignore[attr-defined]

    client._dispatch(json.dumps(_hello(900)))  # type: ignore[attr-defined]
    for _ in range(5):
        await asyncio.sleep(0)
    request_id = connection.sent[0]["id"]
    client._dispatch(  # type: ignore[attr-defined]
        json.dumps(
            {
                "type": "result",
                "id": request_id,
                "ok": True,
                "data": {"events": [], "tip": 900, "truncated": True},
            }
        )
    )

    frame = await asyncio.wait_for(client._events.get(), timeout=2)
    assert frame["type"] == "gap"
    assert frame["truncated"] is True
    assert frame["tip"] == 900


async def test_a_resume_that_fails_does_not_stop_the_live_feed() -> None:
    """A client that refuses to work because it missed something stops for the wrong reason."""
    connection = FakeConnection()
    client = _client(connection)
    client._sequence = 3  # type: ignore[attr-defined]

    client._dispatch(json.dumps(_hello(5)))  # type: ignore[attr-defined]
    client._dispatch(json.dumps(_event(5)))  # type: ignore[attr-defined]  # buffered while resuming
    for _ in range(5):
        await asyncio.sleep(0)
    request_id = connection.sent[0]["id"]
    client._dispatch(  # type: ignore[attr-defined]
        json.dumps(
            {"type": "result", "id": request_id, "ok": False, "error": {"code": "error"}}
        )
    )

    frames = await _drain(client, 1)
    assert frames[0]["data"]["seq"] == 5


async def test_an_older_hello_asks_for_nothing() -> None:
    """A server that restarted has a lower tip; there is no gap, only a new epoch."""
    connection = FakeConnection()
    client = _client(connection)
    client._sequence = 40  # type: ignore[attr-defined]

    client._dispatch(json.dumps(_hello(2)))  # type: ignore[attr-defined]

    assert connection.sent == []


async def test_a_draft_is_its_own_frame_and_not_a_tool() -> None:
    """A draft is state, and `call("save_draft")` would find out at runtime."""
    connection = FakeConnection()
    client = _client(connection)

    task = asyncio.create_task(client.draft("list"))
    for _ in range(5):
        await asyncio.sleep(0)
    sent = connection.pop_sent()
    assert sent and sent[0]["type"] == "draft"
    assert sent[0]["op"] == "list"
    assert "tool" not in sent[0]

    connection_pending = client._pending  # type: ignore[attr-defined]
    (request_id,) = connection_pending
    client._dispatch(  # type: ignore[attr-defined]
        json.dumps({"type": "result", "id": request_id, "ok": True, "data": {"drafts": []}})
    )
    assert await task == {"drafts": []}


async def test_a_closed_socket_is_replaced_on_the_next_call() -> None:
    """A handle that outlives its socket writes into nothing."""
    client = WebSocketClient("ws://test/sync")

    class Dead:
        async def __aiter__(self) -> Any:
            return
            yield  # pragma: no cover

    client._connection = Dead()  # type: ignore[attr-defined]
    await client._read()  # type: ignore[attr-defined]

    assert client._connection is None  # type: ignore[attr-defined]


async def test_an_event_without_a_sequence_still_reaches_the_consumer() -> None:
    """An older trigger must not be swallowed by the deduplication."""
    connection = FakeConnection()
    client = _client(connection)

    client._dispatch(json.dumps({"type": "event", "data": {"uid": "u", "op": "UPDATE"}}))  # type: ignore[attr-defined]

    frame = await asyncio.wait_for(client._events.get(), timeout=2)
    assert frame["data"]["uid"] == "u"
    assert client.sequence is None


@pytest.mark.parametrize("raw", ["not json", "[]", '"a string"', "{}"])
def test_a_frame_that_is_not_a_frame_is_ignored(raw: str) -> None:
    client = _client(FakeConnection())

    client._dispatch(raw)  # type: ignore[attr-defined]

    assert client._events.empty()
