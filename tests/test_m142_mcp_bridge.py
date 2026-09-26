"""M142 tests: loop-side MCP bridge alignment + drift detector.

Verifies:
  1. `_call()` raises RuntimeError when `_server` is None (acceptance #2)
  2. `_call()` propagates exceptions from `_server` (acceptance #3)
  3. Each of the 6 read-only wrappers returns the FakeMcpServer dict (acceptance #3)
  4. Drift detector: module exposes exactly 6 wrappers (acceptance #4)
  5. Drift detector: forbidden tools (`vault_write` / `ikigai_write_tasks` /
     `investigation_*`) are NOT importable from the module (acceptance #5)
  6. `ikigai_task_create` defaults `dry_run=True` (planner-only invariant)
  7. Wrappers don't take a `_server` positional/kw arg (callers go through
     module-level handle)

The bridge is loaded via `importlib.util.spec_from_file_location` because
`.claude/loop/` is not a Python package (no `__init__.py` — by design, to
keep the loop directory out of the runtime import graph). This is the same
pattern as `tests/test_taskdog_mcp_graph.py`.
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
    spec = importlib.util.spec_from_file_location("loop_mcp_bridge", BRIDGE_PATH)
    assert spec is not None, f"Could not create spec for {BRIDGE_PATH}"
    assert spec.loader is not None, f"Spec has no loader for {BRIDGE_PATH}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Reset module state for tests — production may bind _server in another
    # session, but here we want a clean slate.
    mod._server = None
    return mod


@pytest.fixture
def fake_server(bridge):
    """Bind a MagicMock to bridge._server for the duration of one test."""
    mock = MagicMock()
    mock.call.return_value = {"ok": True, "tool": "fake"}
    bridge._server = mock
    yield mock
    bridge._server = None


# ---------------------------------------------------------------------------
# Acceptance #2: _call raises when _server is None
# ---------------------------------------------------------------------------


def test_call_raises_when_server_is_none(bridge):
    """RuntimeError contract: callers see clear message about M146 binding."""
    bridge._server = None
    with pytest.raises(RuntimeError) as exc_info:
        bridge._call("ikigai_health", {})
    assert "_server is not bound" in str(exc_info.value)
    assert "M146" in str(exc_info.value)  # references the production-binding milestone


# ---------------------------------------------------------------------------
# Acceptance #3: _call propagates exceptions
# ---------------------------------------------------------------------------


def test_call_propagates_server_exception(bridge):
    """Server-side errors surface to caller; no swallowing."""
    mock = MagicMock()
    mock.call.side_effect = ConnectionRefusedError("gateway down")
    bridge._server = mock
    with pytest.raises(ConnectionRefusedError, match="gateway down"):
        bridge._call("ikigai_health", {})
    bridge._server = None


# ---------------------------------------------------------------------------
# Acceptance #3: each of the 6 wrappers returns the FakeMcpServer dict
# ---------------------------------------------------------------------------


EXPECTED_TOOLS = {
    "ikigai_decompose": ("ikigai_decompose", {"task_id": "study:topic:st_python_01"}),
    "ikigai_read_tasks": ("ikigai_read_tasks", {"limit": 50}),
    "ikigai_mesh_show": ("ikigai_mesh_show", {"ueid": "study:topic:st_python_01"}),
    "ikigai_health": ("ikigai_health", {}),
    "taskdog_list": ("taskdog_list", {}),
}


def test_ikigai_decompose_returns_fake_server_dict(bridge, fake_server):
    result = bridge.ikigai_decompose(task_id="study:topic:st_python_01")
    assert result == {"ok": True, "tool": "fake"}
    fake_server.call.assert_called_once_with(
        "ikigai_decompose", {"task_id": "study:topic:st_python_01"}
    )


def test_ikigai_read_tasks_returns_fake_server_dict(bridge, fake_server):
    result = bridge.ikigai_read_tasks()
    assert result == {"ok": True, "tool": "fake"}
    fake_server.call.assert_called_once_with("ikigai_read_tasks", {"limit": 50})


def test_ikigai_read_tasks_with_horizon_passes_kwarg(bridge, fake_server):
    bridge.ikigai_read_tasks(horizon="week", limit=10)
    fake_server.call.assert_called_once_with(
        "ikigai_read_tasks", {"horizon": "week", "limit": 10}
    )


def test_ikigai_mesh_show_returns_fake_server_dict(bridge, fake_server):
    result = bridge.ikigai_mesh_show(ueid="study:topic:st_python_01")
    assert result == {"ok": True, "tool": "fake"}
    fake_server.call.assert_called_once_with(
        "ikigai_mesh_show", {"ueid": "study:topic:st_python_01"}
    )


def test_ikigai_health_returns_fake_server_dict(bridge, fake_server):
    result = bridge.ikigai_health()
    assert result == {"ok": True, "tool": "fake"}
    fake_server.call.assert_called_once_with("ikigai_health", {})


def test_taskdog_list_returns_fake_server_dict(bridge, fake_server):
    result = bridge.taskdog_list()
    assert result == {"ok": True, "tool": "fake"}
    fake_server.call.assert_called_once_with("taskdog_list", {})


def test_taskdog_list_with_filters_passes_kwargs(bridge, fake_server):
    bridge.taskdog_list(status="pending", limit=10)
    fake_server.call.assert_called_once_with(
        "taskdog_list", {"status": "pending", "limit": 10}
    )


# ---------------------------------------------------------------------------
# Acceptance #4: drift detector — exactly 6 wrappers, no silent growth
# ---------------------------------------------------------------------------


def test_drift_count_of_wrapped_tools_is_6(bridge):
    """Pin the M142 surface to 6. Adding a 7th requires explicit spec bump."""
    wrappers = {
        name
        for name in dir(bridge)
        if not name.startswith("_")
        and callable(getattr(bridge, name))
        and name not in {"Any"}  # exclude typing re-export
    }
    assert wrappers == {
        "ikigai_decompose",
        "ikigai_read_tasks",
        "ikigai_mesh_show",
        "ikigai_health",
        "ikigai_task_create",
        "taskdog_list",
    }, f"Expected exactly 6 wrappers, got: {sorted(wrappers)}"


# ---------------------------------------------------------------------------
# Acceptance #5: forbidden tools absent from module surface
# ---------------------------------------------------------------------------


FORBIDDEN_NAMES = {
    "vault_write",
    "vault_read",
    "ikigai_write_tasks",
    "investigation_enqueue",
    "investigation_status",
    "investigation_complete",
    "taskdog_read",
    "taskdog_supports_field",
}


def test_forbidden_tools_not_importable(bridge):
    """M144 territory: vault_write, ikigai_write_tasks, investigation_*, etc."""
    exported = set(dir(bridge))
    leaked = exported & FORBIDDEN_NAMES
    assert not leaked, f"M142 is read-only; forbidden tools leaked: {leaked}"


# ---------------------------------------------------------------------------
# Acceptance #6: ikigai_task_create defaults dry_run=True (planner-only)
# ---------------------------------------------------------------------------


def test_ikigai_task_create_default_is_dry_run(bridge, fake_server):
    """Worker must opt-in to a write explicitly. Default = read-shape."""
    bridge.ikigai_task_create(ueid="study:topic:st_python_01")
    fake_server.call.assert_called_once_with(
        "ikigai_task_create",
        {"ueid": "study:topic:st_python_01", "dry_run": True},
    )


def test_ikigai_task_create_passes_fields_when_provided(bridge, fake_server):
    bridge.ikigai_task_create(
        ueid="study:topic:st_python_01",
        fields={"priority": "P1"},
        dry_run=False,  # explicit opt-in to write
    )
    fake_server.call.assert_called_once_with(
        "ikigai_task_create",
        {"ueid": "study:topic:st_python_01", "fields": {"priority": "P1"}, "dry_run": False},
    )


# ---------------------------------------------------------------------------
# Acceptance #7: wrappers don't accept _server positional/kw (callers go through
# module-level handle)
# ---------------------------------------------------------------------------


def test_wrappers_do_not_accept_server_kwarg(bridge, fake_server):
    """If a caller tries to pass `_server=...`, it's a usage bug — surface it."""
    for fn_name in (
        "ikigai_decompose",
        "ikigai_read_tasks",
        "ikigai_mesh_show",
        "ikigai_health",
        "ikigai_task_create",
        "taskdog_list",
    ):
        fn = getattr(bridge, fn_name)
        with pytest.raises(TypeError):
            # 6 args: fn_name + 5 _server attempts
            fn(_server=fake_server)
