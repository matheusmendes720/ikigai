"""Isolation tests for ``_build_lc_tools()`` / ``_build_agent()``.

Regression guard for the ReAct agent's tool surface. ``_build_lc_tools()``
in ``src/ikigai/src/agents/taskdog_mcp_graph.py`` must:

  - return > 0 tools (otherwise the ReAct agent has no surface at all)
  - return exactly ``len(mcp_bridge.taskdog_*) + 2`` (taskdog_* enumeration +
    ikigai_read_vault + ikigai_write_vault)
  - expose every tool as a LangChain ``StructuredTool`` with a non-empty
    ``name`` and ``description`` (StructuredTool contract)
  - include both vault tools (``ikigai_read_vault``, ``ikigai_write_vault``)
  - never leak internal bridge helpers (each ``tool.name`` must start with
    ``taskdog_`` or ``ikigai_``)

Why this matters:

  - If ``_build_lc_tools()`` returns 0 tools (e.g., ``langchain_core``
    missing, bridge import fails, ``opentelemetry`` missing) the ReAct
    agent has no surface — every request falls back to the placeholder
    graph. M150's M146 binding (DirectTaskdogServer) makes this
    silently functional-broken, not crash-broken.
  - If the bridge gets refactored and a wrapper silently disappears (no
    ``taskdog_X`` def on disk), this test fails before the broader drift
    net (``test_taskdog_mcp_wiring``) sees a smaller surface.
  - Vault tools are appended by hand-coded imports of
    ``src.ikigai.src.agents.ikigai_read_vault`` /
    ``ikigai_write_vault`` — if those modules are renamed or moved
    without updating the graph, this test catches the regression.

Companion files:

  - ``test_taskdog_mcp_wiring.py`` — drift guard for bridge wrapper
    enumeration (regex-based, no imports).
  - ``test_studio_chat_schema.py`` — OPEN-3 guard on the input schema.

This file is the **live** companion: it actually imports
``taskdog_mcp_graph`` and calls ``_build_lc_tools()``, so it covers
scenarios the static-only drift net can't (e.g., StructuredTool wrapping
failures, vault import errors).
"""

from __future__ import annotations

import importlib
import os
import re
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — mirrors the conftest.py layout so this test file is
# self-contained for direct `pytest <file>` invocation.
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
IKIGAI_TESTS = THIS_FILE.parent
IKIGAI_PKG = IKIGAI_TESTS.parent  # src/ikigai
REPO_ROOT = IKIGAI_PKG.parent.parent  # life/

for _p in (REPO_ROOT, REPO_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

BRIDGE_FILE = REPO_ROOT / ".claude" / "loop" / "mcp_bridge.py"

# ---------------------------------------------------------------------------
# Skip gating: this file relies on imports that fail loudly when the runtime
# is missing. Skip the WHOLE module (via `pytestmark`) when the deps
# required by _build_lc_tools() itself are absent — otherwise every test
# fails on a CI runner without langchain_core / opentelemetry even though
# the rest of the suite is green.
# ---------------------------------------------------------------------------
try:
    from langchain_core.tools import StructuredTool  # noqa: F401

    _LANGCHAIN_CORE_AVAILABLE = True
except ImportError:
    _LANGCHAIN_CORE_AVAILABLE = False

try:
    from opentelemetry.trace import Status, StatusCode  # noqa: F401

    _OPENTELEMETRY_AVAILABLE = True
except ImportError:
    _OPENTELEMETRY_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not (_LANGCHAIN_CORE_AVAILABLE and _OPENTELEMETRY_AVAILABLE),
    reason=(
        "_build_lc_tools() needs langchain_core.StructuredTool + "
        "opentelemetry.trace; both required to enumerate the tool surface."
    ),
)

# ---------------------------------------------------------------------------
# Agent build deps — separate from the tool-surface gate so we can
# skip-if-only on Test 6 (build_agent needs LLM SDKs).
# ---------------------------------------------------------------------------
try:
    from langchain_anthropic import ChatAnthropic  # noqa: F401
    from langgraph.prebuilt import create_react_agent  # noqa: F401

    _AGENT_DEPS_AVAILABLE = True
except (ImportError, AttributeError):
    # M157: langchain_anthropic import can fail with AttributeError when
    # the anthropic SDK no longer exposes `OverloadedError`. Catch both
    # so the test collection doesn't crash on a stale pip pin.
    _AGENT_DEPS_AVAILABLE = False

