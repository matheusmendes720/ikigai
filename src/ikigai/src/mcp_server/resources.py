"""B3.3 MCP resources: ueid://, queue://, health://, plans://.

Exposes read-only views as MCP resources (per A2UI spec §11 R4). UI clients
can read these via resources/read without going through tools.

Resources:
  ueid://{ueid}            cross-fork view (same as ikigai_mesh_show tool)
  queue://pending          list of pending TaskChange events
  queue://events/{id}      one TaskChange event JSON
  health://gateway         gateway heartbeat (mirrors ikigai_health tool)
  plans://cycles           list of recent PlanningCycles
  plans://cycles/{id}      one PlanningCycle full record
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.contracts.common import UEID
from src.mesh import queue as _queue
from src.mesh.adapters import CliAdapter, SolverforgeCalendarAdapter, TaskdogAdapter
from mcp_server.tools_mesh import ikigai_health


# ---------------------------------------------------------------------------
# ueid://{ueid}
# ---------------------------------------------------------------------------
def ueid_resource(ueid: str) -> str:
    """Cross-fork view for one UEID (4-key contract: cli, taskdog, solverforge_calendar, a2ui)."""
    try:
        parsed = UEID(ueid)
    except ValueError as e:
        return json.dumps({"error": f"Invalid UEID: {e}"})

    adapters = [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]
    view: dict[str, Any] = {}
    for adapter in adapters:
        try:
            view[adapter.name] = adapter.read(parsed)
        except Exception as e:
            view[adapter.name] = {"error": f"{type(e).__name__}: {e}"}

    # a2ui key per spec §4.1 — adapter class deferred per spec §1, so null placeholder
    view["a2ui"] = None

    return json.dumps({"ueid": str(parsed), "view": view}, indent=2, default=str)


# ---------------------------------------------------------------------------
# queue://pending
# ---------------------------------------------------------------------------
def queue_pending_resource() -> str:
    """List of pending TaskChange events in data/review_queue/."""
    events = []
    try:
        for event in _queue.consume_pending():
            events.append(
                {
                    "event_id": event.event_id,
                    "ueid": str(event.ueid),
                    "action": event.action.value,
                    "source_fork": event.source_fork,
                    "timestamp": event.timestamp.isoformat(),
                    "status": event.status,
                }
            )
    except Exception as e:
        return json.dumps({"error": f"queue read failed: {e}"})

    return json.dumps({"events": events, "count": len(events)}, indent=2)


# ---------------------------------------------------------------------------
# queue://events/{id}
# ---------------------------------------------------------------------------
def queue_event_resource(event_id: str) -> str:
    """One TaskChange event by ID."""
    qdir = _queue.QUEUE_DIR
    target = qdir / f"{event_id}.json"
    if not target.exists():
        return json.dumps({"error": f"event {event_id!r} not found"})

    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return json.dumps({"error": f"read failed: {e}"})


# ---------------------------------------------------------------------------
# health://gateway
# ---------------------------------------------------------------------------
def health_resource() -> str:
    """Gateway heartbeat (mirrors ikigai_health tool output)."""
    return ikigai_health()


# ---------------------------------------------------------------------------
# plans://cycles
# ---------------------------------------------------------------------------
def plans_cycles_resource() -> str:
    """List of recent PlanningCycles from ~/.ikigai/plan_entities.db."""
    plan_db = Path.home() / ".ikigai" / "plan_entities.db"
    if not plan_db.exists():
        return json.dumps({"cycles": [], "count": 0})

    try:
        import sqlite3

        conn = sqlite3.connect(str(plan_db))
        cur = conn.cursor()
        cur.execute(
            "SELECT cycle_id, regime, q_he, meta_vector, created_at "
            "FROM plan_entities ORDER BY created_at DESC LIMIT 20"
        )
        rows = cur.fetchall()
        conn.close()
        cycles = [
            {
                "cycle_id": row[0],
                "regime": row[1],
                "q_he": row[2],
                "meta_vector": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]
        return json.dumps({"cycles": cycles, "count": len(cycles)}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"plan_entities.db read failed: {e}"})


def plans_cycle_resource(cycle_id: str) -> str:
    """One PlanningCycle full record from ~/.ikigai/plan_entities.db."""
    plan_db = Path.home() / ".ikigai" / "plan_entities.db"
    if not plan_db.exists():
        return json.dumps({"error": "plan_entities.db not found"})

    try:
        import sqlite3

        conn = sqlite3.connect(str(plan_db))
        cur = conn.cursor()
        cur.execute("SELECT * FROM plan_entities WHERE cycle_id = ?", (cycle_id,))
        row = cur.fetchone()
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        if not row:
            return json.dumps({"error": f"cycle {cycle_id!r} not found"})
        return json.dumps(dict(zip(cols, row)), indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": f"read failed: {e}"})


__all__ = [
    "ueid_resource",
    "queue_pending_resource",
    "queue_event_resource",
    "health_resource",
    "plans_cycles_resource",
    "plans_cycle_resource",
]
