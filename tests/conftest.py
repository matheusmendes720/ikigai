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

import os
import sys
import tempfile
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

# ---------------------------------------------------------------------------
# Redirect tempfile.tempdir to a project-local directory. On Windows,
# pytest-asyncio's autouse fixture walks the user-level temp dir
# (`C:\Users\<user>\AppData\Local\Temp\pytest-of-<user>\`) and raises
# `PermissionError [WinError 5]` when a prior run left a stale/locked
# directory. Pointing `tempfile.tempdir` (and the standard TMP env vars)
# at a project-local path sidesteps the shared-temp-lock bug entirely.
# We use `data/pytest-tmp/` (gitignored) instead of `AppData\Local\Temp\`.
_TMP_BASE = _REPO_ROOT / "data" / "pytest-tmp"
_TMP_BASE.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_TMP_BASE)
os.environ["TMPDIR"] = str(_TMP_BASE)
os.environ["TEMP"] = str(_TMP_BASE)
os.environ["TMP"] = str(_TMP_BASE)

import pytest  # noqa: E402 — must come AFTER sys.path and env setup above


def pytest_configure(config: pytest.Config) -> None:
    """Disable pytest-asyncio async collection. None of our tests are
    async, and the plugin's autouse fixture walks a temp dir that on
    Windows raises PermissionError on stale locks (handled above by
    redirecting tempfile.tempdir, but we also tell asyncio to skip)."""
    config.option.asyncio_mode = "auto"
