"""mcp_client — stdio binding from mcp_bridge to the FastMCP gateway.

Architecture:
    v2 Node → mcp_bridge.ikigai_X(**kwargs) → sync .call(tool_name, args)
        → FastMcpClient (this module) → persistent background asyncio loop
            → mcp.client.stdio.stdio_client → src.mcp_server.server subprocess

FastMcpClient.call() mirrors FakeMcpServer.call() so the existing test
seam (`monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", ...)`)
continues to work without changes — the only swap is the server object.

The persistent thread + asyncio event loop is required because
`mcp.client.stdio.stdio_client` and `ClientSession.call_tool` are async,
but mcp_bridge._call() is sync (line 71 of mcp_bridge.py calls
`_server.call(tool_name, args)` directly). Spawning an asyncio.run()
per call would respawn the subprocess every call — wasteful and slow.

Windows stdio: the mcp SDK's stdio_client uses `create_windows_process()`
internally (mcp/os/win32/utilities.py) which handles binary-mode stdio
correctly. No extra config needed here — that fix lives in the SDK, not
in our transport.

This module is transport-only — it does NOT add any IKIGAI_TOOLS
wrappers. The 12 canonical IKIGAI_TOOLS remain defined in mcp_bridge.py.
Per ADR-013 (planner-only), no math/policy/scoring wrappers are added.
"""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class FastMcpClient:
    """Sync facade over the async FastMCP stdio client.

    Spawns `python -m <server_script>` as a subprocess, opens the stdio
    transport inside a persistent background asyncio event loop, and
    exposes a synchronous .call(tool_name, args) method that matches
    FakeMcpServer.call().

    Lifecycle:
        client = FastMcpClient("src.mcp_server.server")
        result = client.call("ikigai_health", {})   # blocks until reply
        client.close()                             # graceful shutdown
    """

    def __init__(
        self,
        server_script: str,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> None:
        self._server_script = server_script
        self._env = env
        self._cwd = cwd
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._session: ClientSession | None = None
        self._session_cm: Any = None
        self._transport_cm: Any = None
        self._ready = threading.Event()
        self._init_error: BaseException | None = None
        self._closed = False
        self._start_loop()

    def _start_loop(self) -> None:
        """Spawn the background thread that owns the asyncio event loop."""
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"FastMcpClient[{self._server_script}]",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=30.0):
            raise RuntimeError(
                f"FastMcpClient: init timed out after 30s for {self._server_script!r}"
            )
        if self._init_error is not None:
            raise RuntimeError(
                f"FastMcpClient: failed to initialize {self._server_script!r}: "
                f"{type(self._init_error).__name__}: {self._init_error}"
            ) from self._init_error

    def _run_loop(self) -> None:
        """Background thread entrypoint — owns the asyncio loop until close()."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._initialize())
        except BaseException as exc:  # noqa: BLE001 — surface any init failure
            self._init_error = exc
            self._ready.set()
            self._loop.close()
            return
        self._ready.set()
        self._loop.run_forever()
        try:
            self._loop.close()
        except Exception:
            pass

    async def _initialize(self) -> None:
        """Open the stdio transport + ClientSession inside the background loop."""
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", self._server_script],
            env=self._env,
            cwd=self._cwd,
        )
        self._transport_cm = stdio_client(params)
        read_stream, write_stream = await self._transport_cm.__aenter__()
        self._session_cm = ClientSession(read_stream, write_stream)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()

    def call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Synchronous call facade — mirrors FakeMcpServer.call().

        Dispatches the async _do_call into the background loop and blocks
        until the reply arrives (or 30s timeout). Raises on transport
        failure, server crash, or timeout.
        """
        if self._closed:
            raise RuntimeError("FastMcpClient: already closed")
        if self._loop is None or self._session is None:
            raise RuntimeError("FastMcpClient: not initialized")
        future = asyncio.run_coroutine_threadsafe(
            self._do_call(tool_name, args), self._loop
        )
        return future.result(timeout=30.0)

    async def _do_call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Async call dispatched into the background event loop."""
        assert self._session is not None  # noqa: S101 — guarded by .call()
        result = await self._session.call_tool(tool_name, arguments=args)
        return _extract_result(result)

    def close(self) -> None:
        """Graceful shutdown — tears down the session + transport + loop."""
        if self._closed or self._loop is None or self._thread is None:
            return
        self._closed = True
        try:
            future = asyncio.run_coroutine_threadsafe(self._do_close(), self._loop)
            try:
                future.result(timeout=5.0)
            except Exception:
                pass
        except Exception:
            pass
        try:
            self._loop.call_soon_threadsafe(self._loop.stop)
        except Exception:
            pass
        self._thread.join(timeout=5.0)

    async def _do_close(self) -> None:
        """Tear down session + transport inside the background loop."""
        if self._session_cm is not None:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception:
                pass
            self._session_cm = None
        if self._transport_cm is not None:
            try:
                await self._transport_cm.__aexit__(None, None, None)
            except Exception:
                pass
            self._transport_cm = None
        self._session = None


def _extract_result(result: Any) -> dict[str, Any]:
    """Normalize an mcp CallToolResult into a dict for mcp_bridge consumers."""
    # FastMCP path: structured content (preferred when handler returns dict)
    structured = getattr(result, "structuredContent", None)
    if structured:
        if isinstance(structured, dict):
            # Double-wrap pattern: handler returns JSON string, FastMCP wraps it
            # as {"result": "<json string>"}. Detect + JSON-decode the inner string.
            if len(structured) == 1 and "result" in structured and isinstance(structured["result"], str):
                try:
                    decoded = json.loads(structured["result"])
                    if isinstance(decoded, dict):
                        return decoded
                except (json.JSONDecodeError, ValueError):
                    pass
            return dict(structured)
        try:
            return dict(structured)
        except (TypeError, ValueError):
            pass
    # Fallback: textual content[0].text — JSON decode if possible, else raw
    content = getattr(result, "content", None)
    if not content:
        return {}
    first = content[0]
    text = getattr(first, "text", None)
    if text is None:
        return {"raw": str(first)}
    try:
        decoded = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {"text": text}
    if isinstance(decoded, dict):
        return decoded
    return {"value": decoded}


def bind_server_to_gateway(
    server_script: str,
    env: dict[str, str] | None = None,
) -> FastMcpClient:
    """Spawn the FastMCP gateway subprocess and return a sync-call client.

    This is the production equivalent of `FakeMcpServer()` in tests.
    After binding, call `mcp_bridge.bind_prod_server(server_script)` (the
    re-export) or assign the returned client directly to
    `mcp_bridge._server` before invoking any ikigai_X() function.
    """
    return FastMcpClient(server_script=server_script, env=env)
