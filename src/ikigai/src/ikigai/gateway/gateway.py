"""UnifiedMCPGateway — HTTP+SSE front, stdio back.

Task 13 of data-model-unification.

Pure stdlib (http.server, socketserver, threading, queue) — no
starlette, no fastapi. CI does not require them and the gateway's
surface is small:

  POST /call      {"namespace", "tool", "arguments"}  → JSON result
  GET  /health                                          → {"status": "ok", "adapters": [...]}
  GET  /events                                          → text/event-stream (SSE, real streaming)

`namespace` resolves to an MCPClientAdapter (Task 14) registered via
`register()`. A request for an unknown namespace returns 404; an
adapter exception returns 502.

SSE streaming (Task 14): /events holds the connection open via chunked
transfer encoding, emits an initial `gateway.ready` event, then loops
on an in-process event bus. Heartbeats every 15s keep idle connections
alive. Client disconnect is detected via BrokenPipeError on write; the
subscriber is unsubscribed and the handler returns. Adapters or other
gateway code call `gateway.publish_event(event, data)` to fan out to
all open SSE clients.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
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
    sse_heartbeat_interval_s: float = 15.0
    sse_subscriber_queue_size: int = 100


class UnifiedMCPGateway:
    def __init__(self, config: GatewayConfig | None = None) -> None:
        self.config = config or GatewayConfig()
        self._adapters: dict[str, MCPClientAdapter] = {}
        # Event bus for /events subscribers (SSE clients). Each subscriber
        # gets its own bounded queue; on overflow, the publish drops the
        # event for that subscriber (slow consumer protection).
        self._event_subscribers: list[queue.Queue[tuple[str, dict[str, Any]]]] = []
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

    # ──────── Event bus (SSE Task 14) ────────

    def subscribe_events(self) -> queue.Queue[tuple[str, dict[str, Any]]]:
        """Register a new SSE subscriber. Returns the bounded queue.

        Caller MUST call `unsubscribe_events(q)` on disconnect.
        """
        q: queue.Queue[tuple[str, dict[str, Any]]] = queue.Queue(
            maxsize=self.config.sse_subscriber_queue_size
        )
        with self._lock:
            self._event_subscribers.append(q)
        return q

    def unsubscribe_events(self, q: queue.Queue[tuple[str, dict[str, Any]]]) -> None:
        with self._lock:
            try:
                self._event_subscribers.remove(q)
            except ValueError:
                pass  # already removed

    def publish_event(self, event: str, data: dict[str, Any]) -> None:
        """Fan out an event to every open SSE subscriber.

        Slow consumers (full queue) silently drop the event for that
        subscriber. Other subscribers still receive it.
        """
        with self._lock:
            subs = list(self._event_subscribers)
        for q in subs:
            try:
                q.put_nowait((event, data))
            except queue.Full:
                logger.warning(
                    "SSE subscriber queue full; dropping event '%s' for slow consumer",
                    event,
                )

    def emit_adapter_call(
        self,
        namespace: str,
        tool: str,
        arguments: dict[str, Any],
    ) -> None:
        """Publish an SSE event after a successful adapter call_tool.

        Event name: ``{namespace}.{tool_short}`` where tool_short strips a
        known namespace prefix (e.g. ``taskdog_add`` → ``add``,
        ``tuiboard_render`` → ``render``, ``sf_schedule`` → ``schedule``).
        If no known prefix matches, the full tool name is used as the
        short form.

        Payload intentionally excludes the result body (potentially large
        or sensitive); consumers can re-fetch via /call if they need it.
        """
        prefix_map = {
            "taskdog": "taskdog_",
            "tuiboard": "tuiboard_",
            "solverforge-calendar": "sf_",
        }
        prefix = prefix_map.get(namespace)
        tool_short = tool[len(prefix):] if prefix and tool.startswith(prefix) else tool
        self.publish_event(
            f"{namespace}.{tool_short}",
            {
                "namespace": namespace,
                "tool": tool,
                "tool_short": tool_short,
                "arguments": arguments,
            },
        )

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
                    self._sse_stream(list(adapters_ref.keys()))
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

                # Fan out an SSE event so subscribers see adapter activity.
                # Result is intentionally NOT in the payload (potentially
                # large / sensitive). Consumers can re-fetch via /call.
                gateway_ref.emit_adapter_call(namespace, tool, arguments)

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

            def _sse_stream(self, adapter_names: list[str]) -> None:
                """Real SSE: hold connection open, emit heartbeat, drain events.

                Wire protocol (Task 14):
                  - HTTP/1.1 chunked transfer encoding (no Content-Length)
                  - initial `gateway.ready` event with adapter list
                  - subsequent events from gateway.publish_event(...)
                  - 15s heartbeat comment (`: heartbeat N`) to keep proxies
                    and clients from closing idle connections
                  - exit cleanly when client disconnects (BrokenPipeError)
                    OR when gateway shuts down

                Each subscriber is a bounded queue; on disconnect we
                unsubscribe so the publisher fan-out stops targeting us.
                """
                sub_q = gateway_ref.subscribe_events()
                heartbeat_s = gateway_ref.config.sse_heartbeat_interval_s

                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self.send_header("Transfer-Encoding", "chunked")
                    self.end_headers()

                    def write_chunk(chunk: bytes) -> bool:
                        """Returns False if client has disconnected."""
                        try:
                            self.wfile.write(
                                f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n"
                            )
                            self.wfile.flush()
                            return True
                        except (BrokenPipeError, ConnectionResetError, OSError) as e:
                            logger.debug("SSE client disconnected: %s", e)
                            return False

                    # Initial ready event so clients know which adapters are live
                    ready_payload = json.dumps(
                        {"adapters": adapter_names}, default=str
                    ).encode()
                    if not write_chunk(
                        b"event: gateway.ready\ndata: " + ready_payload + b"\n\n"
                    ):
                        return

                    last_heartbeat = time.monotonic()
                    # Loop until client disconnect. Pull events from our
                    # subscriber queue with a 1s timeout so we can also
                    # service heartbeat ticks without busy-waiting.
                    while True:
                        try:
                            event, data = sub_q.get(timeout=1.0)
                            payload = json.dumps(data, default=str).encode()
                            chunk = (
                                f"event: {event}\ndata: ".encode()
                                + payload
                                + b"\n\n"
                            )
                            if not write_chunk(chunk):
                                return
                        except queue.Empty:
                            pass

                        now = time.monotonic()
                        if now - last_heartbeat >= heartbeat_s:
                            # SSE comment line — invisible to EventSource consumers,
                            # but keeps the TCP connection warm.
                            if not write_chunk(
                                f": heartbeat {int(now)}\n\n".encode()
                            ):
                                return
                            last_heartbeat = now
                finally:
                    gateway_ref.unsubscribe_events(sub_q)

        return GatewayHandler


__all__ = ["GatewayConfig", "UnifiedMCPGateway"]
