"""Shared fixtures for interfaces/cli tests.

Path strategy:
- `life/` repo root and `life/src/` must be on sys.path for `from src.contracts...`
  and `from src.mesh...` imports to resolve.
- Each test gets an isolated tmp data dir to avoid touching real `data/`.

We monkeypatch the module-level constants in src.mesh.adapters and
src.mesh.queue so all writes go to the tmp dir.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure `life/` and `life/src/` are on sys.path for `from src.contracts...` and
# `from src.mesh...` imports to resolve.  Must be done BEFORE any `import
# src.mesh.*` statements (even via `from X import Y`).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
for p in (_SRC_ROOT, _REPO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirect all mesh adapter paths to a fresh tmp directory.

    Returns the tmp data root (use as `data/` substitute).
    """
    # Deferred imports so sys.path fixup above is already applied.
    import src.mesh.adapters.cli as _cli_adapter
    import src.mesh.adapters.taskdog as _taskdog_adapter
    import src.mesh.adapters.solverforge_calendar as _upi_adapter
    import src.mesh.queue as _queue

    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    # CliAdapter: data/tasks.jsonl
    monkeypatch.setattr(_cli_adapter, "TASKS_JSONL", data_root / "tasks.jsonl")

    # TaskdogAdapter: data/taskdog/tasks.db
    taskdog_db = data_root / "taskdog" / "tasks.db"
    monkeypatch.setattr(_taskdog_adapter, "TASKDOG_DB", taskdog_db)

    # SolverforgeCalendarAdapter: data/solverforge_calendar/unified_planning.db
    upi_db = data_root / "solverforge_calendar" / "unified_planning.db"
    monkeypatch.setattr(_upi_adapter, "UPI_DB", upi_db)

    # Mesh queue: data/review_queue/
    monkeypatch.setattr(_queue, "QUEUE_DIR", data_root / "review_queue")

    return data_root
