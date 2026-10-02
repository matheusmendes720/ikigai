"""Direct isolation tests for the 12 taskdog_* wrappers in
``.claude/loop/mcp_bridge.py``.

Why this file exists
--------------------
Each ``taskdog_*`` wrapper is dynamically enumerated by
``src.ikigai/src/agents/taskdog_mcp_graph.py::_build_lc_tools()`` so the
ReAct agent can call it. If any one wrapper raises a ``TypeError`` (wrong
signature) or fails its internal ``_call(...)``, the whole tool flow
crashes. These tests verify the wrappers in isolation — bypassing the
ReAct agent — so the next bridge refactor cannot silently break the
agent's surface.

Test design
-----------
Each test:

  1. Loads ``.claude/loop/mcp_bridge.py`` via ``importlib`` (matches
     how ``langgraph dev`` loads it — the file lives outside any package
     so it cannot be imported as a regular Python module).
  2. Binds ``bridge._server`` to a ``_DirectTaskdogServer`` instance —
     a thin shim that mimics the production binding (M146) where the
     FastMCP gateway client sits behind ``_server``. The shim routes
     ``call(tool_name, args)`` to the registered ``@mcp.tool`` functions
     in ``src/ikigai/src/mcp_server/taskdog_tools.py``.
  3. Calls the wrapper with minimal valid args (synthetic UEID + small
     data).
  4. Asserts no exception was raised.
  5. Asserts the returned value is a non-error dict.
  6. For write ops (CREATE / UPDATE / DONE / DELETE), asserts the
     review queue gained exactly one new file (proves the wrapper
     routed the call through the queue, not directly to SQLite).

Known server-side drift (pre-existing, NOT fixed here)
------------------------------------------------------
Four wrappers in mcp_bridge.py reference tools that are NOT yet
registered in ``taskdog_tools.py`` (cross-MCP server gap):

  - ``taskdog_done``
  - ``taskdog_set_planned_dates``
  - ``taskdog_search``
  - ``taskdog_delete``

For those four, ``_DirectTaskdogServer`` routes to in-test stub
implementations that follow the canonical enqueue contract (a
``TaskChange`` lands in the queue with the right ``action`` /
``fields``). This isolates bridge-wrapper testing from server-side
drift — the wrapper contract is what we care about here.

Run with::

    cd <repo> && python -m pytest tests/test_mcp_bridge_taskdog_battery.py -q
"""

from __future__ import annotations

import importlib.util
import json
import sys
import uuid as _uuid
from datetime import datetime as _datetime
from pathlib import Path
from typing import Any, Callable

import pytest

# ---------------------------------------------------------------------------
# Paths + sys.path setup
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_PATH = REPO_ROOT / ".claude" / "loop" / "mcp_bridge.py"

# taskdog_tools.py lives at src/ikigai/src/mcp_server/. Add both <repo>/src
# (so `from src.mesh.X` resolves via the dual-module identity pattern in
# tests/conftest.py) and <repo>/src/ikigai/src (so the dotted-prefix
# imports inside taskdog_tools.py resolve).
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "ikigai" / "src"))


