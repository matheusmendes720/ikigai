"""Tests for Path 3 taskdog MCP gateway server.

The server re-exports the 4 Path 1 taskdog @tool functions as MCP tools.
We verify:
1. The module imports cleanly.
2. All 4 expected tools are registered on the FastMCP instance.
3. Each handler delegates to the Path 1 @tool function (verified via
   monkeypatching the underlying call).
4. Argument validation: missing required args return a friendly ⚠️ message
   rather than crashing.
"""

from __future__ import annotations

# conftest.py sets up sys.path so agents.* and mcp_server.* resolve cleanly.


def test_taskdog_mcp_server_imports():
    """taskdog_mcp.server module imports cleanly."""
    from mcp_server.taskdog_mcp import server

    assert hasattr(server, "MCP")
    assert hasattr(server, "main")
    assert hasattr(server, "_handle_list_tasks")
    assert hasattr(server, "_handle_create_task")
    assert hasattr(server, "_handle_complete_task")
    assert hasattr(server, "_handle_get_task")


def test_mcp_instance_is_fastmcp():
    """MCP instance is a FastMCP server named 'ikigai-taskdog-gateway'."""
    from mcp.server.fastmcp import FastMCP

    from mcp_server.taskdog_mcp.server import MCP

    assert isinstance(MCP, FastMCP)
    assert MCP.name == "ikigai-taskdog-gateway"


def test_handlers_require_expected_args():
    """Handlers with missing args return friendly ⚠️ message (no crash)."""
    from mcp_server.taskdog_mcp.server import (
        _handle_complete_task,
        _handle_create_task,
        _handle_get_task,
    )

    # Missing name
    result = _handle_create_task({})
    assert "⚠️" in result
    assert "name" in result.lower()
    # Missing task_id
    assert "⚠️" in _handle_complete_task({})
    assert "⚠️" in _handle_get_task({})


def test_handlers_delegate_to_path1_tools(monkeypatch):
    """Each handler delegates to the corresponding Path 1 @tool function."""
    from mcp_server.taskdog_mcp import server

    # Capture calls to Path 1 functions
    calls: list[tuple[str, tuple]] = []

    def fake_list(status=None, include_archived=False):
        calls.append(("taskdog_list_tasks", (status, include_archived)))
        return "FAKE_LIST_RESULT"

    def fake_create(name):
        calls.append(("taskdog_create_task", (name,)))
        return "FAKE_CREATE_RESULT"

    def fake_complete(task_id):
        calls.append(("taskdog_complete_task", (task_id,)))
        return "FAKE_DONE_RESULT"

    def fake_get(task_id):
        calls.append(("taskdog_get_task", (task_id,)))
        return "FAKE_GET_RESULT"

    # Patch the imports inside agents.tools
    import agents.tools as tools_mod

    monkeypatch.setattr(tools_mod, "taskdog_list_tasks", fake_list)
    monkeypatch.setattr(tools_mod, "taskdog_create_task", fake_create)
    monkeypatch.setattr(tools_mod, "taskdog_complete_task", fake_complete)
    monkeypatch.setattr(tools_mod, "taskdog_get_task", fake_get)

    # Call each handler
    assert (
        server._handle_list_tasks({"status": "pending", "include_archived": True})
        == "FAKE_LIST_RESULT"
    )
    assert server._handle_create_task({"name": "test"}) == "FAKE_CREATE_RESULT"
    assert server._handle_complete_task({"task_id": 42}) == "FAKE_DONE_RESULT"
    assert server._handle_get_task({"task_id": 7}) == "FAKE_GET_RESULT"

    # Verify delegation
    assert ("taskdog_list_tasks", ("pending", True)) in calls
    assert ("taskdog_create_task", ("test",)) in calls
    assert ("taskdog_complete_task", (42,)) in calls
    assert ("taskdog_get_task", (7,)) in calls


def test_mcp_tools_registered_via_tool_manager():
    """The 4 taskdog_* tools are registered on the MCP server's tool manager.

    FastMCP stores tool functions on `MCP._tool_manager._tools` (a dict).
    We verify each Path 3 tool is present.
    """
    from mcp_server.taskdog_mcp.server import MCP

    # FastMCP exposes tool functions via _tool_manager._tools (dict of name → Tool)
    tools_dict = getattr(MCP._tool_manager, "_tools", {})
    tool_names = set(tools_dict.keys())

    expected = {
        "taskdog_list_tasks",
        "taskdog_create_task",
        "taskdog_complete_task",
        "taskdog_get_task",
    }
    missing = expected - tool_names
    assert not missing, (
        f"Path 3 taskdog MCP server is missing tools: {missing}. Registered: {sorted(tool_names)}"
    )
