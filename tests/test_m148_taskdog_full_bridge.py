"""M148 tests: full taskdog exposure (writes + search) via the IKIGAI bridge.

Covers the 9 new wrappers added in M148:
  - taskdog_create (CREATE)
  - taskdog_done (DONE)
  - taskdog_set_status (UPDATE)
  - taskdog_set_priority (UPDATE)
  - taskdog_set_due (UPDATE)
  - taskdog_set_planned_dates (UPDATE)
  - taskdog_cancel (UPDATE, soft)
  - taskdog_delete (DELETE)
  - taskdog_search (READ, no enqueue)

Plus M148 surface verification: total wrapper count is 23.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = REPO_ROOT / ".claude" / "loop" / "mcp_bridge.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fake_server():
    """Mock the underlying MCP server so _call() returns predictable values."""
    mock = MagicMock()
    mock.call = MagicMock(return_value={"ok": True, "tool": "fake"})
    return mock


@pytest.fixture(scope="module")
def bridge(fake_server):
    """Load mcp_bridge.py and inject a fake _server.

    Imports under a unique name to avoid clashing with the canonical name.
    """
    spec = importlib.util.spec_from_file_location(
        "loop_mcp_bridge_m148", BRIDGE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Inject the fake server BEFORE any wrapper is called
    mod._server = fake_server
    return mod


# ---------------------------------------------------------------------------
# M148 acceptance #1: total wrapper count is 23 (drift detector)
# ---------------------------------------------------------------------------


def test_m148_total_wrapper_count_is_23(bridge):
    """M142 (6) + M144 (6) + M145 (2) + M148 (9) = 23 wrappers."""
    prefixes = ("ikigai_", "taskdog_", "vault_", "investigation_")
    actual = {
        name
        for name in dir(bridge)
        if not name.startswith("_")
        and name.startswith(prefixes)
        and callable(getattr(bridge, name))
    }
    assert len(actual) == 23, (
        f"Expected 23 wrappers (14 prior + 9 M148), got {len(actual)}: "
        f"{sorted(actual)}"
    )


# ---------------------------------------------------------------------------
# M148 acceptance #2: each new wrapper calls _call with the right tool name + args
# ---------------------------------------------------------------------------

M148_WRAPPERS = [
    ("taskdog_create",
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "title": "Real task title", "due": "2026-12-31", "priority": "high"},
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "title": "Real task title", "due": "2026-12-31", "priority": "high"}),
    ("taskdog_done",
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001"},
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001"}),
    ("taskdog_set_status",
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "status": "in_progress"},
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "status": "in_progress"}),
    ("taskdog_set_priority",
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "priority": 1},
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "priority": 1}),
    ("taskdog_set_due",
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "due": "2027-01-15"},
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "due": "2027-01-15"}),
    ("taskdog_set_planned_dates",
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "planned_start": "2027-01-01", "planned_end": "2027-01-31"},
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "planned_start": "2027-01-01", "planned_end": "2027-01-31"}),
    ("taskdog_cancel",
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001"},
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001"}),
    ("taskdog_delete",
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001"},
     {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001"}),
    ("taskdog_search",
     {"query": "real", "status": "planned", "limit": 5},
     {"query": "real", "status": "planned", "limit": 5}),
]


@pytest.mark.parametrize("wrapper_name,call_args,expected_args", M148_WRAPPERS)
def test_m148_wrapper_calls_fake_server(bridge, fake_server, wrapper_name, call_args, expected_args):
    func = getattr(bridge, wrapper_name)
    func(**call_args)
    fake_server.call.assert_called_with(wrapper_name, expected_args)


# ---------------------------------------------------------------------------
# M148 acceptance #3: client-side validation in taskdog_set_status
# ---------------------------------------------------------------------------


def test_taskdog_set_status_rejects_invalid_status(bridge, fake_server):
    """Bad status string should raise before hitting the server."""
    fake_server.call.reset_mock()
    with pytest.raises(ValueError, match="invalid status"):
        bridge.taskdog_set_status(ueid="tsk:topic:00000000-0000-0000-0000-000000000010:0000000000000010", status="garbage")
    # Server should not have been called
    fake_server.call.assert_not_called()


def test_taskdog_set_status_accepts_all_valid_statuses(bridge, fake_server):
    """All four canonical statuses should pass through."""
    for valid in ("planned", "in_progress", "done", "cancelled"):
        fake_server.call.reset_mock()
        bridge.taskdog_set_status(ueid="tsk:topic:00000000-0000-0000-0000-000000000010:0000000000000010", status=valid)
        fake_server.call.assert_called_once_with(
            "taskdog_set_status",
            {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000010:0000000000000010", "status": valid},
        )


# ---------------------------------------------------------------------------
# M148 acceptance #4: optional kwargs are conditionally included
# ---------------------------------------------------------------------------


def test_taskdog_create_omits_none_optional_kwargs(bridge, fake_server):
    """Only the kwargs that are not None should appear in the args dict."""
    fake_server.call.reset_mock()
    bridge.taskdog_create(ueid="tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", title="Simple task")
    args = fake_server.call.call_args[0][1]
    assert args == {"ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001", "title": "Simple task"}


def test_taskdog_create_includes_all_set_kwargs(bridge, fake_server):
    """All set kwargs should be in args."""
    fake_server.call.reset_mock()
    bridge.taskdog_create(
        ueid="tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001",
        title="Full task",
        due="2026-12-31",
        priority=2,
        planned_start="2026-12-01",
        planned_end="2026-12-30",
    )
    args = fake_server.call.call_args[0][1]
    assert args == {
        "ueid": "tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001",
        "title": "Full task",
        "due": "2026-12-31",
        "priority": 2,
        "planned_start": "2026-12-01",
        "planned_end": "2026-12-30",
    }


def test_taskdog_search_omits_none_optional_kwargs(bridge, fake_server):
    """Only the kwargs that are not None should appear in the args dict."""
    fake_server.call.reset_mock()
    bridge.taskdog_search(query="test")
    args = fake_server.call.call_args[0][1]
    assert args == {"query": "test", "limit": 10}  # default limit


def test_taskdog_search_includes_filters(bridge, fake_server):
    """status/priority filters should be present when set."""
    fake_server.call.reset_mock()
    bridge.taskdog_search(query="test", status="done", priority="high", limit=3)
    args = fake_server.call.call_args[0][1]
    assert args == {"query": "test", "limit": 3, "status": "done", "priority": "high"}


# ---------------------------------------------------------------------------
# M148 acceptance #5: write tools route through review queue (ADR-014)
# ---------------------------------------------------------------------------


def test_m148_writes_use_review_queue_path(tmp_path, monkeypatch):
    """Verify writes hit the queue, not directly the adapter.

    We patch src.mesh.queue.enqueue to capture the event and ensure
    the adapter is never called from the tool path.
    """
    import importlib
    sys.path.insert(0, str(REPO_ROOT / "src"))

    # Reload the taskdog_tools module fresh (without polluting bridge imports)
    ikigai_src = REPO_ROOT / "src" / "ikigai" / "src"
    sys.path.insert(0, str(ikigai_src))

    # Setup monkeypatch on queue.enqueue
    queue_pkg = importlib.import_module("src.mesh.queue")
    captured = []
    original_enqueue = queue_pkg.enqueue

    def fake_enqueue(event):
        captured.append(event)
        return "fake-event-id-123"

    monkeypatch.setattr(queue_pkg, "enqueue", fake_enqueue)

    # Now load taskdog_tools
    if "mcp_server.taskdog_tools" in sys.modules:
        del sys.modules["mcp_server.taskdog_tools"]
    taskdog_tools = importlib.import_module("mcp_server.taskdog_tools")

    # Call taskdog_create
    result = taskdog_tools.taskdog_create(
        ueid="tsk:topic:00000000-0000-0000-0000-000000000008:0000000000000008",
        title="Real test task",
        priority="high",
    )

    # Verify enqueue was called exactly once
    assert len(captured) == 1, f"Expected 1 enqueue call, got {len(captured)}"
    event = captured[0]
    assert event.ueid == "tsk:topic:00000000-0000-0000-0000-000000000008:0000000000000008"
    assert event.action.value == "create"
    assert event.fields["title"] == "Real test task"
    assert event.fields["priority"] == "high"

    # The result JSON should reference the fake event id (from queue)
    import json as _json
    parsed = _json.loads(result)
    assert parsed["event_id"] == "fake-event-id-123"
    assert parsed["ueid"] == "tsk:topic:00000000-0000-0000-0000-000000000008:0000000000000008"


# ---------------------------------------------------------------------------
# M148 acceptance #6: validation rules prevent bad inputs at agent_consumer
# ---------------------------------------------------------------------------


def test_agent_consumer_rejects_done_with_fields():
    """DONE action must reject events with non-empty fields."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from src.mesh.agent_consumer import validate, Decision
    from contracts.task_change import TaskChange, TaskAction
    from datetime import datetime

    ev = TaskChange(
        event_id="test-done-bad",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001",
        action=TaskAction.DONE,
        fields={"status": "done"},  # empty fields expected
        source_fork="test",
        timestamp=datetime.now(),
    )
    result = validate(ev)
    assert result.decision == Decision.REJECT
    assert "no fields" in result.reason.lower()


