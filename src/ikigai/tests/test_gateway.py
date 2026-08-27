"""Tests for UnifiedMCPGateway — HTTP+SSE front, stdio back.

Task 13 of data-model-unification.

The gateway is a pure-Python transport shim with no external deps
beyond stdlib (no starlette/fastapi). It's exercised against a fake
downstream client (MCPClientAdapter protocol) so tests don't need a
real socket — see Task 14 for the real downstream adapters.
"""
from __future__ import annotations

import json
import threading
import time
from http.server import HTTPServer
from typing import Any

import pytest

from ikigai.gateway.gateway import UnifiedMCPGateway, GatewayConfig
from ikigai.gateway.client_adapter import MCPClientAdapter


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
    server = HTTPServer(("127.0.0.1", 0), gateway.make_handler())
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
    """SSE endpoint must respond with text/event-stream content type
    and emit at least one event when downstream publishes."""
    cfg = GatewayConfig()
    gateway = UnifiedMCPGateway(cfg)
    gateway.register(FakeAdapter("tuiboard"))

    server = HTTPServer(("127.0.0.1", 0), gateway.make_handler())
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://{host}:{port}"
    try:
        import urllib.request
        req = urllib.request.Request(url + "/events")
        with urllib.request.urlopen(req, timeout=2) as resp:
            ct = resp.headers.get("Content-Type", "")
            assert "text/event-stream" in ct
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_config_defaults() -> None:
    cfg = GatewayConfig()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8765
    assert cfg.max_adapters == 16