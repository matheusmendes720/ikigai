"""Tests for B3.3 MCP resources.

Validates:
  - ueid://{ueid} resource reads cross-fork view
  - queue://pending resource lists pending events
  - queue://events/{event_id} resource reads one event
  - health://gateway resource returns heartbeat
  - plans://cycles resource lists cycles
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from src.contracts.common import UEID

VALID_UEID = UEID("tsk:foo:11111111-1111-1111-1111-111111111111:1111111111111111")


# === ueid://{ueid} ===


def test_ueid_resource_returns_cross_fork_view() -> None:
    from mcp_server.resources import ueid_resource

    result = json.loads(ueid_resource(str(VALID_UEID)))
    assert result["ueid"] == str(VALID_UEID)
    assert "view" in result
    # 4-key contract (a2ui = None since adapter class deferred per spec §1)
    assert set(result["view"].keys()) == {"cli", "taskdog", "solverforge_calendar", "a2ui"}


def test_ueid_resource_rejects_invalid_ueid() -> None:
    from mcp_server.resources import ueid_resource

    result = json.loads(ueid_resource("not-a-ueid"))
    assert "error" in result


# === queue://pending ===


def test_queue_pending_resource_returns_list() -> None:
    from mcp_server.resources import queue_pending_resource

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_dir = Path(tmpdir) / "review_queue"
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("src.mesh.queue.QUEUE_DIR", queue_dir)
            result = json.loads(queue_pending_resource())
    assert "events" in result
    assert "count" in result
    assert isinstance(result["events"], list)


# === queue://events/{id} ===


def test_queue_event_resource_returns_event() -> None:
    from mcp_server.resources import queue_event_resource

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_dir = Path(tmpdir) / "review_queue"
        queue_dir.mkdir()
        (queue_dir / "evt_test123.json").write_text(
            json.dumps(
                {
                    "event_id": "evt_test123",
                    "ueid": str(VALID_UEID),
                    "action": "create",
                    "fields": {"title": "Sample"},
                    "source_fork": "interfaces/cli",
                    "timestamp": "2026-08-28T12:00:00",
                    "status": "pending",
                }
            )
        )
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("src.mesh.queue.QUEUE_DIR", queue_dir)
            result = json.loads(queue_event_resource("evt_test123"))
    assert result["event_id"] == "evt_test123"


def test_queue_event_resource_missing_returns_error() -> None:
    from mcp_server.resources import queue_event_resource

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_dir = Path(tmpdir) / "review_queue"
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("src.mesh.queue.QUEUE_DIR", queue_dir)
            result = json.loads(queue_event_resource("evt_missing"))
    assert "error" in result


# === health://gateway ===


def test_health_resource_matches_tool() -> None:
    """health://gateway resource must return identical data to ikigai_health tool.

    ``uptime_s`` is recomputed on every call (a live wall-clock delta), so the
    two snapshots are taken microseconds apart and can straddle a rounding
    boundary. Every other field must match exactly; ``uptime_s`` must agree
    within a small tolerance instead of bit-exactly.
    """
    from mcp_server.resources import health_resource
    from mcp_server.tools_mesh import ikigai_health

    resource_result = json.loads(health_resource())
    tool_result = json.loads(ikigai_health())

    assert set(resource_result) == set(tool_result)
    volatile = {"uptime_s"}
    for key in set(resource_result) - volatile:
        assert resource_result[key] == tool_result[key], f"field {key!r} differs"
    assert abs(resource_result["uptime_s"] - tool_result["uptime_s"]) < 1.0


# === plans://cycles ===


def test_plans_cycles_resource_returns_list() -> None:
    from mcp_server.resources import plans_cycles_resource

    result = json.loads(plans_cycles_resource())
    assert "cycles" in result
    assert isinstance(result["cycles"], list)