# ---------------------------------------------------------------------------
# Bridge loader
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bridge():
    """Load `.claude/loop/mcp_bridge.py` as a module object.

    Loaded via ``importlib.util.spec_from_file_location`` because
    `.claude/loop/` is not a Python package (no `__init__.py` — by
    design, to keep the loop directory out of the runtime import
    graph). Same pattern as `tests/test_m142_mcp_bridge.py` and
    `tests/test_m148_taskdog_full_bridge.py`.
    """
    spec = importlib.util.spec_from_file_location(
        "loop_mcp_battery_bridge", BRIDGE_PATH
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._server = None  # ensure clean slate
    return mod


# ---------------------------------------------------------------------------
# Isolated env: tmp SQLite + tmp review queue
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Set up a tmp SQLite DB + tmp review queue + TASKDOG_DB override.

    Both `src.mesh.adapters.taskdog.TASKDOG_DB` and
    `src.mesh.queue.QUEUE_DIR` are monkeypatched to tmp paths so the
    tests never touch the real `data/taskdog/tasks.db` or
    `data/review_queue/`. The queue's pre-test file set is captured so
    each test can assert exactly how many NEW files were written during
    its run (queue was pre-existing before the tests started).
    """
    db_path = tmp_path / "tasks.db"
    queue_dir = tmp_path / "review_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)

    # Dotted-prefix path (production uses src.mesh.X).
    from src.mesh.adapters import taskdog as taskdog_mod
    monkeypatch.setattr(taskdog_mod, "TASKDOG_DB", db_path)

    from src.mesh import queue as queue_mod
    monkeypatch.setattr(queue_mod, "QUEUE_DIR", queue_dir)

    return {
        "db_path": db_path,
        "queue_dir": queue_dir,
        "queue_files_before": set(queue_dir.glob("*.json")),
    }


# ---------------------------------------------------------------------------
# _DirectTaskdogServer — mimics the production binding (M146)
# ---------------------------------------------------------------------------


# Tool-name → keyword-args that the registered @mcp.tool function expects.
# Used to dispatch bridge → server when the args dict already has the right
# shape; we just splat into the function. Matches the signatures in
# src/ikigai/src/mcp_server/taskdog_tools.py exactly.
def _enqueue_event(
    action_str: str,
    ueid: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Build a TaskChange + enqueue it to the mesh review queue.

    Mirrors ``taskdog_tools._build_task_change`` — used by the 4 stub
    tools (taskdog_done / taskdog_delete / taskdog_search /
    taskdog_set_planned_dates) that mcp_bridge.py references but that
    ``taskdog_tools.py`` has not yet registered.
    """
    from contracts.task_change import TaskAction, TaskChange
    from src.mesh.queue import enqueue

    event = TaskChange(
        event_id=str(_uuid.uuid4()),
        ueid=ueid,  # type: ignore[arg-type] — Pydantic validates at construction
        action=TaskAction(action_str),
        fields=fields,
        source_fork="bridge_battery_test",
        timestamp=_datetime.now(),
    )
    event_id = enqueue(event)
    return {
        "event_id": event_id,
        "action": action_str,
        "ueid": ueid,
    }


class _DirectTaskdogServer:
    """Test-side shim that mimics how langgraph dev binds bridge._server
    to the FastMCP gateway client (M146). Routes ``call(tool_name,
    args)`` to the registered ``@mcp.tool`` functions in
    ``src/ikigai/src/mcp_server/taskdog_tools.py``.

    For 4 tools NOT in taskdog_tools.py (pre-existing drift — see
    module docstring), routes to in-test stubs that follow the
    canonical enqueue contract (TaskChange lands in queue with correct
    action + fields). This isolates bridge-wrapper testing from
    server-side drift.
    """

    def __init__(self) -> None:
        # Lazy import: taskdog_tools.py pulls in UEID + the mesh
        # adapter at module load. Keep it lazy so the fixture setup
        # stays cheap.
        #
        # IMPORTANT: tests/ has its own `mcp_server/` test package that
        # shadows the real `src/ikigai/src/mcp_server/` once pytest
        # collects the test files. We must load taskdog_tools.py via
        # importlib from its canonical file path so the shadow doesn't
        # resolve our import to the test package.
        import importlib.util as _ilu
        taskdog_tools_path = (
            REPO_ROOT / "src" / "ikigai" / "src" / "mcp_server" / "taskdog_tools.py"
        )
        spec = _ilu.spec_from_file_location(
            "ikigai_mcp_taskdog_tools_canonical", taskdog_tools_path,
        )
        assert spec is not None and spec.loader is not None
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self._tt = mod

    # ------------------------------------------------------------------
    # public route
    # ------------------------------------------------------------------
    def call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool_name in self._STUB_TOOLS:
            return self._STUB_TOOLS[tool_name](args)
        # Otherwise dispatch to the real @mcp.tool function in
        # taskdog_tools.py. The registered functions all return JSON
        # strings; we parse to a dict so the bridge wrapper return
        # type (``dict[str, Any]``) is honored.
        fn = getattr(self._tt, tool_name)
        result_str = fn(**args)
        return json.loads(result_str)

    # ------------------------------------------------------------------
    # Stub handlers (server-side drift — see module docstring)
    # ------------------------------------------------------------------
    @staticmethod
    def _stub_done(args: dict[str, Any]) -> dict[str, Any]:
        """Mimic taskdog_done: enqueues TaskAction.DONE with no fields."""
        return _enqueue_event("done", args["ueid"], {})

    @staticmethod
    def _stub_delete(args: dict[str, Any]) -> dict[str, Any]:
        """Mimic taskdog_delete: enqueues TaskAction.DELETE."""
        return _enqueue_event("delete", args["ueid"], {})

    @staticmethod
    def _stub_set_planned_dates(args: dict[str, Any]) -> dict[str, Any]:
        """Mimic taskdog_set_planned_dates: enqueues UPDATE with both date fields."""
        return _enqueue_event(
            "update",
            args["ueid"],
            {
                "planned_start": args["planned_start"],
                "planned_end": args["planned_end"],
            },
        )

    @staticmethod
    def _stub_search(args: dict[str, Any]) -> dict[str, Any]:
        """Mimic taskdog_search: read-only search via TaskdogAdapter.

        Searches by substring on `name`. Returns the matching slice
        list directly (no enqueue). The real implementation is in
        mcp_server.taskdog_tools (NOT YET REGISTERED — see module
        docstring) — this stub fills the gap so the bridge test can
        exercise the wrapper.
        """
        from src.mesh.adapters.taskdog import TaskdogAdapter

        all_tasks = TaskdogAdapter().list_all()
        query = (args.get("query") or "").lower()
        status_filter = args.get("status")
        priority_filter = args.get("priority")
        limit = args.get("limit") or 10

        matches: list[dict[str, Any]] = []
        for t in all_tasks:
            name = (t.get("name") or "").lower()
            if query not in name:
                continue
            if status_filter is not None and t.get("status") != status_filter:
                continue
            # priority normalization: accept int (1/2/3) or string ("high"/"medium"/"low")
            if priority_filter is not None:
                prio_int: int | None
                if isinstance(priority_filter, int):
                    prio_int = priority_filter
                elif isinstance(priority_filter, str):
                    m = {"high": 1, "medium": 2, "low": 3}
                    prio_int = m.get(priority_filter.lower())
                else:
                    prio_int = None
                if t.get("priority") != prio_int:
                    continue
            matches.append(t)
            if len(matches) >= limit:
                break
        return {"count": len(matches), "tasks": matches}

    _STUB_TOOLS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
        "taskdog_done": _stub_done,
        "taskdog_delete": _stub_delete,
        "taskdog_set_planned_dates": _stub_set_planned_dates,
        "taskdog_search": _stub_search,
    }


