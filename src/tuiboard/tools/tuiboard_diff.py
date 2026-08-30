"""tuiboard_diff — compare two snapshots field-by-field.

Read-only. Returns no diff if either snapshot is missing (raises typed error).
"""
from __future__ import annotations

import os
from pathlib import Path

from tuiboard.models import (
    TuiboardChange, TuiboardDiffInput, TuiboardDiffOutput, TuiboardTaskEntry,
)
from tuiboard.snapshots import SnapshotStore


def _store() -> SnapshotStore:
    sd = Path(os.environ.get("TUIBOARD_SNAPSHOTS_DIR", "data/tuiboard/snapshots"))
    return SnapshotStore(sd)


def handle(args: dict) -> dict:
    inp = TuiboardDiffInput.model_validate(args)
    store = _store()
    src = store.load(inp.from_snapshot_id)  # raises FileNotFoundError → upstream JSON-RPC error
    dst = store.load(inp.to_snapshot_id)

    src_by_ueid = {t["ueid"]: t for t in src.get("tasks", [])}
    dst_by_ueid = {t["ueid"]: t for t in dst.get("tasks", [])}
    src_ids = set(src_by_ueid)
    dst_ids = set(dst_by_ueid)

    added = [TuiboardTaskEntry(**t) for ueid in (dst_ids - src_ids)
             for t in [dst_by_ueid[ueid]]]
    removed = [TuiboardTaskEntry(**t) for ueid in (src_ids - dst_ids)
               for t in [src_by_ueid[ueid]]]
    changed: list[TuiboardChange] = []
    unchanged = 0
    for ueid in src_ids & dst_ids:
        s, d = src_by_ueid[ueid], dst_by_ueid[ueid]
        diffs = _field_diff(s, d)
        if diffs:
            changed.extend(diffs)
        elif inp.include_unchanged:
            unchanged += 1
        else:
            unchanged += 1  # count regardless

    output = TuiboardDiffOutput(
        from_snapshot_id=inp.from_snapshot_id,
        to_snapshot_id=inp.to_snapshot_id,
        added=added, removed=removed, changed=changed,
        unchanged_count=unchanged,
    )
    return output.model_dump(mode="json")


def _field_diff(src: dict, dst: dict) -> list[TuiboardChange]:
    diffs = []
    all_keys = set(src.keys()) | set(dst.keys())
    for k in all_keys:
        if k == "ueid":
            continue
        s_val, d_val = src.get(k), dst.get(k)
        if s_val != d_val:
            diffs.append(TuiboardChange(ueid=src["ueid"], field=k,
                                         before=s_val, after=d_val))
    return diffs
