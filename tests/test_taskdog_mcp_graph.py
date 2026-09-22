"""M105 tests: 3rd graph (ikigai_taskdog_mcp) registered in langgraph.json.

Per M105: taskdog_mcp_graph wraps the 26 MCP tools as a ReAct agent so
the visual debugger sees them. This file verifies:
- langgraph.json lists 3 graphs
- taskdog_mcp_graph module imports cleanly
- placeholder graph works when taskdog-mcp is missing
- sync factory wrapper has correct signature for langgraph_api
"""
from __future__ import annotations

import json
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


def test_langgraph_json_has_3_graphs() -> None:
    config = json.loads((REPO_ROOT / "langgraph.json").read_text())
    graphs = config["graphs"]
    assert "ikigai_maintainer_v2" in graphs
    assert "ikigai_fork_smoke" in graphs
    assert "ikigai_taskdog_mcp" in graphs
    assert len(graphs) == 3
    # Verify the 3rd graph points to our module
    assert graphs["ikigai_taskdog_mcp"].endswith("taskdog_mcp_graph.py:make_taskdog_mcp_graph_sync")


def test_taskdog_mcp_graph_module_imports(ikigai_python: str) -> None:
    """The taskdog_mcp_graph module loads without errors."""
    code = """
import sys
sys.path.insert(0, r'src/ikigai/src')
import importlib.util
spec = importlib.util.find_spec('agents.taskdog_mcp_graph')
assert spec is not None, 'module not found'
import agents.taskdog_mcp_graph as mod
assert hasattr(mod, 'make_taskdog_mcp_graph')
assert hasattr(mod, 'make_taskdog_mcp_graph_sync')
assert hasattr(mod, '_placeholder_graph')
print('module-OK')
"""
    r = subprocess.run(
        [ikigai_python, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"import failed: stderr={r.stderr!r}"
    assert "module-OK" in r.stdout


def test_placeholder_graph_works(ikigai_python: str) -> None:
    """When taskdog-mcp is missing, the placeholder graph returns a setup message."""
    code = """
import sys
sys.path.insert(0, r'src/ikigai/src')
from agents.taskdog_mcp_graph import _placeholder_graph
g = _placeholder_graph('test reason')
result = g.invoke({})
# Find the assistant message
for msg in result.get('messages', []):
    if msg.get('role') == 'assistant':
        content = msg.get('content', '')
        assert 'test reason' in content
        assert 'taskdog' in content.lower()
        print('placeholder-OK')
        break
else:
    print('FAIL: no assistant message')
    sys.exit(1)
"""
    r = subprocess.run(
        [ikigai_python, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"placeholder failed: stderr={r.stderr!r}"
    assert "placeholder-OK" in r.stdout


def test_sync_factory_has_typed_signature(ikigai_python: str) -> None:
    """make_taskdog_mcp_graph_sync has ServerRuntime + RunnableConfig params."""
    code = """
import sys
sys.path.insert(0, r'src/ikigai/src')
from agents.taskdog_mcp_graph import make_taskdog_mcp_graph_sync
import typing
hints = typing.get_type_hints(make_taskdog_mcp_graph_sync)
print('params:', sorted(hints.keys()))
assert 'runtime' in hints
assert 'config' in hints
print('typed-OK')
"""
    r = subprocess.run(
        [ikigai_python, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"inspect failed: stderr={r.stderr!r}"
    assert "typed-OK" in r.stdout


def test_langgraph_validate_with_3_graphs(ikigai_python: str) -> None:
    """langgraph_cli validate accepts all 3 graph factories."""
    r = subprocess.run(
        [ikigai_python, "-m", "langgraph_cli", "validate"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"validate failed: stderr={r.stderr!r}"
    assert "3 graphs" in r.stdout or "3 graphs" in r.stderr