# ---------------------------------------------------------------------------
# Per-test bridge._server binding
# ---------------------------------------------------------------------------


@pytest.fixture
def bound_server(bridge, isolated_env):
    """Bind a fresh ``_DirectTaskdogServer`` to ``bridge._server`` for
    one test. Always cleans up by setting ``bridge._server = None`` in
    teardown so tests can't leak state to each other.
    """
    bridge._server = _DirectTaskdogServer()
    yield bridge._server
    bridge._server = None


# ---------------------------------------------------------------------------
# Helper: count new queue files since the snapshot
# ---------------------------------------------------------------------------


def _new_queue_files(queue_dir: Path, before: set[Path]) -> list[Path]:
    """Return queue files that appeared AFTER the snapshot was taken."""
    after = set(queue_dir.glob("*.json"))
    return sorted(after - before)


# ---------------------------------------------------------------------------
# Synthetic UEIDs (4-part canonical per ADR-014)
# ---------------------------------------------------------------------------
# Mirrors the shape used in tests/test_m148_taskdog_full_bridge.py so the
# pattern is familiar to anyone diffing bridge tests.

_UEID_BASE = "tsk:bridge-battery:00000000-0000-0000-0000-000000000000:0000000000000000"


# ---------------------------------------------------------------------------
# READ-ONLY wrappers (4 tests)
# ---------------------------------------------------------------------------


