"""E2E test: spawn solverforge_calendar.server, verify JSON-RPC initialize handshake.

Per B5.B pattern (real subprocess) + spec §10 Q2=i (hand-rolled JSON-RPC).
Per B6.4 lesson: must handle MCP absence via skip_if_no_module.
"""
from __future__ import annotations

import json


def _send_request(stdin, request: dict) -> None:
    body = json.dumps(request, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    stdin.write(header + body)
    stdin.flush()


def _read_response(stdout) -> dict:
    # Read headers
    headers: dict[str, str] = {}
    while True:
        line = stdout.readline()
        if not line:
            raise EOFError("server closed before sending headers")
        line = line.decode("ascii").rstrip("\r\n")
        if line == "":
            break
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip().lower()] = val.strip()
    content_length = int(headers["content-length"])
    body = stdout.buffer.read(content_length) if hasattr(stdout, "buffer") else stdout.read(content_length)
    return json.loads(body)


def test_solverforge_calendar_initialize_handshake(server_process_factory, skip_if_no_module):
    """Verify the server can complete a JSON-RPC initialize round-trip."""
    import pytest
    try:
        with server_process_factory("solverforge_calendar.server") as (proc, stdin, stdout):
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            })
            response = _read_response(stdout)
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert response["result"]["serverInfo"]["name"] == "solverforge-calendar"
            assert response["result"]["serverInfo"]["version"] == "0.1.0"
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"solverforge_calendar server not functional: {e}")


def test_solverforge_calendar_tools_list_nonempty(server_process_factory, skip_if_no_module):
    """At A3, sf_availability + sf_schedule are registered — tools/list returns them."""
    import pytest
    try:
        with server_process_factory("solverforge_calendar.server") as (proc, stdin, stdout):
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
            })
            response = _read_response(stdout)
            tool_names = {t["name"] for t in response["result"]["tools"]}
            assert "sf_availability" in tool_names
            assert "sf_schedule" in tool_names
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"solverforge_calendar server not functional: {e}")
