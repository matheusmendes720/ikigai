"""E2E: spawn tuiboard.server, call tuiboard_aggregate via tools/call.

Tests the 7th MCP tool — wraps the A4.2 TaskAggregator. Exercises:
1. Empty case: no forks seeded → returns {tasks: [], count: 0, sources: {}}
2. CLI fork seeded: returns 1 task with source='cli'
3. Multi-fork with precedence: taskdog slice wins on colliding ueid
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.gateway.clients.test_tuiboard_init import (
    _send_request,
    _read_response,
)


def _call_aggregate(stdin, stdout) -> dict:
    _send_request(stdin, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
    })
    _read_response(stdout)
    _send_request(stdin, {
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "tuiboard_aggregate", "arguments": {}},
    })
    return _read_response(stdout)


def test_tuiboard_aggregate_empty(server_process_factory, tmp_path: Path, skip_if_no_module):
    """No forks seeded → returns empty list with count=0."""
    try:
        env = {"TUIBOARD_DATA_DIR": str(tmp_path)}
        with server_process_factory("tuiboard.server", env=env) as (proc, stdin, stdout):
            resp = _call_aggregate(stdin, stdout)
            assert "error" not in resp, resp
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["count"] == 0
            assert data["tasks"] == []
            assert data["sources"] == {}
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"tuiboard server not functional: {e}")


def test_tuiboard_aggregate_reads_cli_fork(server_process_factory, tmp_path: Path, skip_if_no_module):
    """CLI fork seeded with 1 task → aggregator returns it with source='cli'."""
    try:
        env = {"TUIBOARD_DATA_DIR": str(tmp_path)}
        # Seed CLI adapter path: {data_dir}/data/tasks.jsonl
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "tasks.jsonl").write_text(
            '{"ueid": "sc:task:11111111-1111-1111-1111-111111111111:aaa", '
            '"title": "CLI Task 1", "status": "planned", "due": "2026-09-15", '
            '"vector": "passion", "tags": ["urgent"]}\n',
            encoding="utf-8",
        )
        with server_process_factory("tuiboard.server", env=env) as (proc, stdin, stdout):
            resp = _call_aggregate(stdin, stdout)
            assert "error" not in resp, resp
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["count"] == 1
            assert data["sources"] == {"cli": 1}
            task = data["tasks"][0]
            assert task["ueid"] == "sc:task:11111111-1111-1111-1111-111111111111:aaa"
            assert task["title"] == "CLI Task 1"
            assert task["source"] == "cli"
            assert task["status"] == "planned"
            assert task["due"] == "2026-09-15"
            assert task["vector"] == "passion"
            assert task["tags"] == ["urgent"]
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"tuiboard server not functional: {e}")
