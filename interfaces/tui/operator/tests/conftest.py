"""Conftest for interfaces/tui/operator/tests/.

Redirects pytest's `tmp_path` to `<repo>/data/pytest-tmp/` to avoid
Windows PermissionError on the user-level temp dir when that dir
is locked by a prior crashed pytest run (per W6.X hygiene wave —
same fix as interfaces/cli/pytest.ini's `--basetemp`).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Ensure `life/` and `life/src/` are on sys.path for `from sys_ikigai.X`
# and `from src.X` imports to resolve.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_ROOT = _REPO_ROOT / "src"
for p in (_REPO_ROOT, _SRC_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


# Redirect tempfile.tempdir (which pytest's tmp_path uses internally) to
# a project-local directory. Without this, pytest-asyncio's autouse
# fixture walks the user-level temp dir and raises PermissionError on
# stale locks (per W6.X).
_TMP_BASE = _REPO_ROOT / "data" / "pytest-tmp"
_TMP_BASE.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_TMP_BASE)
os.environ["TMPDIR"] = str(_TMP_BASE)
os.environ["TEMP"] = str(_TMP_BASE)
os.environ["TMP"] = str(_TMP_BASE)


import pytest  # noqa: E402


@pytest.fixture
def tmp_path_factory_local(tmp_path_factory):
    """tmp_path_factory with basetemp pointing at <repo>/data/pytest-tmp/."""
    return tmp_path_factory


@pytest.fixture
def tmp_path(tmp_path_factory_local):
    """Per-test temp dir under <repo>/data/pytest-tmp/ (avoids Windows lock).

    This overrides pytest's built-in `tmp_path` fixture for tests in
    this directory. Resolves the same problem that
    `interfaces/cli/pytest.ini`'s `--basetemp=.pytest-tmp` solves for
    CLI tests.
    """
    return tmp_path_factory_local.mktemp("pytest-tui")
