"""In-process FakeMcpServer for mcp_bridge unit tests.

Replaces the MCP Gateway stdio subprocess with a canned-response
dict lookup. No daemon, no subprocess, $0/tick, <1s/run.
"""

from __future__ import annotations

from typing import Any


class FakeMcpServer:
    """Canned-response mock for the IKIGAI MCP Gateway.

    Usage:
        server = FakeMcpServer()
        server.canned_response("ikigai_observe_pav_state", date="2026-09-08")
        result = server.call("ikigai_observe_pav_state", {"date": "2026-09-08"})
    """

    def __init__(self) -> None:
        self._canned: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def canned_response(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Register a canned response for a tool call.

        kwargs becomes the expected response payload. Pass-through.
        """
        self._canned[tool_name] = dict(kwargs)
        return dict(kwargs)

    def call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Return canned response for tool_name; record the call."""
        self.calls.append((tool_name, args))
        if tool_name not in self._canned:
            raise KeyError(f"FakeMcpServer: no canned response for {tool_name!r}")
        return dict(self._canned[tool_name])
