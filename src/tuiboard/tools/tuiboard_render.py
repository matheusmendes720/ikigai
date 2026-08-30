"""tuiboard_render — produce positioned frames for a chosen layout."""

from __future__ import annotations

import os
from pathlib import Path

from tuiboard.aggregator import TaskAggregator, AggregatedTask
from tuiboard.models import (
    TuiboardRenderInput,
    TuiboardRenderOutput,
    TuiboardFrame,
    TuiboardPosition,
    TuiboardMetadata,
    _Filters,
)

# Layout dispatch (deviation #3): dispatch dict beats chained if/elif
_BUILDERS = {}


def _data_dir() -> Path:
    return Path(os.environ.get("TUIBOARD_DATA_DIR", "data"))


def _apply_filters(
    tasks: list[AggregatedTask], filters: _Filters | None
) -> list[AggregatedTask]:
    # Filter pipeline order (deviation #2): status -> vector -> tags -> due_before
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


def _build_kanban(tasks: list[AggregatedTask], max_width: int) -> list[TuiboardFrame]:
    by_section: dict[str, list[AggregatedTask]] = {}
    for t in tasks:
        sec = t.status or "planned"
        by_section.setdefault(sec, []).append(t)
    frames: list[TuiboardFrame] = []
    for section in sorted(by_section):
        items = sorted(by_section[section], key=lambda x: x.due or "")
        for row, t in enumerate(items):
            title = (
                t.title if len(t.title) <= max_width else t.title[: max_width - 1] + "…"
            )
            frames.append(
                TuiboardFrame(
                    ueid=t.ueid,
                    title=title,
                    status=t.status,
                    due=t.due,
                    vector=t.vector,
                    tags=list(t.tags),
                    position=TuiboardPosition(section=section, row=row, col=0),
                    child_ueids=[],
                )
            )
    return frames


def _build_list(tasks: list[AggregatedTask], max_width: int) -> list[TuiboardFrame]:
    items = sorted(tasks, key=lambda x: x.due or "")
    frames: list[TuiboardFrame] = []
    for row, t in enumerate(items):
        title = t.title if len(t.title) <= max_width else t.title[: max_width - 1] + "…"
        frames.append(
            TuiboardFrame(
                ueid=t.ueid,
                title=title,
                status=t.status,
                due=t.due,
                vector=t.vector,
                tags=list(t.tags),
                position=TuiboardPosition(section="list", row=row, col=0),
                child_ueids=[],
            )
        )
    return frames


def _build_calendar(tasks: list[AggregatedTask], max_width: int) -> list[TuiboardFrame]:
    by_section: dict[str, list[AggregatedTask]] = {}
    for t in tasks:
        sec = t.due.split("T")[0] if t.due else "no-due"
        by_section.setdefault(sec, []).append(t)
    frames: list[TuiboardFrame] = []
    for section in sorted(by_section):
        items = sorted(by_section[section], key=lambda x: x.due or "")
        for row, t in enumerate(items):
            title = (
                t.title if len(t.title) <= max_width else t.title[: max_width - 1] + "…"
            )
            frames.append(
                TuiboardFrame(
                    ueid=t.ueid,
                    title=title,
                    status=t.status,
                    due=t.due,
                    vector=t.vector,
                    tags=list(t.tags),
                    position=TuiboardPosition(section=section, row=row, col=0),
                    child_ueids=[],
                )
            )
    return frames


def _build_tree(tasks: list[AggregatedTask], max_width: int) -> list[TuiboardFrame]:
    by_section: dict[str, list[AggregatedTask]] = {}
    for t in tasks:
        sec = t.vector or "untagged"
        by_section.setdefault(sec, []).append(t)
    frames: list[TuiboardFrame] = []
    for section in sorted(by_section):
        items = sorted(by_section[section], key=lambda x: (x.status or "", x.due or ""))
        for row, t in enumerate(items):
            title = (
                t.title if len(t.title) <= max_width else t.title[: max_width - 1] + "…"
            )
            frames.append(
                TuiboardFrame(
                    ueid=t.ueid,
                    title=title,
                    status=t.status,
                    due=t.due,
                    vector=t.vector,
                    tags=list(t.tags),
                    position=TuiboardPosition(section=section, row=row, col=0),
                    child_ueids=[],
                )
            )
    return frames


_BUILDERS["kanban"] = _build_kanban
_BUILDERS["list"] = _build_list
_BUILDERS["calendar"] = _build_calendar
_BUILDERS["tree"] = _build_tree


def handle(args: dict) -> dict:
    inp = TuiboardRenderInput.model_validate(args)
    aggregator = TaskAggregator(data_dir=_data_dir())
    all_tasks = aggregator.aggregate()
    total = len(all_tasks)
    filtered = _apply_filters(all_tasks, inp.filters)
    if inp.ueids:
        ueid_set = set(inp.ueids)
        filtered = [t for t in filtered if t.ueid in ueid_set]
    max_width = inp.render_options.max_width if inp.render_options else 120
    frames = _BUILDERS[inp.layout](filtered, max_width)
    output = TuiboardRenderOutput(
        layout=inp.layout,
        frames=frames,
        metadata=TuiboardMetadata(
            total_tasks=total,
            shown_tasks=len(frames),
            truncated=total > len(frames),
        ),
    )
    return output.model_dump(mode="json")
