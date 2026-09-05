"""Fork connectivity smoke tests — verify each MCP fork client is reachable.

Per Phase 8.3: 4 forks (taskdog, solverforge-calendar, tuiboard, native CLI).
Tests skip gracefully when fork binary is not installed (Windows-friendly).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
from http.server import HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any

import pytest

from sys_ikigai.gateway import UnifiedMCPGateway

# ---------------------------------------------------------------------------
# Path setup (same pattern as conftest.py — mirrors its sys.path setup)
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_IKIGAI_PKG_ROOT = _THIS.parent.parent  # <repo-root>/src/ikigai/
_SRC_ROOT = _THIS.parent.parent.parent  # <repo-root>/src/
_REPO_ROOT = _THIS.parent.parent.parent.parent  # <repo-root>
for _p in (str(_IKIGAI_PKG_ROOT), str(_SRC_ROOT), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _binary_available(name: str) -> bool:
    """Check if binary is on PATH (Windows-aware)."""
    return shutil.which(name) is not None


def _spawn_jsonrpc(
    cmd: list[str],
    method: str,
    params: dict[str, Any] | None = None,
    timeout_s: float = 15.0,
) -> dict | None:
    """Spawn subprocess; send JSON-RPC request; return parsed response or None."""
    try:
        request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        try:
            stdout_bytes, _stderr_bytes = proc.communicate(
                input=json.dumps(request).encode("utf-8"),
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            return None
        if proc.returncode != 0:
            return None
        return json.loads(stdout_bytes.decode("utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Per-fork import smoke tests
# ---------------------------------------------------------------------------


def test_taskdog_client_imports():
    """taskdog fork client module is importable."""
    from sys_ikigai.gateway.clients import taskdog

    assert taskdog is not None
    assert hasattr(taskdog, "taskdog_adapter")


def test_solverforge_client_imports():
    """solverforge-calendar fork client module is importable."""
    from sys_ikigai.gateway.clients import solverforge_calendar

    assert solverforge_calendar is not None
    assert hasattr(solverforge_calendar, "solverforge_calendar_adapter")


def test_tuiboard_client_imports():
    """tuiboard fork client module is importable."""
    from sys_ikigai.gateway.clients import tuiboard

    assert tuiboard is not None
    assert hasattr(tuiboard, "tuiboard_adapter")


def test_cli_client_imports():
    """native CLI fork client module is importable."""
    from sys_ikigai.gateway.clients import cli

    assert cli is not None
    assert hasattr(cli, "cli_adapter")


# ---------------------------------------------------------------------------
# Per-fork factory smoke tests (no subprocess needed)
# ---------------------------------------------------------------------------


def test_taskdog_adapter_factory_wires():
    """taskdog_adapter() returns a StdioAdapter with correct name."""
    from sys_ikigai.gateway.clients.taskdog import taskdog_adapter

    adapter = taskdog_adapter()
    assert adapter.name == "taskdog"
    assert len(adapter.command) == 3
    assert adapter.command[0] == "python"
    assert adapter.command[1:] == ["-m", "taskdog_mcp.server"]


def test_solverforge_adapter_factory_wires():
    """solverforge_calendar_adapter() returns a StdioAdapter with correct name."""
    from sys_ikigai.gateway.clients.solverforge_calendar import solverforge_calendar_adapter

    adapter = solverforge_calendar_adapter()
    assert adapter.name == "solverforge-calendar"
    assert len(adapter.command) == 3
    assert adapter.command[0] == "python"
    assert adapter.command[1:] == ["-m", "solverforge_calendar.server"]


def test_tuiboard_adapter_factory_wires():
    """tuiboard_adapter() returns a StdioAdapter with correct name."""
    from sys_ikigai.gateway.clients.tuiboard import tuiboard_adapter

    adapter = tuiboard_adapter()
    assert adapter.name == "tuiboard"
    assert len(adapter.command) >= 1


def test_cli_adapter_factory_wires():
    """cli_adapter() returns a StdioAdapter with correct name."""
    from sys_ikigai.gateway.clients.cli import cli_adapter

    adapter = cli_adapter()
    assert adapter.name == "cli"
    assert len(adapter.command) == 3
    assert adapter.command[1:] == ["-m", "ikigai.cli"]


# ---------------------------------------------------------------------------
# register_default_adapters wires all 4
# ---------------------------------------------------------------------------


def test_register_default_adapters_wires_4_forks():
    """register_default_adapters() registers exactly 4 adapters."""
    from sys_ikigai.gateway import UnifiedMCPGateway, register_default_adapters

    gateway = UnifiedMCPGateway()
    register_default_adapters(gateway)
    names = gateway.adapter_names()
    assert len(names) == 4
    assert set(names) == {"cli", "taskdog", "solverforge-calendar", "tuiboard"}


# ---------------------------------------------------------------------------
# Gateway health_check() method
# ---------------------------------------------------------------------------


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTPServer with one thread per request."""

    daemon_threads = True


