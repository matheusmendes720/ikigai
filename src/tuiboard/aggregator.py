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
        tasks: dict[str, AggregatedTask] = {}
        tasks.update(self._read_cli())
        # A4: add taskdog + solverforge-calendar readers here
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
