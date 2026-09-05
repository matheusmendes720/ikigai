"""Test suite root for tests/ — sets up sys.path for src/ imports.

The test chain mixes TWO import styles:
  - `from src.contracts.sonho import ...` (dotted, repo-root)
    → needs `<repo>/` on sys.path so `src` resolves via `<repo>/src/`
  - `from sys_ikigai.X import Y` (bare namespace)
    → needs `<repo>/` on sys.path so `sys_ikigai` resolves via `<repo>/sys_ikigai/`

Both styles resolve from `<repo>/` alone after the 2026-09-05 namespace rename
that moved `src/ikigai/src/ikigai/` → `sys_ikigai/` at repo root. The old
`_IKIGAI_SRC = <repo>/src/ikigai/src/` sys.path append was a Plan A Task 9
followup workaround for the dual-module-identity bug and is no longer needed.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on path. Resolves BOTH:
#   - `from src.contracts.X` (via <repo>/src/)
#   - `from sys_ikigai.X`    (via <repo>/sys_ikigai/)
# Path(__file__) is tests/conftest.py → parent is tests/ → parent.parent is repo root
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

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
