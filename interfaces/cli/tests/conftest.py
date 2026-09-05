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

# Append life/src/ikigai/src/ so `from agents.v2.X` resolves from
# interfaces/cli/tests/ (matches src/ikigai/tests/conftest pattern at line 61).
# conftest.py is at life/interfaces/cli/tests/conftest.py → _REPO_ROOT (parents[3]) = life/
_IKIGAI_SRC = _REPO_ROOT / "src" / "ikigai" / "src"
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))


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
    # Second module identity — `mesh.queue` (no `src.` prefix) is imported by
    # `src/mesh/review_queue_worker.py` via `from mesh import queue`. Because
    # sys.path contains BOTH repo-root (.) and src/, Python treats `mesh.queue`
    # and `src.mesh.queue` as two distinct module objects (same file, two
    # module table entries). Patching only `src.mesh.queue.QUEUE_DIR` leaves
    # the worker reading from the unpatched `PROJECT_ROOT/data/review_queue/`,
    # so run_once() finds nothing and consumed=0.
    import mesh.queue as _queue_pkg

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

    # Mesh queue: data/review_queue/ — patch BOTH module identities.
    queue_dir = data_root / "review_queue"
    monkeypatch.setattr(_queue, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(_queue_pkg, "QUEUE_DIR", queue_dir)

    return data_root
