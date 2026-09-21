"""gateway_client — singleton accessor for the MCP Gateway server handle.

Architecture:
    v2 Node → mcp_bridge.ikigai_X(**kwargs) → GatewayClient.call(tool_name, args)
        → FastMCP Gateway stdio (production)
        → FakeMcpServer (tests / IKIGAI_DEV_MODE=1 fallback)

The previous bridge bound the server handle as a module-level ``_server``
in mcp_bridge.py — production had to monkey-set it before any call. Phase 6
(decisions #5, #6) lifted that handle into a typed singleton here so:

  - ``mcp_bridge._server`` is a deprecated alias to the same handle
  - ``GatewayClient.call()`` is the canonical surface for direct callers
    (outside the bridge) that want a typed API without touching async
  - ``IKIGAI_DEV_MODE=1`` short-circuits to ``FakeMcpServer`` so
    unit tests / offline development never spawn the stdio subprocess
  - ``reset_gateway_client_singleton()`` lets tests pin a fresh server
    per case (no cross-test state leak)

Production binding flow:
    1. App startup → ``get_gateway_client()`` (returns the live FastMCP
       gateway client)
    2. Test setup → ``reset_gateway_client_singleton(FakeMcpServer())``
    3. IKIGAI_DEV_MODE=1 → ``get_gateway_client()`` returns FakeMcpServer
       so the v2 graph runs end-to-end without subprocess overhead
"""

from __future__ import annotations

import os
from typing import Any, Protocol


class _ServerLike(Protocol):
    """Protocol the singleton must satisfy. Both FastMCP gateway client
    and FakeMcpServer expose ``.call(tool_name, args) -> dict``."""

    def call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]: ...


class GatewayClient:
    """Typed wrapper around the MCP Gateway server handle.

    Why a thin wrapper instead of a bare module-level variable:
      - Type-checked surface for callers outside mcp_bridge
      - Test override via ``reset_gateway_client_singleton(GatewayClient(FakeMcpServer()))``
      - Future-proofs adding OTel span attributes around the call without
        forcing every v2 node to wrap manually
    """

    def __init__(self, server: _ServerLike | None = None) -> None:
        self._server: _ServerLike | None = server

    def call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Forward a tool call to the bound server.

        Raises ``RuntimeError`` if no server is bound — matches the prior
        mcp_bridge contract so drift detectors still trip.
        """
        if self._server is None:
            raise RuntimeError(
                "GatewayClient has no server bound. "
                "Production code must initialize the MCP Gateway client "
                "before calling any ikigai_X tool. "
                "Tests should call reset_gateway_client_singleton(FakeMcpServer())."
            )
        return self._server.call(tool_name, args)

    def bind(self, server: _ServerLike) -> None:
        """Attach a server handle. Idempotent — last writer wins."""
        self._server = server

    def unbind(self) -> None:
        """Detach the current server handle. Useful in test teardown."""
        self._server = None


# ---------------------------------------------------------------------------
# Singleton accessors
# ---------------------------------------------------------------------------

_client: GatewayClient | None = None


def get_gateway_client() -> GatewayClient:
    """Return the process-wide GatewayClient, creating on first call.

    Resolution order:
      1. Already-bound ``_client`` singleton (returns as-is)
      2. ``IKIGAI_DEV_MODE=1`` env var → binds a ``FakeMcpServer``
         (cheap, $0/tick, no stdio subprocess)
      3. Default → returns an UNBOUND ``GatewayClient``. Calls will
         raise ``RuntimeError`` until a real server is bound. This is
         intentional: it surfaces missing initialization instead of
         silently falling back to production outside of dev/test paths.
    """
    global _client
    if _client is not None:
        return _client

    client = GatewayClient()
    if os.environ.get("IKIGAI_DEV_MODE") == "1":
        # Local-only fallback so dev/test runs never spawn the gateway
        # subprocess. Imported lazily to avoid a hard dep on the
        # agents/v2 test fixture path from this module-level location.
        from src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server import (  # type: ignore[import-not-found]
            FakeMcpServer,
        )

        client.bind(FakeMcpServer())
    _client = client
    return _client


def reset_gateway_client_singleton(
    client: GatewayClient | None = None,
) -> GatewayClient:
    """Reset the singleton — test-only entrypoint.

    Pass ``None`` to fully clear (next ``get_gateway_client()`` call
    re-resolves from IKIGAI_DEV_MODE). Pass a fresh ``GatewayClient``
    to pin a specific server for the next test case.

    Returns the new (or cleared) singleton value so callers can capture
    it inline.
    """
    global _client
    if client is None:
        _client = None
    else:
        _client = client
    return _client if _client is not None else get_gateway_client()
