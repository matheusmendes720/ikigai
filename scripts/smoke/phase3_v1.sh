#!/usr/bin/env bash
# Phase 3 v1 — 8-step happy path smoke test
#
# Verifies the canonical flow per docs/superpowers/specs/2026-08-28-phase3-data-mesh-design.md
#   (Section 5).  Runs in an isolated temp dir; the real data/ trees are NOT touched.
#
# Steps:
#   1. Generate a test UEID
#   2. Construct TaskChange (action=CREATE)
#   3. CLI adapter writes its own slice
#   4. CLI enqueues TaskChange to review queue
#   5. Agent consumes queue (consume_pending)
#   6. Agent validates -> Decision.APPROVE
#   7. Agent propagates to all 3 adapters
#   8. Verify all 3 forks have the task + ack queue

set -euo pipefail

# --- Resolve repo root from script location ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
# Convert to native path for Windows Python (Git Bash + MSYS need cygpath).
if command -v cygpath >/dev/null 2>&1; then
    PYTHONPATH_SRC="$(cygpath -w "$REPO/src")"
else
    PYTHONPATH_SRC="$REPO/src"
fi
export PYTHONPATH="$PYTHONPATH_SRC"

# Switch into repo root so Python's implicit cwd-on-sys-path picks up src/.
# (When python is invoked from a different dir with PYTHONPATH set alone,
# some namespace-package setups still fail to find src/.  cd is the
# belt-and-braces fix that matches the test suite's behavior.)
cd "$REPO"

# --- Isolated temp dir (cleaned on EXIT) ---
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Python inside the script needs a Windows-style path to the driver.  Git
# Bash auto-translates args, but the driver uses open(...) which doesn't.
if command -v cygpath >/dev/null 2>&1; then
    TMP_WIN="$(cygpath -w "$TMP")"
else
    TMP_WIN="$TMP"
fi

export SMOKE_TMP="$TMP_WIN"

echo "Phase 3 v1 smoke test"
echo "  repo:    $REPO"
echo "  tmp dir: $TMP"
echo

# --- Write Python driver to temp file ---
cat > "$TMP/phase3_v1.py" << 'PYEOF'
import sys, json, os, uuid, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path

# --- Redirect mesh module paths to isolated temp dir ---
tmp = Path(os.environ["SMOKE_TMP"])
# Pre-create parent dirs (SQLite needs them to exist before open()).
(tmp / "taskdog").mkdir(parents=True, exist_ok=True)
(tmp / "solverforge_calendar").mkdir(parents=True, exist_ok=True)
(tmp / "review_queue").mkdir(parents=True, exist_ok=True)

from src.mesh import queue
from src.mesh.adapters import cli, taskdog, solverforge_calendar
cli.TASKS_JSONL = tmp / "tasks.jsonl"
taskdog.TASKDOG_DB = tmp / "taskdog" / "tasks.db"
solverforge_calendar.UPI_DB = tmp / "solverforge_calendar" / "unified_planning.db"
queue.QUEUE_DIR = tmp / "review_queue"

# --- Bootstrap UPI schema (idempotent) ---
conn = sqlite3.connect(solverforge_calendar.UPI_DB)
conn.executescript("""
    CREATE TABLE IF NOT EXISTS unified_planning_items (
        id TEXT PRIMARY KEY,
        ueid TEXT UNIQUE,
        status TEXT,
        start_at TEXT,
        end_at TEXT,
        blocked_by TEXT,
        tags TEXT,
        ikigai TEXT,
        provenance TEXT
    );
""")
conn.commit()
conn.close()

# --- Imports (after path patching) ---
from src.contracts.task_change import TaskChange, TaskAction, PropagationEvent
from src.mesh.agent_consumer import validate, Decision
from src.mesh.agent_propagator import propagate
from src.mesh.adapters.cli import CliAdapter
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

# ============================================================
# STEP 1: Generate a test UEID
# ============================================================
print("STEP 1: Generate a test UEID (e.g. tsk:smoke-<timestamp>:<uuid>:<hex>)")
timestamp = int(time.time())
test_uuid = str(uuid.uuid4())
test_hex = uuid.uuid4().hex[:16]
ueid = f"tsk:smoke-{timestamp}:{test_uuid}:{test_hex}"
print(f"  ueid={ueid}")

# ============================================================
# STEP 2: Construct TaskChange
# ============================================================
print("STEP 2: Construct TaskChange (event_id, ueid, action=CREATE, "
      "fields={title, due, priority}, source_fork=interfaces/cli)")
event = TaskChange(
    event_id=f"evt_smoke_{timestamp}",
    ueid=ueid,
    action=TaskAction.CREATE,
    fields={"title": "Smoke test task", "due": "2099-12-31", "priority": "high"},
    source_fork="interfaces/cli",
    timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
)
print(f"  event_id={event.event_id}")
print(f"  action={event.action.value}")
print(f"  fields={event.fields}")
print(f"  source_fork={event.source_fork}")

