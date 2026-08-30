"""Tests for UnifiedMCPGateway — HTTP+SSE front, stdio back.

Task 13 of data-model-unification.

The gateway is a pure-Python transport shim with no external deps
beyond stdlib (no starlette/fastapi). It's exercised against a fake
downstream client (MCPClientAdapter protocol) so tests don't need a
real socket — see Task 14 for the real downstream adapters.
"""
from __future__ import annotations

import json
import queue
import socket
import threading
import time
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from typing import Any

import pytest

from ikigai.gateway.client_adapter import MCPClientAdapter
from ikigai.gateway.gateway import GatewayConfig, UnifiedMCPGateway


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTPServer with one thread per request.

    Required for SSE tests: the SSE handler runs an infinite loop in
    do_GET, which would otherwise block serve_forever (and thus
    server.shutdown()) since BaseHTTPServer dispatches synchronously.
    ThreadingMixIn lets serve_forever exit even while SSE handlers are
    still alive in their own threads.
    """

    daemon_threads = True


class FakeAdapter(MCPClientAdapter):
    """Returns canned responses keyed by tool name."""

    def __init__(self, name: str, responses: dict[str, Any] | None = None) -> None:
        super().__init__(name=name, command=["fake"])
        self.responses = responses or {}
        self.calls: list[dict] = []

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append({"name": name, "arguments": arguments})
        return self.responses.get(name, {"echo": arguments})


def _start_gateway(gateway: UnifiedMCPGateway) -> tuple[str, HTTPServer]:
    """Boot the http loop in a background thread for the duration of one test."""
    server = _ThreadingHTTPServer(("127.0.0.1", 0), gateway.make_handler())
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://{host}:{port}", server


def _stop_gateway(server: HTTPServer) -> None:
    server.shutdown()
    server.server_close()


def _post(url: str, payload: dict) -> dict:
    import urllib.request
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url + "/call",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url: str) -> dict:
    import urllib.request
    with urllib.request.urlopen(url + "/health", timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_gateway_health_endpoint() -> None:
    cfg = GatewayConfig()
    gateway = UnifiedMCPGateway(cfg)
    url, server = _start_gateway(gateway)
    try:
        resp = _get(url)
        assert resp["status"] == "ok"
    finally:
        _stop_gateway(server)


def test_gateway_routes_call_to_named_adapter() -> None:
    cfg = GatewayConfig()
    gateway = UnifiedMCPGateway(cfg)
    fake_tuiboard = FakeAdapter("tuiboard", responses={
        "tuiboard_render": {"status": "rendered", "rows": 4},
    })
    fake_taskdog = FakeAdapter("taskdog")
    gateway.register(fake_tuiboard)
    gateway.register(fake_taskdog)

    url, server = _start_gateway(gateway)
    try:
        resp = _post(url, {
            "namespace": "tuiboard",
            "tool": "tuiboard_render",
            "arguments": {"dashboard_id": "home"},
        })
        assert resp == {"result": {"status": "rendered", "rows": 4}}
        assert len(fake_tuiboard.calls) == 1
        assert len(fake_taskdog.calls) == 0
    finally:
        _stop_gateway(server)


def test_gateway_rejects_unknown_namespace() -> None:
    cfg = GatewayConfig()
    gateway = UnifiedMCPGateway(cfg)
    gateway.register(FakeAdapter("tuiboard"))

    url, server = _start_gateway(gateway)
    try:
        import urllib.error
        with pytest.raises(urllib.error.HTTPError) as exc:
            _post(url, {"namespace": "unknown", "tool": "x", "arguments": {}})
        assert exc.value.code == 404
    finally:
        _stop_gateway(server)


def test_gateway_propagates_adapter_error() -> None:
    class BoomAdapter(MCPClientAdapter):
        def __init__(self) -> None:
            super().__init__(name="boom", command=["fake"])
        def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            raise RuntimeError("downstream exploded")

    cfg = GatewayConfig()
    gateway = UnifiedMCPGateway(cfg)
    gateway.register(BoomAdapter())

    url, server = _start_gateway(gateway)
    try:
        import urllib.error
        with pytest.raises(urllib.error.HTTPError) as exc:
            _post(url, {"namespace": "boom", "tool": "x", "arguments": {}})
        assert exc.value.code == 502
    finally:
        _stop_gateway(server)


def test_gateway_lists_adapters_on_health() -> None:
    cfg = GatewayConfig()
    gateway = UnifiedMCPGateway(cfg)
    gateway.register(FakeAdapter("tuiboard"))
    gateway.register(FakeAdapter("taskdog"))
    gateway.register(FakeAdapter("solverforge-calendar"))

    url, server = _start_gateway(gateway)
    try:
        resp = _get(url)
        assert "adapters" in resp
        assert set(resp["adapters"]) == {"tuiboard", "taskdog", "solverforge-calendar"}
    finally:
        _stop_gateway(server)


def test_sse_endpoint_streams_messages() -> None:
    """SSE endpoint must respond with text/event-stream content type,
    use chunked transfer encoding, and emit at least one initial event
    (gateway.ready with adapter list) before the connection stays open.
    """
    # Short heartbeat so the handler detects our socket close quickly
    # and exits the loop (otherwise server.shutdown() deadlocks).
    cfg = GatewayConfig(sse_heartbeat_interval_s=0.2)
    gateway = UnifiedMCPGateway(cfg)
    gateway.register(FakeAdapter("tuiboard"))

    server = _ThreadingHTTPServer(("127.0.0.1", 0), gateway.make_handler())
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import socket

        sock = socket.create_connection((host, port), timeout=5)
        sock.sendall(b"GET /events HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        sock.settimeout(2.0)
        # Read response headers (terminated by \r\n\r\n)
        buf = b""
        deadline = time.monotonic() + 2.0
        while b"\r\n\r\n" not in buf and time.monotonic() < deadline:
            try:
                chunk = sock.recv(4096)
            except TimeoutError:
                break
            if not chunk:
                break
            buf += chunk
        header_blob, _, body_so_far = buf.partition(b"\r\n\r\n")
        headers = header_blob.decode("iso-8859-1")
        status_line = headers.splitlines()[0] if headers else ""
        assert status_line.startswith("HTTP/1.1 200") or status_line.startswith("HTTP/1.0 200"), (
            f"expected 200, got {status_line!r}"
        )
        assert "Content-Type: text/event-stream" in headers, headers
        assert "Transfer-Encoding: chunked" in headers, headers
        # The initial chunked body must include the gateway.ready event
        assert b"gateway.ready" in body_so_far, (
            f"expected gateway.ready in initial body, got {body_so_far!r}"
        )
        sock.close()  # signals BrokenPipeError → handler exits at next heartbeat
        # Wait long enough for the handler to detect the closed socket and exit.
        # On Windows, BrokenPipeError is delayed (writes can buffer past the
        # close for several iterations before the OS raises); 2s gives ~10
        # heartbeat attempts at 0.2s interval, which exceeds the typical
        # Windows TCP buffer-fill latency.
        time.sleep(2.0)
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_config_defaults() -> None:
    cfg = GatewayConfig()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8765
    assert cfg.max_adapters == 16
    assert cfg.sse_heartbeat_interval_s == 15.0
    assert cfg.sse_subscriber_queue_size == 100


def _sse_handshake(host: str, port: int, timeout: float = 2.0) -> tuple[socket.socket, bytes, bytes]:
    """Open a raw SSE connection; return (sock, status_line, body_so_far).

    Caller MUST close the sock when done.
    """
    sock = socket.create_connection((host, port), timeout=5)
    sock.sendall(b"GET /events HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
    sock.settimeout(timeout)
    buf = b""
    deadline = time.monotonic() + timeout
    while b"\r\n\r\n" not in buf and time.monotonic() < deadline:
        try:
            chunk = sock.recv(4096)
        except TimeoutError:
            break
        if not chunk:
            break
        buf += chunk
    header_blob, _, body_so_far = buf.partition(b"\r\n\r\n")
    return sock, header_blob.decode("iso-8859-1").splitlines()[0], body_so_far


def test_sse_event_bus_fans_out_to_subscribers() -> None:
    """publish_event() must deliver to every open subscriber's queue."""
    cfg = GatewayConfig(sse_heartbeat_interval_s=10.0)  # long enough that no heartbeat fires
    gateway = UnifiedMCPGateway(cfg)
    q_a = gateway.subscribe_events()
    q_b = gateway.subscribe_events()
    try:
        gateway.publish_event("task.created", {"ueid": "ikigai:task:abc:1:2", "title": "demo"})
        ev_a, data_a = q_a.get(timeout=1.0)
        ev_b, data_b = q_b.get(timeout=1.0)
        assert ev_a == "task.created"
        assert ev_b == "task.created"
        assert data_a == {"ueid": "ikigai:task:abc:1:2", "title": "demo"}
        assert data_b == {"ueid": "ikigai:task:abc:1:2", "title": "demo"}
    finally:
        gateway.unsubscribe_events(q_a)
        gateway.unsubscribe_events(q_b)


