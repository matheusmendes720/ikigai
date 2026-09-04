"""Test suite root — mirrors src/operational/ layout.

Also auto-isolates src.mesh.queue.QUEUE_DIR to a per-test tmp dir so tests
that touch the review queue never write to the real `data/review_queue/`.
Tests that want a specific queue path can still override via their own
fixture (autouse runs first, then explicit fixtures override).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — must happen BEFORE any test module or pytest plugin imports
# src.* (some plugins walk sys.path or import src.mesh during their own
# collection/setup).
# ---------------------------------------------------------------------------
# Ensure both IKIGAI's own src tree AND the repo-root src tree are on
# sys.path so that:
#   - IKIGAI modules (ikigai/, mcp_server/, agents/) resolve from
#     `src/ikigai/src/` (set by pyproject.toml pythonpath = ["src"]).
#   - Repo-root modules (mesh/, contracts/, operational/, …) resolve
#     from `life/src/` (the directory that actually contains `src.mesh`).
# Without the second entry, `from src.mesh import queue` raises
# `ModuleNotFoundError: No module named 'src.mesh'` on Windows pytest.
_THIS = Path(__file__).resolve()
# Three distinct paths are needed because tests use THREE import styles:
#   1. `from src.ikigai.src.ikigai.vault.vault_read import vault_read`
#      → requires <repo-root>/src/ikigai/ on sys.path (one 'src/ikigai/' is
#        the namespace package prefix the test uses).
#   2. `from src.mesh import queue`
#      → requires <repo-root>/ on sys.path (so 'src.mesh' resolves as a
#        dotted path under the repo-root src/ tree).
#   3. `from contracts.task_change import TaskChange`  (no 'src.' prefix,
#      used by mesh/queue.py and mcp_server/tools_mesh.py)
#      → requires <repo-root>/src/ on sys.path so the bare 'contracts'
#        package resolves. Without this, 17 ikigai_maintainer_node tests +
#        test_server_fastmcp.py collection fail with ModuleNotFoundError.
#
# Plan A Task 9 followup (RESOLVED): the `_IKIGAI_PKG_ROOT` (=
# <repo-root>/src/ikigai/) entry that lives on sys.path collides with the
# dotted `src.ikigai.src.X` import style, because `src/ikigai/` contains a
# `src/` subdirectory. Python's namespace-package machinery sees the inner
# `src/` and creates a spurious `src.ikigai` namespace distribution that
# resolves `src.ikigai` to `<repo>/src/ikigai/src/ikigai/` instead of
# `<repo>/src/ikigai/` — breaking `src.ikigai.src` lookup.
#
# Fix: append `<repo>/src/ikigai/src/` INSTEAD. That directory contains the
# bare `ikigai/` package, so `from ikigai.X import …` works for code in this
# test tree. And because it's INSIDE the dotted chain (not at a sibling
# level), it doesn't disturb `src.ikigai.src.X` resolution.
_IKIGAI_SRC = _THIS.parent.parent / "src"  # <repo-root>/src/ikigai/src/
_SRC_ROOT = _THIS.parent.parent.parent  # <repo-root>/src/  (contracts/, mesh/)
_REPO_ROOT = _THIS.parent.parent.parent.parent  # <repo-root>
for _p in (_REPO_ROOT, _SRC_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
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


def pytest_configure(config):
    """Disable pytest-asyncio async collection. None of our tests are
    async, and the plugin's autouse fixture walks a temp dir that on
    Windows raises PermissionError on stale locks (handled above by
    redirecting tempfile.tempdir, but we also tell asyncio to skip)."""
    config.option.asyncio_mode = "auto"


@pytest.fixture(autouse=True)
def _isolate_review_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto-isolate src.mesh.queue.QUEUE_DIR to a per-test tmp dir.

    Uses pytest's built-in `tmp_path` (per-test, auto-cleaned by pytest)
    instead of `tmp_path_factory.mktemp()` which on Windows creates dirs
    under `AppData\\Local\\Temp\\pytest-of-mathe\\` and raises
    `PermissionError [WinError 5]` when stale dirs from a prior run are
    locked. `tmp_path` is the canonical pytest isolation pattern and
    sidesteps the shared-temp-lock bug.

    Tests that explicitly request a `tmp_queue` / `queue_dir` fixture
    still win because explicit fixtures run after this autouse one.
    Tests that forget to override get safe isolation and never pollute
    `data/review_queue/` on the developer's machine.
    """
    from src.mesh import queue as queue_mod

    monkeypatch.setattr(queue_mod, "QUEUE_DIR", tmp_path)