# ============================================================
# STEP 3: CLI adapter writes its own slice to data/tasks.jsonl
# ============================================================
print("STEP 3: CLI adapter writes its own slice to data/tasks.jsonl")
cli_a = CliAdapter()
cli_a.apply_change(PropagationEvent(
    event_id=event.event_id,
    ueid=event.ueid,
    action=event.action,
    fields=event.fields,
    approved_at=event.timestamp,
    source_fork=event.source_fork,
))
assert cli.TASKS_JSONL.exists(), f"CLI slice missing: {cli.TASKS_JSONL}"
print(f"  slice written: {cli.TASKS_JSONL}")

# ============================================================
# STEP 4: CLI enqueues TaskChange to data/review_queue/<event_id>.json
# ============================================================
print("STEP 4: CLI enqueues TaskChange to data/review_queue/<event_id>.json")
queue.enqueue(event)
queued_files = sorted(queue.QUEUE_DIR.glob("*.json"))
assert len(queued_files) == 1, f"expected 1 queued file, got {len(queued_files)}"
print(f"  queued file: {queued_files[0].name}")

# ============================================================
# STEP 5: Agent consumes queue (consume_pending), returns the event
# ============================================================
print("STEP 5: Agent consumes queue (consume_pending), returns the event")
pending = list(queue.consume_pending())
assert len(pending) == 1, f"expected 1 pending event, got {len(pending)}"
assert pending[0].event_id == event.event_id
print(f"  consumed count={len(pending)}")
print(f"  event_id={pending[0].event_id}")

# ============================================================
# STEP 6: Agent validates (validate) -> Decision.APPROVE
# ============================================================
print("STEP 6: Agent validates (validate) -> Decision.APPROVE")
v = validate(pending[0])
print(f"  decision={v.decision.value}")
assert v.decision == Decision.APPROVE, f"validation failed: {v.reason}"

# ============================================================
# STEP 7: Agent propagates to all 3 adapters
# ============================================================
print("STEP 7: Agent propagates (propagate) to all 3 adapters: "
      "CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter")
adapters = [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]
results = propagate(pending[0], v, adapters)
for r in results:
    print(f"  {r.fork_name}: success={r.success}")
    if not r.success:
        print(f"    error: {r.error}")
assert len(results) == 3, f"expected 3 results, got {len(results)}"
assert all(r.success for r in results), "some adapters failed"

# ============================================================
# STEP 8: Verify all 3 forks have the task
# ============================================================
print("STEP 8: Verify all 3 forks have the task")

# CLI: tasks.jsonl contains a JSON line with ueid
print("  CLI: tasks.jsonl contains a JSON line with ueid")
cli_lines = cli.TASKS_JSONL.read_text().strip().split("\n")
cli_tasks = [json.loads(line) for line in cli_lines if line.strip()]
cli_count = sum(1 for t in cli_tasks if t["ueid"] == ueid)
print(f"    count={cli_count}")
assert cli_count >= 1, f"CLI count={cli_count}"

# taskdog: SQLite tasks table has COUNT=1 for the ueid
print("  taskdog: SQLite tasks table has COUNT=1 for the ueid")
conn = sqlite3.connect(taskdog.TASKDOG_DB)
td_count = conn.execute(
    "SELECT COUNT(*) FROM tasks WHERE ueid=?", (ueid,)
).fetchone()[0]
conn.close()
print(f"    count={td_count}")
assert td_count == 1, f"taskdog count={td_count}"

# UPI: SQLite unified_planning_items table has COUNT=1 for the ueid
print("  UPI: SQLite unified_planning_items table has COUNT=1 for the ueid")
conn = sqlite3.connect(solverforge_calendar.UPI_DB)
upi_count = conn.execute(
    "SELECT COUNT(*) FROM unified_planning_items WHERE ueid=?", (ueid,)
).fetchone()[0]
conn.close()
print(f"    count={upi_count}")
assert upi_count == 1, f"UPI count={upi_count}"

# Then: queue.ack(event_id, propagated); consume_pending returns empty
print("  Then: queue.ack(event_id, propagated); consume_pending returns empty")
queue.ack(event.event_id, "propagated")
remaining = list(queue.consume_pending())
print(f"    remaining={len(remaining)}")
assert len(remaining) == 0, f"queue not drained, {len(remaining)} pending"

print()
print("SMOKE TEST PASSED")
PYEOF

# --- Run the driver ---
# Use `python -c "exec(open(...))"` rather than `python <script>` so that
# sys.path[0] is the cwd (the repo, where src/ lives) rather than the
# temp dir.  Without this, Windows Python refuses to resolve the `src`
# namespace package even with PYTHONPATH set.
python -c "exec(open(r'${TMP_WIN}\\phase3_v1.py').read())"