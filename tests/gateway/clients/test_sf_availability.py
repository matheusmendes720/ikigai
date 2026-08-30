"""E2E: spawn solverforge_calendar.server, call sf_availability via tools/call."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import (
    _send_request,
    _read_response,
)


def test_sf_availability_empty_window(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """With no events, sf_availability returns the entire window as free."""
    try:
        env = {"SOLVERFORGE_DATA_DIR": str(tmp_path / "sf")}
        with server_process_factory("solverforge_calendar.server", env=env) as (
            proc,
            stdin,
            stdout,
        ):
            start = datetime(2026, 9, 1, 0, 0, 0)
            end = datetime(2026, 9, 1, 23, 59, 0)
            _send_request(
                stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
                },
            )
            _read_response(stdout)  # consume initialize response
            _send_request(
                stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "sf_availability",
                        "arguments": {
                            "window_start": start.isoformat(),
                            "window_end": end.isoformat(),
                        },
                    },
                },
            )
            response = _read_response(stdout)
            assert "error" not in response, response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["window_start"] == start.isoformat()
            assert len(content["free_slots"]) == 1  # entire window is free
            assert content["busy_intervals"] == []
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"solverforge_calendar module not importable: {e}")
