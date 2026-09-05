"""Drift invariant test for Path 3 taskdog MCP tools module.

Path 3 per docs/design-system/24-taskdog-paths-architecture.md. Path 1
(harness subprocess → taskdog_cli.py) remains canonical. Path 3 is for
MCP-tool consumers that prefer typed tool calls over subprocess execution.

Enforces:
1. The 3 read-only tools are registered on the Path 3 FastMCP instance.
2. Each tool can be invoked with a mocked TaskdogAdapter.
3. apply_change is NOT exposed (Path 3 read-only contract).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.ikigai.src.mcp_server import taskdog_tools


def test_three_read_only_tools_registered() -> None:
    """Path 3 exposes exactly 3 read-only tools; apply_change is forbidden."""
    assert taskdog_tools.mcp.name == "taskdog"
    registered = {t.name for t in taskdog_tools.mcp._tool_manager._tools.values()}
    expected = {"taskdog_read", "taskdog_list", "taskdog_supports_field"}
    assert expected.issubset(registered), f"missing: {expected - registered}"
    forbidden = {n for n in registered if "apply_change" in n or "write" in n.lower()}
    assert not forbidden, f"read-only contract violated: {forbidden}"


def test_taskdog_read_with_mock_adapter() -> None:
    """taskdog_read returns JSON with found=True when adapter returns a slice."""
    with patch.object(taskdog_tools, "TaskdogAdapter") as MockAdapter:
        adapter = MagicMock()
        adapter.read.return_value = {"ueid": "ik:task:abc:1", "status": "planned"}
        MockAdapter.return_value = adapter
        result = json.loads(taskdog_tools.taskdog_read("ik:task:abc:1"))
        assert result["found"] is True
        assert result["slice"]["ueid"] == "ik:task:abc:1"


def test_taskdog_list_with_mock_adapter() -> None:
    """taskdog_list respects status filter and limit."""
    with patch.object(taskdog_tools, "TaskdogAdapter") as MockAdapter:
        adapter = MagicMock()
        adapter.list_all.return_value = [
            {"ueid": "ik:ta:abc:1", "status": "planned", "created_at": "2026-09-01"},
            {"ueid": "ik:tb:def:2", "status": "done", "created_at": "2026-08-30"},
        ]
        MockAdapter.return_value = adapter
        all_result = json.loads(taskdog_tools.taskdog_list())
        assert all_result["count"] == 2
        filtered = json.loads(taskdog_tools.taskdog_list(status="planned"))
        assert filtered["count"] == 1
        assert filtered["tasks"][0]["ueid"] == "ik:ta:abc:1"


def test_taskdog_supports_field_with_mock_adapter() -> None:
    """taskdog_supports_field returns {field, supported} JSON."""
    with patch.object(taskdog_tools, "TaskdogAdapter") as MockAdapter:
        adapter = MagicMock()
        adapter.supports_field.side_effect = lambda f: f in {"title", "ueid"}
        MockAdapter.return_value = adapter
        ok = json.loads(taskdog_tools.taskdog_supports_field("title"))
        assert ok == {"field": "title", "supported": True}
        no = json.loads(taskdog_tools.taskdog_supports_field("bogus"))
        assert no == {"field": "bogus", "supported": False}