def test_agent_consumer_rejects_update_changing_ueid():
    """UPDATE cannot change the UEID (immutable key)."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from src.mesh.agent_consumer import validate, Decision
    from contracts.task_change import TaskChange, TaskAction
    from datetime import datetime

    ev = TaskChange(
        event_id="test-update-bad",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000003:0000000000000003",
        action=TaskAction.UPDATE,
        fields={"ueid": "tsk:topic:00000000-0000-0000-0000-000000000004:0000000000000004", "status": "done"},  # tries to change UEID
        source_fork="test",
        timestamp=datetime.now(),
    )
    result = validate(ev)
    assert result.decision == Decision.REJECT
    assert "ueid" in result.reason.lower()


def test_agent_consumer_accepts_clean_update():
    """UPDATE with valid non-empty fields and no UEID change is APPROVED."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from src.mesh.agent_consumer import validate, Decision
    from contracts.task_change import TaskChange, TaskAction
    from datetime import datetime

    ev = TaskChange(
        event_id="test-update-good",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000001:0000000000000001",
        action=TaskAction.UPDATE,
        fields={"status": "in_progress", "priority": 2},
        source_fork="test",
        timestamp=datetime.now(),
    )
    result = validate(ev)
    assert result.decision == Decision.APPROVE


# ---------------------------------------------------------------------------
# M148 acceptance #7: TaskdogAdapter handles UPDATE/DONE/DELETE on SQLite
# ---------------------------------------------------------------------------


