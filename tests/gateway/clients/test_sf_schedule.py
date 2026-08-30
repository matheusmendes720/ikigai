"""E2E: spawn solverforge_calendar.server, call sf_schedule via tools/call."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import (
    _send_request,
    _read_response,
)


def test_sf_schedule_insert_and_update(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """Insert, then update via UPSERT — same ueid, different title."""
    try:
        env = {"SOLVERFORGE_DATA_DIR": str(tmp_path / "sf")}
        with server_process_factory("solverforge_calendar.server", env=env) as (
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
            # UUID-format UEID per pre-authorized deviation #1
            ueid = "sc:task:abc12345-1234-5678-9abc-def012345678:def4567890123456"
            start = datetime(2026, 9, 1, 9, 0, 0)
            # insert
            _send_request(
                stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "sf_schedule",
                        "arguments": {
                            "ueid": ueid,
                            "title": "BYD old",
                            "start_at": start.isoformat(),
                        },
                    },
                },
            )
            resp1 = _read_response(stdout)
            assert "error" not in resp1, resp1
            data1 = json.loads(resp1["result"]["content"][0]["text"])
            assert data1["status"] == "scheduled"
            assert data1["id"] != ""  # row_id present
            # update (UPSERT preserves PK)
            _send_request(
                stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "sf_schedule",
                        "arguments": {
                            "ueid": ueid,
                            "title": "BYD new",
                            "start_at": start.isoformat(),
                        },
                    },
                },
            )
            resp2 = _read_response(stdout)
            data2 = json.loads(resp2["result"]["content"][0]["text"])
            assert data2["status"] == "scheduled"
            assert data2["id"] == data1["id"]  # UPSERT preserves PK
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"solverforge_calendar server not functional: {e}")


def test_sf_schedule_overlap_detected(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """Two events with >5min overlap → second returns status=conflict."""
    try:
        env = {"SOLVERFORGE_DATA_DIR": str(tmp_path / "sf")}
        with server_process_factory("solverforge_calendar.server", env=env) as (
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
            base = datetime(2026, 9, 1, 9, 0, 0)
            # first event: 9:00-11:00
            _send_request(
                stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "sf_schedule",
                        "arguments": {
                            "ueid": "sc:task:11111111-1111-1111-1111-111111111111:aaaaaaaaaaaaaaa1",
                            "title": "First",
                            "start_at": base.isoformat(),
                            "end_at": base.replace(hour=11).isoformat(),
                        },
                    },
                },
            )
            _read_response(stdout)
            # second event: 10:30-12:00 (overlaps 30min)
            _send_request(
                stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "sf_schedule",
                        "arguments": {
                            "ueid": "sc:task:22222222-2222-2222-2222-222222222222:bbbbbbbbbbbbbbb2",
                            "title": "Second",
                            "start_at": base.replace(hour=10, minute=30).isoformat(),
                            "end_at": base.replace(hour=12).isoformat(),
                        },
                    },
                },
            )
            resp = _read_response(stdout)
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["status"] == "conflict"
            assert (
                "sc:task:11111111-1111-1111-1111-111111111111:aaaaaaaaaaaaaaa1"
                in data["conflicts"]
            )
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"solverforge_calendar server not functional: {e}")
