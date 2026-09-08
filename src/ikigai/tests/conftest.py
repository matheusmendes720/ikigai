"""Test suite root — mirrors src/operational/ layout.

After the 2026-09-05 namespace rename (src/ikigai/src/ikigai/ → sys_ikigai/ at
repo root), the THREE import styles below resolve from TWO sys.path entries:
  - `from sys_ikigai.X import Y`     → <repo-root>/sys_ikigai/
  - `from src.mesh import queue`     → <repo-root>/src/mesh/
  - `from contracts.X import Y`      → <repo-root>/src/contracts/

So `_REPO_ROOT` alone (which gives access to BOTH `sys_ikigai/` and `src/`)
suffices. The old `<repo>/src/ikigai/src/` sys.path append was a Plan A
Task 9 followup workaround for the dual-module-identity bug and is removed.

Also auto-isolates src.mesh.queue.QUEUE_DIR to a per-test tmp dir so tests
that touch the review queue never write to the real `data/review_queue/`.
Tests that want a specific queue path can still override via their own
fixture (autouse runs first, then explicit fixtures override).
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — must happen BEFORE any test module or pytest plugin imports
# src.* (some plugins walk sys.path or import src.mesh during their own
# collection/setup).
# ---------------------------------------------------------------------------
# Post-rename: only <repo-root>/ is needed. It contains both `sys_ikigai/`
# (at repo root) and `src/` (the dotted prefix package).
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent  # <repo-root>
_SRC_ROOT = _THIS.parent.parent.parent  # <repo-root>/src/  (contracts/, mesh/)
for _p in (_REPO_ROOT, _SRC_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ---------------------------------------------------------------------------
# Dual-module-identity aliasing (drift invariant — test_drift_invariants.py).
#
# After the 2026-09-05 sys_ikigai namespace rename (commit 685dec5), the
# canonical import path is `sys_ikigai.*`. The W4.7/W6.X drift tests still
# assert BOTH `ikigai.*` AND `sys_ikigai.*` resolve to the same module
# objects — a guard against the dual-module-identity bug class (see memory
# entry [[test-review-queue-worker-dual-module-fix-2026-09-05]]).
#
# Pre-register the legacy `ikigai.*` aliases here so any test that does
# `importlib.import_module("ikigai.security.X")` (or `import ikigai.X.Y`)
# finds the module in sys.modules and skips the path-based loader entirely.
# This is conftest-scoped so it runs once per pytest session, before any
# test module is imported.
_ALIAS_MODULES: tuple[str, ...] = (
    "sys_ikigai",
    "sys_ikigai.entities",
    "sys_ikigai.gateway",
    "sys_ikigai.state_machines",
    "sys_ikigai.propagation",
    "sys_ikigai.vault",
    "sys_ikigai.security",
    "sys_ikigai.security.vault_write_wrapper",
    "sys_ikigai.security.kill_switch",
    "sys_ikigai.security.transition_validator",
    "sys_ikigai.adapters",
    "sys_ikigai.adapters.drift_detector",
    "sys_ikigai.adapters.checkpoint_adapter",
    "sys_ikigai.adapters.sqlite_bridge",
    "sys_ikigai.adapters.state_reducer",
)
for _mod_name in _ALIAS_MODULES:
    _mod = importlib.import_module(_mod_name)
    _alias = _mod_name.replace("sys_ikigai", "ikigai", 1)
    sys.modules.setdefault(_alias, _mod)
del _mod_name, _mod, _alias

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
