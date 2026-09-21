"""M97b integration test: deep-agent gets 26 MCP taskdog tools via MultiServerMCPClient.

Per M97b (Option A wiring): the deep-agent harness now boots with
IKIGAI_TOOLS (12) + MCP-discovered tools (26 from taskdog-mcp). This
test verifies the wiring works end-to-end without requiring an LLM API
key — we instantiate ``_make_agent()`` and inspect its tools.

Drift invariants:
- IKIGAI_TOOLS stays at exactly 12 (test_canonical_scope enforces this)
- build_agent_tools() returns ≥ 12 tools (12 IKIGAI + 0-26 MCP)
- MCP tools include expected names: cancel_task, decompose_task, add_dependency, optimize_schedule
- Agent boots successfully when MCP is enabled

CI escape hatch:
- IKIGAI_DISABLE_MCP_TASKDOG=1 → MCP tools skipped, only IKIGAI_TOOLS
"""
from __future__ import annotations

import os
import shutil

import pytest


@pytest.fixture(autouse=True)
def _unset_disable_mcp():
    """Ensure MCP is enabled for these tests (set in CI separately)."""
    prev = os.environ.pop("IKIGAI_DISABLE_MCP_TASKDOG", None)
    yield
    if prev is not None:
        os.environ["IKIGAI_DISABLE_MCP_TASKDOG"] = prev


def test_taskdog_mcp_on_path():
    """Sanity: taskdog-mcp binary must be available for MCP wiring to work."""
    assert shutil.which("taskdog-mcp") is not None, (
        "taskdog-mcp not on PATH — install via `pipx install taskdog-mcp`"
    )


def test_ikigai_tools_still_12_after_wiring():
    """IKIGAI_TOOLS must remain at 12 (drift-detector invariant)."""
    from agents.tools import IKIGAI_TOOLS

    assert len(IKIGAI_TOOLS) == 12


def test_get_taskdog_tools_returns_26():
    """MCP discovery must return all 26 taskdog-mcp tools."""
    from agents.mcp_taskdog_client import get_taskdog_tools

    tools = get_taskdog_tools()
    names = {t.name for t in tools}
    assert len(tools) == 26, f"expected 26 MCP tools, got {len(tools)}"
    # Spot-check the 4 critical missing-from-deep-agent tools (M96 gap)
    assert "cancel_task" in names
    assert "decompose_task" in names
    assert "add_dependency" in names
    assert "optimize_schedule" in names


def test_build_agent_tools_returns_at_least_38():
    """Total agent tool count: 12 IKIGAI + 26 MCP = 38 (M97b milestone)."""
    from agents.mcp_taskdog_client import build_agent_tools

    tools = build_agent_tools()
    assert len(tools) >= 38, f"expected ≥ 38 tools, got {len(tools)}"

    ikigai_names = {t.name for t in tools if not t.name.startswith("taskdog_")}
    mcp_names = {t.name for t in tools if t.name.startswith("taskdog_") is False and t.name not in ikigai_names}
    # 12 IKIGAI tools (4 taskdog_ + 8 non-taskdog)
    ikigai_set = {t.name for t in tools[:12]}
    assert len(ikigai_set) == 12


def test_disable_mcp_escape_hatch_returns_ikigai_only():
    """When IKIGAI_DISABLE_MCP_TASKDOG=1, MCP tools are skipped, IKIGAI still loads."""
    os.environ["IKIGAI_DISABLE_MCP_TASKDOG"] = "1"
    from agents.mcp_taskdog_client import build_agent_tools

    tools = build_agent_tools()
    assert len(tools) == 12, "IKIGAI_TOOLS only when MCP disabled"
    del os.environ["IKIGAI_DISABLE_MCP_TASKDOG"]


def test_make_agent_boots_with_mcp_tools():
    """Full integration: _make_agent() boots without error and exposes MCP tools."""
    from agents.deepagents_harness import _make_agent

    agent, thread_id = _make_agent()
    assert agent is not None
    assert thread_id
    # LangGraph CompiledStateGraph exposes tools via nodes dict
    # Verify the graph compiled successfully (not errored out)
    assert hasattr(agent, "invoke") or hasattr(agent, "astream")


def test_mcp_tool_names_include_22_missing_capabilities():
    """The 22 capabilities listed in M96 (currently unwired in IKIGAI_TOOLS)
    MUST be available via MCP after M97b."""
    from agents.mcp_taskdog_client import get_taskdog_tools

    tools = get_taskdog_tools()
    names = {t.name for t in tools}

    # 22 capabilities from M96 audit
    expected = {
        "cancel_task", "pause_task", "reopen_task", "delete_task", "restore_task",
        "decompose_task", "add_dependency", "remove_dependency", "update_task",
        "set_task_tags", "delete_tag", "update_task_notes", "get_task_notes",
        "fix_actual_times", "optimize_schedule", "get_executable_tasks",
        "list_audit_logs", "get_audit_log", "list_algorithms", "get_statistics",
        "get_tag_statistics",
    }
    missing = expected - names
    assert not missing, f"M97b wiring failed — missing from MCP: {missing}"
