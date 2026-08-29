"""Tests for B3.2 mesh tools (ikigai_mesh_show, ikigai_task_create, ikigai_health)."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.contracts.common import UEID


VALID_UEID = UEID("tsk:foo:11111111-1111-1111-1111-111111111111:1111111111111111")


# === ikigai_mesh_show ===

def test_mesh_show_joins_across_adapters() -> None:
    from mcp_server.tools_mesh import ikigai_mesh_show
    from src.mesh.adapters.cli import CliAdapter
    from src.mesh.adapters.taskdog import TaskdogAdapter
    from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter
    adapters = [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]
    with patch("mcp_server.tools_mesh._load_adapters", return_value=adapters):
        result = json.loads(ikigai_mesh_show(ueid=str(VALID_UEID)))
    assert result["ueid"] == str(VALID_UEID)
    assert "view" in result
    assert set(result["view"].keys()) == {"cli", "taskdog", "solverforge_calendar"}


def test_mesh_show_rejects_invalid_ueid() -> None:
    from mcp_server.tools_mesh import ikigai_mesh_show
    result = json.loads(ikigai_mesh_show(ueid="not-a-ueid"))
    assert "error" in result
    assert "UEID" in result["error"]


# === ikigai_task_create ===

def test_task_create_emits_to_review_queue(monkeypatch) -> None:
    import tempfile
    from pathlib import Path
    from mcp_server.tools_mesh import ikigai_task_create

    # Use explicit temp directory to avoid Windows permission issues with pytest tmp_path
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        queue_dir = tmp_path / "review_queue"
        queue_dir.mkdir()
        monkeypatch.setattr("src.mesh.queue.QUEUE_DIR", queue_dir)

        result = json.loads(ikigai_task_create(
            ueid=str(VALID_UEID),
            fields={"title": "Test task", "priority": "high"},
            source_fork="interfaces/cli",
        ))
        assert result["status"] == "pending"
        assert "event_id" in result
        queue_files = list(queue_dir.glob("*.json"))
        assert len(queue_files) == 1
        payload = json.loads(queue_files[0].read_text())
        assert payload["ueid"] == str(VALID_UEID)
        assert payload["action"] == "create"


def test_task_create_rejects_non_create_action() -> None:
    from mcp_server.tools_mesh import ikigai_task_create
    result = json.loads(ikigai_task_create(
        ueid=str(VALID_UEID),
        fields={"title": "x"},
        source_fork="interfaces/cli",
        action="delete",
    ))
    assert "error" in result
    assert "v1" in result["error"]


def test_task_create_rejects_invalid_ueid() -> None:
    from mcp_server.tools_mesh import ikigai_task_create
    result = json.loads(ikigai_task_create(
        ueid="bad",
        fields={"title": "x"},
        source_fork="interfaces/cli",
    ))
    assert "error" in result


def test_task_create_rejects_missing_title() -> None:
    from mcp_server.tools_mesh import ikigai_task_create
    result = json.loads(ikigai_task_create(
        ueid=str(VALID_UEID),
        fields={},
        source_fork="interfaces/cli",
    ))
    assert "error" in result
    assert "title" in result["error"]


# === ikigai_health ===

def test_health_returns_version_and_adapters() -> None:
    from mcp_server.tools_mesh import ikigai_health
    result = json.loads(ikigai_health())
    assert result["name"] == "ikigai-gateway"
    assert result["version"] == "1.0.0"
    assert "uptime_s" in result
    assert result["uptime_s"] >= 0
    adapter_names = {a["name"] for a in result["adapters"]}
    assert {"cli", "taskdog", "solverforge_calendar"} <= adapter_names
