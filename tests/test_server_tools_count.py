"""Verify mcp_server/server.py registers the 8 PAV-flavored stub tools.

Phase 6 (decisions #5, #6) appended 8 @MCP.tool decorators so the wire
surface lines up with mcp_bridge expectations:

  - ikigai_observe_state
  - ikigai_score_vectors
  - ikigai_heuristics
  - ikigai_balance
  - ikigai_plan
  - ikigai_reflect
  - ikigai_tag_and_persist
  - ikigai_commit_summary

This test parses server.py text for @MCP.tool(name=...) decorators and
asserts all 8 are present — protects against silent removal during
future V5-E-style surgery. The decorator scan is more reliable than
importing MCP (which would require a running gateway to enumerate).

NOTE: This is a focused, append-only smoke test. The full registry
alignment is already covered by src/ikigai/tests/test_server_fastmcp.py
::test_all_tools_registered. This test is the targeted guard for the
8 stub names so any drift here surfaces here instead of buried in
the bigger alignment test.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_SERVER_PY = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "ikigai"
    / "src"
    / "mcp_server"
    / "server.py"
)


_EXPECTED_PHASE6_TOOLS: tuple[str, ...] = (
    "ikigai_observe_state",
    "ikigai_score_vectors",
    "ikigai_heuristics",
    "ikigai_balance",
    "ikigai_plan",
    "ikigai_reflect",
    "ikigai_tag_and_persist",
    "ikigai_commit_summary",
)


@pytest.fixture(scope="module")
def server_text() -> str:
    """Read server.py once per module — fixture avoids disk hits per case."""
    return _SERVER_PY.read_text(encoding="utf-8")


def _declared_tool_names(text: str) -> set[str]:
    """Return every name="..." value inside an @MCP.tool(...) decorator."""
    return set(re.findall(r'@MCP\.tool\(\s*name="([a-zA-Z_]+)"', text))


def test_server_file_exists() -> None:
    assert _SERVER_PY.is_file(), f"server.py missing at {_SERVER_PY}"


def test_phase6_tools_all_registered(server_text: str) -> None:
    """All 8 Phase 6 stub tools must appear as @MCP.tool(name=...)."""
    declared = _declared_tool_names(server_text)
    missing = set(_EXPECTED_PHASE6_TOOLS) - declared
    assert not missing, (
        f"Phase 6 stub tools missing from server.py: {sorted(missing)}. "
        f"Per decisions #5/#6 these names MUST be registered to align "
        f"mcp_bridge with server surface."
    )


def test_phase6_tools_only_registered_once_each(server_text: str) -> None:
    """Each Phase 6 tool must be declared exactly once — guards against
    accidental double-registration during copy-paste surgery."""
    declared = _declared_tool_names(server_text)
    for name in _EXPECTED_PHASE6_TOOLS:
        # Re-scan counting occurrences specifically for this name.
        count = len(re.findall(rf'@MCP\.tool\(\s*name="{re.escape(name)}"', server_text))
        assert count == 1, (
            f"Tool {name!r} registered {count}x in server.py — expected exactly 1."
        )
    # Sanity: declared set contains the 8 names (defends against accidental
    # rename that keeps the count but loses the names).
    assert declared >= set(_EXPECTED_PHASE6_TOOLS)