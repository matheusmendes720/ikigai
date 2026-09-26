"""mcp_runtime — production binding for .claude/loop/mcp_bridge.py.

Starts a FastMCP stdio client (subprocess running `python -u -m mcp_server`),
wraps it in a sync adapter that exposes `.call(tool, args)` and
`.read_resource(uri)`, and assigns the wrapper to `mcp_bridge._server`. Also
calls `init_tracing()` from `src.ikigai/src/observability/otel_init` so M143
spans actually export in production.

**M146 scope.** Closes the loop-bridge chain (M142 → M143 → M144 → M145 →
M146). Without this module, the bridge works in tests but `loop-tick.sh`
never invokes real MCP tools.

Subprocess args match `.mcp.json` exactly — same command, same `-u` flag
(Windows pipe fix from commit b93a1f3), same cwd, same PYTHONPATH.

Architecture:
    loop-tick.sh (cron)
        → `python -c "from .claude.loop.mcp_runtime import bind_server; bind_server()"`
        → mcp_runtime.bind_server()
            → subprocess.Popen(['python', '-u', '-m', 'mcp_server'], cwd=ikigai_src)
            → asyncio.run(ClientSession(stdio_client(...)))
            → builds `_SyncAdapter(session)` that exposes `.call/.read_resource`
            → assigns to mcp_bridge._server
        → orchestrator prompt runs; calls mcp_bridge.ikigai_mesh_show(...)
            → mcp_bridge._call("ikigai_mesh_show", {...})
            → mcp_bridge._server.call("ikigai_mesh_show", {...})
            → adapter.call_tool(name, args) on the live session
            → result dict back to orchestrator

Tests monkeypatch `_server` per the FakeMcpServer pattern from M142; this
module is only invoked at loop startup, never inside tests (per M142 §Design
choices: "Production binding is M146 — tests use FakeMcpServer").

See `specs/M146-loop-production-binding/SPEC.md` for full design rationale.
"""

from __future__ import annotations

import asyncio
import atexit
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ---------------------------------------------------------------------------
# Path constants — match .mcp.json "ikigai" server config
# ---------------------------------------------------------------------------

# Repo root: this file lives at <repo>/.claude/loop/mcp_runtime.py
REPO_ROOT = Path(__file__).resolve().parents[2]
IKIGAI_SRC_DIR = REPO_ROOT / "src" / "ikigai" / "src"
BRIDGE_PATH = REPO_ROOT / ".claude" / "loop" / "mcp_bridge.py"

# Subprocess command — prefer IKIGAI venv at src/ikigai/.venv (one level
# above src/); fall back to current interpreter. This matches what
# `ikigai.bat` and pytest use for the IKIGAI test suite.
IKIGAI_VENV_PYTHON = REPO_ROOT / "src" / "ikigai" / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
PYTHON_BIN = str(IKIGAI_VENV_PYTHON if IKIGAI_VENV_PYTHON.exists() else sys.executable)

# Subprocess args — `-u` is the Windows pipe fix (commit b93a1f3)
SUBPROCESS_ARGS = ["-u", "-m", "mcp_server"]


# ---------------------------------------------------------------------------
# Sync adapter — wraps ClientSession (async) into a sync call/read surface
# ---------------------------------------------------------------------------


