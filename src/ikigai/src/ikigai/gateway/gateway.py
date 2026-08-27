"""UnifiedMCPGateway — HTTP+SSE front, stdio back.

Task 13 of data-model-unification.

Pure stdlib (http.server, socketserver, threading) — no starlette, no
fastapi. CI does not require them and the gateway's surface is small:

  POST /call      {"namespace", "tool", "arguments"}  → JSON result
  GET  /health                                          → {"status": "ok", "adapters": [...]}
  GET  /events                                          → text/event-stream (SSE)

`namespace` resolves to an MCPClientAdapter (Task 14) registered via
`register()`. A request for an unknown namespace returns 404; an
adapter exception returns 502.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler
from typing import Any

from ikigai.gateway.client_adapter import MCPClientAdapter

logger = logging.getLogger(__name__)


@dataclass
class GatewayConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    max_adapters: int = 16


class UnifiedMCPGateway:
    def __init__(self, config: GatewayConfig | None = None) -> None:
        self.config = config or GatewayConfig()
        self._adapters: dict[str, MCPClientAdapter] = {}
        self._lock = threading.Lock()

    # ──────── Adapter registry ────────

    def register(self, adapter: MCPClientAdapter) -> None:
        with self._lock:
            if len(self._adapters) >= self.config.max_adapters:
                raise RuntimeError(
                    f"adapter cap reached ({self.config.max_adapters}); refusing to register more"
                )
            if adapter.name in self._adapters:
                raise RuntimeError(f"adapter '{adapter.name}' already registered")
            self._adapters[adapter.name] = adapter

    def adapter_names(self) -> list[str]:
        with self._lock:
            return sorted(self._adapters.keys())

    # ──────── HTTP handler factory ────────

    def make_handler(self):  # returns a BaseHTTPRequestHandler subclass
        adapters_ref = self._adapters
        gateway_ref = self

        class GatewayHandler(BaseHTTPRequestHandler):
            # Quieter logs (default stderr spam is unreadable in tests)
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — stdlib name
                logger.debug(format, *args)

            # ──────── Routes ────────

            def do_GET(self) -> None:
                if self.path == "/health":
                    self._json(
                        200,
                        {
                            "status": "ok",
                            "adapters": sorted(adapters_ref.keys()),
                        },
                    )
                elif self.path == "/events":
                    self._sse_event("gateway.ready", {"adapters": list(adapters_ref.keys())})
                else:
                    self._json(404, {"error": "not_found", "path": self.path})

            def do_POST(self) -> None:
                if self.path != "/call":
                    self._json(404, {"error": "not_found", "path": self.path})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length) if length else b""
                    payload = json.loads(body or b"{}")
                except json.JSONDecodeError as e:
                    self._json(400, {"error": "invalid_json", "detail": str(e)})
                    return

                namespace = payload.get("namespace")
                tool = payload.get("tool")
                arguments = payload.get("arguments") or {}

                if not isinstance(namespace, str) or not isinstance(tool, str):
                    self._json(
                        400,
                        {
                            "error": "missing_or_invalid",
                            "expected": ["namespace (str)", "tool (str)", "arguments (dict)"],
                        },
                    )
                    return

                adapter = adapters_ref.get(namespace)
                if adapter is None:
                    self._json(
                        404,
                        {
                            "error": "unknown_namespace",
                            "namespace": namespace,
                            "known": sorted(adapters_ref.keys()),
                        },
                    )
                    return

                try:
                    result = adapter.call_tool(tool, arguments)
                except Exception as e:
                    logger.exception("downstream '%s' tool '%s' failed", namespace, tool)
                    self._json(
                        502,
                        {
                            "error": "downstream_error",
                            "namespace": namespace,
                            "tool": tool,
                            "detail": str(e),
                        },
                    )
                    return

                # Result must be JSON-serialisable; coerce dicts via default=str.
                try:
                    self._json(200, {"result": result})
                except TypeError as e:
                    self._json(
                        500,
                        {
                            "error": "non_serialisable_result",
                            "tool": tool,
                            "detail": str(e),
                        },
                    )

            # ──────── Response helpers ────────

            def _json(self, status: int, payload: dict) -> None:
                body = json.dumps(payload, default=str).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _sse_event(self, event: str, data: dict) -> None:
                # Minimal SSE: one event, then close the connection. Real
                # downstream event streaming is added in Task 14.
                payload = json.dumps(data, default=str)
                body = f"event: {event}\ndata: {payload}\n\n".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return GatewayHandler


__all__ = ["GatewayConfig", "UnifiedMCPGateway"]