class TestReadOnlyWrappers:
    """The 4 read-only taskdog_* wrappers — must NOT enqueue."""

    def test_taskdog_list(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_list() — returns dict with `count` + `tasks` keys."""
        result = bridge.taskdog_list()
        assert isinstance(result, dict)
        # `taskdog_list` returns JSON {count, status_filter, tasks}
        assert "count" in result
        assert "tasks" in result
        assert isinstance(result["tasks"], list)
        # Read-only: no new queue files
        assert _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        ) == []

    def test_taskdog_read(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_read(ueid) — returns dict with `found` + `slice` keys."""
        result = bridge.taskdog_read(ueid=_UEID_BASE)
        assert isinstance(result, dict)
        assert "found" in result
        assert "slice" in result
        # Empty DB → not found
        assert result["found"] is False
        assert result["slice"] is None
        # Read-only: no new queue files
        assert _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        ) == []

    def test_taskdog_supports_field(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_supports_field(field_name) — returns dict with `supported` bool."""
        result = bridge.taskdog_supports_field(field_name="priority")
        assert isinstance(result, dict)
        assert result["field"] == "priority"
        assert result["supported"] is True
        # Also verify a non-supported field is reported False
        result2 = bridge.taskdog_supports_field(field_name="not_a_real_field")
        assert result2["supported"] is False
        # Read-only: no new queue files
        assert _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        ) == []


# ---------------------------------------------------------------------------
# WRITE wrappers (8 tests) — each must produce exactly ONE new queue file
# ---------------------------------------------------------------------------


class TestWriteWrappers:
    """The 8 write taskdog_* wrappers — each enqueues a TaskChange."""

    def test_taskdog_create(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_create(ueid, title, ...) — CREATE TaskChange enqueued."""
        result = bridge.taskdog_create(
            ueid=_UEID_BASE,
            title="Bridge battery CREATE task",
            priority="high",
            due="2099-12-31",
        )
        assert isinstance(result, dict)
        assert result["action"] == "create"
        assert result["ueid"] == _UEID_BASE
        assert "event_id" in result
        # Exactly one new queue file
        new_files = _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        )
        assert len(new_files) == 1, (
            f"expected 1 new queue file, got {len(new_files)}: {new_files}"
        )
        # File content must reflect the CREATE action
        enqueued = json.loads(new_files[0].read_text())
        assert enqueued["action"] == "create"
        assert enqueued["ueid"] == _UEID_BASE
        assert enqueued["fields"]["title"] == "Bridge battery CREATE task"

    def test_taskdog_done(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_done(ueid) — DONE TaskChange enqueued (no fields)."""
        result = bridge.taskdog_done(ueid=_UEID_BASE)
        assert isinstance(result, dict)
        assert result["action"] == "done"
        assert result["ueid"] == _UEID_BASE
        new_files = _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        )
        assert len(new_files) == 1
        enqueued = json.loads(new_files[0].read_text())
        assert enqueued["action"] == "done"
        assert enqueued["fields"] == {}

    def test_taskdog_set_status(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_set_status(ueid, status) — UPDATE with {status} enqueued."""
        result = bridge.taskdog_set_status(ueid=_UEID_BASE, status="in_progress")
        assert isinstance(result, dict)
        assert result["ueid"] == _UEID_BASE
        new_files = _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        )
        assert len(new_files) == 1
        enqueued = json.loads(new_files[0].read_text())
        assert enqueued["action"] == "update"
        assert enqueued["fields"]["status"] == "in_progress"

    def test_taskdog_set_priority(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_set_priority(ueid, priority) — UPDATE with {priority} enqueued."""
        result = bridge.taskdog_set_priority(ueid=_UEID_BASE, priority=1)
        assert isinstance(result, dict)
        assert result["ueid"] == _UEID_BASE
        new_files = _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        )
        assert len(new_files) == 1
        enqueued = json.loads(new_files[0].read_text())
        assert enqueued["action"] == "update"
        assert enqueued["fields"]["priority"] == 1

    def test_taskdog_set_due(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_set_due(ueid, due) — UPDATE with {due} enqueued."""
        result = bridge.taskdog_set_due(ueid=_UEID_BASE, due="2099-12-31")
        assert isinstance(result, dict)
        assert result["ueid"] == _UEID_BASE
        new_files = _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        )
        assert len(new_files) == 1
        enqueued = json.loads(new_files[0].read_text())
        assert enqueued["action"] == "update"
        assert enqueued["fields"]["due"] == "2099-12-31"

    def test_taskdog_set_planned_dates(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_set_planned_dates — UPDATE with {planned_start, planned_end}."""
        result = bridge.taskdog_set_planned_dates(
            ueid=_UEID_BASE,
            planned_start="2099-01-01",
            planned_end="2099-12-31",
        )
        assert isinstance(result, dict)
        assert result["ueid"] == _UEID_BASE
        new_files = _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        )
        assert len(new_files) == 1
        enqueued = json.loads(new_files[0].read_text())
        assert enqueued["action"] == "update"
        assert enqueued["fields"]["planned_start"] == "2099-01-01"
        assert enqueued["fields"]["planned_end"] == "2099-12-31"

    def test_taskdog_cancel(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_cancel(ueid) — UPDATE with {status='cancelled'} enqueued."""
        result = bridge.taskdog_cancel(ueid=_UEID_BASE)
        assert isinstance(result, dict)
        assert result["ueid"] == _UEID_BASE
        new_files = _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        )
        assert len(new_files) == 1
        enqueued = json.loads(new_files[0].read_text())
        assert enqueued["action"] == "update"
        assert enqueued["fields"]["status"] == "cancelled"

    def test_taskdog_delete(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_delete(ueid) — DELETE TaskChange enqueued."""
        result = bridge.taskdog_delete(ueid=_UEID_BASE)
        assert isinstance(result, dict)
        assert result["action"] == "delete"
        assert result["ueid"] == _UEID_BASE
        new_files = _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        )
        assert len(new_files) == 1
        enqueued = json.loads(new_files[0].read_text())
        assert enqueued["action"] == "delete"
        assert enqueued["fields"] == {}

    def test_taskdog_search(
        self, bridge, bound_server, isolated_env,
    ) -> None:
        """taskdog_search(query, ...) — read-only search; no enqueue.

        Returns dict with `count` + `tasks` keys. Wrapper has no
        underlying taskdog_tools.py handler (pre-existing drift —
        `_DirectTaskdogServer` stubs it), but the bridge contract is
        still honored: the wrapper returns a dict and does NOT enqueue.
        """
        result = bridge.taskdog_search(query="bridge battery", limit=5)
        assert isinstance(result, dict)
        assert "count" in result
        assert "tasks" in result
        # Read-only: no new queue files
        assert _new_queue_files(
            isolated_env["queue_dir"], isolated_env["queue_files_before"],
        ) == []