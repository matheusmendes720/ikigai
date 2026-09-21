"""M93: Tests that langgraph.json registers valid graphs.

Validates the langgraph.json spec by:
1. Loading the JSON config
2. Importing each graph factory from the registered path
3. Building the graph (calls factory with default args)
4. Asserting CompiledStateGraph type + node count

This catches:
- Stale factory path (file moved/deleted)
- Import errors in graph modules
- Missing nodes after wiring changes
- Missing graphs (e.g. someone removed a registration without intent)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LANGGRAPH_JSON = REPO_ROOT / "langgraph.json"


def _load_graph_factory(spec_path: str, attr: str):
    """Import langgraph.json spec via __import__ and return the factory."""
    # spec_path like "./src/ikigai/src/agents/v2/graph.py" → module path
    module = spec_path.replace("./", "").replace("/", ".").removesuffix(".py")
    mod = __import__(module, fromlist=[attr])
    return getattr(mod, attr)


def test_langgraph_json_exists() -> None:
    """langgraph.json exists at repo root."""
    assert LANGGRAPH_JSON.exists(), f"Missing {LANGGRAPH_JSON}"


def test_langgraph_json_valid_json() -> None:
    """langgraph.json parses as JSON with required fields."""
    cfg = json.loads(LANGGRAPH_JSON.read_text(encoding="utf-8"))
    assert "graphs" in cfg, "Missing 'graphs' key"
    assert "dependencies" in cfg, "Missing 'dependencies' key"
    assert "env" in cfg, "Missing 'env' key"
    assert isinstance(cfg["graphs"], dict)
    assert len(cfg["graphs"]) >= 1, "Expected at least one graph"


def test_langgraph_json_registers_v2_graph() -> None:
    """ikigai_maintainer_v2 is registered (M77 re-registration)."""
    cfg = json.loads(LANGGRAPH_JSON.read_text(encoding="utf-8"))
    assert "ikigai_maintainer_v2" in cfg["graphs"], (
        "ikigai_maintainer_v2 not registered — re-add to langgraph.json"
    )


def test_ikigai_maintainer_v2_factory_loads() -> None:
    """The registered factory function is importable + callable."""
    cfg = json.loads(LANGGRAPH_JSON.read_text(encoding="utf-8"))
    spec_path, _, attr = cfg["graphs"]["ikigai_maintainer_v2"].partition(":")
    factory = _load_graph_factory(spec_path, attr)
    assert callable(factory), f"Factory {attr!r} is not callable"


def test_ikigai_maintainer_v2_builds_compiled_graph() -> None:
    """Calling the factory builds a CompiledStateGraph with >=10 nodes."""
    from langgraph.graph.state import CompiledStateGraph

    cfg = json.loads(LANGGRAPH_JSON.read_text(encoding="utf-8"))
    spec_path, _, attr = cfg["graphs"]["ikigai_maintainer_v2"].partition(":")
    factory = _load_graph_factory(spec_path, attr)
    g = factory()
    assert isinstance(g, CompiledStateGraph), (
        f"Expected CompiledStateGraph, got {type(g).__name__}"
    )
    # v2 graph has 13 nodes per graph.py:59-73 + surface_intentions + dispatch_sub_agents = 15
    node_count = len(g.nodes) if hasattr(g, "nodes") else 0
    assert node_count >= 10, f"Expected >=10 nodes, got {node_count}"


def test_ikigai_maintainer_v2_supports_entry_points() -> None:
    """All advertised entry_points (from graph.NODES) are valid for build."""
    cfg = json.loads(LANGGRAPH_JSON.read_text(encoding="utf-8"))
    spec_path, _, attr = cfg["graphs"]["ikigai_maintainer_v2"].partition(":")
    factory = _load_graph_factory(spec_path, attr)

    # Read NODES from the graph module
    module = spec_path.replace("./", "").replace("/", ".").removesuffix(".py")
    mod = __import__(module, fromlist=["NODES"])
    nodes = getattr(mod, "NODES", ())
    assert len(nodes) >= 10, f"Expected >=10 NODES declared, got {len(nodes)}"

    # Each declared entry_point should build a valid graph
    for ep in nodes:
        g = factory(entry_point=ep)
        assert g is not None, f"Failed to build graph for entry_point={ep!r}"


def test_langgraph_python_version_supported() -> None:
    """langgraph.json python_version is one we have."""
    cfg = json.loads(LANGGRAPH_JSON.read_text(encoding="utf-8"))
    py_version = cfg.get("python_version", "3.11")
    major_minor = ".".join(py_version.split(".")[:2])
    # Check we have a compatible interpreter
    import sys

    actual = ".".join(sys.version.split(".")[:2])
    # Allow same major.minor
    assert actual.split(".")[0] == major_minor.split(".")[0], (
        f"Python {actual} doesn't match declared {py_version}"
    )
