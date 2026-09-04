"""Conftest for tests/ikigai/agents/v2/ — sets up sys.path for graph imports.

Per Plan A Task 9, this directory hosts node tests for the v2 LangGraph
graph (commit, tag_and_persist, plan, reflect, etc.). The imports use the
canonical ``from src.ikigai.src.agents.v2....`` dotted path which requires
both the repo root (for namespace ``src.ikigai.src``) and the ikigai src
tree (for bare ``ikigai.*``) on sys.path.

Why a per-directory conftest and not just tests/ikigai/conftest.py?
Pytest 9.1.1 + Windows namespace packages have an ordering quirk where
``tests/ikigai/conftest.py`` module-level sys.path mutations run AFTER
test modules are imported (in some invocation patterns). A per-directory
conftest here is loaded earlier in the collection tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import os
if os.environ.get("DEBUG_CONFTEST"):
    print(f"[conftest v2] LOADED {__file__}", file=sys.stderr)


def _add_paths() -> None:
    # Conftest is at tests/ikigai/agents/v2/conftest.py → 5 levels up to repo root.
    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    paths = [
        # Repo root → resolves `src.ikigai.src.*` via namespace package chain.
        repo_root,
        # Repo-root src/ → resolves `src.mesh.*`, bare `contracts.*`.
        repo_root / "src",
        # IKIGAI src tree → resolves bare `ikigai.*`, `agents.*`, `mcp_server.*`.
        repo_root / "src" / "ikigai" / "src",
    ]
    for p in paths:
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
    if os.environ.get("DEBUG_CONFTEST"):
        print(f"[conftest v2] ADDED {len(paths)} paths; repo_root={repo_root}", file=sys.stderr)


_add_paths()

# Verify after add
if os.environ.get("DEBUG_CONFTEST"):
    print(f"[conftest v2] sys.path[:6]:", file=sys.stderr)
    for p in sys.path[:6]:
        print(f"  {p}", file=sys.stderr)


def pytest_load_initial_conftests(early_config, parser, args):
    """Run BEFORE any conftest module is imported."""
    if os.environ.get("DEBUG_CONFTEST"):
        print(f"[conftest v2] HOOK CALLED", file=sys.stderr)
    _add_paths()
