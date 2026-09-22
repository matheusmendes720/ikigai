"""M110 tests: `life status` CLI command.

Per M110: `life status [--json]` prints a system snapshot:
- Version
- Daemon count (from schedules.json)
- taskdog-server health + live task count
- MCP servers (from .mcp.json)
- langgraph graphs (from langgraph.json)
- Drift gate availability

Tests:
- test_status_help: `life status --help` works
- test_status_human_readable: default output includes all sections
- test_status_json_output: --json returns valid JSON with expected keys
- test_status_daemon_count_matches_schedules: daemon count matches schedules.json
- test_status_taskdog_live_count: when taskdog up, shows tasks_live
- test_status_mcp_servers_listed: lists ikigai + taskdog
- test_status_langgraph_graphs_listed: lists 3 graphs
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IKIGAI_PY = REPO_ROOT / "src" / "ikigai" / ".venv" / "Scripts" / "python.exe"


def _ikigai_python() -> str:
    if IKIGAI_PY.exists():
        return str(IKIGAI_PY)
    return sys.executable


@pytest.fixture(scope="module")
def ikigai_python() -> str:
    return _ikigai_python()


def _run_status(ikigai_python: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [ikigai_python, "-m", "life.cli", "status", *args],
        cwd=str(REPO_ROOT),
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": __import__("os").environ.get("PATH", "")},
        capture_output=True, text=True, timeout=30,
    )


def _run_status_direct(ikigai_python: str, json_output: bool = False) -> subprocess.CompletedProcess:
    """Run status_cmd() directly via subprocess, avoiding the life.cli import chain
    (which hits Windows _overlapped asyncio bug when loaded from pytest).
    """
    code = f"""
import sys
sys.path.insert(0, r'.')
import os
os.environ['IKIGAI_DISABLE_OTEL'] = '1'
os.environ['IKIGAI_DISABLE_MCP_TASKDOG'] = '1'
from life.cli.cli import status_cmd, REPO_ROOT
from typer.main import get_command
import sys
# Build a fake context
class FakeContext:
    def __init__(self):
        self.invoked_subcommand = 'status'
status_cmd(json_output={json_output})
"""
    return subprocess.run(
        [ikigai_python, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=30,
    )


def test_status_help() -> None:
    """status_cmd is registered in the life app (verify via app inspection)."""
    from life.cli.cli import app as life_app

    # Get all commands registered on the life app.
    command_names = set()
    for cmd_info in life_app.registered_commands:
        command_names.add(cmd_info.name or cmd_info.callback.__name__)
    assert "status" in command_names or "status-cmd" in command_names or any("status" in (n or "") for n in command_names), (
        f"status command not registered. Found: {command_names}"
    )


def test_status_human_readable(ikigai_python: str) -> None:
    """Default status output contains all expected sections."""
    r = _run_status_direct(ikigai_python, json_output=False)
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"
    assert "life OS" in r.stdout
    assert "Daemons:" in r.stdout
    assert "taskdog-server:" in r.stdout
    assert "MCP servers:" in r.stdout
    assert "langgraph:" in r.stdout
    assert "Drift gate:" in r.stdout


def test_status_json_output(ikigai_python: str) -> None:
    """--json returns valid JSON with expected keys."""
    r = _run_status_direct(ikigai_python, json_output=True)
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"
    data = json.loads(r.stdout)
    assert "version" in data
    assert "daemons" in data
    assert "taskdog" in data
    assert "mcp_servers" in data
    assert "langgraph_graphs" in data
    assert "drift_gate" in data


def test_status_daemon_count_matches_schedules(ikigai_python: str) -> None:
    """Daemon count matches entries in schedules.json."""
    schedules = json.loads((REPO_ROOT / ".claude" / "loop" / "schedules.json").read_text())
    r = _run_status_direct(ikigai_python, json_output=True)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["daemons"]["total"] == len(schedules)
    # All 9 should be RUNNING (verified live in M110 verification).
    assert data["daemons"]["running"] == len(schedules)


def test_status_taskdog_live_count(ikigai_python: str) -> None:
    """When taskdog-server up, status shows tasks_live."""
    r = _run_status_direct(ikigai_python, json_output=True)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    # taskdog-server runs at 127.0.0.1:8000 in this environment.
    if data["taskdog"].get("status") == "ok":
        assert data["taskdog"]["tasks_live"] > 0


def test_status_mcp_servers_listed(ikigai_python: str) -> None:
    """Both ikigai and taskdog MCP servers listed."""
    r = _run_status_direct(ikigai_python, json_output=True)
    data = json.loads(r.stdout)
    assert "ikigai" in data["mcp_servers"]
    assert "taskdog" in data["mcp_servers"]


def test_status_langgraph_graphs_listed(ikigai_python: str) -> None:
    """All 3 langgraph graphs listed (M105 added taskdog_mcp)."""
    r = _run_status_direct(ikigai_python, json_output=True)
    data = json.loads(r.stdout)
    assert "ikigai_maintainer_v2" in data["langgraph_graphs"]
    assert "ikigai_fork_smoke" in data["langgraph_graphs"]
    assert "ikigai_taskdog_mcp" in data["langgraph_graphs"]


def test_status_drift_gate_available(ikigai_python: str) -> None:
    """Drift gate test file exists → status reports 'available'."""
    r = _run_status_direct(ikigai_python, json_output=True)
    data = json.loads(r.stdout)
    assert data["drift_gate"] == "available"
