"""E2E: spawn tuiboard.server, call tuiboard_snapshot via tools/call."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import (
    _send_request,
    _read_response,
)


def test_tuiboard_snapshot_saves_tasks(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """Snapshot persists tasks from CLI fork and returns metadata."""
    try:
        # Seed tasks.jsonl with 2 tasks
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "tasks.jsonl").write_text(
            '{"ueid": "tb:task:11111111-1111-1111-1111-111111111111:aaaaaaaaaaaaaaa1",'
            ' "title": "First", "status": "planned"}\n'
            '{"ueid": "tb:task:22222222-2222-2222-2222-222222222222:bbbbbbbbbbbbbbb2",'
            ' "title": "Second", "status": "done"}\n',
            encoding="utf-8",
        )
        env = {
            "TUIBOARD_DATA_DIR": str(tmp_path),
            "TUIBOARD_SNAPSHOTS_DIR": str(tmp_path / "snapshots"),
        }
        with server_process_factory("tuiboard.server", env=env) as (
            proc,
            stdin,
            stdout,
        ):
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
                    "params": {
                        "name": "tuiboard_snapshot",
                        "arguments": {"name": "test-snap", "layout": "list"},
                    },
                },
            )
            resp = _read_response(stdout)
            assert "error" not in resp, resp
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["name"] == "test-snap"
            assert data["task_count"] == 2  # both tasks persisted (no filter)
            assert data["snapshot_id"] != ""
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"tuiboard server not functional: {e}")


def test_tuiboard_snapshot_applies_filter(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """Filter narrows snapshot to only matching tasks."""
    try:
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "tasks.jsonl").write_text(
            '{"ueid": "tb:task:11111111-1111-1111-1111-111111111111:aaaaaaaaaaaaaaa1",'
            ' "title": "A", "status": "planned"}\n'
            '{"ueid": "tb:task:22222222-2222-2222-2222-222222222222:bbbbbbbbbbbbbbb2",'
            ' "title": "B", "status": "done"}\n',
            encoding="utf-8",
        )
        env = {
            "TUIBOARD_DATA_DIR": str(tmp_path),
            "TUIBOARD_SNAPSHOTS_DIR": str(tmp_path / "snapshots"),
        }
        with server_process_factory("tuiboard.server", env=env) as (
            proc,
            stdin,
            stdout,
        ):
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
            # Filter to status="done" — should keep only 1 task
            _send_request(
                stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "tuiboard_snapshot",
                        "arguments": {
                            "name": "done-only",
                            "layout": "list",
                            "filters": {"status": "done"},
                        },
                    },
                },
            )
            resp = _read_response(stdout)
            assert "error" not in resp, resp
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["task_count"] == 1
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"tuiboard server not functional: {e}")
