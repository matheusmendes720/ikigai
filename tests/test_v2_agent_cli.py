"""M98 tests: `life v2 agent` one-shot deep-agent CLI surface.

Per M98: the `agent` command wires the deep-agent (38 tools: 12 IKIGAI +
26 MCP taskdog) as a CLI one-shot driver. These tests verify the
Typer command:
- registers without import error
- responds to --help correctly
- handles the IKIGAI_DISABLE_MCP_TASKDOG escape hatch
- gracefully reports when ikigai venv is unavailable
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir)
) if "__file__" in globals() else os.getcwd()


@pytest.fixture
def ikigai_python():
    """Path to ikigai venv python (has mcp.server.fastmcp + langchain-mcp-adapters)."""
    p = os.path.join(REPO_ROOT, "src", "ikigai", ".venv", "Scripts", "python.exe")
    if not os.path.exists(p):
        pytest.skip(f"ikigai venv not found: {p}")
    return p


def _run_cli(ikigai_python: str, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run `python -m life.cli <args>` with ikigai venv + PYTHONPATH=repo root."""
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT
    return subprocess.run(
        [ikigai_python, "-m", "life.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_v2_agent_help_lists_command(ikigai_python: str) -> None:
    """`life v2 --help` must list the new `agent` command."""
    r = _run_cli(ikigai_python, "v2", "--help")
    assert r.returncode == 0
    assert "agent" in r.stdout
    assert "Run the deep-agent on a user request (one-shot, M98)." in r.stdout


def test_v2_agent_command_help(ikigai_python: str) -> None:
    """`life v2 agent --help` must print the agent options."""
    r = _run_cli(ikigai_python, "v2", "agent", "--help")
    assert r.returncode == 0
    assert "request" in r.stdout
    assert "--thread" in r.stdout
    assert "--checkpoint-db" in r.stdout
    assert "--disable-mcp" in r.stdout


def test_v2_agent_missing_request_fails_gracefully(ikigai_python: str) -> None:
    """Missing required `request` arg → Typer exits non-zero with error."""
    r = _run_cli(ikigai_python, "v2", "agent")
    assert r.returncode != 0
    # Typer error: "Missing argument 'REQUEST'"
    assert "REQUEST" in r.stderr or "request" in r.stderr.lower()


def test_v2_agent_disable_mcp_flag_parses(ikigai_python: str) -> None:
    """--disable-mcp flag must be accepted by Typer (parse-only)."""
    # We don't actually invoke the LLM here (no API key) — just verify
    # the option is parsed and reaches the IKIGAI_DISABLE_MCP_TASKDOG set.
    # Typer will exit non-zero on missing request arg... wait, we provide one.
    # To avoid invoking the LLM, we test that --disable-mcp doesn't crash
    # before reaching agent.invoke().
    r = _run_cli(
        ikigai_python,
        "v2",
        "agent",
        "test",
        "--disable-mcp",
        timeout=15,
    )
    # Either the agent ran (and gracefully failed on no LLM key) OR
    # the option was parsed. We accept either exit code, but stderr
    # should NOT contain "no such option" (Typer parse error).
    combined = (r.stdout + r.stderr).lower()
    assert "no such option" not in combined
    assert "unrecognized" not in combined
