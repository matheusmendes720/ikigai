"""mcp_runtime — production binding for .claude/loop/mcp_bridge.py.

Starts a FastMCP stdio subprocess (`python -u -m mcp_server`), wraps it in
a sync adapter that exposes `.call(tool, args)` and `.read_resource(uri)`,
and assigns the wrapper to `mcp_bridge._server`. Also calls
`init_tracing()` from `src/ikigai/src/observability/otel_init` so M143
spans actually export in production.

**M146 + M147 scope.** M146 shipped with `stdio_client` from `mcp` lib,
which uses `anyio.open_process` + `FileReadStream` — that transport fails
on Windows with `BrokenResourceError` (overlapped I/O pipe + worker-thread
read). M147 replaces it with a raw `subprocess.Popen` + dedicated reader
thread that we control directly.

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

import atexit
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Path constants — match .mcp.json "ikigai" server config
# ---------------------------------------------------------------------------

# Repo root: this file lives at <repo>/.claude/loop/mcp_runtime.py
REPO_ROOT = Path(__file__).resolve().parents[2]
IKIGAI_SRC_DIR = REPO_ROOT / "src" / "ikigai" / "src"
BRIDGE_PATH = REPO_ROOT / ".claude" / "loop" / "mcp_bridge.py"

# Subprocess command — prefer IKIGAI venv at src/ikigai/.venv (one level
# above src/); fall back to current interpreter.
_venv_dir = "Scripts" if os.name == "nt" else "bin"
_venv_exe = "python.exe" if os.name == "nt" else "python"
IKIGAI_VENV_PYTHON = REPO_ROOT / "src" / "ikigai" / ".venv" / _venv_dir / _venv_exe
PYTHON_BIN = str(IKIGAI_VENV_PYTHON if IKIGAI_VENV_PYTHON.exists() else sys.executable)

# Subprocess args — `-u` is the Windows pipe fix (commit b93a1f3)
SUBPROCESS_ARGS = ["-u", "-m", "mcp_server"]


# ---------------------------------------------------------------------------
# Raw transport — M147 design. Sidesteps `mcp.client.stdio.stdio_client`
# (which uses anyio + FileReadStream and fails on Windows overlapped pipes).
# ---------------------------------------------------------------------------


class _RawClient:
    """Minimal synchronous JSON-RPC 2.0 client over a subprocess pipe.

    Spawned subprocess runs `python -u -m mcp_server`. We speak JSON-RPC
    directly: write one request line per call to stdin, read lines from
    stdout (parsed by a background thread), and match responses to
    requests by `id`.

    Why not `stdio_client`: see specs/M147-fix-windows-stdio/SPEC.md. The
    upstream client uses `to_thread.run_sync(file.read)` on a pipe that
    uses overlapped I/O, which fails on Windows with BrokenResourceError.

    Thread safety: `call_tool()` and `read_resource()` are safe to call
    from multiple threads — each call gets a unique `_next_id()`, pending
    requests are tracked in `_responses` keyed by id, and the reader
    thread dispatches responses under `_lock`.
    """

    def __init__(self, proc: subprocess.Popen) -> None:
        self._proc = proc
        self._next_id = 0
        self._lock = threading.Lock()
        self._responses: dict[int, dict[str, Any]] = {}
        self._response_event = threading.Event()
        self._stopped = False

        self._reader = threading.Thread(
            target=self._reader_loop, daemon=True, name="mcp-raw-reader"
        )
        self._reader.start()

    def _reader_loop(self) -> None:
        """Background loop: read stdout bytes → parse JSON-RPC lines."""
        try:
            buffer = b""
            while not self._stopped:
                if not self._proc.stdout:
                    break
                # Read line-by-line. BufferedReader.readline() returns as
                # soon as a newline arrives — more reliable than byte-by-byte
                # reads for Windows subprocess pipes.
                line_bytes = self._proc.stdout.readline()
                if not line_bytes:
                    break  # EOF — subprocess closed stdout
                buffer += line_bytes
                # Process complete lines (newline-terminated)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    text = line.decode("utf-8", errors="replace").strip()
                    if not text:
                        continue
                    try:
                        msg = json.loads(text)
                    except json.JSONDecodeError:
                        continue  # ignore non-JSON lines
                    self._dispatch(msg)
        except Exception:
            pass  # reader thread dies silently

    def _send_sync(self, msg: dict[str, Any]) -> None:
        """Write a JSON-RPC message to subprocess stdin (lock-free)."""
        line = (json.dumps(msg) + "\n").encode("utf-8")
        with self._lock:
            if self._proc.stdin:
                self._proc.stdin.write(line)
                self._proc.stdin.flush()

    def _dispatch(self, msg: dict[str, Any]) -> None:
        """Route a JSON-RPC message: response (has `id` + result/error)
        or notification (no id, method present)."""
        if "id" in msg and ("result" in msg or "error" in msg):
            with self._lock:
                self._responses[msg["id"]] = msg
            self._response_event.set()

    def _send(self, method: str, params: dict[str, Any] | None = None) -> int:
        """Write a JSON-RPC request to subprocess stdin. Returns request id."""
        with self._lock:
            self._next_id += 1
            req_id = self._next_id
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            msg["params"] = params
        line = (json.dumps(msg) + "\n").encode("utf-8")
        with self._lock:
            if self._proc.stdin:
                self._proc.stdin.write(line)
                self._proc.stdin.flush()
        return req_id

    def _notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Write a JSON-RPC notification (no `id` field) to subprocess stdin.

        Notifications are fire-and-forget — the server doesn't respond.
        Per JSON-RPC 2.0 spec, a notification's `id` field MUST be omitted
        entirely (not null). FastMCP rejects notifications with an `id`
        field (tries to validate it as a request and fails the literal
        check on `method`).
        """
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        line = (json.dumps(msg) + "\n").encode("utf-8")
        with self._lock:
            if self._proc.stdin:
                self._proc.stdin.write(line)
                self._proc.stdin.flush()

    def _await(self, req_id: int, timeout: float = 30.0) -> dict[str, Any]:
        """Wait for the response matching `req_id`. Returns the full
        JSON-RPC envelope. Raises TimeoutError if no response in time."""
        deadline = timeout
        while deadline > 0:
            with self._lock:
                if req_id in self._responses:
                    return self._responses.pop(req_id)
            # Check event WITHOUT clearing — if set, we have data; the
            # dispatcher will set it again on the next message.
            if self._response_event.is_set():
                # Drain the event but don't lose notifications — loop
                # again to re-check _responses under the lock.
                self._response_event.clear()
                continue
            self._response_event.wait(timeout=min(0.1, deadline))
            deadline -= 0.1
        raise TimeoutError(
            f"No response from MCP server for request id={req_id} within {timeout}s"
        )

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call an MCP tool. Returns the parsed result dict.

        FastMCP returns content as a list of TextContent/etc. items with
        a `.text` field. We extract the JSON payload from the first
        TextContent (matches what stdio_client unwraps).

        Retries on TimeoutError: FastMCP occasionally drops requests
        during/right after the handshake (timing-dependent bug on
        Windows). We retry up to 3 times with 1s delay.
        """
        import time as _time
        last_exc: TimeoutError | None = None
        for attempt in range(3):
            req_id = self._send("tools/call", {"name": name, "arguments": arguments or {}})
            try:
                resp = self._await(req_id, timeout=10.0)
            except TimeoutError as e:
                last_exc = e
                _time.sleep(1.0)
                continue
            if "error" in resp:
                err = resp["error"]
                raise RuntimeError(
                    f"MCP tool '{name}' failed: {err.get('code', '?')} — "
                    f"{err.get('message', '?')}"
                )
            result = resp.get("result", {})
            # FastMCP result shape: {"content": [{"type": "text", "text": "<json>"}], "isError": false}
            content = result.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        try:
                            return json.loads(item["text"])
                        except (json.JSONDecodeError, TypeError):
                            return {"text": item["text"]}
                texts = [item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in content]
                return {"text": "\n".join(texts), "items": texts}
            return {"raw": result}
        raise last_exc if last_exc else RuntimeError(f"MCP tool '{name}' failed: unknown error")

    def read_resource(self, uri: str) -> Any:
        """Read an MCP resource. Returns the raw result envelope.

        The bridge's `_parse_resource_envelope()` (mcp_bridge.py) handles
        the shape.

        Retries on TimeoutError (same reasoning as `call_tool`).
        """
        import time as _time
        last_exc: TimeoutError | None = None
        for attempt in range(3):
            req_id = self._send("resources/read", {"uri": uri})
            try:
                resp = self._await(req_id, timeout=10.0)
            except TimeoutError as e:
                last_exc = e
                _time.sleep(1.0)
                continue
            if "error" in resp:
                err = resp["error"]
                raise RuntimeError(
                    f"MCP resource '{uri}' read failed: {err.get('code', '?')} — "
                    f"{err.get('message', '?')}"
                )
            return resp.get("result", {})
        raise last_exc if last_exc else RuntimeError(f"MCP resource '{uri}' read failed: unknown error")

    def close(self) -> None:
        """Stop the reader thread and terminate the subprocess."""
        self._stopped = True
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
        except Exception:
            pass
        try:
            self._proc.terminate()
            self._proc.wait(timeout=3)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass


class _RawTransport:
    """Spawns the MCP server subprocess and returns a `_RawClient`.

    Mirrors what `stdio_client` + `ClientSession.initialize()` do, but
    with raw subprocess pipes that work reliably on Windows.
    """

    @staticmethod
    def start(python: str, cwd: str, env: dict[str, str]) -> _RawClient:
        """Spawn the subprocess + complete the MCP handshake. Returns a
        connected _RawClient."""
        if not Path(python).exists():
            raise FileNotFoundError(f"Python interpreter not found: {python}")

        proc = subprocess.Popen(
            [python, *SUBPROCESS_ARGS],
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        # Wait for the FastMCP server to enter its event loop before
        # sending any JSON-RPC. Without this, requests sent immediately
        # after Popen get queued in stdin but never processed because the
        # server's main() hasn't reached its run_stdio_async() yet.
        # 5s is required on Windows (shorter waits are unreliable).
        import time as _time
        _time.sleep(5.0)
        # If the subprocess dies in that window, surface the stderr.
        if proc.poll() is not None:
            err = proc.stderr.read1(2000).decode("utf-8", errors="replace") if proc.stderr else ""
            raise RuntimeError(
                f"MCP server subprocess exited during startup (code={proc.returncode}). "
                f"stderr: {err[:500]}"
            )

        client = _RawClient(proc)

        # MCP initialize handshake.
        # NOTE: FastMCP on Windows has TWO quirks:
        # 1. Server doesn't respond to initialize until it receives
        #    `notifications/initialized` (FastMCP-specific ordering).
        # 2. Sending both messages back-to-back without delay also fails —
        #    the server needs a moment between them to process initialize.
        # Solution: send initialize, wait 2s, send notification, await response.
        # We also retry the whole handshake if the first attempt times out —
        # FastMCP is flaky on Windows and we want bind_server() to be reliable.
        last_init_exc: RuntimeError | None = None
        for handshake_attempt in range(2):
            try:
                init_req_id = client._send("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "loop-mcp-bridge", "version": "1.0.0"},
                })
                _time.sleep(3.0)
                # Send initialized notification — this triggers the server
                # to finally send the initialize response.
                client._notify("notifications/initialized", {})
                init_resp = client._await(init_req_id, timeout=15.0)
                if "error" in init_resp:
                    raise RuntimeError(
                        f"MCP initialize failed: {init_resp['error'].get('message')}"
                    )
                return client
            except (TimeoutError, RuntimeError) as e:
                last_init_exc = e
                # Drain any leftover responses from previous attempt
                with client._lock:
                    client._responses.clear()
                _time.sleep(2.0)
        proc.terminate()
        raise RuntimeError(
            f"MCP server handshake failed after retries: {last_init_exc}. "
            f"Check that `python -m mcp_server` works from {IKIGAI_SRC_DIR}."
        ) from last_init_exc


# ---------------------------------------------------------------------------
# Sync adapter — wraps _RawClient (sync) into the surface mcp_bridge expects
# ---------------------------------------------------------------------------


class _SyncAdapter:
    """Sync wrapper around the raw MCP client.

    Exposes the same surface that M142-M145 tests mock with MagicMock:
      - `.call(tool_name: str, args: dict) -> dict` (for tool wrappers)
      - `.read_resource(uri: str) -> Any` (for M145 resource accessors)

    The underlying _RawClient is already synchronous (thread-based),
    so this is essentially a type-narrowing shim.
    """

    def __init__(self, client: _RawClient) -> None:
        self._client = client

    def call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Sync wrapper around `_RawClient.call_tool`."""
        return self._client.call_tool(tool_name, args)

    def read_resource(self, uri: str) -> Any:
        """Sync wrapper around `_RawClient.read_resource`."""
        return self._client.read_resource(uri)

    def close(self) -> None:
        """Tear down the subprocess."""
        self._client.close()


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
        RuntimeError: if the subprocess fails to start or the handshake
            doesn't complete in time
    """
    if not IKIGAI_SRC_DIR.exists():
        raise FileNotFoundError(
            f"IKIGAI source dir not found: {IKIGAI_SRC_DIR}. "
            f"Cannot start MCP server without it."
        )

    mcp_bridge = _get_mcp_bridge()

    python = ikigai_python or _resolve_ikigai_python()
    # PYTHONPATH mirrors `.mcp.json` so the server's `from src.mesh.X`
    # imports resolve. Absolute paths (relative paths are resolved against
    # the subprocess's cwd, not ours).
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([
            str(REPO_ROOT),
            str(REPO_ROOT / "src"),
            str(IKIGAI_SRC_DIR),
        ]),
    }

    client = _RawTransport.start(python, str(IKIGAI_SRC_DIR), env)

    adapter = _SyncAdapter(client)

    mcp_bridge._server = adapter
    mcp_bridge._runtime_client = client  # type: ignore[attr-defined]
    atexit.register(unbind_server)


def unbind_server() -> None:
    """Tear down the subprocess + reader thread.

    Safe to call multiple times. Safe to call even if `bind_server()`
    was never called (no-op in that case).
    """
    try:
        mcp_bridge = _get_mcp_bridge()
    except ImportError:
        return  # bridge not loaded — nothing to unbind

    client = getattr(mcp_bridge, "_runtime_client", None)
    if client is not None:
        try:
            client.close()
        except Exception:
            pass
        mcp_bridge._runtime_client = None  # type: ignore[attr-defined]
    mcp_bridge._server = None


# ---------------------------------------------------------------------------
# Observability initialization
# ---------------------------------------------------------------------------


def init_observability() -> bool:
    """Initialize OpenTelemetry tracing for the loop bridge.

    Idempotent: safe to call multiple times. Returns True if tracing was
    initialized (or already was), False if observability module wasn't
    available (IKIGAI venv missing, no network, etc.).

    Calls `init_tracing()` from `src/ikigai/src/observability/otel_init.py`,
    which wires OTel to LangSmith + Langfuse via two OTLP exporters from a
    single SDK. No-op if the module isn't importable.
    """
    try:
        sys.path.insert(0, str(IKIGAI_SRC_DIR))
        from observability.otel_init import init_tracing  # type: ignore[import-not-found]
    except ImportError:
        return False
    try:
        init_tracing()
        return True
    except Exception:
        return False
