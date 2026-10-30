"""Drift guard + smoke tests for the taskdog MCP wiring.

Two concerns live in this file:

1. **Drift test** (`test_taskdog_mcp_wiring`): every @mcp.tool function
   declared in ``src/ikigai/src/mcp_server/taskdog_tools.py`` MUST be
   exposed by ``_build_lc_tools()`` in
   ``src/ikigai/src/agents/taskdog_mcp_graph.py``.

   ``_build_lc_tools()`` discovers tools by enumerating ``dir(bridge)``
   for ``taskdog_*`` attributes on the loop-layer
   ``.claude/loop/mcp_bridge.py`` module. So the wiring invariant is:
   every @mcp.tool name from taskdog_tools.py MUST have a
   corresponding ``def taskdog_X(...)`` in mcp_bridge.py.

   Without this guard, a new @mcp.tool added to taskdog_tools.py would
   silently miss the ReAct agent's tool surface — the LangGraph graph
   would not be able to call it.

2. **Smoke tests** (one per wrapper): for each ``taskdog_*`` wrapper in
   ``mcp_bridge.py``, verify it is registered as a top-level function
   with a callable signature, and that it dispatches via ``_call(...)``
   with the correct tool name. We do NOT exercise real execution —
   production binding (M146) is gated on env wiring.

Regression history:
- M168 (this file): closes the gap surfaced when the taskdog_tools
  MCP surface grew to 21 functions (M148 + M163/M164) but only 12
  wrappers existed in mcp_bridge.py. _build_lc_tools() silently
  exposed only 12 tools. Drift net had no guard for this.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path resolution — mirrors test_drift_extended_invariants._resolve_repo_root()
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
IKIGAI_TESTS = THIS_FILE.parent  # src/ikigai/tests
IKIGAI_PKG = IKIGAI_TESTS.parent  # src/ikigai
REPO_ROOT = IKIGAI_PKG.parent.parent  # life/ (workspace root)


def _resolve_repo_root() -> Path:
    for parent in THIS_FILE.parents:
        if (parent / "src" / "ikigai" / "src" / "agents").is_dir():
            return parent
    raise RuntimeError(
        f"Could not locate repo root from {THIS_FILE} — expected "
        "<repo>/src/ikigai/tests/test_taskdog_mcp_wiring.py"
    )


REPO_ROOT = _resolve_repo_root()

MCP_TOOLS_FILE = REPO_ROOT / "src" / "ikigai" / "src" / "mcp_server" / "taskdog_tools.py"
BRIDGE_FILE = REPO_ROOT / ".claude" / "loop" / "mcp_bridge.py"
GRAPH_FILE = REPO_ROOT / "src" / "ikigai" / "src" / "agents" / "taskdog_mcp_graph.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_mcp_tools(taskdog_tools_text: str) -> set[str]:
    """Extract every function name declared with an ``@mcp.tool`` decorator.

    Mirrors the discovery rule used by the existing
    ``test_taskdog_tools_read_only_contract`` drift net, but uses a
    regex that handles multi-line decorator bodies (the existing one
    only matches single-line forms — see M168 retrospective).

    The function name follows the decorator regardless of whether the
    decorator uses ``@mcp.tool(name="...")`` (explicit canonical
    name) or bare ``@mcp.tool()`` (function name IS the tool name).
    We extract function names (not source names) because the public tool
    name advertised by FastMCP matches the function name unless the
    decorator explicitly overrides it — and per `taskdog_tools.py`
    conventions, the function name always equals the public name.
    """
    # Tolerant regex: any @mcp.tool followed (possibly across newlines)
    # by `def <name>` — captures the function name.
    pattern = r"@mcp\.tool[^{]*?def\s+(\w+)"
    return {m.group(1) for m in re.finditer(pattern, taskdog_tools_text, re.DOTALL)}


def _extract_bridge_wrappers(bridge_text: str) -> set[str]:
    """Extract every top-level ``def taskdog_*(...)`` wrapper in mcp_bridge.py.

    Skips indented defs (helpers inside other functions).
    """
    pattern = r"^def\s+(taskdog_\w+)\s*\("
    return {m.group(1) for m in re.finditer(pattern, bridge_text, re.MULTILINE)}


def _extract_lc_tools_discovery_target(graph_text: str) -> str | None:
    """Extract the bridge module path that _build_lc_tools() loads.

    The discovery source is the bridge_path constant: ``_BRIDGE_PATH``
    computed by walking 4 levels up from ``__file__`` and appending
    ``.claude/loop/mcp_bridge.py``. We don't re-derive it — we just
    confirm the graph file references ``.claude/loop/mcp_bridge.py``
    so the drift test stays self-contained if the discovery rule
    ever changes.
    """
    # Look for the canonical bridge path reference.
    if (
        ".claude/loop/mcp_bridge.py" not in graph_text
        and ".claude\\loop\\mcp_bridge.py" not in graph_text
    ):
        return None
    return str(BRIDGE_FILE)


# ---------------------------------------------------------------------------
# 1. Drift test — every @mcp.tool must be exposed via _build_lc_tools()
# ---------------------------------------------------------------------------


def test_taskdog_mcp_wiring() -> None:
    """Every @mcp.tool function in taskdog_tools.py MUST be exposed by
    ``_build_lc_tools()``.

    ``_build_lc_tools()`` discovers tools by enumerating ``dir(bridge)``
    for ``taskdog_*`` attributes on ``.claude/loop/mcp_bridge.py``. So
    the wiring invariant is: every @mcp.tool name MUST have a
    corresponding top-level ``def taskdog_X(...)`` in mcp_bridge.py.

    Without this guard, a new @mcp.tool added to taskdog_tools.py would
    silently miss the ReAct agent's tool surface — the LangGraph graph
    would not be able to call it.
    """
    if not MCP_TOOLS_FILE.exists():
        pytest.skip(f"taskdog_tools.py not found: {MCP_TOOLS_FILE}")
    if not BRIDGE_FILE.exists():
        pytest.skip(f"mcp_bridge.py not found: {BRIDGE_FILE}")

    mcp_tools = _extract_mcp_tools(MCP_TOOLS_FILE.read_text(encoding="utf-8"))
    bridge_wrappers = _extract_bridge_wrappers(BRIDGE_FILE.read_text(encoding="utf-8"))

    # Every @mcp.tool must be exposed. NOTE: this is a ONE-WAY check —
    # we do not require that every bridge wrapper exists as @mcp.tool
    # (the bridge may have its own write-surface tools, e.g.
    # taskdog_delete / taskdog_done / taskdog_set_planned_dates /
    # taskdog_search, that don't have @mcp.tool decorators yet).
    missing_in_bridge = mcp_tools - bridge_wrappers

    assert not missing_in_bridge, (
        "taskdog @mcp.tool functions missing from mcp_bridge.py "
        "(ReAct agent can't call them via _build_lc_tools()):\n"
        + "\n".join(f"  - {name}" for name in sorted(missing_in_bridge))
        + f"\n\n@mcp.tool tools (declared in taskdog_tools.py): "
        f"{len(mcp_tools)}" + f"\n  bridge taskdog_* wrappers (in mcp_bridge.py): "
        f"{len(bridge_wrappers)}" + "\n\nFix: add a corresponding `def taskdog_X(...)` wrapper to "
        ".claude/loop/mcp_bridge.py following the existing _call() dispatch "
        "pattern. Each wrapper should be a thin shim: build `args` dict "
        'from kwargs and return _call("taskdog_X", args).'
    )


def test_taskdog_mcp_wiring_graph_references_bridge() -> None:
    """Sanity: taskdog_mcp_graph.py still references the bridge module path.

    Guards against silent drift in the path-discovery logic of
    _build_lc_tools() (e.g., if someone moves mcp_bridge.py to a new
    directory and forgets to update _BRIDGE_PATH derivation).
    """
    if not GRAPH_FILE.exists():
        pytest.skip(f"taskdog_mcp_graph.py not found: {GRAPH_FILE}")

    graph_text = GRAPH_FILE.read_text(encoding="utf-8")
    target = _extract_lc_tools_discovery_target(graph_text)
    assert target is not None, (
        "taskdog_mcp_graph.py no longer references .claude/loop/mcp_bridge.py. "
        "_build_lc_tools() discovery rule may have changed — re-derive the path "
        "logic and update this test."
    )


# ---------------------------------------------------------------------------
# 2. Smoke tests — one per wrapper. Verifies registration, not execution.
# ---------------------------------------------------------------------------


# All wrappers we expect to find in mcp_bridge.py after M168. This list
# is the union of:
#  - 8 M148 originals (list/read/supports_field/set_status/set_priority/
#    set_due/create/cancel)
#  - 4 M148 additions (done/set_planned_dates/delete/search)
#  - 4 tag tools (add/remove/list/clear)
#  - 4 dep tools (add/remove/list/blocked)
#  - 2 note tools (add/show)
#  - 2 status wrappers (pause/reopen)
#  - 1 audit tool
EXPECTED_BRIDGE_WRAPPERS: frozenset[str] = frozenset(
    {
        # M148 original 8
        "taskdog_read",
        "taskdog_list",
        "taskdog_supports_field",
        "taskdog_create",
        "taskdog_set_status",
        "taskdog_set_priority",
        "taskdog_set_due",
        "taskdog_cancel",
        # M148 additions
        "taskdog_done",
        "taskdog_set_planned_dates",
        "taskdog_delete",
        "taskdog_search",
        # M163/M164 tag surface
        "taskdog_tag_add",
        "taskdog_tag_remove",
        "taskdog_tag_list",
        "taskdog_tag_clear",
        # M163/M164 dep surface
        "taskdog_dep_add",
        "taskdog_dep_remove",
        "taskdog_dep_list",
        "taskdog_dep_blocked",
        # M163/M164 note surface
        "taskdog_note_add",
        "taskdog_note_show",
        # M163/M164 status wrappers
        "taskdog_pause",
        "taskdog_reopen",
        # M163/M164 audit
        "taskdog_audit",
    }
)


def _assert_wrapper_registered(wrapper_name: str) -> None:
    """Smoke test: wrapper is registered as a top-level function and
    its body dispatches via ``_call("<wrapper_name>", ...)``.
    """
    import importlib.util
    import sys as _sys

    if not BRIDGE_FILE.exists():
        pytest.skip(f"mcp_bridge.py not found: {BRIDGE_FILE}")

    # Load the bridge module fresh (idempotent — pinned under stable name).
    spec = importlib.util.spec_from_file_location("_smoke_test_taskdog_bridge", BRIDGE_FILE)
    if spec is None or spec.loader is None:
        pytest.skip(f"Could not load bridge module: {BRIDGE_FILE}")
    bridge = importlib.util.module_from_spec(spec)
    _sys.modules["_smoke_test_taskdog_bridge"] = bridge
    spec.loader.exec_module(bridge)

    # 1. The wrapper exists as a top-level attribute.
    func = getattr(bridge, wrapper_name, None)
    assert func is not None, f"wrapper {wrapper_name} not registered on mcp_bridge module"
    assert callable(func), f"wrapper {wrapper_name} is not callable"

    # 2. The body dispatches via _call(<wrapper_name>, ...).
    src = BRIDGE_FILE.read_text(encoding="utf-8")
    # Look for `_call("taskdog_X", ...)` pattern within the wrapper definition.
    # We use a tolerant regex that handles multi-line bodies.
    pattern = (
        r"def\s+"
        + re.escape(wrapper_name)
        + r"\s*\([^)]*\)[^@]*?_call\(\s*\""
        + re.escape(wrapper_name)
        + r"\""
    )
    match = re.search(pattern, src, re.DOTALL)
    if match is None:
        def_idx = src.find("def " + wrapper_name)
        snippet = src[def_idx : def_idx + 500] if def_idx != -1 else "NOT FOUND"
        pytest.fail(
            f"wrapper {wrapper_name} does not call _call({wrapper_name!r}, ...). "
            f"Source snippet:\n{snippet}"
        )


@pytest.mark.parametrize("wrapper_name", sorted(EXPECTED_BRIDGE_WRAPPERS))
def test_bridge_wrapper_registration(wrapper_name: str) -> None:
    """Smoke test: each expected wrapper is registered and dispatches correctly."""
    _assert_wrapper_registered(wrapper_name)


@pytest.mark.parametrize(
    "wrapper_name",
    sorted(
        {
            "taskdog_tag_add",
            "taskdog_tag_remove",
            "taskdog_tag_list",
            "taskdog_tag_clear",
            "taskdog_dep_add",
            "taskdog_dep_remove",
            "taskdog_dep_list",
            "taskdog_dep_blocked",
            "taskdog_note_add",
            "taskdog_note_show",
            "taskdog_pause",
            "taskdog_reopen",
            "taskdog_audit",
        }
    ),
)
def test_m168_new_wrapper_registration(wrapper_name: str) -> None:
    """Smoke test (M168-specific): the 13 new wrappers added in M168
    are registered in mcp_bridge.py.

    Each wrapper must exist as a top-level function AND dispatch via
    ``_call("<wrapper_name>", ...)``. This test guards the wiring
    fix specifically — if a future refactor removes one of these
    wrappers, this test fails with a clear error pointing to the
    specific missing wrapper.
    """
    _assert_wrapper_registered(wrapper_name)


# ---------------------------------------------------------------------------
# 3. Coverage sanity — drift net must not regress
# ---------------------------------------------------------------------------


def test_m168_known_wrapper_count() -> None:
    """Sanity: the bridge has all 25 expected taskdog_* wrappers.

    Pinned count guards against silent drift (e.g., accidental removal
    during a refactor) — if a wrapper is removed without intent, this
    test fails before the broader drift net sees a smaller surface.
    """
    if not BRIDGE_FILE.exists():
        pytest.skip(f"mcp_bridge.py not found: {BRIDGE_FILE}")

    bridge_wrappers = _extract_bridge_wrappers(BRIDGE_FILE.read_text(encoding="utf-8"))
    expected = EXPECTED_BRIDGE_WRAPPERS

    missing = expected - bridge_wrappers
    assert not missing, (
        f"Expected taskdog_* wrappers missing from mcp_bridge.py: "
        f"{sorted(missing)}\n"
        f"Got: {sorted(bridge_wrappers)}"
    )
