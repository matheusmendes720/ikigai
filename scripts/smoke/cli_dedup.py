#!/usr/bin/env python
"""CliAdapter dedup smoke — proves the v1.2 fix.

Bug being fixed: CliAdapter.apply_change appended without dedup, so
do_task_add + worker.run_once wrote the same CREATE event twice.

This smoke asserts the new invariant directly:
  1. First apply_change with UEID-A → file has 1 line
  2. Second apply_change with same UEID-A → file still has 1 line (no-op)
  3. Third apply_change with UEID-B → file has 2 lines (different UEID)
  4. read() returns the record for both UEIDs

Isolated: uses tmp_path; does NOT touch production data/.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import uuid as uuid_lib
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))  # noqa: E402

from src.contracts.common import UEID  # noqa: E402
from src.contracts.task_change import PropagationEvent, TaskAction, TaskChange  # noqa: E402
from src.mesh.adapters import cli as cli_mod  # noqa: E402
from src.mesh.adapters.cli import CliAdapter  # noqa: E402


def _make_event(ueid: UEID, title: str, source: str = "test") -> TaskChange:
    return TaskChange(
        event_id=f"evt_{uuid_lib.uuid4().hex[:12]}",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": title, "due": "2026-12-31", "priority": "medium"},
        source_fork=source,
        timestamp=datetime.now(timezone.utc),
    )


def main() -> int:
    failures: list[str] = []
    summary: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="cli_dedup_smoke_"))
    print(f"[setup] isolated tmp dir: {tmp}", flush=True)

    try:
        # Redirect module-level path
        cli_mod.TASKS_JSONL = tmp / "tasks.jsonl"

        adapter = CliAdapter()

        # 1. First apply_change with UEID-A → expect 1 line
        ueid_a = UEID(f"tsk:dedup-a:{uuid_lib.uuid4().hex[:8]}:{uuid_lib.uuid4().hex[:8]}")
        event_a = _make_event(ueid_a, "Task A")
        adapter.apply_change(PropagationEvent(
            event_id=event_a.event_id,
            ueid=event_a.ueid,
            action=event_a.action,
            fields=event_a.fields,
            approved_at=event_a.timestamp,
            source_fork=event_a.source_fork,
        ))
        path = cli_mod.TASKS_JSONL
        lines = path.read_text().splitlines() if path.exists() else []
        if len(lines) != 1:
            failures.append(f"After 1st apply_change: expected 1 line, got {len(lines)}")
        else:
            summary.append("[1] After 1st apply_change: 1 line ✓")

        # 2. Second apply_change with SAME UEID-A → expect still 1 line
        adapter.apply_change(PropagationEvent(
            event_id=event_a.event_id,
            ueid=event_a.ueid,
            action=event_a.action,
            fields=event_a.fields,
            approved_at=event_a.timestamp,
            source_fork=event_a.source_fork,
        ))
        lines = path.read_text().splitlines()
        if len(lines) != 1:
            failures.append(
                f"After 2nd apply_change (same ueid): expected 1 line, got {len(lines)} — DEDUP BROKEN"
            )
        else:
            summary.append("[2] After 2nd apply_change (same ueid): still 1 line — dedup ✓")

        # 3. Third apply_change with DIFFERENT UEID-B → expect 2 lines
        ueid_b = UEID(f"tsk:dedup-b:{uuid_lib.uuid4().hex[:8]}:{uuid_lib.uuid4().hex[:8]}")
        event_b = _make_event(ueid_b, "Task B")
        adapter.apply_change(PropagationEvent(
            event_id=event_b.event_id,
            ueid=event_b.ueid,
            action=event_b.action,
            fields=event_b.fields,
            approved_at=event_b.timestamp,
            source_fork=event_b.source_fork,
        ))
        lines = path.read_text().splitlines()
        if len(lines) != 2:
            failures.append(
                f"After 3rd apply_change (new ueid): expected 2 lines, got {len(lines)}"
            )
        else:
            summary.append("[3] After 3rd apply_change (new ueid): 2 lines ✓")

        # 4. read() returns record for both UEIDs
        rec_a = adapter.read(ueid_a)
        rec_b = adapter.read(ueid_b)
        if rec_a is None or rec_a.get("title") != "Task A":
            failures.append(f"read(ueid_a) returned wrong: {rec_a}")
        else:
            summary.append("[4a] read(ueid_a) returned title='Task A' ✓")
        if rec_b is None or rec_b.get("title") != "Task B":
            failures.append(f"read(ueid_b) returned wrong: {rec_b}")
        else:
            summary.append("[4b] read(ueid_b) returned title='Task B' ✓")

        # 5. JSONL integrity: every line is valid JSON with a ueid
        for i, line in enumerate(lines):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                failures.append(f"Line {i} not valid JSON: {e}")
                continue
            if not rec.get("ueid"):
                failures.append(f"Line {i} missing ueid field")

        print("\n--- CLI DEDUP SMOKE SUMMARY ---", flush=True)
        for line in summary:
            print(line, flush=True)
        if failures:
            print("\n--- FAILURES ---", flush=True)
            for f in failures:
                print(f"  X {f}", flush=True)
            return 1
        print("\nALL CHECKS PASSED - CliAdapter dedup works", flush=True)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())