"""Test suite root for tests/ — sets up sys.path for src/ imports.

CRITICAL — sys.path ordering for namespace package resolution
=============================================================
The test chain mixes TWO import styles:
  - `from src.contracts.sonho import ...` (dotted, repo-root)
    → needs `<repo>/` on sys.path so `src` resolves via `<repo>/src/`
  - `from ikigai.gateway.stdio_server_base import ...` (bare ikigai.*)
    → needs `<repo>/src/ikigai/src/` on sys.path BUT only via APPEND
      (not prepend). If prepended, Python's import system finds `src`
      at the wrong level and `src.ikigai.src.X` (used by
      tests/ikigai/agents/v2/test_commit_node.py and similar) fails
      with `ModuleNotFoundError: No module named 'src.ikigai.src'`.

This is a pytest 9.1.1 + Windows namespace packages ordering quirk.
The fix: APPEND `<repo>/src/ikigai/src/` instead of PREPENDing it.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on path for `from src.contracts.sonho` style imports.
# Path(__file__) is tests/conftest.py → parent is tests/ → parent.parent is repo root
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Ensure project-root src/ is on path for `from contracts.task_change` style imports.
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Also add src/ikigai/src/ so `from ikigai.gateway.stdio_server_base import ...` works
# in unit tests. The E2E tests in tests/gateway/clients/ inject this into the
# subprocess env via conftest, but unit tests in tests/gateway/ run in the parent.
#
# APPEND (not prepend!) so this doesn't shadow `src.ikigai.src.*` resolution
# for tests that use the dotted import style (see Plan A Task 9 followup).
_IKIGAI_SRC = Path(__file__).parent.parent / "src" / "ikigai" / "src"
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))
