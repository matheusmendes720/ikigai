"""The transport binds the address a CLIENT uses (contract C-2).

FastMCP takes the host as a constructor argument and reads nothing from the
environment: `mcp.run()` accepts only the transport, and the default host is
the loopback. A container that sets `FASTMCP_HOST` and trusts the library to
honour it ends up with a server bound to 127.0.0.1 — unreachable from every
other container, and from the host.

Worse, the healthcheck that connects to 0.0.0.0 would still pass: the kernel
resolves 0.0.0.0 to the loopback, so a server that only listens there answers
it. That is the green lie C-2 warns about, produced by the check that exists
to prevent it.

These tests pin the three things that have to hold together:

1. the address comes from the environment;
2. the running server and the resolver cannot disagree;
3. the healthcheck dials the client-reachable address, not the bind address.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("mcp", reason="the MCP SDK is required for the transport tests")


@pytest.fixture(scope="module")
def transport() -> Any:
    from src.transport import mcp_server

    return mcp_server


def test_the_bind_address_comes_from_the_environment(
    transport: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FASTMCP_HOST", "0.0.0.0")
    monkeypatch.setenv("FASTMCP_PORT", "9001")

    assert transport.transport_host() == "0.0.0.0"
    assert transport.transport_port() == 9001


def test_the_default_bind_address_is_the_loopback(
    transport: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loopback is the safe default: a service is not exposed by accident."""
    monkeypatch.delenv("FASTMCP_HOST", raising=False)
    monkeypatch.delenv("FASTMCP_PORT", raising=False)

    assert transport.transport_host() == "127.0.0.1"
    assert transport.transport_port() == 8000


def test_a_port_that_is_not_a_number_is_rejected(
    transport: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FASTMCP_PORT", "eight thousand")

    with pytest.raises(ValueError, match="FASTMCP_PORT"):
        transport.transport_port()


def test_the_running_server_binds_the_address_the_resolver_names(transport: Any) -> None:
    """The instance and the resolver cannot drift apart."""
    assert transport.mcp.settings.host == transport.transport_host()
    assert transport.mcp.settings.port == transport.transport_port()


def test_the_healthcheck_dials_a_client_reachable_address() -> None:
    from src.transport.healthcheck import _client_address

    assert _client_address("127.0.0.1") == "127.0.0.1"

    try:
        address = _client_address("0.0.0.0")
    except RuntimeError:
        pytest.skip("this host has no address a client could reach")

    assert not address.startswith("127."), (
        "a wildcard bind must resolve to a non-loopback address: connecting to "
        "the loopback would pass on a server no other container can reach"
    )
