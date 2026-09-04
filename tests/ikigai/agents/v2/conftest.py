"""Conftest for tests/ikigai/agents/v2/ — sets up sys.path for graph imports.

Per Plan A Task 9, this directory hosts node tests for the v2 LangGraph
graph (commit, tag_and_persist, plan, reflect, etc.). The imports use the
canonical ``from src.ikigai.src.agents.v2....`` dotted path.

CRITICAL — sys.path ordering for namespace package resolution
=============================================================
The test chain mixes TWO import styles:
  - `from src.ikigai.src.mcp_server.tools_vault import vault_write`
    (dotted, needs `life/` on sys.path so `src` resolves via `life/src/`)
  - `from ikigai.vault.vault_read import vault_read`
    (bare, needs `life/src/ikigai/src/` on sys.path so `ikigai.X` resolves)

If `life/src/ikigai/src/` is PREPENDED (sys.path.insert(0, ...)), Python
finds it FIRST when resolving `src.ikigai.src.X` — but treats `src` as a
top-level package (NOT as a sub-package of itself), so `src.ikigai.src.X`
resolves to `life/src/ikigai/src/ikigai/src/X` (which doesn't exist) and
fails with `ModuleNotFoundError: No module named 'src.ikigai.src'`.

Fix: APPEND `life/src/ikigai/src/` to sys.path (or insert at high index).
Python then tries `life/` first, finds `src.ikigai.src` correctly via the
namespace chain, and only falls back to bare `ikigai.X` from the appended
path when the dotted resolution fails (or for the second import style).

Why a per-directory conftest and not just tests/ikigai/conftest.py?
Pytest 9.1.1 + Windows namespace packages have an ordering quirk where
parent conftest.py module-level sys.path mutations run AFTER test modules
are imported in some invocation patterns. A per-directory conftest here
is loaded earlier in the collection tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import os

if os.environ.get("DEBUG_CONFTEST"):
    print(f"[conftest v2] LOADED {__file__}", file=sys.stderr)


def _add_paths() -> None:
    """Add paths to sys.path in the CORRECT ORDER for namespace package resolution.

    Conftest is at tests/ikigai/agents/v2/conftest.py → 5 levels up to repo root.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent

    # Paths that must be PREPENDED (insert(0, ...)) so Python finds them first.
    # These resolve the dotted `src.ikigai.src.*` style by walking the namespace
    # chain via `life/src/` (where `src` is a real directory).
    prepend_paths = [
        repo_root,  # resolves `src.ikigai.src.*` (namespace package chain)
        repo_root / "src",  # resolves `src.mesh.*`, bare `contracts.*`
    ]

    # Paths that must be APPENDED (or inserted at high index) so they DON'T
    # shadow `src.ikigai.src` resolution. These resolve the bare `ikigai.*`,
    # `agents.*`, `mcp_server.*` import style.
    append_paths = [
        repo_root / "src" / "ikigai" / "src",  # bare `ikigai.*`, `agents.*`, `mcp_server.*`
    ]

    for p in prepend_paths:
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))

    # Append to end (high index) — Python only consults these when the
    # prepend paths can't satisfy the import. This avoids the namespace
    # package conflict where `src` shadows `src.ikigai.src`.
    for p in append_paths:
        if p.is_dir() and str(p) not in sys.path:
            sys.path.append(str(p))

    if os.environ.get("DEBUG_CONFTEST"):
        print(
            f"[conftest v2] ADDED {len(prepend_paths)} prepend + {len(append_paths)} append paths; "
            f"repo_root={repo_root}",
            file=sys.stderr,
        )


_add_paths()

# Verify after add
if os.environ.get("DEBUG_CONFTEST"):
    print(f"[conftest v2] sys.path[:8]:", file=sys.stderr)
    for i, p in enumerate(sys.path[:8]):
        print(f"  [{i}] {p}", file=sys.stderr)


def pytest_load_initial_conftests(early_config, parser, args):
    """Run BEFORE any conftest module is imported."""
    if os.environ.get("DEBUG_CONFTEST"):
        print(f"[conftest v2] HOOK CALLED", file=sys.stderr)
    _add_paths()

