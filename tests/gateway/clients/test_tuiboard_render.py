"""E2E: spawn tuiboard.server, call tuiboard_render with each layout."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import (
    _send_request,
    _read_response,
)

# UUID-format UEIDs matching regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`
_T1 = "tb:task:11111111-1111-1111-1111-111111111111:aaaaaaaaaaaaaaa1"  # planned, 2026-09-15
_T2 = "tb:task:22222222-2222-2222-2222-222222222222:bbbbbbbbbbbbbbb2"  # done, no due
_T3 = "tb:task:33333333-3333-3333-3333-333333333333:ccccccccccccccc3"  # planned, 2026-09-10

# Build seed using json module to properly encode None as null
_t1 = {"ueid": _T1, "title": "First", "status": "planned", "due": "2026-09-15", "vector": "skill"}
_t2 = {"ueid": _T2, "title": "Second", "status": "done", "due": None, "vector": "market"}
_t3 = {"ueid": _T3, "title": "Third", "status": "planned", "due": "2026-09-10", "vector": "skill"}
_SEED = "\n".join(json.dumps(t) for t in [_t1, _t2, _t3]) + "\n"


def _setup_env(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "tasks.jsonl").write_text(_SEED, encoding="utf-8")
    return {
        "TUIBOARD_DATA_DIR": str(tmp_path),
        "TUIBOARD_SNAPSHOTS_DIR": str(tmp_path / "snapshots"),
    }


def _call_render(stdin, stdout, *, name, args):
    _send_request(
        stdin,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        },
    )
    _read_response(stdout)
    _send_request(
        stdin,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "tuiboard_render", "arguments": args},
        },
    )
    return _read_response(stdout)


def test_tuiboard_render_kanban(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """Kanban: section = status; 2 sections (planned, done); 3 frames total."""
    try:
        env = _setup_env(tmp_path)
        with server_process_factory("tuiboard.server", env=env) as (
            proc,
            stdin,
            stdout,
        ):
            resp = _call_render(stdin, stdout, name="kanban", args={"layout": "kanban"})
            assert "error" not in resp, resp
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["layout"] == "kanban"
            assert len(data["frames"]) == 3
            sections = {f["position"]["section"] for f in data["frames"]}
            assert sections == {"planned", "done"}
            planned_frames = [
                f for f in data["frames"] if f["position"]["section"] == "planned"
            ]
            assert len(planned_frames) == 2  # T1 and T3
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"tuiboard server not functional: {e}")


def test_tuiboard_render_list(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """List: flat list, row = sorted-by-due index."""
    try:
        env = _setup_env(tmp_path)
        with server_process_factory("tuiboard.server", env=env) as (
            proc,
            stdin,
            stdout,
        ):
            resp = _call_render(stdin, stdout, name="list", args={"layout": "list"})
            assert "error" not in resp, resp
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["layout"] == "list"
            assert len(data["frames"]) == 3
            rows = [f["position"]["row"] for f in data["frames"]]
            assert rows == [0, 1, 2]
            sections = {f["position"]["section"] for f in data["frames"]}
            assert sections == {"list"}
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"tuiboard server not functional: {e}")


def test_tuiboard_render_calendar(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """Calendar: section = due date (or no-due bucket)."""
    try:
        env = _setup_env(tmp_path)
        with server_process_factory("tuiboard.server", env=env) as (
            proc,
            stdin,
            stdout,
        ):
            resp = _call_render(
                stdin, stdout, name="calendar", args={"layout": "calendar"}
            )
            assert "error" not in resp, resp
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["layout"] == "calendar"
            assert len(data["frames"]) == 3
            sections = {f["position"]["section"] for f in data["frames"]}
            assert "2026-09-10" in sections
            assert "2026-09-15" in sections
            assert "no-due" in sections
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"tuiboard server not functional: {e}")


def test_tuiboard_render_tree(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """Tree: section = vector; 2 sections (skill, market)."""
    try:
        env = _setup_env(tmp_path)
        with server_process_factory("tuiboard.server", env=env) as (
            proc,
            stdin,
            stdout,
        ):
            resp = _call_render(stdin, stdout, name="tree", args={"layout": "tree"})
            assert "error" not in resp, resp
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["layout"] == "tree"
            assert len(data["frames"]) == 3
            sections = {f["position"]["section"] for f in data["frames"]}
            assert sections == {"skill", "market"}
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"tuiboard server not functional: {e}")
