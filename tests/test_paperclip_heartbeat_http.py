"""Tests for the Paperclip canonical HTTP adapter (M190).

Three tests, all use stdlib ``ThreadingHTTPServer`` in a background
thread + ``httpx`` as the test client (already in our dep tree).

* ``test_heartbeat_requires_auth_token`` — POST without ``Authorization``
  → HTTP 401 (per §6.4 of the orchestrator-specs doc, auth is required).
* ``test_heartbeat_returns_run_handle_shape`` — POST with valid payload
  → HTTP 200 with the documented RunHandle shape
  (``status``, ``runId``, ``commitSha``, ``worktreePath``, ``error``).
* ``test_heartbeat_passes_payload_to_graph`` — the ``specText`` from the
  payload must reach ``_build_paperclip_graph`` (proves end-to-end
  plumbing). We monkeypatch the graph factory to a stub that records
  the initial state passed to ``.invoke(...)``.

Test isolation:
- The server module reads ``HEARTBEAT_TOKEN`` at import time, so the
  fixture sets the env var BEFORE importing the module.
- Each test uses an ephemeral port (``socket`` finds a free one) so
  multiple test runs don't collide.
- ``_build_paperclip_graph`` is monkeypatched to a stub so no real
  graph + SqliteSaver + worktree helper subprocess runs.
"""

from __future__ import annotations

import importlib
import os
import socket
import threading
import time
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest


def _find_free_port() -> int:
    """Bind to port 0 to let the OS pick a free port, then release."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def heartbeat_module(monkeypatch: pytest.MonkeyPatch):
    """Import the heartbeat server module with a known token + free port.

    Returns the imported module so tests can monkeypatch its symbols
    (``_build_paperclip_graph``) before the server thread starts.
    """
    monkeypatch.setenv("HEARTBEAT_TOKEN", "test-token-abc")
    monkeypatch.setenv("HEARTBEAT_PORT", "0")
    # Force a fresh import so the env vars take effect at module load.
    if "scripts.paperclip_heartbeat_http" in os.sys.modules:
        del os.sys.modules["scripts.paperclip_heartbeat_http"]
    return importlib.import_module("scripts.paperclip_heartbeat_http")


@pytest.fixture
def server(heartbeat_module: Any) -> Any:
    """Start the heartbeat HTTP server on a free port in a background thread.

    Yields the base URL so tests can ``httpx.post(f"{base}/heartbeat", ...)``.
    Tears the server down on test exit.
    """
    from http.server import ThreadingHTTPServer

    port = _find_free_port()
    server_inst = ThreadingHTTPServer(
        ("127.0.0.1", port), heartbeat_module.HeartbeatHandler
    )
    thread = threading.Thread(target=server_inst.serve_forever, daemon=True)
    thread.start()
    # Give the OS a beat to bind the socket.
    time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server_inst.shutdown()
        server_inst.server_close()
        thread.join(timeout=2)


def test_heartbeat_requires_auth_token(server: str) -> None:
    """POST without Authorization header must return HTTP 401.

    The canonical Paperclip HTTP adapter (§6.4) sends an
    ``Authorization: Bearer <token>`` header on every POST. A missing
    header means either a misconfigured Paperclip agent or a direct
    attack — we fail closed.
    """
    payload = {
        "runId": "run-no-auth",
        "agentId": "agent-xyz",
        "context": {"taskId": "M190", "wakeReason": "scheduled"},
        "specText": "do the thing",
    }
    resp = httpx.post(f"{server}/heartbeat", json=payload, timeout=5.0)
    assert resp.status_code == 401, f"expected 401, got {resp.status_code}"
    body = resp.json()
    assert "error" in body


def test_heartbeat_returns_run_handle_shape(
    server: str, heartbeat_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST with valid payload → HTTP 200 + RunHandle shape.

    Per the SPEC's Endpoint contract, the response MUST carry:
    ``status``, ``runId``, ``commitSha``, ``worktreePath``, ``error``.
    Extra keys are fine (canonical adapter is forward-compatible), but
    the named five are mandatory.
    """
    captured_state: dict[str, Any] = {}

    def fake_invoke(initial_state: Any, config: Any) -> dict[str, Any]:
        captured_state.update(initial_state)
        return {
            "task_id": initial_state.get("task_id"),
            "spec_text": initial_state.get("spec_text"),
            "commit_sha": "deadbeef1234",
            "worktree_path": "/tmp/wt-xyz",
            "branch_name": "feat/M190",
            "tests_ok": True,
            "last_step": "worktree_cleanup",
        }

    fake_graph = MagicMock()
    fake_graph.invoke = fake_invoke

    monkeypatch.setattr(
        heartbeat_module,
        "_build_paperclip_graph",
        lambda **kwargs: fake_graph,
    )

    payload = {
        "runId": "run-shape-123",
        "agentId": "agent-xyz",
        "context": {"taskId": "M190-shape", "wakeReason": "scheduled"},
        "specText": "Add a hello_paperclip() function",
    }
    resp = httpx.post(
        f"{server}/heartbeat",
        json=payload,
        headers={"Authorization": "Bearer test-token-abc"},
        timeout=5.0,
    )
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    required_keys = {"status", "runId", "commitSha", "worktreePath", "error"}
    assert required_keys.issubset(body.keys()), (
        f"RunHandle missing required keys: {required_keys - set(body.keys())} "
        f"in body={body}"
    )
    assert body["status"] == "succeeded", f"expected succeeded, got {body['status']}"
    assert body["runId"] == "run-shape-123"
    assert body["commitSha"] == "deadbeef1234"
    assert body["error"] is None

    # Side-effect: the payload was passed through to the graph factory.
    assert captured_state.get("task_id") == "M190-shape"
    assert captured_state.get("spec_text") == "Add a hello_paperclip() function"


