"""StdioAdapter — generic MCP stdio client.

Task 14 of data-model-unification.

Wraps a stdio MCP server (subprocess + JSON-RPC 2.0 over stdin/stdout)
behind the MCPClientAdapter ABC. Used by tuiboard, taskdog, and
solverforge-calendar adapters in this same task.

Implementation:
- spawn subprocess on first call (lazy)
- write Content-Length-framed JSON-RPC requests
- read Content-Length-framed JSON-RPC responses
- monotonic request id; single-writer lock per subprocess
- stderr drained into a ring buffer for diagnostics
- hard timeout per call; subprocess killed on timeout
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from ikigai.gateway.client_adapter import MCPClientAdapter

logger = logging.getLogger(__name__)


@dataclass
class StdioAdapterConfig:
    """Spawn config for a stdio MCP server."""

    command: list[str]
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    call_timeout_s: float = 30.0
    stderr_tail: int = 200


class StdioAdapterError(RuntimeError):
    """Raised when the downstream server returns an error or times out."""


class StdioAdapter(MCPClientAdapter):
    """MCPClientAdapter backed by a stdio subprocess running JSON-RPC 2.0."""

    def __init__(
        self,
        *,
        name: str,
        config: StdioAdapterConfig,
    ) -> None:
        super().__init__(name=name, command=config.command)
        self._config = config
        self._proc: subprocess.Popen[bytes] | None = None
        self._lock = threading.Lock()
        self._next_id = 1
        self._stderr_tail: deque[str] = deque(maxlen=config.stderr_tail)

    # ──────── Lifecycle ────────

    def _ensure_proc(self) -> subprocess.Popen[bytes]:
        if self._proc is not None and self._proc.poll() is None:
            return self._proc
        env = os.environ.copy()
        env.update(self._config.env)
        self._proc = subprocess.Popen(
            self._config.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,  # unbuffered — critical for JSON-RPC framing on Windows pipes
            env=env,
            cwd=self._config.cwd,
        )
        self._next_id = 1
        return self._proc

    def close(self) -> None:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                    self._proc.wait(timeout=2.0)
                except Exception:
                    self._proc.kill()
            self._proc = None

    def stderr_recent(self, n: int = 50) -> list[str]:
        """Last N stderr lines (best-effort, drained at call time)."""
        with self._lock:
            return list(self._stderr_tail)[-n:]

    # ──────── Transport ────────

    def _write_frame(self, payload: bytes) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
        self._proc.stdin.write(header + payload)
        self._proc.stdin.flush()

    def _read_frame(self, timeout_s: float) -> bytes:
        assert self._proc is not None and self._proc.stdout is not None
        deadline = time.monotonic() + timeout_s
        # Read header lines until blank line
        header_lines: list[bytes] = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise StdioAdapterError(f"{self.name}: read header timeout")
            line = self._proc.stdout.readline()
            if not line:
                raise StdioAdapterError(f"{self.name}: subprocess exited (no header)")
            line = line.rstrip(b"\r\n")
            if line == b"":
                break
            header_lines.append(line)
        # Parse Content-Length
        length = 0
        for h in header_lines:
            k, _, v = h.partition(b":")
            if k.strip().lower() == b"content-length":
                try:
                    length = int(v.strip())
                except ValueError as e:
                    raise StdioAdapterError(f"{self.name}: bad Content-Length {v!r}") from e
                break
        if length <= 0:
            raise StdioAdapterError(f"{self.name}: missing Content-Length")
        # Read body
        body = b""
        while len(body) < length:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise StdioAdapterError(f"{self.name}: read body timeout")
            chunk = self._proc.stdout.read(length - len(body))
            if not chunk:
                raise StdioAdapterError(f"{self.name}: subprocess exited mid-body")
            body += chunk
        return body

    def _drain_stderr(self) -> None:
        """Best-effort non-blocking drain of subprocess stderr."""
        assert self._proc is not None and self._proc.stderr is not None
        # `read(N)` blocks until N bytes arrive OR the pipe closes —
        # on Windows with empty stderr this hangs forever. `read1(N)`
        # returns whatever is currently buffered without blocking.
        try:
            data = self._proc.stderr.read1(4096)
        except Exception:
            return
        if not data:
            return
        for line in data.decode("utf-8", errors="replace").splitlines():
            self._stderr_tail.append(line)
            logger.warning("[%s stderr] %s", self.name, line)

    # ──────── Public API ────────

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        with self._lock:
            proc = self._ensure_proc()
            req_id = self._next_id
            self._next_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
            payload = json.dumps(request, default=str).encode("utf-8")
            try:
                self._write_frame(payload)
                response_blob = self._read_frame(self._config.call_timeout_s)
                self._drain_stderr()
            except StdioAdapterError:
                self.close()
                raise

        response = json.loads(response_blob.decode("utf-8"))
        if "error" in response:
            err = response["error"]
            msg = err.get("message", "downstream error") if isinstance(err, dict) else str(err)
            raise StdioAdapterError(f"{self.name}: {msg}")
        result = response.get("result")
        # MCP convention: result has {"content": [{"type": "text", "text": "..."}]}
        # or {"data": ...}. We unwrap text content if present.
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list):
                texts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
                joined = "\n".join(t for t in texts if t)
                if joined:
                    try:
                        return json.loads(joined)
                    except json.JSONDecodeError:
                        return joined
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        return result


__all__ = ["StdioAdapter", "StdioAdapterConfig", "StdioAdapterError"]