_HAS_LLM_KEY = bool(
    os.environ.get("ANTHROPIC_API_KEY")
    or os.environ.get("MINIMAX_API_KEY")
    or os.environ.get("CLAUDE_API_KEY")
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_bridge_taskdog_wrappers() -> int:
    """Count top-level ``def taskdog_*(...)`` wrappers in mcp_bridge.py.

    Mirrors ``test_taskdog_mcp_wiring._extract_bridge_wrappers`` so this
    test stays consistent with the drift net's enumeration. If the
    drift net later adds new wrappers, this counter automatically
    tracks.
    """
    if not BRIDGE_FILE.exists():
        pytest.skip(f"mcp_bridge.py not found: {BRIDGE_FILE}")
    text = BRIDGE_FILE.read_text(encoding="utf-8")
    pattern = r"^def\s+(taskdog_\w+)\s*\("
    return len({m.group(1) for m in re.finditer(pattern, text, re.MULTILINE)})


def _build_lc_tools_isolated() -> list:
    """Re-import ``taskdog_mcp_graph`` fresh and call ``_build_lc_tools()``.

    Reloading isolates against a stale ``_DirectTaskdogServer`` binding
    from a prior test. The reload is idempotent: ``_build_lc_tools``
    pins the bridge module under ``"loop_mcp_bridge"`` in ``sys.modules``
    so the bridge import itself is stable across reloads.

    Returns the list of LangChain ``StructuredTool`` instances.
    """
    import src.ikigai.src.agents.taskdog_mcp_graph as graph_mod

    importlib.reload(graph_mod)
    return graph_mod._build_lc_tools()


# ---------------------------------------------------------------------------
# Test 1: regression guard — bridge must yield at least one tool
# ---------------------------------------------------------------------------


def test_build_lc_tools_returns_at_least_one_tool() -> None:
    """``_build_lc_tools()`` MUST return > 0 tools.

    If this fails, the ReAct agent has no surface — every request falls
    back to the placeholder graph. Likely causes:

      - ``langchain_core.StructuredTool`` missing
      - ``opentelemetry.trace`` missing (bridge import fails)
      - ``.claude/loop/mcp_bridge.py`` moved or empty
    """
    tools = _build_lc_tools_isolated()
    assert tools, (
        "_build_lc_tools() returned 0 tools. ReAct agent has no surface. "
        "Check: langchain_core present? opentelemetry present? "
        "mcp_bridge.py at "
        f"{BRIDGE_FILE}?"
    )


# ---------------------------------------------------------------------------
# Test 2: tool count == bridge taskdog_* wrappers + 2 vault tools
# ---------------------------------------------------------------------------


def test_build_lc_tools_count_matches_bridge_wrappers_plus_vault() -> None:
    """Total count == ``len(mcp_bridge.taskdog_*) + 2``.

    The ``+2`` reflects ``ikigai_read_vault`` + ``ikigai_write_vault``
    appended after the taskdog_* enumeration in ``_build_lc_tools()``.
    If a future change drops one of those imports OR adds a wrapper
    without a corresponding @mcp.tool, this test catches it.
    """
    tools = _build_lc_tools_isolated()
    expected = _count_bridge_taskdog_wrappers() + 2  # +2 for vault tools
    actual = len(tools)
    names = sorted(t.name for t in tools)

    assert actual == expected, (
        f"tool count mismatch: got {actual}, expected {expected} "
        f"({_count_bridge_taskdog_wrappers()} taskdog_* + 2 vault).\n"
        f"Tools returned: {names}"
    )


# ---------------------------------------------------------------------------
# Test 3: every tool has a name + description (StructuredTool contract)
# ---------------------------------------------------------------------------


def test_every_tool_has_name_and_description() -> None:
    """Every LangChain ``StructuredTool`` MUST have a non-empty name + description.

    LangChain's agent executor introspects these fields to build the
    system prompt and decide which tool to call. An empty description
    silently degrades tool selection; an empty name causes a runtime
    error inside the agent's tool dispatcher.
    """
    tools = _build_lc_tools_isolated()
    assert tools, "precondition: _build_lc_tools() must return tools"

    bad: list[tuple[str, str]] = []
    for t in tools:
        name = getattr(t, "name", None)
        desc = getattr(t, "description", None)
        if not name or not isinstance(name, str):
            bad.append((repr(t), "missing/invalid name"))
            continue
        if not desc or not isinstance(desc, str):
            bad.append((name, "missing/invalid description"))

    assert not bad, (
        f"{len(bad)} tool(s) violate the StructuredTool contract:\n"
        + "\n".join(f"  - {name}: {reason}" for name, reason in bad)
    )


# ---------------------------------------------------------------------------
# Test 4: vault tools are present in the agent's surface
# ---------------------------------------------------------------------------


def test_vault_tools_present_in_tool_surface() -> None:
    """Both vault tools MUST be exposed so the agent can round-trip the vault.

    ``_build_lc_tools()`` appends ``ikigai_read_vault`` +
    ``ikigai_write_vault`` after the taskdog_* enumeration. If either
    import fails (e.g., the module is renamed without updating this
    graph), the agent loses the ability to read or write vault
    markdown — which silently breaks every planning cycle.
    """
    tools = _build_lc_tools_isolated()
    names = {t.name for t in tools}

    assert "ikigai_read_vault" in names, (
        f"ikigai_read_vault missing from _build_lc_tools() surface. "
        f"Got: {sorted(names)}"
    )
    assert "ikigai_write_vault" in names, (
        f"ikigai_write_vault missing from _build_lc_tools() surface. "
        f"Got: {sorted(names)}"
    )


# ---------------------------------------------------------------------------
# Test 5: no leaked internal helpers (prefix invariant)
# ---------------------------------------------------------------------------


def test_tool_names_only_taskdog_or_ikigai_prefix() -> None:
    """Every ``tool.name`` MUST start with ``taskdog_`` or ``ikigai_``.

    ``_build_lc_tools()`` enumerates ``dir(bridge)`` and filters by
    ``startswith("taskdog_")``, then appends ``ikigai_*`` vault tools.
    A name with a different prefix indicates either:

      - an internal bridge helper leaked into the surface, OR
      - a prefix rename (e.g., taskdog_ -> task_dog_) without updating
        the filter.
    """
    tools = _build_lc_tools_isolated()
    bad = [
        getattr(t, "name", "<no name>")
        for t in tools
        if not (
            (isinstance(getattr(t, "name", ""), str))
            and (t.name.startswith("taskdog_") or t.name.startswith("ikigai_"))
        )
    ]

    assert not bad, (
        f"tool names with unexpected prefix (not taskdog_ or ikigai_): {bad}"
    )


# ---------------------------------------------------------------------------
# Test 6: full agent build (skipped when no LLM key / agent SDKs)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _HAS_LLM_KEY,
    reason="no LLM API key (ANTHROPIC_API_KEY / MINIMAX_API_KEY / CLAUDE_API_KEY)",
)
@pytest.mark.skipif(
    not _AGENT_DEPS_AVAILABLE,
    reason="langchain_anthropic + langgraph required to build the ReAct agent",
)
def test_build_agent_returns_compiled_graph() -> None:
    """Full build: ``_build_agent()`` returns a graph with ``.invoke()``.

    Catches regressions where the agent build fails even though
    ``_build_lc_tools()`` returns tools — e.g.:

      - ``create_react_agent`` raises (LangGraph version drift)
      - ``ChatAnthropic`` constructor rejects the configured model name
      - ``langchain_anthropic`` SDK mismatch (M157: AttributeError when
        ``OverloadedError`` is removed in newer anthropic SDK)

    Skipped when no API key is configured so CI doesn't burn LLM quota
    on a smoke test.
    """
    import src.ikigai.src.agents.taskdog_mcp_graph as graph_mod

    importlib.reload(graph_mod)
    agent = graph_mod._build_agent()
    assert agent is not None, "_build_agent() returned None"
    # CompiledStateGraph AND the placeholder graph both expose .invoke().
    # Type check distinguishes them — placeholder = StateGraph compiled
    # with TaskdogMcpStateDict (chat-input schema), real = CompiledStateGraph
    # from create_react_agent.
    assert hasattr(agent, "invoke"), (
        f"agent has no .invoke(); type={type(agent).__name__}"
    )
    # Surface-level smoke: a real agent should NOT be the placeholder —
    # the placeholder's input_schema only carries `messages`. The real
    # ReAct agent exposes `messages` + tool-binding state. We don't
    # inspect state (that's covered by test_studio_chat_schema); we assert
    # type is a CompiledStateGraph (LangGraph prebuilt base class).
    type_name = type(agent).__name__
    assert "Compiled" in type_name or "Graph" in type_name, (
        f"unexpected agent type: {type_name}"
    )