@echo off
REM Phase 3 v1 - 8-step happy path smoke test
REM
REM Verifies the canonical flow per
REM   docs/superpowers/specs/2026-08-28-phase3-data-mesh-design.md (Section 5).
REM Runs in an isolated temp dir; the real data/ trees are NOT touched.
REM
REM Steps:
REM   1. Generate a test UEID
REM   2. Construct TaskChange (action=CREATE)
REM   3. CLI adapter writes its own slice
REM   4. CLI enqueues TaskChange to review queue
REM   5. Agent consumes queue (consume_pending)
REM   6. Agent validates -> Decision.APPROVE
REM   7. Agent propagates to all 3 adapters
REM   8. Verify all 3 forks have the task + ack queue

setlocal enabledelayedexpansion

REM --- Resolve repo root from script location ---
set "SCRIPT_DIR=%~dp0"
set "REPO=%SCRIPT_DIR%..\.."
set "PYTHONPATH=%REPO%\src"

REM --- Isolated temp dir (cleaned at end) ---
set "TMP_DIR=%TEMP%\phase3_v1_%RANDOM%"
mkdir "%TMP_DIR%" 2>nul
if errorlevel 1 (
    echo ERROR: failed to create temp dir: %TMP_DIR%
    exit /b 1
)

set "SMOKE_TMP=%TMP_DIR%"

echo Phase 3 v1 smoke test
echo   repo:    %REPO%
echo   tmp dir: %TMP_DIR%
echo.