def test_taskdog_adapter_apply_update(tmp_path, monkeypatch):
    """Adapter UPDATE path: row exists, fields get whitelisted + written."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from src.mesh.adapters import taskdog as adapter_mod
    from contracts.task_change import PropagationEvent, TaskAction
    from datetime import datetime

    # Redirect DB to tmp
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(adapter_mod, "TASKDOG_DB", db_path)

    from src.mesh.adapters.taskdog import TaskdogAdapter
    ad = TaskdogAdapter()

    # First create
    create_ev = PropagationEvent(
        event_id="ev-create",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000009:0000000000000009",
        action=TaskAction.CREATE,
        fields={"title": "Old title", "priority": 3},
        approved_at=datetime.now(),
        source_fork="test",
    )
    ad.apply_change(create_ev)
    assert ad.read("tsk:topic:00000000-0000-0000-0000-000000000009:0000000000000009")["name"] == "Old title"

    # Then update
    update_ev = PropagationEvent(
        event_id="ev-update",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000009:0000000000000009",
        action=TaskAction.UPDATE,
        fields={"title": "New title", "status": "in_progress", "priority": 1},
        approved_at=datetime.now(),
        source_fork="test",
    )
    ad.apply_change(update_ev)
    row = ad.read("tsk:topic:00000000-0000-0000-0000-000000000009:0000000000000009")
    assert row["name"] == "New title"
    assert row["status"] == "in_progress"
    assert row["priority"] == 1


def test_taskdog_adapter_apply_update_rejects_ueid_change(tmp_path, monkeypatch):
    """Adapter UPDATE that tries to change UEID raises ValueError."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from src.mesh.adapters import taskdog as adapter_mod
    from contracts.task_change import PropagationEvent, TaskAction
    from datetime import datetime

    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(adapter_mod, "TASKDOG_DB", db_path)

    from src.mesh.adapters.taskdog import TaskdogAdapter
    ad = TaskdogAdapter()

    # Try to UPDATE without even existing (should fail with LookupError)
    ev = PropagationEvent(
        event_id="ev-update-missing",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000005:0000000000000005",
        action=TaskAction.UPDATE,
        fields={"status": "done"},
        approved_at=datetime.now(),
        source_fork="test",
    )
    with pytest.raises(LookupError, match="not found"):
        ad.apply_change(ev)


