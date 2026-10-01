"""Shared fixtures for interfaces/studio tests.

The studio server lives under `interfaces/studio/` but its imports reach
into `src/mesh/adapters/taskdog.py` (the canonical taskdog adapter). So
the same sys.path + monkeypatch recipe used in `interfaces/cli/tests/conftest.py`
applies here: prepend `<repo>/src` and `<repo>/` to sys.path BEFORE the
imports happen, then redirect mesh adapter paths to a tmp dir.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Path fixup: repo root + src must be on sys.path for `from src.mesh...`
# imports to resolve.  Must be done BEFORE any `import src.*` statements.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
for p in (_SRC_ROOT, _REPO_ROOT):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirect all mesh adapter paths to a fresh tmp directory.

    Returns the tmp data root (use as `data/` substitute).
    """
    import src.mesh.adapters.taskdog as _taskdog_adapter

    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    taskdog_db = data_root / "taskdog" / "tasks.db"
    monkeypatch.setattr(_taskdog_adapter, "TASKDOG_DB", taskdog_db)
    # Force SQLite path (don't try the HTTP daemon) — adapter honors this.
    monkeypatch.setenv("TASKDOG_HTTP_ENABLED", "0")

    return data_root


@pytest.fixture
def client(tmp_data_dir):
    """Yield a FastAPI TestClient with the studio app freshly built."""
    # Import here so the sys.path fixup above is applied first.
    from fastapi.testclient import TestClient

    from interfaces.studio.server import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c