"""Agents package — IKIGAi-Maintainer deep agent.

Namespace note (2026-10-29): the repo ships TWO directories named ``agents``:
  - ``<repo>/src/agents/``                  — planner layer (memory/, reflection/)
  - ``<repo>/src/ikigai/src/agents/``       — IKIGAI internal (v2/, tools.py, …)

Both are importable as the top-level ``agents`` package, and consumers
(e.g. ``tests/test_cross_session_memory.py``) legitimately mix them:
``agents.memory.cross_session`` (planner) + ``agents.v2.vault_cache`` (IKIGAI).

A plain top-level package can only live at ONE directory, so whichever
directory wins the ``sys.path`` race would hide the other's subpackages.
We therefore extend ``__path__`` with the sibling directory, making the two
directories ONE logical package. The mirrored extension lives in
``src/agents/__init__.py`` so the merge is symmetric.
"""

from __future__ import annotations

from pathlib import Path

# Merge the planner-layer ``agents`` directory into this package's search
# path (see module docstring). Guarded so the package still works when
# installed standalone (e.g. a wheel built from this directory alone).
_PLANNER_AGENTS = Path(__file__).resolve().parents[3] / "agents"
if _PLANNER_AGENTS.is_dir() and str(_PLANNER_AGENTS) not in __path__:
    __path__.append(str(_PLANNER_AGENTS))
