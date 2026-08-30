"""tuiboard_aggregate — read tasks from all 3 forks with precedence logic.

Wraps the A4.2 TaskAggregator (cli + solverforge-calendar + taskdog) and
exposes it via MCP. Returns aggregated view + per-source counts.
"""
from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from tuiboard.aggregator import AggregatedTask, TaskAggregator
from tuiboard.models import (
    TuiboardAggregateInput,
    TuiboardAggregateOutput,
    TuiboardAggregateTask,
)


def _data_dir() -> Path:
    return Path(os.environ.get("TUIBOARD_DATA_DIR", "data"))


def _to_dict(t: AggregatedTask) -> dict:
    return {
        "ueid": t.ueid,
        "title": t.title,
        "status": t.status,
        "source": t.source,
        "due": t.due,
        "vector": t.vector,
        "tags": list(t.tags),
    }


def handle(args: dict) -> dict:
    _ = TuiboardAggregateInput.model_validate(args)
    aggregator = TaskAggregator(data_dir=_data_dir())
    tasks = aggregator.aggregate()
    sources = Counter(t.source for t in tasks)
    output = TuiboardAggregateOutput(
        tasks=[TuiboardAggregateTask(**_to_dict(t)) for t in tasks],
        count=len(tasks),
        sources=dict(sources),
    )
    return output.model_dump(mode="json")
