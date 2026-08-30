"""tuiboard_snapshot — save a snapshot of current fork tasks (filtered)."""

from __future__ import annotations

import os
from pathlib import Path

from tuiboard.aggregator import TaskAggregator, AggregatedTask
from tuiboard.models import TuiboardSnapshotInput, TuiboardSnapshotOutput
from tuiboard.snapshots import SnapshotStore

# Filter pipeline order (deviation #2): status -> vector -> tags -> due_before


def _store() -> SnapshotStore:
    sd = Path(os.environ.get("TUIBOARD_SNAPSHOTS_DIR", "data/tuiboard/snapshots"))
    return SnapshotStore(sd)


def _data_dir() -> Path:
    return Path(os.environ.get("TUIBOARD_DATA_DIR", "data"))


def _apply_filters(tasks: list[AggregatedTask], filters) -> list[AggregatedTask]:
    if filters is None:
        return tasks
    result = tasks
    if filters.status is not None:
        result = [t for t in result if t.status == filters.status]
    if filters.vector is not None:
        result = [t for t in result if t.vector == filters.vector]
    if filters.tags:
        result = [t for t in result if all(tag in t.tags for tag in filters.tags)]
    if filters.due_before is not None:
        result = [t for t in result if t.due is not None and t.due < filters.due_before]
    return result


def _to_dict(t: AggregatedTask) -> dict:
    return {
        "ueid": t.ueid,
        "title": t.title,
        "status": t.status,
        "due": t.due,
        "vector": t.vector,
        "tags": list(t.tags),
    }


def handle(args: dict) -> dict:
    inp = TuiboardSnapshotInput.model_validate(args)
    store = _store()
    aggregator = TaskAggregator(data_dir=_data_dir())
    all_tasks = aggregator.aggregate()
    filtered = _apply_filters(all_tasks, inp.filters)
    task_dicts = [_to_dict(t) for t in filtered]
    saved = store.save(
        name=inp.name,
        tasks=task_dicts,
        filters=inp.filters.model_dump() if inp.filters else None,
        description=inp.description,
    )
    output = TuiboardSnapshotOutput(**saved)
    return output.model_dump(mode="json")
