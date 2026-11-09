"""The bot's websocket door: the scheme is the protocol, not a detail.

The bot reaches the transport two ways — MCP for the calls, the websocket for
what the store changed — and the two live on DIFFERENT ports with different
protocols. Port 8001 belongs to the websocket, and `http://` names it just as
well as `ws://` does: same host, same port, same reachability, wrong protocol.

That is what the compose said. The bot's store leg died on it — measured on
the box: `http://ws:8001/sync` failed in 591 ms with *"scheme isn't ws or
wss"*, while `ws://ws:8001/sync` answered a real tool call in 99 ms. Nothing
in the suite measured either, so the container kept reporting healthy while
every search, read and write from the phone was refused.

These tests are that measurement. They need no network: the URL is refused
before a socket is opened, which is the point of checking it there.
"""

from __future__ import annotations

import asyncio

import pytest

from src.bot.ws_client import WebSocketClient, _url_complaint


def test_an_http_url_is_refused_and_names_the_scheme() -> None:
    """The message has to say what is wrong with the URL, not where to look."""
    complaint = _url_complaint("http://ws:8001/sync")

    assert complaint is not None
    assert "ws://" in complaint
    assert "wss://" in complaint
    # The old message built an address out of the URL and sent the reader to
    # `http:8001/sync`, which is not a host and not a port.
    assert "http:8001" not in complaint


@pytest.mark.parametrize("url", ["ws://ws:8001/sync", "wss://ws:8001/sync"])
def test_both_websocket_schemes_pass(url: str) -> None:
    assert _url_complaint(url) is None


def test_the_call_refuses_a_wrong_scheme_before_opening_a_socket() -> None:
    """The refusal happens with no network: there is nothing to reach.

    A guard that needed the box would be a guard that only runs on the box,
    which is how the defect survived — the compose was never asked what
    protocol it named.
    """
    client = WebSocketClient("http://ws:8001/sync", "token")

    async def attempt() -> None:
        await client.call("search_artifacts", {"query": {"text": "x", "limit": 1}})

    with pytest.raises(RuntimeError) as raised:
        asyncio.run(attempt())

    assert "ws://" in str(raised.value)
