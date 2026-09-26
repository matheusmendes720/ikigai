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
    """Pin the M142 surface to 6. Adding a 7th requires explicit spec bump.

    Counts only the canonical IKIGAI / taskdog wrappers, NOT imports like
    `Status` / `StatusCode` / `get_tracer` (added in M143 for OTel).
    """
    forbidden = {
        "ikigai_decompose",
        "ikigai_read_tasks",
        "ikigai_mesh_show",
        "ikigai_health",
        "ikigai_task_create",
        "taskdog_list",
    }
    actual = {
        name
        for name in forbidden
        if hasattr(bridge, name) and callable(getattr(bridge, name))
    }
    assert actual == forbidden, (
        f"M142 surface drift: expected={sorted(forbidden)}, "
        f"present={sorted(actual)}"
    )
    # And no 7th canonical-style wrapper has been added silently
    actual_wrapped = {
        name
        for name in dir(bridge)
        if not name.startswith("_")
        and name.startswith(("ikigai_", "taskdog_", "vault_", "investigation_"))
        and callable(getattr(bridge, name))
    }
    # M142 enforces 6 read-only wrappers. M144 added 6 more (write-side),
    # bringing the total to 12. Splitting drift detection into read + write
    # subsets lets each milestone evolve independently.
    assert len(actual_wrapped) == 12, (
        f"M142+M144 wrapper drift: expected exactly 12 wrappers (6 read + "
        f"6 write), got {len(actual_wrapped)}: {sorted(actual_wrapped)}"
    )


def test_drift_count_of_read_only_wrappers_is_6(bridge):
    """M142 invariant: read-only slice has exactly 6 wrappers.

    Subset of the 12-wrapper total. If M147 adds a 7th read-only tool,
    this test fails — explicit spec bump required.
    """
    read_only = {
        "ikigai_decompose",
        "ikigai_read_tasks",
        "ikigai_mesh_show",
        "ikigai_health",
        "ikigai_task_create",
        "taskdog_list",
    }
    actual = {
        name for name in read_only
        if hasattr(bridge, name) and callable(getattr(bridge, name))
    }
    assert actual == read_only, (
        f"M142 read-only surface drift: expected={sorted(read_only)}, "
        f"present={sorted(actual)}"
    )


def test_drift_count_of_write_wrappers_is_6(bridge):
    """M144 invariant: write-side slice has exactly 6 wrappers.

    Subset of the 12-wrapper total. If M148 adds a 7th write tool,
    this test fails — explicit spec bump required.
    """
    write_side = {
        "vault_read",
        "ikigai_write_tasks",
        "vault_write",
        "investigation_enqueue",
        "investigation_status",
        "investigation_complete",
    }
    actual = {
        name for name in write_side
        if hasattr(bridge, name) and callable(getattr(bridge, name))
    }
    assert actual == write_side, (
        f"M144 write-side surface drift: expected={sorted(write_side)}, "
        f"present={sorted(actual)}"
    )


# ---------------------------------------------------------------------------
# Acceptance #5: PAV-math tools absent from module surface (still forbidden)
# ---------------------------------------------------------------------------


# Per ADR-013 (planner-only boundary). These 8 PAV-math stubs are registered
# in server.py for v2-graph drift detection but must NEVER appear in the
# loop bridge — they execute math/policy/scoring that the loop layer is
# forbidden to invoke. See src/ikigai/src/mcp_server/server.py:218+ for the
# full list.
FORBIDDEN_NAMES = {
    "ikigai_observe_pav_state",
    "ikigai_score_vectors",
    "ikigai_heuristics",
    "ikigai_balance",
    "ikigai_plan",
    "ikigai_reflect",
    "ikigai_tag_and_persist",
    "ikigai_commit_summary",
}


def test_forbidden_tools_not_importable(bridge):
    """ADR-013: PAV-math tools MUST NOT be importable from the loop bridge.

    Note: as of M144, vault_write / ikigai_write_tasks / investigation_*
    are LEGITIMATE bridge surface (no longer forbidden). This test now
    only checks the 8 PAV-math names.
    """
    exported = set(dir(bridge))
    leaked = exported & FORBIDDEN_NAMES
    assert not leaked, f"PAV-math tools leaked (ADR-013 violation): {leaked}"


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