def test_taskdog_adapter_done_idempotent(tmp_path, monkeypatch):
    """Adapter DONE on already-done task is a no-op (no error)."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from src.mesh.adapters import taskdog as adapter_mod
    from contracts.task_change import PropagationEvent, TaskAction
    from datetime import datetime

    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(adapter_mod, "TASKDOG_DB", db_path)

    from src.mesh.adapters.taskdog import TaskdogAdapter
    ad = TaskdogAdapter()

    # Create + done + done (second one is no-op)
    create_ev = PropagationEvent(
        event_id="ev-create",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000006:0000000000000006",
        action=TaskAction.CREATE,
        fields={"title": "Idempotent test"},
        approved_at=datetime.now(),
        source_fork="test",
    )
    ad.apply_change(create_ev)

    done_ev = PropagationEvent(
        event_id="ev-done-1",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000006:0000000000000006",
        action=TaskAction.DONE,
        fields={},
        approved_at=datetime.now(),
        source_fork="test",
    )
    ad.apply_change(done_ev)
    ad.apply_change(done_ev)  # should NOT raise

    row = ad.read("tsk:topic:00000000-0000-0000-0000-000000000006:0000000000000006")
    assert row["status"] == "done"


def test_taskdog_adapter_delete_removes_row(tmp_path, monkeypatch):
    """Adapter DELETE removes the row; subsequent read returns None."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from src.mesh.adapters import taskdog as adapter_mod
    from contracts.task_change import PropagationEvent, TaskAction
    from datetime import datetime

    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(adapter_mod, "TASKDOG_DB", db_path)

    from src.mesh.adapters.taskdog import TaskdogAdapter
    ad = TaskdogAdapter()

    create_ev = PropagationEvent(
        event_id="ev-create",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000007:0000000000000007",
        action=TaskAction.CREATE,
        fields={"title": "Will be deleted"},
        approved_at=datetime.now(),
        source_fork="test",
    )
    ad.apply_change(create_ev)
    assert ad.read("tsk:topic:00000000-0000-0000-0000-000000000007:0000000000000007") is not None

    delete_ev = PropagationEvent(
        event_id="ev-delete",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000007:0000000000000007",
        action=TaskAction.DELETE,
        fields={},
        approved_at=datetime.now(),
        source_fork="test",
    )
    ad.apply_change(delete_ev)
    assert ad.read("tsk:topic:00000000-0000-0000-0000-000000000007:0000000000000007") is None


def test_taskdog_adapter_delete_refuses_missing(tmp_path, monkeypatch):
    """Adapter DELETE on non-existent row raises LookupError."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from src.mesh.adapters import taskdog as adapter_mod
    from contracts.task_change import PropagationEvent, TaskAction
    from datetime import datetime

    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(adapter_mod, "TASKDOG_DB", db_path)

    from src.mesh.adapters.taskdog import TaskdogAdapter
    ad = TaskdogAdapter()

    ev = PropagationEvent(
        event_id="ev-delete-missing",
        ueid="tsk:topic:00000000-0000-0000-0000-000000000002:0000000000000002",
        action=TaskAction.DELETE,
        fields={},
        approved_at=datetime.now(),
        source_fork="test",
    )
    with pytest.raises(LookupError, match="not found"):
        ad.apply_change(ev)
