"""Shared fixtures for interfaces/cli tests.

Path strategy:
- `life/` repo root and `life/src/` must be on sys.path for `from src.contracts...`
  and `from src.mesh...` imports to resolve.
- Post 2026-09-05 namespace rename, `sys_ikigai/` lives at repo root too, so
  the `_REPO_ROOT` prepend already covers it. `sys_ikigai/vault/...` etc. resolve
  via `from sys_ikigai.X`.
- BUT: `agents/`, `mcp_server/`, `observability/`, `strategics/`, and
  `ikigai_wrapper.py` are SIBLINGS of `sys_ikigai/`, not inside it (they live
  at `<repo>/src/ikigai/src/`). These still need `<repo>/src/ikigai/src/`
  appended so `from agents.v2.X import Y` etc. resolve.
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

# Append `<repo>/src/ikigai/src/` so sibling packages of sys_ikigai/
# (`agents`, `mcp_server`, `observability`, `strategics`, `ikigai_wrapper`)
# resolve. These are NOT inside `sys_ikigai/` per the 2026-09-05 namespace
# rename. The sys_ikigai/ package itself is at repo root, so it doesn't need
# this entry.
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
    # OUT OF SCOPE for 2026-09-05 sys_ikigai rename: `src/mesh/review_queue_worker.py`
    # imports `from mesh import queue` (bare, no `src.` prefix). Because both
    # `life/` and `life/src/` are on sys.path, `mesh` and `src.mesh` resolve to
    # TWO distinct module instances of the same files. Patching only
    # `src.mesh.queue.QUEUE_DIR` leaves the worker reading from the unpatched
    # `mesh.queue.QUEUE_DIR`, so run_once() finds nothing. Track for follow-up:
    # the structural fix would change production code to `from src.mesh import queue`.
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