def test_health_check_returns_adapter_list():
    """health_check() returns status + adapter list."""
    from sys_ikigai.gateway import UnifiedMCPGateway, register_default_adapters

    gateway = UnifiedMCPGateway()
    register_default_adapters(gateway)
    health = gateway.health_check()
    assert health["status"] == "ok"
    assert "adapters" in health
    assert len(health["adapters"]) == 4
    assert set(health["adapters"]) == {"cli", "taskdog", "solverforge-calendar", "tuiboard"}


# ---------------------------------------------------------------------------
# HTTP /health endpoint smoke test
# ---------------------------------------------------------------------------


def _start_gateway(gateway: UnifiedMCPGateway) -> tuple[str, HTTPServer]:
    """Boot the HTTP server in a background thread."""
    server = _ThreadingHTTPServer(("127.0.0.1", 0), gateway.make_handler())
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://{host}:{port}", server


def _stop_gateway(server: HTTPServer) -> None:
    server.shutdown()
    server.server_close()


def _get_health(url: str) -> dict:
    import urllib.request

    with urllib.request.urlopen(url + "/health", timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_gateway_http_health_endpoint():
    """GET /health on UnifiedMCPGateway returns adapter list."""
    from sys_ikigai.gateway import UnifiedMCPGateway, register_default_adapters

    gateway = UnifiedMCPGateway()
    register_default_adapters(gateway)
    url, server = _start_gateway(gateway)
    try:
        resp = _get_health(url)
        assert resp["status"] == "ok"
        assert "adapters" in resp
        assert len(resp["adapters"]) == 4
    finally:
        _stop_gateway(server)


# ---------------------------------------------------------------------------
# E2E round-trip via HTTP POST /call
# ---------------------------------------------------------------------------


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


def test_gateway_e2e_call_taskdog_via_http():
    """POST /call taskdog namespace → returns 200 + result (mocked)."""
    from sys_ikigai.gateway import UnifiedMCPGateway
    from sys_ikigai.gateway.client_adapter import MCPClientAdapter

    class FakeTaskdog(MCPClientAdapter):
        def __init__(self) -> None:
            super().__init__(name="taskdog", command=["fake"])

        def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            return {"id": "td-1", "status": "queued", "echo": arguments}

    gateway = UnifiedMCPGateway()
    gateway.register(FakeTaskdog())
    url, server = _start_gateway(gateway)
    try:
        resp = _post(
            url,
            {
                "namespace": "taskdog",
                "tool": "taskdog_add",
                "arguments": {"title": "smoke task"},
            },
        )
        assert resp["result"]["id"] == "td-1"
        assert resp["result"]["status"] == "queued"
    finally:
        _stop_gateway(server)


def test_gateway_e2e_unknown_namespace_returns_404():
    """POST /call with unknown namespace → HTTP 404."""
    import urllib.error

    from sys_ikigai.gateway import UnifiedMCPGateway

    gateway = UnifiedMCPGateway()
    url, server = _start_gateway(gateway)
    try:
        with pytest.raises(urllib.error.HTTPError) as exc:
            _post(url, {"namespace": "nonexistent", "tool": "x", "arguments": {}})
        assert exc.value.code == 404
    finally:
        _stop_gateway(server)
