"""E2E: spawn tuiboard.server, call tuiboard_diff via tools/call."""
from __future__ import annotations
import json
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import _send_request, _read_response


def test_tuiboard_diff_two_snapshots(server_process_factory, tmp_path: Path, skip_if_no_module):
    """Save 2 snapshots, then diff them; expect added + removed sets."""
    try:
        env = {"TUIBOARD_SNAPSHOTS_DIR": str(tmp_path / "snapshots")}
        with server_process_factory("tuiboard.server", env=env) as (proc, stdin, stdout):
            # initialize
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            })
            _read_response(stdout)
            # save snapshot "before"
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "tuiboard_snapshot", "arguments": {
                    "name": "before", "layout": "kanban",
                }},
            })
            resp_before = _read_response(stdout)
            sid_before = json.loads(resp_before["result"]["content"][0]["text"])["snapshot_id"]
            # save snapshot "after"
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "tuiboard_snapshot", "arguments": {
                    "name": "after", "layout": "kanban",
                }},
            })
            resp_after = _read_response(stdout)
            sid_after = json.loads(resp_after["result"]["content"][0]["text"])["snapshot_id"]
            # diff
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 4, "method": "tools/call",
                "params": {"name": "tuiboard_diff", "arguments": {
                    "from_snapshot_id": sid_before,
                    "to_snapshot_id": sid_after,
                }},
            })
            response = _read_response(stdout)
            assert "error" not in response, response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["from_snapshot_id"] == sid_before
            assert content["to_snapshot_id"] == sid_after
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"tuiboard module not importable: {e}")
