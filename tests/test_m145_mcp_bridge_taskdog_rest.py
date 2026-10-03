"""M145 tests: taskdog fork tools + MCP resource accessors on .claude/loop/mcp_bridge.py.

Adds 2 taskdog fork wrappers (read-side) + 6 resource accessors on top of
M142/M144's 12 wrappers:
  - taskdog_read(ueid, db_path=None)
  - taskdog_supports_field(field_name)
  - read_ueid_resource(ueid)
  - read_queue_pending_resource()
  - read_queue_event_resource(event_id)
  - read_health_resource()
  - read_plans_cycles_resource()
  - read_plans_cycle_resource(cycle_id)

Verified contract:
  1. taskdog_* wrappers delegate to _call() with correct args
  2. taskdog_read's db_path is omitted from payload when None
  3. Each resource accessor delegates to _server.read_resource() with correct URI
  4. RESOURCE_URIS dict has exactly 6 entries (drift guard)
  5. Total wrapper count = 14 (8 read + 6 write)
  6. RESOURCE_URIS uses `{placeholder}` format strings (not f-strings)
  7. Resource accessors don't go through _call (no OTel span)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_PATH = REPO_ROOT / ".claude" / "loop" / "mcp_bridge.py"


@pytest.fixture(scope="module")
def bridge():
    """Load `.claude/loop/mcp_bridge.py` as a module object."""
    spec = importlib.util.spec_from_file_location("loop_mcp_bridge_m145", BRIDGE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._server = None
    return mod


@pytest.fixture
def fake_server(bridge):
    """Bind a MagicMock to bridge._server for the duration of one test.

    Provides BOTH `.call(...)` (for tool wrappers) and
    `.read_resource(uri)` (for resource accessors).
    """
    mock = MagicMock()
    mock.call.return_value = {"ok": True, "tool": "fake"}
    mock.read_resource.return_value = {"ok": True, "resource": "fake"}
    bridge._server = mock
    yield mock
    bridge._server = None


# ---------------------------------------------------------------------------
# Acceptance #1: taskdog_* wrappers delegate correctly
# ---------------------------------------------------------------------------


def test_taskdog_read_calls_with_ueid(bridge, fake_server):
    bridge.taskdog_read(ueid="study:topic:abc")
    fake_server.call.assert_called_once_with(
        "taskdog_read", {"ueid": "study:topic:abc"}
    )


def test_taskdog_read_omits_db_path_when_none(bridge, fake_server):
    """db_path default None → omitted from payload (clean server payload)."""
    bridge.taskdog_read(ueid="study:topic:abc")
    args = fake_server.call.call_args[0][1]
    assert "db_path" not in args


def test_taskdog_read_passes_db_path_when_provided(bridge, fake_server):
    bridge.taskdog_read(ueid="study:topic:abc", db_path="/tmp/td.db")
    fake_server.call.assert_called_once_with(
        "taskdog_read",
        {"ueid": "study:topic:abc", "db_path": "/tmp/td.db"},
    )


def test_taskdog_supports_field_calls_with_field_name(bridge, fake_server):
    bridge.taskdog_supports_field(field_name="priority")
    fake_server.call.assert_called_once_with(
        "taskdog_supports_field", {"field_name": "priority"}
    )


# ---------------------------------------------------------------------------
# Acceptance #3: resource accessors delegate to _server.read_resource
# ---------------------------------------------------------------------------


def test_read_ueid_resource_calls_with_correct_uri(bridge, fake_server):
    bridge.read_ueid_resource(ueid="study:topic:abc")
    fake_server.read_resource.assert_called_once_with(
        "ueid://study:topic:abc"
    )


def test_read_queue_pending_resource_calls_with_correct_uri(bridge, fake_server):
    bridge.read_queue_pending_resource()
    fake_server.read_resource.assert_called_once_with("queue://pending")


def test_read_queue_event_resource_calls_with_correct_uri(bridge, fake_server):
    bridge.read_queue_event_resource(event_id="evt-2026-09-26-001")
    fake_server.read_resource.assert_called_once_with(
        "queue://events/evt-2026-09-26-001"
    )


def test_read_health_resource_calls_with_correct_uri(bridge, fake_server):
    bridge.read_health_resource()
    fake_server.read_resource.assert_called_once_with("health://gateway")


def test_read_plans_cycles_resource_calls_with_correct_uri(bridge, fake_server):
    bridge.read_plans_cycles_resource()
    fake_server.read_resource.assert_called_once_with("plans://cycles")


def test_read_plans_cycle_resource_calls_with_correct_uri(bridge, fake_server):
    bridge.read_plans_cycle_resource(cycle_id="cycle-2026-Q3")
    fake_server.read_resource.assert_called_once_with(
        "plans://cycles/cycle-2026-Q3"
    )


# ---------------------------------------------------------------------------
# Acceptance #4: RESOURCE_URIS dict has exactly 6 entries
# ---------------------------------------------------------------------------


def test_resource_uri_dict_length_is_6(bridge):
    """Drift guard: if a future @MCP.resource is added to server.py,
    the bridge must add it here too. Pinning at 6 prevents silent drift."""
    assert len(bridge.RESOURCE_URIS) == 6, (
        f"RESOURCE_URIS drift: expected 6 entries, got "
        f"{len(bridge.RESOURCE_URIS)}: {sorted(bridge.RESOURCE_URIS.keys())}"
    )


def test_resource_uri_dict_expected_keys(bridge):
    """Pin the exact 6 keys so a typo can't sneak past."""
    assert set(bridge.RESOURCE_URIS.keys()) == {
        "ueid",
        "queue_pending",
        "queue_event",
        "health",
        "plans_cycles",
        "plans_cycle",
    }


