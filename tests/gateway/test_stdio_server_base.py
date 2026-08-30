"""Tests for the shared JSON-RPC 2.0 stdio server transport."""
from __future__ import annotations

from ikigai.gateway.stdio_server_base import StdioServerBase


def test_handle_initialize_returns_server_info():
    server = StdioServerBase(name="test-server", version="0.0.1")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
    }
    response = server.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["serverInfo"]["name"] == "test-server"
    assert response["result"]["serverInfo"]["version"] == "0.0.1"


def test_handle_tools_list_returns_registered_tools():
    server = StdioServerBase(name="test", version="0.1.0")

    def echo(args: dict) -> dict:
        return {"echoed": args}

    server.register_tool(name="echo", handler=echo, schema={"type": "object"})
    request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    response = server.handle_request(request)
    assert response["result"]["tools"][0]["name"] == "echo"


def test_handle_tools_call_invokes_handler():
    server = StdioServerBase(name="test", version="0.1.0")
    server.register_tool(
        name="double",
        handler=lambda args: {"result": args["x"] * 2},
        schema={"type": "object", "properties": {"x": {"type": "integer"}}},
    )
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "double", "arguments": {"x": 21}},
    }
    response = server.handle_request(request)
    assert response["result"]["content"][0]["text"] == '{"result": 42}'


def test_handle_unknown_method_returns_error():
    server = StdioServerBase(name="test", version="0.1.0")
    request = {"jsonrpc": "2.0", "id": 4, "method": "does/not/exist", "params": {}}
    response = server.handle_request(request)
    assert response["error"]["code"] == -32601
    assert "does/not/exist" in response["error"]["message"]
