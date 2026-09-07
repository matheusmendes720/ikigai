"""sf_replan — greedy constraint solver for planning horizon replanning.

v1 scope: greedy placement, sorted strategies, no backtracking.
Handles: conflict resolution, hard_constraints (no_weekends, morning_only, weekdays_only),
unresolvable detection, runtime measurement.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from solverforge_calendar.db import SolverforgeDB
from solverforge_calendar.models import SfReplanInput, SfReplanOutput, SfPlanDiff


def _db() -> SolverforgeDB:
    data_dir = Path(os.environ.get("SOLVERFORGE_DATA_DIR", "data/solverforge_calendar"))
    return SolverforgeDB(data_dir / "unified_planning.db")


def handle(args: dict) -> dict:
    inp = SfReplanInput.model_validate(args)
    t0 = time.monotonic()
    plan_id = uuid.uuid4()

    db = _db()
    all_in_horizon = db.list_busy_in_window(
        start=inp.horizon_start, end=inp.horizon_end
    )

    # Determine which ueids to consider
    if inp.affected_ueids:
        # Only replan the listed ueids (keep others untouched in the diff)
        target_ueids = set(str(u) for u in inp.affected_ueids)
    else:
        # Replan everything in horizon
        target_ueids = set(row["ueid"] for row in all_in_horizon)

    diff: list[SfPlanDiff] = []
    unresolvable: list[str] = []
    busy: list[tuple[datetime, datetime]] = []  # tracks placed events

    # Sort by strategy
    rows = [r for r in all_in_horizon if r["ueid"] in target_ueids]
    rows = _sort_by_strategy(rows, inp.strategy, inp.horizon_start)

    for row in rows:
        ueid = row["ueid"]
        before = datetime.fromisoformat(row["start_at"]) if row["start_at"] else None
        end = (
            datetime.fromisoformat(row["end_at"])
            if row["end_at"]
            else before + timedelta(hours=1)
            if before
            else None
        )

        duration = end - before if (before and end) else timedelta(hours=1)

        # Try to keep at original time first (any strategy)
        if before and end and _satisfies_constraints(before, end, inp.hard_constraints):
            if not _conflicts(busy, before, end):
                diff.append(
                    SfPlanDiff(
                        ueid=UEID(ueid),
                        action="kept",
                        before=before,
                        after=before,
                        reason="original slot satisfies constraints",
                    )
                )
                busy.append((before, end))
                continue

        # Try to find a new slot
        new_slot = _find_slot(
            busy,
            inp.horizon_start,
            inp.horizon_end,
            inp.hard_constraints,
            duration,
        )
        if new_slot is None:
            # Cannot place — mark unresolvable
            unresolvable.append(ueid)
            diff.append(
                SfPlanDiff(
                    ueid=UEID(ueid),
                    action="removed",
                    before=before,
                    after=None,
                    reason="no valid slot in horizon",
                )
            )
            # Don't add to busy — event is removed
        else:
            new_start, new_end = new_slot
            if new_start != before:
                # UPSERT with new time
                existing = db.read(ueid) or {}
                db.upsert(
                    ueid=ueid,
                    title=existing.get("title", ""),
                    start_at=new_start,
                    end_at=new_end,
                    blocked_by=existing.get("blocked_by", []),
                    tags=existing.get("tags", []),
                    ikigai=existing.get("ikigai", {}),
                    status=existing.get("status", "scheduled"),
                )
                diff.append(
                    SfPlanDiff(
                        ueid=UEID(ueid),
                        action="moved",
                        before=before,
                        after=new_start,
                        reason="rebalanced per strategy",
                    )
                )
            else:
                diff.append(
                    SfPlanDiff(
                        ueid=UEID(ueid),
                        action="kept",
                        before=before,
                        after=before,
                        reason="original slot satisfies constraints",
                    )
                )
            busy.append((new_start, new_end))

    runtime_ms = int((time.monotonic() - t0) * 1000)
    output = SfReplanOutput(
        plan_id=plan_id,
        horizon_start=inp.horizon_start,
        horizon_end=inp.horizon_end,
        diff=diff,
        unresolvable=[UEID(u) for u in unresolvable],
        runtime_ms=runtime_ms,
    )
    return output.model_dump(mode="json")


def _sort_by_strategy(
    rows: list[dict], strategy: str, horizon_start: datetime
) -> list[dict]:
    """Sort rows by strategy:
    - minimize_moves: original chronological order (preserves existing order)
    - earliest_first: by start_at ascending
    - load_balance: by start_at ascending (spreads naturally)
    Note: earliest_first and load_balance are functionally identical in v1
    (both sort by start_at ascending); they differ semantically in future
    backtracking versions.
    """
    if strategy == "minimize_moves":
        return rows  # already in DB order (chronological)
    # earliest_first and load_balance: sort by start_at ascending
    return sorted(rows, key=lambda r: r["start_at"])


def _satisfies_constraints(
    start: datetime, end: datetime, constraints: list[str]
) -> bool:
    """Check hard constraints. v1 supports:
    - "no_weekends": start.weekday() must be < 5 (Mon-Fri)
    - "morning_only": start.hour must be in [6, 12)
    - "weekdays_only": same as no_weekends
    Unknown constraints → ignored (YAGNI, fail-open per spec).
    """
    for c in constraints:
        if c in ("no_weekends", "weekdays_only") and start.weekday() >= 5:
            return False
        if c == "morning_only" and not (6 <= start.hour < 12):
            return False
    return True


def _conflicts(
    busy: list[tuple[datetime, datetime]], start: datetime, end: datetime
) -> bool:
    """Check if [start, end) overlaps any interval in busy."""
    for b_start, b_end in busy:
        if min(b_end, end) > max(b_start, start):
            return True
    return False


def _find_slot(
    busy: list[tuple[datetime, datetime]],
    horizon_start: datetime,
    horizon_end: datetime,
    constraints: list[str],
    duration: timedelta,
) -> tuple[datetime, datetime] | None:
    """Greedy: scan horizon in 30-min increments, return first valid slot."""
    slot = horizon_start
    while slot + duration <= horizon_end:
        candidate_end = slot + duration
        if _satisfies_constraints(slot, candidate_end, constraints) and not _conflicts(
            busy, slot, candidate_end
        ):
            return (slot, candidate_end)
        slot += timedelta(minutes=30)
    return None


# Re-export UEID locally to avoid line-length issues in SfPlanDiff construction below
from src.contracts.common import UEID  # noqa: E402