def test_resource_uri_dict_expected_values(bridge):
    """Pin the URI templates so server.py + bridge stay aligned."""
    assert bridge.RESOURCE_URIS["ueid"] == "ueid://{ueid}"
    assert bridge.RESOURCE_URIS["queue_pending"] == "queue://pending"
    assert bridge.RESOURCE_URIS["queue_event"] == "queue://events/{event_id}"
    assert bridge.RESOURCE_URIS["health"] == "health://gateway"
    assert bridge.RESOURCE_URIS["plans_cycles"] == "plans://cycles"
    assert bridge.RESOURCE_URIS["plans_cycle"] == "plans://cycles/{cycle_id}"


# ---------------------------------------------------------------------------
# Acceptance #5: total wrapper count = 14 (8 read + 6 write)
# ---------------------------------------------------------------------------


def test_total_wrapper_count_is_36(bridge):
    """M142 (6) + M144 (6) + M145 (2) + M148 (9) + M163/M164 (13) = 36 wrappers."""
    prefixes = ("ikigai_", "taskdog_", "vault_", "investigation_")
    actual = {
        name
        for name in dir(bridge)
        if not name.startswith("_")
        and name.startswith(prefixes)
        and callable(getattr(bridge, name))
    }
    assert len(actual) == 36, (
        f"Expected 36 wrappers (23 prior + 13 M163/M164), got {len(actual)}: "
        f"{sorted(actual)}"
    )


def test_read_subset_count_is_8(bridge):
    """M142 (6) + M145 (2) = 8 read-only wrappers."""
    read_only = {
        "ikigai_decompose",
        "ikigai_read_tasks",
        "ikigai_mesh_show",
        "ikigai_health",
        "ikigai_task_create",
        "taskdog_list",
        "taskdog_read",
        "taskdog_supports_field",
    }
    actual = {
        name for name in read_only
        if hasattr(bridge, name) and callable(getattr(bridge, name))
    }
    assert actual == read_only, (
        f"M142+M145 read-only surface drift: expected={sorted(read_only)}, "
        f"present={sorted(actual)}"
    )


# ---------------------------------------------------------------------------
# Acceptance #6: RESOURCE_URIS uses {placeholder} format strings
# ---------------------------------------------------------------------------


def test_resource_uris_use_placeholder_format(bridge):
    """URIs that need parameterization use {name} format (not f-strings).

    This lets callers do `RESOURCE_URIS['ueid'].format(ueid=...)` cleanly.
    """
    # URIs with placeholders must contain {name}
    assert "{ueid}" in bridge.RESOURCE_URIS["ueid"]
    assert "{event_id}" in bridge.RESOURCE_URIS["queue_event"]
    assert "{cycle_id}" in bridge.RESOURCE_URIS["plans_cycle"]
    # URIs without parameters must NOT contain {name}
    assert "{" not in bridge.RESOURCE_URIS["queue_pending"]
    assert "{" not in bridge.RESOURCE_URIS["health"]
    assert "{" not in bridge.RESOURCE_URIS["plans_cycles"]


def test_resource_uri_format_produces_valid_string(bridge):
    """Sanity check: format() works as expected on each URI."""
    assert bridge.RESOURCE_URIS["ueid"].format(ueid="x") == "ueid://x"
    assert (
        bridge.RESOURCE_URIS["queue_event"].format(event_id="y") == "queue://events/y"
    )
    assert (
        bridge.RESOURCE_URIS["plans_cycle"].format(cycle_id="z")
        == "plans://cycles/z"
    )


# ---------------------------------------------------------------------------
# Acceptance #7: resource accessors don't go through _call
# ---------------------------------------------------------------------------


def test_resource_accessors_do_not_call_server_call(bridge, fake_server):
    """Resources use read_resource(uri), NOT call(tool_name, args)."""
    bridge.read_ueid_resource(ueid="x")
    bridge.read_queue_pending_resource()
    bridge.read_queue_event_resource(event_id="y")
    bridge.read_health_resource()
    bridge.read_plans_cycles_resource()
    bridge.read_plans_cycle_resource(cycle_id="z")
    # All 6 went through read_resource, NOT through call
    assert fake_server.call.call_count == 0, (
        f"Resource accessors should not use _server.call(): "
        f"got {fake_server.call.call_count} calls"
    )
    assert fake_server.read_resource.call_count == 6


# ---------------------------------------------------------------------------
# Bonus: server fake returns the right shape for both tool and resource paths
# ---------------------------------------------------------------------------


def test_resource_accessor_returns_server_payload_verbatim(bridge, fake_server):
    """Per M145 honest scope: accessors return raw server payload."""
    fake_server.read_resource.return_value = {"uri": "ueid://x", "body": "test"}
    result = bridge.read_ueid_resource(ueid="x")
    assert result == {"uri": "ueid://x", "body": "test"}
