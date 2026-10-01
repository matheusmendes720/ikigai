"""Tests for the Studio UI server.

Coverage (4 endpoints + helpers):
  - GET  /                       serves index.html
  - GET  /styles.css             serves styles.css
  - GET  /api/tasks              returns empty list + by_status=0s
  - POST /api/tasks              creates a task, returns 201 + slice
  - POST /api/tasks/{ueid}/done  marks task done (idempotent)
  - POST /api/chat               proxies to LangGraph API (503 when down)
  - GET  /api/metrics            drift + invariant count payload

The Studio app uses the existing TaskdogAdapter, so all writes hit
the local SQLite (monkeypatched to tmp_data_dir via the conftest fixture).
HTTP bridge is disabled for tests (env TASKDOG_HTTP_ENABLED=0) so the
daemon on :8000 doesn't shadow the fixture.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

VALID_UEID = "tsk:studio-test:00000000-0000-0000-0000-000000000001:0000000000000001"
VALID_UEID_2 = "tsk:studio-test-2:00000000-0000-0000-0000-000000000002:0000000000000002"


# ----------------------------------------------------------------------
# Static
# ----------------------------------------------------------------------


def test_root_serves_index_html(client) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "<!doctype html>" in r.text.lower()
    assert "Life Studio" in r.text or "Studio" in r.text


def test_styles_css_served(client) -> None:
    r = client.get("/styles.css")
    assert r.status_code == 200
    assert ":root" in r.text or "--bg" in r.text


# ----------------------------------------------------------------------
# Tasks — list
# ----------------------------------------------------------------------


def test_list_tasks_empty_returns_zero(client) -> None:
    r = client.get("/api/tasks")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 0
    assert body["tasks"] == []
    assert body["by_status"] == {}


def test_list_tasks_after_create_returns_count(client) -> None:
    # Seed: create one task via POST
    cr = client.post(
        "/api/tasks",
        json={"ueid": VALID_UEID, "title": "first task", "priority": "high"},
    )
    assert cr.status_code == 201, cr.text

    r = client.get("/api/tasks")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["tasks"][0]["ueid"] == VALID_UEID
    assert body["by_status"] == {"planned": 1}


def test_list_tasks_status_filter(client) -> None:
    # Create one planned task and mark it done.
    client.post(
        "/api/tasks",
        json={"ueid": VALID_UEID, "title": "filter me"},
    )
    client.post(f"/api/tasks/{VALID_UEID}/done")

    r = client.get("/api/tasks", params={"status": "done"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["tasks"][0]["status"] == "done"

    r = client.get("/api/tasks", params={"status": "planned"})
    body = r.json()
    assert body["count"] == 0


def test_list_tasks_limit(client) -> None:
    # Seed 2 tasks
    for ueid in (VALID_UEID, VALID_UEID_2):
        client.post("/api/tasks", json={"ueid": ueid, "title": f"task {ueid}"})

    r = client.get("/api/tasks", params={"limit": 1})
    body = r.json()
    assert body["count"] == 1


# ----------------------------------------------------------------------
# Tasks — create
# ----------------------------------------------------------------------


def test_create_task_returns_201_and_slice(client) -> None:
    r = client.post(
        "/api/tasks",
        json={"ueid": VALID_UEID, "title": "hello", "priority": "medium"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["ueid"] == VALID_UEID
    assert body["slice"]["name"] == "hello"
    assert body["slice"]["status"] == "planned"
    assert body["slice"]["priority"] == 2  # "medium" -> 2


def test_create_task_rejects_invalid_ueid(client) -> None:
    r = client.post(
        "/api/tasks",
        json={"ueid": "not-a-ueid", "title": "x"},
    )
    assert r.status_code == 422


def test_create_task_requires_title(client) -> None:
    r = client.post("/api/tasks", json={"ueid": VALID_UEID})
    assert r.status_code == 422


def test_create_task_rejects_unknown_field(client) -> None:
    """extra='forbid' on CreateTaskBody: unknown fields -> 422."""
    r = client.post(
        "/api/tasks",
        json={"ueid": VALID_UEID, "title": "ok", "sneaky": "value"},
    )
    assert r.status_code == 422


# ----------------------------------------------------------------------
# Tasks — mark done
# ----------------------------------------------------------------------


def test_mark_done_moves_status_to_done(client) -> None:
    client.post("/api/tasks", json={"ueid": VALID_UEID, "title": "do me"})
    r = client.post(f"/api/tasks/{VALID_UEID}/done")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["status"] == "done"
    # Verify in the list view too
    listed = client.get("/api/tasks").json()
    assert listed["tasks"][0]["status"] == "done"


def test_mark_done_is_idempotent(client) -> None:
    client.post("/api/tasks", json={"ueid": VALID_UEID, "title": "idem"})
    first = client.post(f"/api/tasks/{VALID_UEID}/done")
    second = client.post(f"/api/tasks/{VALID_UEID}/done")
    assert first.status_code == 200
    assert second.status_code == 200  # adapter is idempotent on done


def test_mark_done_unknown_ueid_returns_404(client) -> None:
    r = client.post(f"/api/tasks/{VALID_UEID}/done")
    assert r.status_code == 404


def test_mark_done_invalid_ueid_returns_422(client) -> None:
    r = client.post("/api/tasks/not-a-ueid/done")
    assert r.status_code == 422


# ----------------------------------------------------------------------
# Chat
# ----------------------------------------------------------------------


def test_chat_returns_503_when_langgraph_unreachable(client, monkeypatch) -> None:
    """When the LangGraph API isn't reachable, /api/chat returns 503
    with a structured error so the UI can render it inline.
    """
    # Point the server at an unreachable host/port.
    monkeypatch.setattr("interfaces.studio.server.LANGGRAPH_API", "http://127.0.0.1:1")
    monkeypatch.setattr("interfaces.studio.server.CHAT_TIMEOUT_S", 0.5)

    r = client.post("/api/chat", json={"message": "hello"})
    # The server returns 503 with body {ok:false, ...}
    assert r.status_code == 503
    body = r.json()
    assert body["ok"] is False
    assert "thread_id" in body
    assert "error" in body


def test_chat_accepts_explicit_thread_id(client, monkeypatch) -> None:
    """Even when the upstream is down, the server must echo the
    thread_id we supplied so the client can persist state across calls.
    """
    monkeypatch.setattr("interfaces.studio.server.LANGGRAPH_API", "http://127.0.0.1:1")
    monkeypatch.setattr("interfaces.studio.server.CHAT_TIMEOUT_S", 0.5)

    fixed_thread = "11111111-2222-3333-4444-555555555555"
    r = client.post(
        "/api/chat",
        json={"message": "hi", "thread_id": fixed_thread},
    )
    body = r.json()
    assert body["thread_id"] == fixed_thread


def test_chat_rejects_empty_message(client) -> None:
    r = client.post("/api/chat", json={"message": ""})
    assert r.status_code == 422


def test_chat_rejects_extra_field(client) -> None:
    r = client.post(
        "/api/chat",
        json={"message": "hi", "leak": "secret"},
    )
    assert r.status_code == 422


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------


def test_metrics_returns_drift_and_invariants(client, tmp_path, monkeypatch) -> None:
    """When the heartbeat path is missing or pointing at a non-existent
    file, /api/metrics returns a structured payload with skipped=True.
    """
    # Point heartbeat at a non-existent file.
    monkeypatch.setattr(
        "interfaces.studio.server.HEARTBEAT", tmp_path / "no-heartbeat.json"
    )
    r = client.get("/api/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "drift_pass" in body
    assert "last_heartbeat" in body
    assert "daemons_running" in body
    assert "invariant_count" in body
    # No heartbeat file → skipped path
    assert body["last_heartbeat"] is None
    assert body["skipped"] is True


def test_metrics_reads_heartbeat_when_present(client, monkeypatch, tmp_path) -> None:
    """When a heartbeat file exists, /api/metrics surfaces last_heartbeat."""
    hb = tmp_path / ".daemon-heartbeat.json"
    hb.write_text(
        json.dumps({"last_heartbeat": "2026-10-01T12:00:00Z", "tick_id": "x"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("interfaces.studio.server.HEARTBEAT", hb)
    r = client.get("/api/metrics")
    body = r.json()
    assert body["last_heartbeat"] == "2026-10-01T12:00:00Z"
    assert body["skipped"] is False
    assert body["tick_id"] == "x"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def test_pid_alive_returns_true_for_self() -> None:
    """Cross-platform PID check — current process is alive."""
    import os

    from interfaces.studio.server import _pid_alive

    assert _pid_alive(os.getpid()) is True
    assert _pid_alive(0) is False
    assert _pid_alive(-1) is False


def test_count_by_status_groups_correctly() -> None:
    from interfaces.studio.server import _count_by_status

    tasks: list[dict[str, Any]] = [
        {"status": "planned"},
        {"status": "planned"},
        {"status": "done"},
        {"status": None},  # -> "unknown"
        {"status": "in_progress"},
    ]
    out = _count_by_status(tasks)
    assert out == {
        "planned": 2,
        "done": 1,
        "in_progress": 1,
        "unknown": 1,
    }


def test_create_app_returns_fresh_instance() -> None:
    """create_app() factory pattern — two calls produce independent apps."""
    from interfaces.studio.server import create_app

    a = create_app()
    b = create_app()
    assert a is not b
    # Both expose the same routes
    a_paths = {r.path for r in a.routes}
    b_paths = {r.path for r in b.routes}
    assert "/api/tasks" in a_paths
    assert "/api/tasks" in b_paths


def test_invalid_ueid_string_message_contains_ueid_value() -> None:
    """Error responses include the offending UEID so the UI can show it."""
    # Use the validation directly so the test stays self-contained.
    from src.contracts.common import UEID

    with pytest.raises(ValueError) as exc:
        UEID("bogus-format")
    assert "bogus-format" in str(exc.value)