"""Test suite root for tests/ikigai/ — sets up sys.path for graph imports.

Per Plan A Task 9 followup, this conftest uses CORRECTED path ordering to
resolve namespace package conflicts. The test chain mixes TWO import styles:
  - `from src.ikigai.src.agents.v2....` (dotted, canonical repo-root path)
    → needs <repo>/ (life/) PREPENDED to sys.path so `src` resolves via
      the `life/src/` directory (NOT via `life/src/ikigai/src/` which
      would shadow `src.ikigai.src` as a top-level `src` package).
  - `from ikigai....`, `from agents....`, `from mcp_server....` (bare
    package paths used internally)
    → needs <repo>/src/ikigai/src/ APPENDED to sys.path (NOT prepended)
      so it does NOT shadow the dotted resolution.
  - `from src.mesh....`, `from contracts....` (repo-root src/ tree)
    → needs <repo>/src/ on sys.path so `src.mesh` / `contracts` resolve.

Both module-level sys.path mutation AND `pytest_load_initial_conftests`
are required because pytest collects conftest.py BEFORE test modules but
runs pytest_load_initial_conftests BEFORE the conftest is imported. This
double-setup is necessary for tests to find the `src.ikigai.src.*` chain
on Windows + pytest 9.1.1 namespace packages.

Plan A Task 9 — keep this conftest stable; tests/ikigai/agents/v2/ now
holds node tests for the v2 graph (commit, tag_and_persist, etc.).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def _add_paths() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent

    # PREPEND these — Python resolves dotted `src.ikigai.src.*` via the
    # namespace chain at `life/src/`. If `life/src/ikigai/src/` is also
    # prepended, Python's import system finds `src` FIRST at the wrong
    # level and `src.ikigai.src.X` fails to resolve.
    prepend_paths = [
        repo_root,  # resolves `src.ikigai.src.*` (namespace package chain)
        repo_root / "src",  # resolves `src.mesh.*`, bare `contracts.*`
    ]

    # APPEND these — they provide the bare `ikigai.*`, `agents.*`,
    # `mcp_server.*` import style. Appending (instead of prepending) keeps
    # them from shadowing the dotted `src.ikigai.src.*` resolution above.
    append_paths = [
        repo_root / "src" / "ikigai" / "src",  # bare ikigai.*, agents.*, mcp_server.*
    ]

    for p in prepend_paths:
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))

    for p in append_paths:
        if p.is_dir() and str(p) not in sys.path:
            sys.path.append(str(p))

    return repo_root


# Module-level: runs when conftest.py is first imported (after test discovery
# but before the test module is collected/imported in most pytest versions).
_REPO_ROOT = _add_paths()


# ---------------------------------------------------------------------------
# Redirect tempfile.tempdir to a project-local directory. On Windows,
# pytest-asyncio's autouse fixture walks the user-level temp dir
# (`C:\Users\<user>\AppData\Local\Temp\pytest-of-<user>\`) and raises
# `PermissionError [WinError 5]` when a prior run left a stale/locked
# directory. Pointing `tempfile.tempdir` (and the standard TMP env vars)
# at a project-local path sidesteps the shared-temp-lock bug entirely.
# Mirrors the same fix in src/ikigai/tests/conftest.py.
_TMP_BASE = _REPO_ROOT / "data" / "pytest-tmp"
_TMP_BASE.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_TMP_BASE)
os.environ["TMPDIR"] = str(_TMP_BASE)
os.environ["TEMP"] = str(_TMP_BASE)
os.environ["TMP"] = str(_TMP_BASE)


def pytest_load_initial_conftests(early_config, parser, args):
    """Re-run path setup BEFORE conftest module is imported.

    Some pytest versions (9.x) discover conftest modules lazily and may
    import test modules before the conftest module body executes. This
    hook guarantees sys.path is set before any test module is imported.
    """
    _add_paths()
