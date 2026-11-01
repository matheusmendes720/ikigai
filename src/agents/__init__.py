"""agents — planner-only agent layer.

Architectural rules (enforced by drift net, see test_canonical_scope.py):
- planner-only per ADR-013 (no PAV math execution)
- IKIGAI_TOOLS = 12 planning tools
- mesh v1 = create action only

Namespace note (2026-10-29): the repo ships TWO directories named ``agents``:
  - ``<repo>/src/agents/``                  — planner layer (memory/, reflection/)
  - ``<repo>/src/ikigai/src/agents/``       — IKIGAI internal (v2/, tools.py, …)

Both are importable as the top-level ``agents`` package, and consumers
(e.g. ``tests/test_cross_session_memory.py``) legitimately mix them:
``agents.memory.cross_session`` (planner) + ``agents.v2.vault_cache`` (IKIGAI).

A plain top-level package can only live at ONE directory, so whichever
directory wins the ``sys.path`` race would hide the other's subpackages.
We therefore extend ``__path__`` with the sibling directory, making the two
directories ONE logical package. Submodule resolution then finds both
``agents.memory`` and ``agents.v2`` regardless of which ``__init__.py``
executed. The mirrored extension lives in
``src/ikigai/src/agents/__init__.py`` so the merge is symmetric.
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"

# Merge the IKIGAI-internal ``agents`` directory into this package's
# search path (see module docstring). Guarded so the package still works
# when installed standalone (e.g. a wheel built from this directory alone).
_IKIGAI_AGENTS = Path(__file__).resolve().parents[1] / "ikigai" / "src" / "agents"
if _IKIGAI_AGENTS.is_dir() and str(_IKIGAI_AGENTS) not in __path__:
    __path__.append(str(_IKIGAI_AGENTS))
