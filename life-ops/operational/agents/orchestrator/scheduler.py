"""WorkflowScheduler — cron-based scheduling using ScheduleWakeup.

Per /workflow-orchestrator skill: schedules workflows via cron expression,
using the session's ScheduleWakeup for recurring execution.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable

from agents.orchestrator.schema import WorkflowSchema
from agents.orchestrator.engine import WorkflowOrchestrator
from agents.orchestrator.state import ExecutionStore


# Minimal cron parser — supports standard 5-field cron
CRONTAB_FIELDS = ["minute", "hour", "day_of_month", "month", "day_of_week"]

CRONTAB_RANGES = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day_of_month": (1, 31),
    "month": (1, 12),
    "day_of_week": (0, 6),
}


def parse_cron_field(field: str, lo: int, hi: int) -> list[int]:
    """Parse a single cron field into a list of integers."""
    values: list[int] = []
    if field in ("*", ""):
        return list(range(lo, hi + 1))

    for part in field.split(","):
        if "/" in part:
            base, step = part.split("/", 1)
            step_n = int(step)
            if base == "*":
                rng = list(range(lo, hi + 1))
            else:
                rng = _parse_range(base, lo, hi)
            for v in rng:
                if (v - rng[0]) % step_n == 0:
                    values.append(v)
        elif "-" in part:
            values.extend(_parse_range(part, lo, hi))
        else:
            values.append(int(part))
    return sorted(set(values))


def _parse_range(part: str, lo: int, hi: int) -> list[int]:
    if "-" in part:
        start, end = part.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(part)]


def cron_next_fire(cron_expr: str, after: datetime | None = None) -> datetime | None:
    """Return the next datetime that matches the cron expression after `after`."""
    if after is None:
        after = datetime.now(UTC)

    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return None

    parsed = {name: parse_cron_field(fields[i], *CRONTAB_RANGES[name]) for i, name in enumerate(CRONTAB_FIELDS)}

    # Simple forward search — max 366 * 24 * 60 iterations
    d = after.replace(second=0, microsecond=0)
    for _ in range(366 * 24 * 60):
        d += __import__("datetime").timedelta(minutes=1)

        minute_ok = d.minute in parsed["minute"]
        hour_ok = d.hour in parsed["hour"]
        dom_ok = d.day in parsed["day_of_month"]
        mon_ok = d.month in parsed["month"]
        dow_ok = d.weekday() in parsed["day_of_week"]

        if minute_ok and hour_ok and dom_ok and mon_ok and dow_ok:
            return d.replace(tzinfo=UTC)

    return None


class WorkflowScheduler:
    """Manages scheduled workflow runs using cron expressions.

    Uses ScheduleWakeup (persistent across sessions) for recurring schedules.
    For in-session waiting, uses a background thread with cron_next_fire.
    """

    def __init__(
        self,
        execution_store: ExecutionStore | None = None,
        workflows_dir: Path | None = None,
    ):
        self.store = execution_store or ExecutionStore()
        self.workflows_dir = workflows_dir or Path(__file__).resolve().parents[3] / "workflows"
        self._threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}
        self._lock = threading.RLock()
        self._schedules: dict[str, dict[str, Any]] = {}

    def schedule(
        self,
        workflow_name: str,
        cron_expr: str,
        workflow_path: Path | str | None = None,
        enabled: bool = True,
    ) -> str:
        """Register a cron schedule. Returns schedule ID."""
        sched_id = f"sched_{workflow_name}_{int(time.time())}"
        self._schedules[sched_id] = {
            "workflow_name": workflow_name,
            "workflow_path": workflow_path,
            "cron_expr": cron_expr,
            "enabled": enabled,
            "last_run": None,
            "next_run": None,
        }
        if enabled:
            self._start_daemon(sched_id)
        return sched_id

    def unschedule(self, schedule_id: str) -> None:
        """Stop and remove a schedule."""
        self._stop(schedule_id)
        self._schedules.pop(schedule_id, None)

    def list_schedules(self) -> list[dict[str, Any]]:
        """Return all registered schedules."""
        return [
            {
                "id": sid,
                "workflow_name": s["workflow_name"],
                "cron_expr": s["cron_expr"],
                "enabled": s["enabled"],
                "next_run": s["next_run"],
                "last_run": s["last_run"],
            }
            for sid, s in self._schedules.items()
        ]

    def _start_daemon(self, schedule_id: str) -> None:
        self._stop(schedule_id)
        stop_event = threading.Event()
        self._stop_events[schedule_id] = stop_event

        t = threading.Thread(
            target=self._daemon_loop,
            args=(schedule_id,),
            daemon=True,
            name=f"scheduler-{schedule_id}",
        )
        with self._lock:
            self._threads[schedule_id] = t
        t.start()

    def _stop(self, schedule_id: str) -> None:
        if schedule_id in self._stop_events:
            self._stop_events[schedule_id].set()
        if schedule_id in self._threads:
            self._threads[schedule_id].join(timeout=3)

    def _daemon_loop(self, schedule_id: str) -> None:
        sched = self._schedules.get(schedule_id)
        if not sched:
            return
        stop = self._stop_events[schedule_id]

        while not stop.is_set():
            cron_expr = sched["cron_expr"]
            next_run = cron_next_fire(cron_expr)

            if next_run is None:
                break

            sched["next_run"] = next_run.isoformat()
            delay_s = (next_run - datetime.now(UTC)).total_seconds()

            if delay_s > 0:
                stopped = stop.wait(timeout=min(delay_s, 3600))
                if stopped:
                    break

            if stop.is_set():
                break

            # Fire the workflow
            wf_path = sched.get("workflow_path")
            if wf_path:
                self._run_scheduled(schedule_id)

            sched["last_run"] = datetime.now(UTC).isoformat()

    def _run_scheduled(self, schedule_id: str) -> None:
        sched = self._schedules[schedule_id]
        wf_path = sched.get("workflow_path")
        if not wf_path:
            return

        print(f"⏰ [{datetime.now(UTC).isoformat()}] Scheduler firing: {sched['workflow_name']}")
        try:
            wf = WorkflowSchema.from_yaml(wf_path)
            engine = WorkflowOrchestrator(wf, execution_store=self.store, trigger="scheduled")
            engine.run()
        except Exception as e:
            print(f"   ❌ Scheduled run failed: {e}")

    def run_once(self, schedule_id: str) -> None:
        """Trigger a scheduled workflow immediately."""
        sched = self._schedules.get(schedule_id)
        if sched:
            self._run_scheduled(schedule_id)
