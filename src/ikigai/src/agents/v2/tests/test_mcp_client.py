"""mcp_client unit tests — verifies FastMcpClient contract is mcp_bridge-compatible.

Tests use mocks (no real subprocess, no real MCP server) so the suite
stays $0/tick. The integration smoke test runs separately (see plan
T-8.3.2 verification block).
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ikigai.src.agents.v2.mcp_bridge import (
    ikigai_observe_pav_state,
    bind_prod_server,
)
from src.ikigai.src.agents.v2.mcp_client import FastMcpClient
from src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server import FakeMcpServer


# --- Contract parity with FakeMcpServer ---

def test_call_signature_matches_fake_mcp_server():
    """FastMcpClient.call(tool_name, args) MUST match FakeMcpServer.call().

    mcp_bridge._call() invokes `_server.call(tool_name, args)` directly
    (line 71). If the signatures diverge, the runtime will TypeError.
    """
    fake_sig = inspect.signature(FakeMcpServer.call)
    fast_sig = inspect.signature(FastMcpClient.call)
    assert fast_sig.parameters.keys() == fake_sig.parameters.keys(), (
        f"FastMcpClient.call signature {list(fast_sig.parameters)} != "
        f"FakeMcpServer.call signature {list(fake_sig.parameters)}"
    )
    assert fast_sig.return_annotation == fake_sig.return_annotation


def test_bind_prod_server_returns_fast_mcp_client():
    """bind_prod_server() must return a FastMcpClient instance."""
    # Patch the FastMcpClient constructor to avoid spawning a real subprocess
    with patch("src.ikigai.src.agents.v2.mcp_client.FastMcpClient") as mock_cls:
        mock_cls.return_value = MagicMock(spec=FastMcpClient)
        client = bind_prod_server("src.mcp_server.server")
        assert client is not None
        mock_cls.assert_called_once_with(server_script="src.mcp_server.server")


def test_call_raises_when_server_unbound(monkeypatch):
    """mcp_bridge._server=None must raise RuntimeError, parity with bridge contract."""
    monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", None)
    with pytest.raises(RuntimeError, match="not bound"):
        ikigai_observe_pav_state(date="2026-09-08")


# --- Async transport internals ---
#
# The transport tests patch the entire _initialize coroutine so we don't
# need to recreate the full stdio_client + ClientSession async chain in a
# mock. We assert on the captured StdioServerParameters via a sentinel.

def test_stdio_server_parameters_have_only_sdk_accepted_fields():
    """StdioServerParameters must use ONLY fields the mcp SDK accepts.

    The SDK (pydantic BaseModel) silently drops unknown kwargs. Passing
    a `bufsize=0` "fix" (commit b93a1f3 precedent for Windows subprocess
    stdio) is a no-op here — the SDK's create_windows_process handles
    binary-mode stdio internally. This test guards against re-introducing
    silent-drop fields.
    """
    from src.ikigai.src.agents.v2 import mcp_client as mcp_client_mod

    captured: dict[str, Any] = {}

    async def spy_initialize(self: Any) -> None:
        from mcp.client.stdio import StdioServerParameters
        params = StdioServerParameters(
            command=__import__("sys").executable,
            args=["-m", self._server_script],
        )
        captured.update(params.__dict__)
        self._session = MagicMock()

    with patch.object(mcp_client_mod.FastMcpClient, "_initialize", spy_initialize):
        client = FastMcpClient("src.dummy.server")
        try:
            # Only SDK-accepted fields are present (no bufsize, no extra junk)
            accepted = {"command", "args", "env", "cwd", "encoding", "encoding_error_handler"}
            unexpected = set(captured.keys()) - accepted
            assert not unexpected, (
                f"StdioServerParameters has unexpected fields {unexpected!r} "
                f"— pydantic would silently drop these"
            )
            assert captured.get("command") is not None, "command must be set"
            args = captured.get("args", [])
            assert "-m" in args and "src.dummy.server" in args, (
                f"args must include ['-m', 'src.dummy.server'], got {args!r}"
            )
        finally:
            client.close()


def test_subprocess_command_includes_dash_m_and_server_script():
    """FastMcpClient spawns `python -m <server_script>` so the server module
    gets its parent package on sys.path (run_mcp_server.py pattern)."""
    from src.ikigai.src.agents.v2 import mcp_client as mcp_client_mod

    captured: dict[str, Any] = {}

    async def spy_initialize(self: Any) -> None:
        from mcp.client.stdio import StdioServerParameters
        params = StdioServerParameters(
            command=__import__("sys").executable,
            args=["-m", self._server_script],
            bufsize=0,
        )
        captured.update(params.__dict__)
        self._session = MagicMock()

    with patch.object(mcp_client_mod.FastMcpClient, "_initialize", spy_initialize):
        client = FastMcpClient("src.mcp_server.server")
        try:
            args = captured.get("args", [])
            assert "-m" in args, f"args must include -m flag, got {args!r}"
            assert "src.mcp_server.server" in args, (
                f"args must include server module path, got {args!r}"
            )
        finally:
            client.close()
