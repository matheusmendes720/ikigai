"""M108 tests: Claude Code MCP config has taskdog-mcp registered.

Per M108: .mcp.json lists both `ikigai` and `taskdog` MCP servers so
Claude Code can invoke either via its MCP protocol.

Tests:
- test_mcp_config_exists: .mcp.json is valid JSON
- test_ikigai_server_registered: ikigai MCP server entry present
- test_taskdog_server_registered: taskdog MCP server entry present (NEW M108)
- test_taskdog_command_in_path: taskdog-mcp binary is callable
- test_mcp_servers_count: at least 2 servers
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_CONFIG = REPO_ROOT / ".mcp.json"


def test_mcp_config_exists() -> None:
    assert MCP_CONFIG.exists(), f".mcp.json not found at {MCP_CONFIG}"
    json.loads(MCP_CONFIG.read_text())  # valid JSON


def test_mcp_servers_count() -> None:
    config = json.loads(MCP_CONFIG.read_text())
    servers = config.get("mcpServers", {})
    assert len(servers) >= 2, f"expected ≥2 servers, got {len(servers)}: {list(servers)}"


def test_ikigai_server_registered() -> None:
    config = json.loads(MCP_CONFIG.read_text())
    ikigai = config["mcpServers"].get("ikigai")
    assert ikigai is not None
    assert "command" in ikigai
    assert ikigai["command"] == "python"
    assert "-m" in ikigai["args"]
    assert "mcp_server" in ikigai["args"]


def test_taskdog_server_registered() -> None:
    """M108: taskdog MCP server entry is registered."""
    config = json.loads(MCP_CONFIG.read_text())
    taskdog = config["mcpServers"].get("taskdog")
    assert taskdog is not None, "taskdog server missing from .mcp.json"
    assert "command" in taskdog
    assert taskdog["command"] == "taskdog-mcp"


def test_taskdog_command_in_path() -> None:
    """taskdog-mcp binary is on PATH and --help works."""
    binary = shutil.which("taskdog-mcp")
    assert binary is not None, "taskdog-mcp not on PATH"
    r = subprocess.run(
        [binary, "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert r.returncode == 0, f"--help failed: stderr={r.stderr!r}"
    assert "Taskdog MCP" in r.stdout or "MCP" in r.stdout
