#!/usr/bin/env python
"""MVP Marco smoke — proves the sync cycle works end-to-end with existing code.

Goal: run `cli add → queue → worker → all adapters → read-back` once,
under full data isolation (tmp_path; production data/ untouched).

If this passes, the "Marco demo" base is verified. We can then add thin CLI
wrappers (`life plan add/list`) without re-speccing the data flow.

Sequence:
  1. Generate UEID + TaskChange event
  2. CliAdapter writes its own slice (mirrors do_task_add)
  3. Enqueue TaskChange to data/review_queue/
  4. Worker drains via run_once([3 adapters])
  5. Read back from each adapter; assert same UEID + title
  6. Idempotency: 2nd run_once consumes 0
  7. Queue ack status verified
  8. Print summary; exit 0/1

Constraints honored (per user 2026-08-29):
  - Zero policy engine / QHE / scoring imports
  - Pure filesystem + SQLite; no LLM
  - Production data/ directory NOT touched
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import uuid as uuid_lib
from datetime import datetime, timezone
from pathlib import Path

# Resolve repo root so we can import src.* without PYTHONPATH gymnastics
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))  # noqa: E402

from src.contracts.common import UEID  # noqa: E402
from src.contracts.task_change import PropagationEvent, TaskAction, TaskChange  # noqa: E402
from src.mesh.adapters import cli as cli_mod  # noqa: E402
from src.mesh.adapters import solverforge_calendar as solforge_mod  # noqa: E402
from src.mesh.adapters import taskdog as taskdog_mod  # noqa: E402
from src.mesh.adapters.cli import CliAdapter  # noqa: E402
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter  # noqa: E402
from src.mesh.adapters.taskdog import TaskdogAdapter  # noqa: E402
from src.mesh import queue as queue_mod  # noqa: E402
from src.mesh.review_queue_worker import run_once  # noqa: E402


def _setup_isolated_paths(tmp: Path) -> None:
    """Redirect all module-level adapter paths to the tmp dir.

    Same pattern as the test_review_queue_worker_e2e fixture.
    This prevents writes to the production data/ tree.
    """
    cli_mod.TASKS_JSONL = tmp / "tasks.jsonl"
    taskdog_mod.TASKDOG_DB = tmp / "tasks.db"
    solforge_mod.UPI_DB = tmp / "unified_planning.db"
    queue_mod.QUEUE_DIR = tmp / "review_queue"
    (tmp / "review_queue").mkdir(parents=True, exist_ok=True)


def main() -> int:
    """Run the MVP Marco smoke. Returns 0 on pass, 1 on fail."""
    failures: list[str] = []
    summary: list[str] = []

    # --- Step 0: isolated tmp dir, redirected module paths ---
    tmp = Path(tempfile.mkdtemp(prefix="mvp_marco_smoke_"))
    print(f"[setup] isolated tmp dir: {tmp}", flush=True)

    try:
        _setup_isolated_paths(tmp)

        # --- Step 1: build UEID + TaskChange event ---
        title = "MVP Marco smoke test"
        due = "2026-12-31"
        slug = "mvp-marco-smoke-test"
        ueid_str = f"tsk:{slug}:{uuid_lib.uuid4().hex[:8]}:{uuid_lib.uuid4().hex[:8]}"
        ueid = UEID(ueid_str)
        event = TaskChange(
            event_id=f"evt_{uuid_lib.uuid4().hex[:12]}",
            ueid=ueid,
            action=TaskAction.CREATE,
            fields={"title": title, "due": due, "priority": "medium"},
            source_fork="mvp_smoke",
            timestamp=datetime.now(timezone.utc),
        )
        summary.append(f"[1] ueid={ueid}  event_id={event.event_id}")

        # --- Step 2: CliAdapter writes its own slice ---
        cli = CliAdapter()
        cli.apply_change(PropagationEvent(
            event_id=event.event_id,
            ueid=event.ueid,
            action=event.action,
            fields=event.fields,
            approved_at=event.timestamp,
            source_fork=event.source_fork,
        ))
        cli_path = cli_mod.TASKS_JSONL
        if not cli_path.exists():
            failures.append("CliAdapter did not write tasks.jsonl")
        else:
            lines = cli_path.read_text().splitlines()
            if len(lines) != 1:
                failures.append(f"CliAdapter wrote {len(lines)} lines, expected 1")
            else:
                rec = json.loads(lines[0])
                if rec.get("ueid") != str(ueid):
                    failures.append(f"Cli record ueid mismatch: {rec.get('ueid')}")
                else:
                    summary.append("[2] CliAdapter wrote 1 record to tasks.jsonl ✓")

        # --- Step 3: enqueue event ---
        queue_mod.enqueue(event)
        queue_files = list(queue_mod.QUEUE_DIR.glob("*.json"))
        if len(queue_files) != 1:
            failures.append(f"Expected 1 queue file, got {len(queue_files)}")
        else:
            summary.append("[3] Enqueued 1 event to review_queue/ ✓")

        # --- Step 4: worker drains via run_once with 3 adapters ---
        adapters = [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]
        wr = run_once(adapters)
        summary.append(
            f"[4] Worker drain: consumed={wr.consumed} "
            f"approved={wr.approved} partial={wr.partial}"
        )
        if wr.consumed != 1:
            failures.append(f"Expected consumed=1, got {wr.consumed}")
        if wr.approved != 1:
            failures.append(f"Expected approved=1, got {wr.approved}")
        if wr.partial != 0:
            failures.append(
                f"Expected partial=0 (all 3 should succeed), got {wr.partial}"
            )

        # --- Step 5: cross-fork read-back, assert consistency ---
        # Each adapter stores title under a different key (cli='title',
        # taskdog='name', solverforge='ikigai' JSON blob). We assert:
        #   - record exists
        #   - ueid matches
        #   - title value appears SOMEWHERE in the record (proves persisted)
        # The exact key is per-adapter and is a v1 schema choice, not a bug.
        for name, adapter in zip(["cli", "taskdog", "solverforge_calendar"], adapters):
            try:
                record = adapter.read(ueid)
            except Exception as e:
                failures.append(f"{name} adapter read raised: {e}")
                continue
            if record is None:
                failures.append(f"{name} adapter returned None")
                continue
            if record.get("ueid") != str(ueid):
                failures.append(f"{name} ueid mismatch: {record.get('ueid')}")
            elif title not in json.dumps(record, default=str):
                failures.append(f"{name} title value not present anywhere in record")
            else:
                summary.append(f"[5] {name}: ueid ✓ title persisted ✓")

        # --- Step 6: idempotency ---
        wr2 = run_once(adapters)
        if wr2.consumed != 0:
            failures.append(
                f"Idempotency: expected consumed=0 on 2nd run, got {wr2.consumed}"
            )
        else:
            summary.append("[6] Idempotent: 2nd run_once consumed=0 ✓")

        # --- Step 7: queue ack status verified ---
        ack_files = list(queue_mod.QUEUE_DIR.glob(f"{event.event_id}.json"))
        if not ack_files:
            failures.append("Queue file missing after worker drain")
        else:
            ack_status = json.loads(ack_files[0].read_text()).get("status")
            summary.append(f"[7] Queue ack status: {ack_status}")
            if ack_status not in ("propagated", "partial_propagation"):
                failures.append(f"Unexpected ack status: {ack_status}")

        # --- Final summary ---
        print("\n--- MVP MARCO SMOKE SUMMARY ---", flush=True)
        for line in summary:
            print(line, flush=True)
        if failures:
            print("\n--- FAILURES ---", flush=True)
            for f in failures:
                print(f"  X {f}", flush=True)
            return 1
        print("\nALL CHECKS PASSED - Marco MVP cycle works end-to-end", flush=True)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
