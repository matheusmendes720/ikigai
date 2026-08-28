"""Shared fixtures for interfaces/cli tests.

Path strategy:
- `life/` repo root must be on sys.path for `from src.contracts.common import UEID`.
- Each test gets an isolated tmp data dir to avoid touching real `data/`.

We monkeypatch the module-level constants in src.mesh.adapters and
src.mesh.queue so all writes go to the tmp dir.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure `life/` repo root is on sys.path so `from src.contracts...` works.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Imports happen AFTER sys.path fixup so src.* resolves.
import src.mesh.adapters.cli as _cli_adapter  # noqa: E402
import src.mesh.adapters.taskdog as _taskdog_adapter  # noqa: E402
import src.mesh.adapters.solverforge_calendar as _upi_adapter  # noqa: E402
import src.mesh.queue as _queue  # noqa: E402


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirect all mesh adapter paths to a fresh tmp directory.

    Returns the tmp data root (use as `data/` substitute).
    """
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
