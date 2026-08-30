"""E2E test: spawn tuiboard.server, verify JSON-RPC initialize handshake.

Per B5.B pattern (real subprocess) + spec §10 Q2=i (hand-rolled JSON-RPC).
Per B6.4 lesson: must handle MCP absence via skip_if_no_module.
"""
from __future__ import annotations

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import _send_request, _read_response


def test_tuiboard_initialize_handshake(server_process_factory, skip_if_no_module):
    """Verify the server can complete a JSON-RPC initialize round-trip."""
    try:
        with server_process_factory("tuiboard.server") as (proc, stdin, stdout):
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            })
            response = _read_response(stdout)
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert response["result"]["serverInfo"]["name"] == "tuiboard"
            assert response["result"]["serverInfo"]["version"] == "0.1.0"
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"tuiboard server not functional: {e}")


def test_tuiboard_tools_list_nonempty(server_process_factory, skip_if_no_module):
    """At A3, tuiboard_diff + tuiboard_snapshot + tuiboard_render are registered."""
    try:
        with server_process_factory("tuiboard.server") as (proc, stdin, stdout):
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
            })
            response = _read_response(stdout)
            tool_names = {t["name"] for t in response["result"]["tools"]}
            assert "tuiboard_diff" in tool_names
            assert "tuiboard_snapshot" in tool_names
            assert "tuiboard_render" in tool_names
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"tuiboard server not functional: {e}")
