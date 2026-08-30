"""Multi-fork task aggregator for tuiboard.

Reads from CliAdapter + TaskdogAdapter + SolverforgeCalendarAdapter. Per spec:
- tuiboard is a RENDERING fork (no own storage adapter)
- Aggregator deduplicates by ueid across forks
- A3 version: basic single-fork read. A4 extends to all 3 forks with
  precedence logic (taskdog > solverforge-calendar > cli).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class AggregatedTask:
    ueid: str
    title: str
    status: str | None
    source: Literal["cli", "taskdog", "solverforge-calendar"]
    due: str | None = None
    vector: str | None = None
    tags: tuple[str, ...] = ()


class TaskAggregator:
    """Reads tasks from cross-fork storage adapters and deduplicates by ueid."""

    def __init__(self, *, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    def aggregate(self) -> list[AggregatedTask]:
        """Aggregate across 3 forks with precedence taskdog > solverforge-calendar > cli.

        Implementation: update dict in REVERSE precedence order (lowest first,
        highest last). dict.update() overwrites prior entries with the same ueid,
        so the last source to write wins. Result: a ueid present in taskdog
        uses taskdog's slice; one present only in cli uses cli's slice.
        """
        tasks: dict[str, AggregatedTask] = {}
        tasks.update(self._read_cli())            # lowest precedence (write first)
        tasks.update(self._read_solverforge())    # overwrites cli on collision
        tasks.update(self._read_taskdog())        # highest precedence (overwrites all)
        return list(tasks.values())

    def _read_cli(self) -> dict[str, AggregatedTask]:
        """Read from data/tasks.jsonl (canonical CLI adapter path)."""
        tasks_file = self._data_dir / "data" / "tasks.jsonl"
        if not tasks_file.exists():
            return {}
        result: dict[str, AggregatedTask] = {}
        for line in tasks_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            ueid = entry.get("ueid")
            if not ueid:
                continue
            result[ueid] = AggregatedTask(
                ueid=ueid,
                title=entry.get("title", ""),
                status=entry.get("status"),
                source="cli",
                due=entry.get("due"),
                vector=entry.get("vector"),
                tags=tuple(entry.get("tags", [])),
            )
        return result

    def _read_taskdog(self) -> dict[str, AggregatedTask]:
        """Read from TaskdogAdapter (SQLite, fixed project-relative path).

        Returns {} if DB missing (graceful degradation — aggregator still
        returns whatever the other forks provide).
        """
        try:
            from src.mesh.adapters.taskdog import TaskdogAdapter
        except ImportError:
            return {}
        adapter = TaskdogAdapter()
        result: dict[str, AggregatedTask] = {}
        for row in adapter.list_all():
            ueid = row.get("ueid")
            if not ueid:
                continue
            # taskdog's `name` → title; `deadline` → due (drop time portion if present)
            deadline = row.get("deadline") or ""
            due = deadline.split("T")[0] if deadline else None
            result[ueid] = AggregatedTask(
                ueid=ueid,
                title=row.get("name") or "",
                status=row.get("status"),
                source="taskdog",
                due=due,
                vector=None,
                tags=(),
            )
        return result

    def _read_solverforge(self) -> dict[str, AggregatedTask]:
        """Read from SolverforgeCalendarAdapter (SQLite, fixed project-relative path).

        Returns {} if DB missing or import fails (graceful degradation).
        The adapter stores title in `ikigai` JSON blob (per apply_change contract).
        """
        try:
            from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter
        except ImportError:
            return {}
        adapter = SolverforgeCalendarAdapter()
        result: dict[str, AggregatedTask] = {}
        for row in adapter.list_all():
            ueid = row.get("ueid")
            if not ueid:
                continue
            # Title lives inside the ikigai JSON blob; tags is its own JSON field.
            ikigai = row.get("ikigai") or {}
            tags = row.get("tags") or []
            # start_at → due (drop time portion if present)
            start_at = row.get("start_at") or ""
            due = start_at.split("T")[0] if start_at else None
            result[ueid] = AggregatedTask(
                ueid=ueid,
                title=ikigai.get("title") or "",
                status=row.get("status"),
                source="solverforge-calendar",
                due=due,
                vector=None,
                tags=tuple(tags),
            )
        return result
