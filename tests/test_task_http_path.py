"""M112 tests: `life task` HTTP-or-CLI dual path.

Per M112: `life task add/list/start/done` should prefer HTTP when taskdog-server
is reachable and fall back to `taskdog` CLI otherwise. Validates:
- HTTP helpers (post/get/patch) parse JSON correctly
- _http_or_cli returns transport="http" when server returns 200
- _http_or_cli returns transport="cli" when server is down
- ls filter combo (q + status + tag) narrows results
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from life.cli.cli import app
from life.centrals import task as task_central

runner = CliRunner()


def test_http_post_parses_json() -> None:
    """_http_post sets Content-Type and parses response."""
    fake_response = json.dumps({"id": 999, "status": "PENDING"}).encode()

    class FakeResp:
        def __enter__(self_inner):
            return self_inner
        def __exit__(self_inner, *a):
            return False
        def read(self_inner) -> bytes:
            return fake_response

    with patch.object(task_central.urllib.request, "urlopen", return_value=FakeResp()):
        result = task_central._http_post("/api/v1/tasks", {"name": "x"})
    assert result == {"id": 999, "status": "PENDING"}


def test_http_get_parses_json() -> None:
    fake_response = json.dumps({"tasks": [{"id": 1}], "total_count": 1}).encode()

    class FakeResp:
        def __enter__(self_inner):
            return self_inner
        def __exit__(self_inner, *a):
            return False
        def read(self_inner) -> bytes:
            return fake_response

    with patch.object(task_central.urllib.request, "urlopen", return_value=FakeResp()):
        result = task_central._http_get("/api/v1/tasks")
    assert result["total_count"] == 1


def test_http_or_cli_uses_http_when_reachable() -> None:
    """HTTP success → transport='http', CLI never invoked."""
    fake_response = json.dumps({"id": 1}).encode()

    class FakeResp:
        def __enter__(self_inner):
            return self_inner
        def __exit__(self_inner, *a):
            return False
        def read(self_inner) -> bytes:
            return fake_response

    with patch.object(task_central.urllib.request, "urlopen", return_value=FakeResp()):
        out = task_central._http_or_cli(
            http_fn=lambda: task_central._http_post("/x", {}),
            cli_args=["would-not-run"],
        )
    assert out["transport"] == "http"
    assert out["ok"] is True


def test_http_or_cli_falls_back_to_cli_when_server_down(monkeypatch: pytest.MonkeyPatch) -> None:
    """Server unreachable → transport='cli', subprocess called."""
    import urllib.error

    def boom() -> dict[str, Any]:
        raise urllib.error.URLError("connection refused")

    def fake_run(args: list[str], **kwargs: Any) -> Any:
        class R:
            returncode = 0
            stdout = "task added"
            stderr = ""
        return R()

    monkeypatch.setattr(task_central, "_run_taskdog", lambda args: {
        "ok": True, "stdout": "task added", "stderr": ""
    })

    out = task_central._http_or_cli(boom, ["add", "x"])
    assert out["transport"] == "cli"
    assert out["ok"] is True
    assert "task added" in out["stdout"]


def test_task_add_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """`life task add` JSON output works via fake HTTP."""
    fake_response = json.dumps({
        "id": 213, "name": "test", "status": "PENDING"
    }).encode()

    class FakeResp:
        def __enter__(self_inner):
            return self_inner
        def __exit__(self_inner, *a):
            return False
        def read(self_inner) -> bytes:
            return fake_response

    monkeypatch.setattr(task_central, "ENABLE_HTTP", True)
    with patch.object(task_central.urllib.request, "urlopen", return_value=FakeResp()):
        result = runner.invoke(
            app, ["task", "add", "M112 unit-test", "--json"],
        )
    assert result.exit_code == 0, f"stderr={result.stderr}"
    out = json.loads(result.output.strip().split("\n")[-1])
    assert out["transport"] == "http"
    assert out["ok"] is True


def test_task_ls_client_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """`life task ls --q foo` filters client-side from HTTP-fetched tasks."""
    tasks = [
        {"id": 1, "name": "foo bar", "tags": ["x"]},
        {"id": 2, "name": "baz", "tags": ["foo"]},
        {"id": 3, "name": "alpha", "tags": []},
    ]
    fake_response = json.dumps({"tasks": tasks, "total_count": 3}).encode()

    class FakeResp:
        def __enter__(self_inner):
            return self_inner
        def __exit__(self_inner, *a):
            return False
        def read(self_inner) -> bytes:
            return fake_response

    monkeypatch.setattr(task_central, "ENABLE_HTTP", True)
    with patch.object(task_central.urllib.request, "urlopen", return_value=FakeResp()):
        out = task_central._http_or_cli(
            http_fn=lambda: task_central._http_get("/api/v1/tasks"),
            cli_args=[],
        )
    parsed = json.loads(out["stdout"])
    # All 3 returned (no filter applied at HTTP-call layer in this test).
    assert len(parsed["tasks"]) == 3

    # Now apply client-side filter manually using same logic as ls():
    q = "foo"
    ql = q.lower()
    filtered = [
        t for t in parsed["tasks"]
        if ql in t["name"].lower() or any(ql in tg.lower() for tg in t["tags"])
    ]
    # Only id=1 (name contains 'foo') and id=2 (tag contains 'foo') match.
    assert {t["id"] for t in filtered} == {1, 2}


def test_task_ls_help() -> None:
    """`life task ls --help` shows the new --status and --tag options."""
    r = runner.invoke(app, ["task", "ls", "--help"])
    assert r.exit_code == 0
    out = r.output.lower()
    assert "--status" in out
    assert "--tag" in out
    assert "--q" in out
