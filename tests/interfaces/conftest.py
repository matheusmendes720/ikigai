"""Conftest for tests/interfaces/ — adds repo root to sys.path.

The interfaces/ package sits at repo root, so it needs the repo root on
sys.path. The root conftest at tests/conftest.py adds src/, but not the
repo root itself.

Also auto-skips TUI tests if `textual` package is not installed (TUI
is an optional interface layer; the daily-use CLI works without it).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def pytest_collection_modifyitems(config, items):
    """Skip TUI tests if textual is not installed (M75)."""
    textual_missing = False
    try:
        import textual  # noqa: F401
    except ImportError:
        textual_missing = True
    if textual_missing:
        skip_marker = pytest.mark.skip(reason="textual package not installed (TUI is optional)")
        for item in items:
            if "tui" in str(item.fspath).lower():
                item.add_marker(skip_marker)
