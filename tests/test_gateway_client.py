"""Tests for gateway_client.py — singleton + IKIGAI_DEV_MODE fallback.

Phase 6 (decisions #5, #6) introduced GatewayClient as the typed
accessor over the MCP Gateway server handle. Two behaviors matter:

  1. Singleton: get_gateway_client() returns the same instance across
     calls within a process; reset_gateway_client_singleton() clears it.
  2. Dev-mode fallback: IKIGAI_DEV_MODE=1 binds a FakeMcpServer so
     dev/test runs never spawn the gateway subprocess.

The unbound state must raise RuntimeError on .call() to surface missing
initialization instead of silently returning empty dicts.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from src.ikigai.src.gateway_client import (  # type: ignore[import-not-found]
    GatewayClient,
    get_gateway_client,
    reset_gateway_client_singleton,
)


class _RecordingServer:
    """Minimal Protocol-conforming server for direct .call() tests.

    Mirrors FakeMcpServer's call surface without depending on the
    test-fixture module — keeps this test self-contained.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, args))
        return {"tool": tool_name, "echo": args}


@pytest.fixture(autouse=True)
def _isolate_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force IKIGAI_DEV_MODE off by default so we test explicit paths.

    Per-case dev-mode tests opt-in by setting the env var directly.
    """
    monkeypatch.delenv("IKIGAI_DEV_MODE", raising=False)
    reset_gateway_client_singleton(None)


def test_get_gateway_client_returns_same_instance() -> None:
    """Singleton contract — two calls return the same object."""
    a = get_gateway_client()
    b = get_gateway_client()
    assert a is b


def test_get_gateway_client_unbound_call_raises() -> None:
    """Without IKIGAI_DEV_MODE=1 and without a bound server, .call() must raise."""
    client = get_gateway_client()
    assert client._server is None  # unbound by default
    with pytest.raises(RuntimeError, match="no server bound"):
        client.call("ikigai_decompose", {"task_id": "x"})


def test_reset_gateway_client_singleton_clears() -> None:
    """reset_gateway_client_singleton(None) clears the singleton so a fresh
    resolution happens on next get_gateway_client()."""
    first = get_gateway_client()
    assert first is not None
    reset_gateway_client_singleton(None)
    second = get_gateway_client()
    # New instance — previous singleton discarded.
    assert second is not first


def test_reset_gateway_client_singleton_pins_server() -> None:
    """reset_gateway_client_singleton(client) installs a pre-bound client
    so the next call goes through it without env-var ceremony."""
    server = _RecordingServer()
    pinned = GatewayClient(server=server)
    reset_gateway_client_singleton(pinned)
    client = get_gateway_client()
    assert client is pinned
    result = client.call("ikigai_observe_state", {"date": "2026-09-14"})
    assert result == {"tool": "ikigai_observe_state", "echo": {"date": "2026-09-14"}}
    assert server.calls == [("ikigai_observe_state", {"date": "2026-09-14"})]


def test_ikigai_dev_mode_fallback_binds_fake_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """IKIGAI_DEV_MODE=1 → singleton binds FakeMcpServer, so .call() works
    out-of-the-box without a real gateway subprocess."""
    # Order matters: set the env var BEFORE clearing the singleton so the
    # next get_gateway_client() call resolves through the dev-mode branch.
    monkeypatch.setenv("IKIGAI_DEV_MODE", "1")
    reset_gateway_client_singleton(None)
    client = get_gateway_client()
    assert client._server is not None
    # FakeMcpServer has the protocol methods but raises KeyError on
    # uncanned calls — verify the dev-mode bind exists by class identity.
    assert type(client._server).__name__ == "FakeMcpServer"


def test_gateway_client_bind_and_unbind() -> None:
    """Direct .bind() / .unbind() lifecycle on a GatewayClient instance."""
    client = GatewayClient()
    server = _RecordingServer()
    client.bind(server)
    assert client._server is server
    result = client.call("ikigai_decompose", {"task_id": "t1"})
    assert result == {"tool": "ikigai_decompose", "echo": {"task_id": "t1"}}
    client.unbind()
    assert client._server is None
    with pytest.raises(RuntimeError):
        client.call("ikigai_decompose", {"task_id": "t1"})