def test_sse_publish_drops_for_full_subscriber_others_still_receive() -> None:
    """A subscriber with a full queue must be skipped without blocking others."""
    cfg = GatewayConfig(sse_subscriber_queue_size=1)
    gateway = UnifiedMCPGateway(cfg)
    q_full = gateway.subscribe_events()  # maxsize=1 (from config)
    # q_other is registered with capacity large enough to receive every publish
    q_other: queue.Queue = queue.Queue(maxsize=100)
    with gateway._lock:  # type: ignore[attr-defined]
        gateway._event_subscribers.append(q_other)  # type: ignore[attr-defined]
    try:
        # Fill q_full so the next put_nowait raises queue.Full
        q_full.put_nowait(("seed", {}))
        gateway.publish_event("e1", {"k": 1})  # dropped for q_full, delivered to q_other
        gateway.publish_event("e2", {"k": 2})  # dropped for q_full, delivered to q_other
        assert q_full.qsize() == 1  # seed only — first two publishes dropped
        assert q_other.qsize() == 2  # both received
    finally:
        gateway.unsubscribe_events(q_full)
        gateway.unsubscribe_events(q_other)


def test_sse_subscriber_is_removed_after_disconnect() -> None:
    """After the client disconnects, the handler must call unsubscribe_events."""
    cfg = GatewayConfig(sse_heartbeat_interval_s=0.2)
    gateway = UnifiedMCPGateway(cfg)
    gateway.register(FakeAdapter("tuiboard"))

    server = _ThreadingHTTPServer(("127.0.0.1", 0), gateway.make_handler())
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        sock, status_line, _ = _sse_handshake(host, port, timeout=2.0)
        assert "200" in status_line, status_line
        # Subscriber is registered while the handler is alive
        with gateway._lock:  # type: ignore[attr-defined]
            assert len(gateway._event_subscribers) == 1  # type: ignore[attr-defined]
        sock.close()
        # Wait long enough for the next heartbeat write to surface BrokenPipeError
        # (TCP RST propagation on Windows can take a few iterations), then for
        # the handler's finally block to unsubscribe.
        time.sleep(2.0)
        with gateway._lock:  # type: ignore[attr-defined]
            assert gateway._event_subscribers == []  # type: ignore[attr-defined]
    finally:
        server.shutdown()
        server.server_close()
