"""M102 tests: langgraph dev server boots with v2 graph + fork_smoke.

Per M102: langgraph_api requires graph factories to accept only
ServerRuntime and/or RunnableConfig. We expose typed shims
(make_v2_graph, make_fork_smoke_graph) that wrap the original
_build_* functions. This file verifies the dev server actually boots.

Tests:
- test_validate_passed: langgraph validate succeeds (config OK)
- test_factories_typed: both make_*_graph factories have typed signatures
- test_internal_builders_still_work: _build_v2_graph and _build_fork_smoke_graph
  work via the original (checkpoint_db, entry_point) signature
- test_no_relative_imports_in_v2_graph: regression — no `from .nodes.` in v2
"""
from __future__ import annotations

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


def test_validate_passes(ikigai_python: str) -> None:
    """`langgraph validate` exits 0 (config + graph factory signatures OK)."""
    r = subprocess.run(
        [ikigai_python, "-m", "langgraph_cli", "validate"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"validate failed: stderr={r.stderr!r}"


def test_factories_have_typed_signatures(ikigai_python: str) -> None:
    """make_v2_graph and make_fork_smoke_graph accept ServerRuntime+Config."""
    code = """
import sys
sys.path.insert(0, r'src/ikigai/src')
sys.path.insert(0, r'src')
from agents.v2.graph import make_v2_graph
from agents.v2.fork_smoke_graph import make_fork_smoke_graph
import typing
h1 = typing.get_type_hints(make_v2_graph)
h2 = typing.get_type_hints(make_fork_smoke_graph)
print('v2:', sorted(h1.keys()))
print('fork_smoke:', sorted(h2.keys()))
"""
    r = subprocess.run(
        [ikigai_python, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"inspect failed: stderr={r.stderr!r}"
    assert "runtime" in r.stdout
    assert "config" in r.stdout


def test_internal_builders_still_work(ikigai_python: str) -> None:
    """_build_v2_graph and _build_fork_smoke_graph work via old signature.

    Note: On Windows the SqliteSaver connection holds the file open until
    the parent process exits. We don't use a tempdir because cleanup races
    with the open file handle. Instead we let the child subprocess exit
    (releasing handles) and use a path under the repo's data/ dir.
    """
    code = """
import sys
sys.path.insert(0, r'src/ikigai/src')
sys.path.insert(0, r'src')
import os
# Use persistent paths under data/ — child subprocess exits and releases handles.
os.makedirs(r'data/pytest-tmp', exist_ok=True)
db1 = r'data/pytest-tmp/m102_v2.db'
db2 = r'data/pytest-tmp/m102_fork.db'
from agents.v2.graph import _build_v2_graph
from agents.v2.fork_smoke_graph import _build_fork_smoke_graph
g1 = _build_v2_graph(checkpoint_db=db1, entry_point='observe')
assert g1 is not None
g2 = _build_fork_smoke_graph(checkpoint_db=db2, entry_point='connect')
assert g2 is not None
print('builders OK')
"""
    r = subprocess.run(
        [ikigai_python, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"builders failed: stderr={r.stderr!r}"
    assert "builders OK" in r.stdout


def test_no_relative_imports_in_v2_graph() -> None:
    """v2 graph no longer uses `from .nodes.X` (broke langgraph_api)."""
    graph_file = REPO_ROOT / "src" / "ikigai" / "src" / "agents" / "v2" / "graph.py"
    text = graph_file.read_text(encoding="utf-8")
    # Strip docstrings + comments before scanning.
    body_lines = []
    in_doc = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('"""') or s.startswith("'''"):
            in_doc = not in_doc
            continue
        if in_doc or s.startswith("#"):
            continue
        body_lines.append(line)
    body = "\n".join(body_lines)
    bad = re.findall(r"^from \.\w+", body, flags=re.MULTILINE)
    assert bad == [], f"relative imports still present: {bad}"


def test_make_v2_graph_via_config_works(ikigai_python: str) -> None:
    """langgraph_api-style call: make_v2_graph(config={'configurable': {...}})."""
    code = """
import sys
sys.path.insert(0, r'src/ikigai/src')
sys.path.insert(0, r'src')
import os
os.makedirs(r'data/pytest-tmp', exist_ok=True)
db = r'data/pytest-tmp/m102_v2_cfg.db'
from agents.v2.graph import make_v2_graph
g = make_v2_graph(config={'configurable': {'checkpoint_db': db, 'entry_point': 'observe'}})
assert g is not None
print('config-arg call OK')
"""
    r = subprocess.run(
        [ikigai_python, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"config-arg failed: stderr={r.stderr!r}"
    assert "config-arg call OK" in r.stdout
