"""Shared JSON-RPC 2.0 stdio server base — used by all fork MCP servers.

Per spec §10 (decisions): hand-rolled JSON-RPC 2.0 over Content-Length-framed
stdio, stdlib only. Each fork server inherits from this base and registers
its own tools via register_tool().
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class StdioServerBase:
    """Base class for fork MCP servers.

    Usage:
        server = StdioServerBase(name="my-fork", version="0.1.0")
        server.register_tool(name="my_tool", handler=my_handler, schema={...})
        server.serve_forever()
    """

    def __init__(self, *, name: str, version: str) -> None:
        self._name = name
        self._version = version
        self._tools: dict[str, tuple[Callable[[dict], dict], dict]] = {}

    def register_tool(
        self,
        *,
        name: str,
        handler: Callable[[dict], dict],
        schema: dict,
    ) -> None:
        """Register a tool. handler takes args dict, returns result dict."""
        self._tools[name] = (handler, schema)

    def handle_request(self, request: dict) -> dict:
        """Dispatch a single JSON-RPC 2.0 request, return a response dict."""
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": self._name, "version": self._version},
                    "capabilities": {"tools": {}},
                }
            elif method == "tools/list":
                result = {
                    "tools": [
                        {"name": name, "inputSchema": schema}
                        for name, (_, schema) in self._tools.items()
                    ]
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                if tool_name not in self._tools:
                    raise ValueError(f"unknown tool: {tool_name}")
                handler, _ = self._tools[tool_name]
                inner = handler(arguments)
                result = {
                    "content": [{"type": "text", "text": _to_json(inner)}],
                    "isError": False,
                }
            elif method == "notifications/cancelled":
                # No-op: client cancels; we just acknowledge by returning empty result
                result = {}
            else:
                return _error_response(req_id, -32601, f"method not found: {method}")
            return _success_response(req_id, result)
        except ValueError as e:
            return _error_response(req_id, -32602, f"invalid params: {e}")
        except Exception as e:
            logger.exception("handler crashed")
            return _error_response(req_id, -32603, f"internal error: {e}")

    def serve_forever(self) -> None:
        """Read Content-Length-framed JSON-RPC requests from stdin, write to stdout.

        Frame format: Content-Length: <N>\\r\\n\\r\\n<N bytes of JSON>

        Uses sys.stdin.buffer (binary mode) because text-mode readline() hangs on
        Windows subprocess pipes (CPython bug). All decoding is ASCII since the
        JSON-RPC framing is ASCII-only.
        """
        while True:
            headers = {}
            while True:
                line = sys.stdin.buffer.readline()
                if not line:  # EOF
                    return
                line = line.decode("ascii", errors="replace").rstrip("\r\n")
                if line == "":
                    break
                if ":" in line:
                    key, val = line.split(":", 1)
                    headers[key.strip().lower()] = val.strip()

            content_length = int(headers.get("content-length", "0"))
            if content_length == 0:
                continue
            payload = sys.stdin.buffer.read(content_length)
            request = _from_json_bytes(payload)
            response = self.handle_request(request)
            sys.stdout.buffer.write(_frame_response(response))
            sys.stdout.buffer.flush()


def _to_json(obj: Any) -> str:
    import json

    return json.dumps(obj)


def _from_json_bytes(data: bytes) -> dict:
    import json

    return json.loads(data.decode("utf-8"))


def _frame_response(response: dict) -> bytes:
    body = _to_json(response).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def _success_response(req_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error_response(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
