"""sf_schedule — UPSERT a scheduled event with overlap detection + blocked_by resolution.

Semantics:
- Atomic UPSERT on ueid (existing row updated in place, new row inserted)
- 5-min overlap detection: if new event's [start_at, end_at) overlaps any existing
  event by >5 min (excluding self), return status="conflict" with conflicts=[...]
- blocked_by resolution: if any dep ueid's status is not "done", return status="blocked"
- Default end_at = start_at + 1h if not provided
- Even on conflict/blocked, the row IS upserted — caller decides whether to retry
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from solverforge_calendar.db import SolverforgeDB
from solverforge_calendar.models import SfScheduleInput, SfScheduleOutput

_OVERLAP_THRESHOLD = timedelta(minutes=5)


def _db() -> SolverforgeDB:
    data_dir = Path(os.environ.get("SOLVERFORGE_DATA_DIR", "data/solverforge_calendar"))
    return SolverforgeDB(data_dir / "unified_planning.db")


def handle(args: dict) -> dict:
    inp = SfScheduleInput.model_validate(args)

    # Default end_at = start_at + 1h
    end_at = inp.end_at if inp.end_at else inp.start_at + timedelta(hours=1)

    db = _db()

    # blocked_by resolution
    status = "scheduled"
    warnings: list[str] = []
    if inp.blocked_by:
        all_done = all(
            (db.read(dep) or {}).get("status") == "done" for dep in inp.blocked_by
        )
        if not all_done:
            status = "blocked"
            warnings.append("blocked_by deps not all done")

    # Overlap detection (5-min threshold)
    conflicts: list[str] = []
    for row in db.list_busy_in_window(start=inp.start_at, end=end_at):
        if row["ueid"] == inp.ueid:
            continue  # skip self (UPDATE case)
        if not row["end_at"]:
            continue
        existing_start = datetime.fromisoformat(row["start_at"])
        existing_end = datetime.fromisoformat(row["end_at"])
        overlap = min(existing_end, end_at) - max(existing_start, inp.start_at)
        if overlap > _OVERLAP_THRESHOLD:
            conflicts.append(row["ueid"])

    if conflicts:
        status = "conflict"
        warnings.append(f"{len(conflicts)} overlap conflict(s)")

    # UPSERT
    result = db.upsert(
        ueid=inp.ueid,
        title=inp.title,
        start_at=inp.start_at,
        end_at=end_at,
        blocked_by=[str(d) for d in inp.blocked_by],
        tags=inp.tags,
        ikigai=inp.ikigai,
        status=status,
    )

    output = SfScheduleOutput(
        ueid=inp.ueid,
        id=result["id"],
        status=status,
        scheduled_at=datetime.now(timezone.utc),
        conflicts=conflicts,
        warnings=warnings,
    )
    return output.model_dump(mode="json")
