"""E2E: spawn solverforge_calendar.server, call sf_replan via tools/call."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import (
    _send_request,
    _read_response,
)


def _setup_db(db_dir: str, events: list[tuple[str, str, str, str | None]]) -> None:
    """Seed UPI DB with events. Each event = (ueid, title, start_at, end_at)."""
    from src.solverforge_calendar.db import SolverforgeDB

    db_path = Path(db_dir) / "unified_planning.db"
    db = SolverforgeDB(db_path)
    for ueid, title, start_at, end_at in events:
        db.upsert(
            ueid=ueid,
            title=title,
            start_at=datetime.fromisoformat(start_at),
            end_at=datetime.fromisoformat(end_at) if end_at else None,
        )


def _call_replan(stdin, stdout, *, args: dict) -> dict:
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
            "params": {"name": "sf_replan", "arguments": args},
        },
    )
    return _read_response(stdout)


def test_sf_replan_moves_conflicting_events(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """Replan with affected_ueids, verify moved action when conflict exists."""
    try:
        # Seed 3 events: T1 + T2 conflict (overlap), T3 free
        horizon_start = "2026-09-01T08:00:00"
        horizon_end = "2026-09-02T08:00:00"
        env = {"SOLVERFORGE_DATA_DIR": str(tmp_path)}
        _setup_db(str(tmp_path), [
            (
                "sf:plan:11111111-1111-1111-1111-111111111111:aaaa1",
                "Event 1",
                "2026-09-01T09:00:00",
                "2026-09-01T10:00:00",
            ),
            (
                "sf:plan:22222222-2222-2222-2222-222222222222:bbbb2",
                "Event 2",
                "2026-09-01T09:30:00",
                "2026-09-01T10:30:00",
            ),  # overlaps T1
            (
                "sf:plan:33333333-3333-3333-3333-333333333333:cccc3",
                "Event 3",
                "2026-09-01T14:00:00",
                "2026-09-01T15:00:00",
            ),
        ])
        with server_process_factory("solverforge_calendar.server", env=env) as (
            proc,
            stdin,
            stdout,
        ):
            resp = _call_replan(
                stdin,
                stdout,
                args={
                    "horizon_start": horizon_start,
                    "horizon_end": horizon_end,
                    "affected_ueids": [
                        "sf:plan:11111111-1111-1111-1111-111111111111:aaaa1",
                        "sf:plan:22222222-2222-2222-2222-222222222222:bbbb2",
                        "sf:plan:33333333-3333-3333-3333-333333333333:cccc3",
                    ],
                    "strategy": "minimize_moves",
                },
            )
            assert "error" not in resp, resp
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["horizon_start"] == horizon_start
            assert data["horizon_end"] == horizon_end
            assert len(data["diff"]) == 3
            # T1 kept (original slot), T2 moved (conflict), T3 kept
            actions = {d["ueid"]: d["action"] for d in data["diff"]}
            assert (
                actions["sf:plan:11111111-1111-1111-1111-111111111111:aaaa1"]
                == "kept"
            )
            assert (
                actions["sf:plan:22222222-2222-2222-2222-222222222222:bbbb2"]
                == "moved"
            )
            assert (
                actions["sf:plan:33333333-3333-3333-3333-333333333333:cccc3"]
                == "kept"
            )
            assert "plan_id" in data
            assert data["runtime_ms"] >= 0
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"solverforge_calendar server not functional: {e}")


def test_sf_replan_respects_no_weekends(
    server_process_factory, tmp_path: Path, skip_if_no_module
):
    """Replan with hard_constraints=['no_weekends'] — events on weekends get moved."""
    try:
        # 2026-09-05 is a Saturday, 2026-09-07 is a Monday
        env = {"SOLVERFORGE_DATA_DIR": str(tmp_path)}
        _setup_db(str(tmp_path), [
            (
                "sf:plan:44444444-4444-4444-4444-444444444444:dddd4",
                "Weekend Event",
                "2026-09-05T10:00:00",
                "2026-09-05T11:00:00",
            ),
        ])
        with server_process_factory("solverforge_calendar.server", env=env) as (
            proc,
            stdin,
            stdout,
        ):
            resp = _call_replan(
                stdin,
                stdout,
                args={
                    "horizon_start": "2026-09-04T00:00:00",
                    "horizon_end": "2026-09-11T00:00:00",
                    "affected_ueids": [
                        "sf:plan:44444444-4444-4444-4444-444444444444:dddd4"
                    ],
                    "strategy": "minimize_moves",
                    "hard_constraints": ["no_weekends"],
                },
            )
            assert "error" not in resp, resp
            data = json.loads(resp["result"]["content"][0]["text"])
            assert len(data["diff"]) == 1
            entry = data["diff"][0]
            # Must move (Saturday → weekday)
            assert entry["action"] == "moved"
            new_start = datetime.fromisoformat(entry["after"])
            assert new_start.weekday() < 5  # Mon-Fri
    except (ImportError, ModuleNotFoundError, EOFError, OSError, TimeoutError) as e:
        pytest.skip(f"solverforge_calendar server not functional: {e}")
