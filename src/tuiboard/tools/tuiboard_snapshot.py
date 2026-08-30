"""tuiboard_snapshot — save a snapshot (minimal stub for E2E).

Per A2.6 deviation: minimal stub that accepts {name, layout} args and
calls SnapshotStore.save() with empty tasks list. Full handler ships in A3.
"""
from __future__ import annotations

import os
from pathlib import Path

from tuiboard.models import TuiboardSnapshotInput
from tuiboard.snapshots import SnapshotStore


def _store() -> SnapshotStore:
    sd = Path(os.environ.get("TUIBOARD_SNAPSHOTS_DIR", "data/tuiboard/snapshots"))
    return SnapshotStore(sd)


def handle(args: dict) -> dict:
    # Minimal validation - just accept name and layout
    inp = TuiboardSnapshotInput.model_validate(args)
    store = _store()
    # Extract layout as filters dict for the store
    filters = {"layout": inp.layout} if inp.layout else {}
    result = store.save(
        name=inp.name,
        tasks=[],  # Empty tasks list for stub
        filters=filters,
        description=inp.description,
    )
    return result