class _SyncAdapter:
    """Sync wrapper around an async `ClientSession`.

    Exposes the same surface that M142-M145 tests mock with MagicMock:
      - `.call(tool_name: str, args: dict) -> dict` (for tool wrappers)
      - `.read_resource(uri: str) -> Any` (for M145 resource accessors)

    The async ClientSession is driven by `asyncio.run` per call. This is
    correct but not pooled (M148 optimization). Per constitution §2
    (reversibility > cleverness), simple is correct.
    """

    def __init__(self, session: ClientSession, loop: asyncio.AbstractEventLoop) -> None:
        self._session = session
        self._loop = loop

    def call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Sync wrapper around `session.call_tool(name, arguments=...)`."""
        future = asyncio.run_coroutine_threadsafe(
            self._session.call_tool(tool_name, arguments=args),
            self._loop,
        )
        result = future.result()
        # FastMCP returns CallToolResult with .content (list of TextContent
        # etc.). Wrap into a dict for the M142 wrapper contract.
        content = getattr(result, "content", None)
        if content is None:
            return {"raw": result.model_dump() if hasattr(result, "model_dump") else str(result)}
        # If content is a list of TextContent items, concat their .text
        if isinstance(content, list):
            texts = [getattr(c, "text", str(c)) for c in content]
            joined = "\n".join(t for t in texts if t)
            try:
                import json as _json
                return _json.loads(joined)
            except (ValueError, TypeError):
                return {"text": joined, "items": texts}
        return {"text": str(content)}

    def read_resource(self, uri: str) -> Any:
        """Sync wrapper around `session.read_resource(uri)`."""
        future = asyncio.run_coroutine_threadsafe(
            self._session.read_resource(uri),
            self._loop,
        )
        result = future.result()
        # FastMCP returns ReadResourceResult with .contents (list). Return
        # the raw result — the bridge's _parse_resource_envelope() handles
        # the shape (mcp_bridge.py:443+).
        return result


# ---------------------------------------------------------------------------
# Bind / unbind — subprocess lifecycle
# ---------------------------------------------------------------------------


def _resolve_ikigai_python() -> str:
    """Pick the IKIGAI venv python if it exists, else sys.executable.

    Returns the absolute path as a string (subprocess-friendly).
    """
    if IKIGAI_VENV_PYTHON.exists():
        return str(IKIGAI_VENV_PYTHON)
    return sys.executable


def _get_mcp_bridge():
    """Resolve the mcp_bridge module, looking under both its canonical and
    test-aliased names (test files load it via spec_from_file_location).
    """
    # Canonical name first (production: loaded via `from .claude.loop import mcp_bridge`)
    if "mcp_bridge" in sys.modules:
        return sys.modules["mcp_bridge"]
    # Fallback: find any module whose __file__ is the mcp_bridge.py we know about
    for mod in list(sys.modules.values()):
        if mod is None:
            continue
        mod_file = getattr(mod, "__file__", None)
        if mod_file and Path(mod_file).resolve() == BRIDGE_PATH.resolve():
            return mod
    raise ImportError(
        f"mcp_bridge module not found in sys.modules. "
        f"Expected at {BRIDGE_PATH}. Did bind_server() get called?"
    )


def bind_server(*, ikigai_python: str | None = None) -> None:
    """Start the FastMCP server as a subprocess and bind a sync client.

    Side effects:
      - Sets `mcp_bridge._server` to a `_SyncAdapter` instance
      - Registers an `atexit` hook that calls `unbind_server()`

    Raises:
        FileNotFoundError: if the IKIGAI server module can't be located
        RuntimeError: if the subprocess fails to start within timeout
    """
    # Validate IKIGAI source dir FIRST so callers get a clear error even
    # if mcp_bridge hasn't been imported yet (e.g. early startup probe).
    if not IKIGAI_SRC_DIR.exists():
        raise FileNotFoundError(
            f"IKIGAI source dir not found: {IKIGAI_SRC_DIR}. "
            f"Cannot start MCP server without it."
        )

    mcp_bridge = _get_mcp_bridge()

    python = ikigai_python or _resolve_ikigai_python()
    # PYTHONPATH must mirror `.mcp.json` so the server's `from src.mesh.X`
    # imports resolve. Two paths:
    #   - REPO_ROOT: so `src.*` resolves as a top-level package
    #   - REPO_ROOT/src: so the dotted imports work directly
    #   - IKIGAI_SRC_DIR: so the `mcp_server` package itself is importable
    params = StdioServerParameters(
        command=python,
        args=SUBPROCESS_ARGS,
        cwd=str(IKIGAI_SRC_DIR),
        env={
            **os.environ,
            "PYTHONPATH": (
                str(REPO_ROOT) + os.pathsep
                + str(REPO_ROOT / "src") + os.pathsep
                + str(IKIGAI_SRC_DIR)
            ),
        },
    )

    # Spawn the event loop in a background thread so the sync adapter can
    # submit coroutines via `run_coroutine_threadsafe`. The MCP client
    # owns the loop for the lifetime of the connection.
    loop = asyncio.new_event_loop()

    def _run_loop() -> None:
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        finally:
            loop.close()

    import threading

    thread = threading.Thread(target=_run_loop, daemon=True, name="mcp-runtime-loop")
    thread.start()

    # Bridge stdio_client (async ctx manager) into the background loop
    async def _connect() -> tuple[Any, Any]:
        async with stdio_client(params) as (read, write):
            session = ClientSession(read, write)
            await session.initialize()
            # Stash on the loop for later cleanup
            loop._mcp_session = session  # type: ignore[attr-defined]
            loop._mcp_streams = (read, write)  # type: ignore[attr-defined]
            # Keep the session alive forever — unbind_server() will close it
            await asyncio.Event().wait()

    future = asyncio.run_coroutine_threadsafe(_connect(), loop)
    # Wait briefly for initialize() to complete
    try:
        # Poll until _mcp_session is set or 30s elapses (MCP handshake can
        # take 10-20s on slow machines due to module import + socket setup)
        for _ in range(300):
            if hasattr(loop, "_mcp_session"):
                break
            import time as _time
            _time.sleep(0.1)
        else:
            raise RuntimeError(
                "MCP server failed to initialize within 30s. "
                "Check that `python -m mcp_server` works from "
                f"{IKIGAI_SRC_DIR}."
            )
    except Exception:
        # Clean up the loop if init failed
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)
        raise

    session = loop._mcp_session  # type: ignore[attr-defined]
    adapter = _SyncAdapter(session, loop)

    # Mutate mcp_bridge module state — this is the contract M142 established
    mcp_bridge._server = adapter
    mcp_bridge._runtime_loop = loop  # type: ignore[attr-defined]
    mcp_bridge._runtime_thread = thread  # type: ignore[attr-defined]

    # Register cleanup at interpreter exit (defensive — loop-tick.sh
    # typically exits cleanly via os._exit after the orchestrator returns)
    atexit.register(unbind_server)


def unbind_server() -> None:
    """Tear down the subprocess + event loop + ClientSession.

    Safe to call multiple times. Safe to call even if `bind_server()`
    was never called (no-op in that case).
    """
    try:
        mcp_bridge = _get_mcp_bridge()
    except ImportError:
        return  # bridge not loaded — nothing to unbind

    server = getattr(mcp_bridge, "_server", None)
    loop = getattr(mcp_bridge, "_runtime_loop", None)
    thread = getattr(mcp_bridge, "_runtime_thread", None)

    if server is None and loop is None:
        return  # never bound

    # Tell the session to close, then stop the loop
    if loop is not None and hasattr(loop, "_mcp_session"):
        async def _close() -> None:
            session = loop._mcp_session  # type: ignore[attr-defined]
            try:
                await session.close()
            except Exception:
                pass

        try:
            future = asyncio.run_coroutine_threadsafe(_close(), loop)
            future.result(timeout=5)
        except Exception:
            pass  # best-effort cleanup

    if loop is not None:
        try:
            loop.call_soon_threadsafe(loop.stop)
        except Exception:
            pass

    if thread is not None and thread.is_alive():
        thread.join(timeout=5)

    mcp_bridge._server = None
    mcp_bridge._runtime_loop = None  # type: ignore[attr-defined]
    mcp_bridge._runtime_thread = None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Observability initialization
# ---------------------------------------------------------------------------


def init_observability() -> bool:
    """Call `init_tracing()` from `src.ikigai/src.observability/otel_init`.

    Returns True if tracing was newly initialized, False if it was already
    initialized (the underlying `init_tracing()` is idempotent).

    Safe to call without LangSmith/Langfuse credentials — `init_tracing()`
    only enables exporters whose env vars are set; works local-only.

    Per constitution §5 (state on disk, not in conversation), spans export
    to disk/file even without remote exporters — the OTel SDK always writes
    to whatever processor is configured.
    """
    try:
        from src.ikigai.src.observability.otel_init import init_tracing, _INITIALIZED
    except ImportError as exc:
        raise ImportError(
            f"Cannot import init_tracing from src.ikigai.src.observability.otel_init: {exc}. "
            f"Make sure src/ is on PYTHONPATH and the IKIGAI venv is installed."
        ) from exc

    was_initialized = _INITIALIZED
    init_tracing()
    return not was_initialized
