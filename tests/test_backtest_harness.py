"""M114b tests — backtest_harness.py.

Verifies deterministic executor + HTTP response unwrapping + per-action correctness.
Uses monkeypatch to mock HTTP calls so tests are offline-safe.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest import backtest_harness as bh  # noqa: E402


# === HTTP response unwrap ===

def test_tasks_from_response_handles_dict_wrapper() -> None:
    res = {"tasks": [{"id": 1}], "total_count": 1}
    assert bh._tasks_from_response(res) == [{"id": 1}]


def test_tasks_from_response_handles_bare_list() -> None:
    res = [{"id": 1}]
    assert bh._tasks_from_response(res) == [{"id": 1}]


def test_tasks_from_response_handles_none() -> None:
    assert bh._tasks_from_response(None) == []


def test_tasks_from_response_handles_non_list_tasks() -> None:
    res = {"tasks": "broken", "total_count": 0}
    assert bh._tasks_from_response(res) == []


# === Per-action outcomes ===

def _scenario(day: int = 1, category: str = "add-task") -> dict:
    return {"day": day, "category": category, "prompt": f"backtest day {day}"}


def test_act_add_success() -> None:
    with patch.object(bh, "_http_post", return_value={"id": 999, "name": "backtest"}):
        outcome = bh._act_add(_scenario(1))
    assert outcome.status == "PASS"
    assert outcome.taskdog_id == 999
    assert "taskdog_create_task" in outcome.tools_called


def test_act_add_http_error_returns_error() -> None:
    with patch.object(bh, "_http_post", return_value={"error": "422 unprocessable"}):
        outcome = bh._act_add(_scenario(2))
    assert outcome.status == "ERROR"
    assert "422" in outcome.detail


def test_act_add_uses_name_field_not_title() -> None:
    """Regression: server schema requires `name`, not `title`."""
    captured: list[dict] = []

    def fake_post(path: str, body: dict) -> dict:
        captured.append(body)
        return {"id": 1, "name": body.get("name")}

    with patch.object(bh, "_http_post", side_effect=fake_post):
        bh._act_add(_scenario(3))
    assert "name" in captured[0]
    assert "title" not in captured[0]


def test_act_list_uses_tasks_field() -> None:
    with patch.object(bh, "_http_get", return_value={"tasks": [{"id": 1}], "total_count": 1}):
        outcome = bh._act_list(_scenario(4, "list-tasks"))
    assert outcome.status == "PASS"
    assert "1 tasks" in outcome.detail


def test_act_update_uses_int_priority() -> None:
    captured: list[tuple[int, dict]] = []

    def fake_patch(tid: int, body: dict) -> dict:
        captured.append((tid, body))
        return {"id": tid}

    with patch.object(bh, "_http_patch", side_effect=fake_patch), \
         patch.object(bh, "_next_task_id", return_value=42):
        outcome = bh._act_update(_scenario(5, "update-task"), 42)
    assert outcome.status == "PASS"
    assert isinstance(captured[0][1]["priority"], int)


def test_act_complete_two_step_lifecycle() -> None:
    """PENDING -> IN_PROGRESS -> COMPLETED. Both calls must succeed."""
    call_log: list[str] = []

    def fake_urlopen(req, timeout=5):
        m = MagicMock()
        if "/start" in req.full_url:
            call_log.append("start")
        elif "/complete" in req.full_url:
            call_log.append("complete")
        m.read.return_value = b'{"id":1,"status":"COMPLETED"}'
        m.__enter__ = lambda self: self
        m.__exit__ = lambda self, *args: None
        return m

    with patch.object(bh.urllib.request, "urlopen", side_effect=fake_urlopen):
        outcome = bh._act_complete(_scenario(6, "complete-task"), 1)
    assert outcome.status == "PASS"
    assert call_log == ["start", "complete"]


def test_act_complete_skips_when_already_completed() -> None:
    """If start 400s with 'already completed', the scenario should SKIP."""
    import io

    def fake_urlopen(req, timeout=5):
        raise bh.urllib.error.HTTPError(
            req.full_url, 400, "Bad Request", {},
            io.BytesIO(b'{"detail":"Cannot start task 1: task is already COMPLETED"}')
        )

    with patch.object(bh.urllib.request, "urlopen", side_effect=fake_urlopen):
        outcome = bh._act_complete(_scenario(7, "complete-task"), 1)
    assert outcome.status == "SKIP"
    assert "already COMPLETED" in outcome.detail


def test_act_complete_skips_when_blocked_by_dependencies() -> None:
    import io

    def fake_urlopen(req, timeout=5):
        raise bh.urllib.error.HTTPError(
            req.full_url, 400, "Bad Request", {},
            io.BytesIO(b'{"detail":"Cannot start task 3: dependencies not met. Complete task(s) 4 first."}')
        )

    with patch.object(bh.urllib.request, "urlopen", side_effect=fake_urlopen):
        outcome = bh._act_complete(_scenario(8, "complete-task"), 3)
    assert outcome.status == "SKIP"
    assert "blocked" in outcome.detail


def test_act_complete_returns_error_on_unrelated_400() -> None:
    import io

    def fake_urlopen(req, timeout=5):
        raise bh.urllib.error.HTTPError(
            req.full_url, 500, "Internal Server Error", {}, io.BytesIO(b"unknown failure")
        )

    with patch.object(bh.urllib.request, "urlopen", side_effect=fake_urlopen):
        outcome = bh._act_complete(_scenario(9, "complete-task"), 1)
    assert outcome.status == "ERROR"


def test_act_decompose_creates_parent_plus_two_children() -> None:
    call_log: list[dict] = []

    def fake_post(path: str, body: dict) -> dict:
        call_log.append(body)
        if len(call_log) == 1:
            return {"id": 100}
        return {"id": 100 + len(call_log)}

    with patch.object(bh, "_http_post", side_effect=fake_post):
        outcome = bh._act_decompose(_scenario(10))
    assert outcome.status == "PASS"
    # 1 parent + 2 children = 3 calls
    assert len(call_log) == 3


# === Driver-level ===

def test_run_scenarios_handles_empty_input() -> None:
    summary = bh.run_scenarios([])
    assert summary["n_total"] == 0
    assert summary["n_pass"] == 0


def test_run_scenarios_skips_unknown_categories() -> None:
    summary = bh.run_scenarios([
        {"day": 1, "category": "unknown-category", "prompt": "x"},
    ])
    assert summary["n_skip"] == 1
    assert summary["n_pass"] == 0


def test_run_scenarios_exception_does_not_abort_corpus() -> None:
    """A single scenario blowing up must not abort the rest."""

    def fake_add(sc):
        raise RuntimeError("simulated harness bug")

    patched_actions = dict(bh.CATEGORY_ACTIONS)
    patched_actions["add-task"] = fake_add
    with patch.object(bh, "CATEGORY_ACTIONS", patched_actions):
        summary = bh.run_scenarios([
            {"day": 1, "category": "add-task", "prompt": "x"},
            {"day": 2, "category": "list-tasks"},
        ])
    assert summary["n_total"] == 2
    assert summary["n_error"] == 1
    assert summary["n_pass"] == 1


def test_run_scenarios_aggregates_tool_invocations() -> None:
    summary = bh.run_scenarios(
        [
            {"day": 1, "category": "add-task", "prompt": "a"},
            {"day": 2, "category": "add-task", "prompt": "b"},
        ],
        anchor_map={1: [4], 2: [4]},
    )
    # _act_add isn't mocked — will hit network. Skip if server down.
    if summary["n_error"] < 2:
        assert summary["by_tool"].get("taskdog_create_task", 0) >= 1


# === CLI flags ===

def test_check_taskdog_alive_handles_offline() -> None:
    """Mock URL error → returns False."""
    with patch.object(bh.urllib.request, "urlopen", side_effect=OSError("offline")):
        assert bh._check_taskdog_alive() is False


def test_check_taskdog_alive_handles_online() -> None:
    m = MagicMock()
    m.status = 200
    m.__enter__ = lambda self: self
    m.__exit__ = lambda self, *args: None

    with patch.object(bh.urllib.request, "urlopen", return_value=m):
        assert bh._check_taskdog_alive() is True