def test_heartbeat_passes_payload_to_graph(
    server: str, heartbeat_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end plumbing: ``specText`` from the payload reaches the graph.

    The canonical Paperclip heartbeat payload carries the user's spec
    text under ``specText`` (custom field per §6.4 payloadTemplate merge).
    The handler MUST pass that text into ``PaperclipStateDict.spec_text``
    so ``read_spec_node`` validates it. We mock the graph factory and
    capture the initial state dict.
    """
    captured: dict[str, Any] = {}

    def fake_invoke(initial_state: Any, config: Any) -> dict[str, Any]:
        captured["initial_state"] = initial_state
        captured["config"] = config
        # Return a "succeeded" final state without errors.
        return {
            "task_id": initial_state.get("task_id"),
            "spec_text": initial_state.get("spec_text"),
            "last_step": "worktree_cleanup",
        }

    fake_graph = MagicMock()
    fake_graph.invoke = fake_invoke

    monkeypatch.setattr(
        heartbeat_module,
        "_build_paperclip_graph",
        lambda **kwargs: fake_graph,
    )

    payload = {
        "runId": "run-plumbing",
        "agentId": "agent-abc",
        "context": {"taskId": "M190-plumbing", "wakeReason": "on_demand"},
        "specText": "PLUMBING_MARKER: build a thing that does a thing",
    }
    resp = httpx.post(
        f"{server}/heartbeat",
        json=payload,
        headers={"Authorization": "Bearer test-token-abc"},
        timeout=5.0,
    )
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    assert captured, "graph.invoke was never called"
    state = captured["initial_state"]
    config = captured["config"]

    # specText → spec_text, context.taskId → task_id, OPEN-3 messages=[]
    assert state["spec_text"] == payload["specText"], (
        f"specText from payload not propagated; state={state}"
    )
    assert state["task_id"] == "M190-plumbing"
    assert state["messages"] == [], "OPEN-3 requires messages=[] initial state"

    # thread_id config drives SqliteSaver keying
    cfg = config.get("configurable", {})
    assert cfg.get("thread_id") == "M190-plumbing", (
        f"thread_id must be task_id for SqliteSaver keying; got config={config}"
    )
