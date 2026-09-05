"""Conftest for tests/ikigai/agents/v2/ — sets up sys.path for graph imports.

Per Plan A Task 9, this directory hosts node tests for the v2 LangGraph
graph (commit, tag_and_persist, plan, reflect, etc.). The imports use the
canonical ``from src.ikigai.src.agents.v2....`` dotted path.

After the 2026-09-05 namespace rename, `sys_ikigai/` lives at repo root, so
`<repo>/` on sys.path resolves BOTH:
  - `from src.ikigai.src.mcp_server.tools_vault import vault_write` (dotted)
  - `from sys_ikigai.vault.vault_read import vault_read` (bare)

The old APPEND of `<repo>/src/ikigai/src/` (Plan A Task 9 followup
workaround for the dual-module-identity bug) is removed since sys_ikigai
no longer needs an extra sys.path entry.

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
    """Add paths to sys.path. Conftest at tests/ikigai/agents/v2/conftest.py → 5 levels up to repo root."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent

    prepend_paths = [
        repo_root,  # resolves `sys_ikigai.X` AND `src.ikigai.src.X` (namespace chain)
        repo_root / "src",  # resolves `src.mesh.*`, bare `contracts.*`
    ]

    for p in prepend_paths:
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))

    if os.environ.get("DEBUG_CONFTEST"):
        print(
            f"[conftest v2] ADDED {len(prepend_paths)} prepend paths; "
            f"repo_root={repo_root}",
            file=sys.stderr,
        )


_add_paths()

# Verify after add
if os.environ.get("DEBUG_CONFTEST"):
    print("[conftest v2] sys.path:", file=sys.stderr)
    for i, p in enumerate(sys.path):
        if "ikigai" in p.lower() or i < 6:
            print(f"  [{i}] {p}", file=sys.stderr)


def pytest_load_initial_conftests(early_config, parser, args):
    """Run BEFORE any conftest module is imported."""
    if os.environ.get("DEBUG_CONFTEST"):
        print("[conftest v2] HOOK CALLED", file=sys.stderr)
    _add_paths()