REM --- Write Python driver to temp file via echo block ---
REM Parens need ^( and ^), redirectors ^< and ^>, etc.  No $, no ' in the
REM Python code below (the surrounding cmd string is double-quoted so ""
REM is harmless here).
> "%TMP_DIR%\phase3_v1.py" (
    echo import sys, json, os, uuid, sqlite3, time
    echo from datetime import datetime, timezone
    echo from pathlib import Path
    echo.
    echo # --- Redirect mesh module paths to isolated temp dir ---
    echo tmp = Path^(os.environ["SMOKE_TMP"]^)
    echo # Pre-create parent dirs ^(SQLite needs them to exist before open^(^)^).
    echo ^(tmp / "taskdog"^).mkdir^(parents=True, exist_ok=True^)
    echo ^(tmp / "solverforge_calendar"^).mkdir^(parents=True, exist_ok=True^)
    echo ^(tmp / "review_queue"^).mkdir^(parents=True, exist_ok=True^)
    echo.
    echo from src.mesh import queue
    echo from src.mesh.adapters import cli, taskdog, solverforge_calendar
    echo cli.TASKS_JSONL = tmp / "tasks.jsonl"
    echo taskdog.TASKDOG_DB = tmp / "taskdog" / "tasks.db"
    echo solverforge_calendar.UPI_DB = tmp / "solverforge_calendar" / "unified_planning.db"
    echo queue.QUEUE_DIR = tmp / "review_queue"
    echo.
    echo # --- Bootstrap UPI schema ^(idempotent^) ---
    echo conn = sqlite3.connect^(solverforge_calendar.UPI_DB^)
    echo conn.executescript^("""
    echo     CREATE TABLE IF NOT EXISTS unified_planning_items ^(
    echo         id TEXT PRIMARY KEY,
    echo         ueid TEXT UNIQUE,
    echo         status TEXT,
    echo         start_at TEXT,
    echo         end_at TEXT,
    echo         blocked_by TEXT,
    echo         tags TEXT,
    echo         ikigai TEXT,
    echo         provenance TEXT
    echo     ^);
    echo """^)
    echo conn.commit^(^)
    echo conn.close^(^)
    echo.
    echo # --- Imports ^(after path patching^) ---
    echo from src.contracts.task_change import TaskChange, TaskAction, PropagationEvent
    echo from src.mesh.agent_consumer import validate, Decision
    echo from src.mesh.agent_propagator import propagate
    echo from src.mesh.adapters.cli import CliAdapter
    echo from src.mesh.adapters.taskdog import TaskdogAdapter
    echo from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter
    echo.
    echo # ============================================================
    echo # STEP 1: Generate a test UEID
    echo # ============================================================
    echo print^("STEP 1: Generate a test UEID ^(e.g. tsk:smoke-^<timestamp^>:^<uuid^>:^<hex^>^)"^)
    echo timestamp = int^(time.time^(^)^)
    echo test_uuid = str^(uuid.uuid4^(^)^)
    echo test_hex = uuid.uuid4^(^).hex[:16]
    echo ueid = f"tsk:smoke-{timestamp}:{test_uuid}:{test_hex}"
    echo print^(f"  ueid={ueid}"^)
    echo.
    echo # ============================================================
    echo # STEP 2: Construct TaskChange
    echo # ============================================================
    echo print^("STEP 2: Construct TaskChange ^(event_id, ueid, action=CREATE, fields={title, due, priority}, source_fork=interfaces/cli^)"^)
    echo event = TaskChange^(
    echo     event_id=f"evt_smoke_{timestamp}",
    echo     ueid=ueid,
    echo     action=TaskAction.CREATE,
    echo     fields={"title": "Smoke test task", "due": "2099-12-31", "priority": "high"},
    echo     source_fork="interfaces/cli",
    echo     timestamp=datetime.now^(timezone.utc^).replace^(tzinfo=None^),
    echo ^)
    echo print^(f"  event_id={event.event_id}"^)
    echo print^(f"  action={event.action.value}"^)
    echo print^(f"  fields={event.fields}"^)
    echo print^(f"  source_fork={event.source_fork}"^)
    echo.
    echo # ============================================================
    echo # STEP 3: CLI adapter writes its own slice to data/tasks.jsonl
    echo # ============================================================
    echo print^("STEP 3: CLI adapter writes its own slice to data/tasks.jsonl"^)
    echo cli_a = CliAdapter^(^)
    echo cli_a.apply_change^(PropagationEvent^(
    echo     event_id=event.event_id,
    echo     ueid=event.ueid,
    echo     action=event.action,
    echo     fields=event.fields,
    echo     approved_at=event.timestamp,
    echo     source_fork=event.source_fork,
    echo ^)^)
    echo assert cli.TASKS_JSONL.exists^(^), f"CLI slice missing: {cli.TASKS_JSONL}"
    echo print^(f"  slice written: {cli.TASKS_JSONL}"^)
    echo.
    echo # ============================================================
    echo # STEP 4: CLI enqueues TaskChange to data/review_queue/^<event_id^>.json
    echo # ============================================================
    echo print^("STEP 4: CLI enqueues TaskChange to data/review_queue/^<event_id^>.json"^)
    echo queue.enqueue^(event^)
    echo queued_files = sorted^(queue.QUEUE_DIR.glob^("*.json"^)^)
    echo assert len^(queued_files^) == 1, f"expected 1 queued file, got {len^(queued_files^)}"
    echo print^(f"  queued file: {queued_files[0].name}"^)
    echo.
    echo # ============================================================
    echo # STEP 5: Agent consumes queue ^(consume_pending^), returns the event
    echo # ============================================================
    echo print^("STEP 5: Agent consumes queue ^(consume_pending^), returns the event"^)
    echo pending = list^(queue.consume_pending^(^)^)
    echo assert len^(pending^) == 1, f"expected 1 pending event, got {len^(pending^)}"
    echo assert pending[0].event_id == event.event_id
    echo print^(f"  consumed count={len^(pending^)}"^)
    echo print^(f"  event_id={pending[0].event_id}"^)
    echo.
    echo # ============================================================
    echo # STEP 6: Agent validates ^(validate^) -^> Decision.APPROVE
    echo # ============================================================
    echo print^("STEP 6: Agent validates ^(validate^) -^> Decision.APPROVE"^)
    echo v = validate^(pending[0]^)
    echo print^(f"  decision={v.decision.value}"^)
    echo assert v.decision == Decision.APPROVE, f"validation failed: {v.reason}"
    echo.
    echo # ============================================================
    echo # STEP 7: Agent propagates to all 3 adapters
    echo # ============================================================
    echo print^("STEP 7: Agent propagates ^(propagate^) to all 3 adapters: CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter"^)
    echo adapters = [CliAdapter^(^), TaskdogAdapter^(^), SolverforgeCalendarAdapter^(^)]
    echo results = propagate^(pending[0], v, adapters^)
    echo for r in results:
    echo     print^(f"  {r.fork_name}: success={r.success}"^)
    echo     if not r.success:
    echo         print^(f"    error: {r.error}"^)
    echo assert len^(results^) == 3, f"expected 3 results, got {len^(results^)}"
    echo assert all^(r.success for r in results^), "some adapters failed"
    echo.
    echo # ============================================================
    echo # STEP 8: Verify all 3 forks have the task
    echo # ============================================================
    echo print^("STEP 8: Verify all 3 forks have the task"^)
    echo.
    echo # CLI: tasks.jsonl contains a JSON line with ueid
    echo print^("  CLI: tasks.jsonl contains a JSON line with ueid"^)
    echo cli_lines = cli.TASKS_JSONL.read_text^(^).strip^(^).split^("^n"^)
    echo cli_tasks = [json.loads^(line^) for line in cli_lines if line.strip^(^)]
    echo cli_count = sum^(1 for t in cli_tasks if t["ueid"] == ueid^)
    echo print^(f"    count={cli_count}"^)
    echo assert cli_count ^>= 1, f"CLI count={cli_count}"
    echo.
    echo # taskdog: SQLite tasks table has COUNT=1 for the ueid
    echo print^("  taskdog: SQLite tasks table has COUNT=1 for the ueid"^)
    echo conn = sqlite3.connect^(taskdog.TASKDOG_DB^)
    echo td_count = conn.execute^(
    echo     "SELECT COUNT^(*) FROM tasks WHERE ueid=?", ^(ueid,^)
    echo ^).fetchone^(^)[0]
    echo conn.close^(^)
    echo print^(f"    count={td_count}"^)
    echo assert td_count == 1, f"taskdog count={td_count}"
    echo.
    echo # UPI: SQLite unified_planning_items table has COUNT=1 for the ueid
    echo print^("  UPI: SQLite unified_planning_items table has COUNT=1 for the ueid"^)
    echo conn = sqlite3.connect^(solverforge_calendar.UPI_DB^)
    echo upi_count = conn.execute^(
    echo     "SELECT COUNT^(*) FROM unified_planning_items WHERE ueid=?", ^(ueid,^)
    echo ^).fetchone^(^)[0]
    echo conn.close^(^)
    echo print^(f"    count={upi_count}"^)
    echo assert upi_count == 1, f"UPI count={upi_count}"
    echo.
    echo # Then: queue.ack^(event_id, propagated^); consume_pending returns empty
    echo print^("  Then: queue.ack^(event_id, propagated^); consume_pending returns empty"^)
    echo queue.ack^(event.event_id, "propagated"^)
    echo remaining = list^(queue.consume_pending^(^)^)
    echo print^(f"    remaining={len^(remaining^)}"^)
    echo assert len^(remaining^) == 0, f"queue not drained, {len^(remaining^)} pending"
    echo.
    echo print^(^)
    echo print^("SMOKE TEST PASSED"^)
)
if errorlevel 1 (
    echo ERROR: failed to write Python driver
    rmdir /s /q "%TMP_DIR%"
    exit /b 1
)

REM --- Run the driver ---
REM Use `python -c "exec(open(...))"` rather than `python ^<script^>` so that
REM sys.path[0] is the cwd (the repo, where src/ lives) rather than the
REM temp dir. Without this, Windows Python refuses to resolve the `src`
REM namespace package even with PYTHONPATH set.
pushd "%REPO%"
python -c "exec(open(r'%TMP_DIR%\phase3_v1.py').read())"
set "RC=%ERRORLEVEL%"
popd

REM --- Cleanup ---
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
exit /b %RC%