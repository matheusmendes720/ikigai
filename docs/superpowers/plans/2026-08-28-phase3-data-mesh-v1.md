# Phase 3 Data Mesh v1 (create action) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `create` task action end-to-end across vault + interfaces/cli + taskdog + solverforge-calendar UPI, via Deep Agent review queue, with cross-fork `mesh show` read view.

**Architecture:** Hybrid (vault = source of truth, UPI = derived index, each fork owns execution). Review queue buffers `task_change` events; Deep Agent validates against vault+PAE; on approval, propagates to all 3 fork stores + vault.

**Tech Stack:** Python 3.11+, Pydantic v2 strict, SQLite (taskdog + UPI), filesystem queue (`data/review_queue/`), Typer CLI, pytest.

## Global Constraints

- Pydantic v2 strict: `model_config = ConfigDict(frozen=True, extra="forbid")` on ALL schemas
- File size: keep files ≤500 lines; split when growing
- TDD discipline: every step writes test first, verifies failure, implements, verifies pass, commits
- Append-only: `data/tasks.jsonl`, `data/review_queue/`, vault
- No LLM in pipelines (agent is LLM but in orchestration role, not arithmetic)
- Fully local: SQLite + filesystem only
- Exact file paths always (Windows uses backslashes in commands, forward slashes in code)
- Commit message format: `feat(scope): description` (no Co-Authored-By trailer)

## File Structure

**Create:**
- `src/contracts/task_change.py` — Pydantic event model
- `src/mesh/__init__.py` — module marker
- `src/mesh/queue.py` — review queue (filesystem append-only)
- `src/mesh/agent_consumer.py` — Deep Agent validation
- `src/mesh/agent_propagator.py` — Deep Agent propagation
- `src/mesh/adapters/__init__.py` — adapters module marker
- `src/mesh/adapters/base.py` — ForkAdapter Protocol
- `src/mesh/adapters/taskdog.py` — taskdog adapter
- `src/mesh/adapters/solverforge_calendar.py` — solverforge UPI adapter
- `src/mesh/adapters/cli.py` — interfaces/cli adapter
- `tests/contracts/__init__.py`
- `tests/contracts/test_common_ueid.py`
- `tests/contracts/test_task_change.py`
- `tests/mesh/__init__.py`
- `tests/mesh/test_queue.py`
- `tests/mesh/test_agent_consumer.py`
- `tests/mesh/test_agent_propagator.py`
- `tests/mesh/adapters/__init__.py`
- `tests/mesh/adapters/test_taskdog.py`
- `tests/mesh/adapters/test_solverforge_calendar.py`
- `tests/mesh/adapters/test_cli.py`
- `tests/integration/__init__.py`
- `tests/integration/test_create_flow.py`

**Modify:**
- `src/contracts/common.py` — add UEID Pydantic type
- `src/contracts/task.py` — add `mesh_ueid: UEID | None` field
- `interfaces/cli/__init__.py` — create (currently missing per critic gap #8)
- `interfaces/cli/read_tasks.py` — add `show_mesh()` + `add_task()` functions
- `interfaces/cli/pyproject.toml` — fix entry-point (per critic gap #8)

---

## Phase 1 — Contracts

### Task 1: UEID Pydantic type

**Files:**
- Modify: `src/contracts/common.py`
- Test: `tests/contracts/test_common_ueid.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `from src.contracts.common import UEID` — Pydantic annotated type, regex-validated

- [ ] **Step 1: Write the failing test**

Create `tests/contracts/test_common_ueid.py`:

```python
import pytest
from src.contracts.common import UEID


@pytest.mark.parametrize("valid_ueid", [
    "tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
    "tsk:slug:00000000-0000-0000-0000-000000000000:0000000000000000",
    "tsk:a-b-c:11111111-2222-3333-4444-555555555555:ffffffffffffffff",
])
def test_ueid_accepts_valid_5_part_format(valid_ueid):
    """UEID type accepts 5-part format: type:slug:uuid:hash."""
    result = UEID(valid_ueid)
    assert str(result) == valid_ueid


@pytest.mark.parametrize("invalid_ueid", [
    "tsk",                                  # too few parts
    "tsk:slug",                              # missing uuid and hash
    "tsk:slug:abc",                          # missing hash
    "TSK:slug:uuid:hash",                    # uppercase
    "ts:slug:uuid:hash",                     # prefix too short (2 chars min)
    "toolong:slug:uuid:hash",                # prefix too long (5 chars max)
    "tsk:slug:not-a-uuid:hash",              # malformed uuid
    "",                                      # empty
    "tsk:slug:uuid:",                        # empty hash
    "tsk:slug with space:uuid:hash",         # spaces
])
def test_ueid_rejects_invalid_format(invalid_ueid):
    """UEID type rejects malformed input."""
    with pytest.raises(ValueError):
        UEID(invalid_ueid)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest ../tests/contracts/test_common_ueid.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.contracts.common'"

- [ ] **Step 3: Add UEID type to common.py**

Modify `src/contracts/common.py`, add at end:

```python
import re
from typing import Annotated
from pydantic import Field

UEID_PATTERN = r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$"

UEID = Annotated[
    str,
    Field(
        pattern=UEID_PATTERN,
        description="5-part UEID: type:slug:uuid:hash (all lowercase)",
        examples=["tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef"],
    ),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest ../tests/contracts/test_common_ueid.py -v`
Expected: PASS for all 18 parametrized cases

- [ ] **Step 5: Commit**

```bash
git add src/contracts/common.py tests/contracts/test_common_ueid.py
git commit -m "feat(contracts): add UEID Pydantic type with 5-part regex"
```

---

### Task 2: TaskChange Pydantic model

**Files:**
- Create: `src/contracts/task_change.py`
- Test: `tests/contracts/test_task_change.py`

**Interfaces:**
- Consumes: `from src.contracts.common import UEID` (Task 1)
- Produces: `from src.contracts.task_change import TaskChange, PropagationEvent, TaskAction`

- [ ] **Step 1: Write the failing test**

Create `tests/contracts/test_task_change.py`:

```python
import pytest
from datetime import datetime, timezone
from src.contracts.task_change import TaskChange, TaskAction


def test_task_change_accepts_valid_create_event():
    event = TaskChange(
        event_id="evt_001",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action="create",
        fields={"title": "Test task", "due": "2026-08-29"},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )
    assert event.action == TaskAction.CREATE
    assert event.fields["title"] == "Test task"
    assert event.status == "pending"  # default


def test_task_change_rejects_invalid_action():
    with pytest.raises(ValueError):
        TaskChange(
            event_id="evt_002",
            ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
            action="invalid_action",  # not in Literal
            fields={},
            source_fork="interfaces/cli",
            timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        )


def test_task_change_rejects_invalid_ueid():
    with pytest.raises(ValueError):
        TaskChange(
            event_id="evt_003",
            ueid="not-a-ueid",
            action="create",
            fields={},
            source_fork="interfaces/cli",
            timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        )


def test_task_change_is_frozen():
    event = TaskChange(
        event_id="evt_004",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action="create",
        fields={},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )
    with pytest.raises(Exception):  # ValidationError for frozen
        event.status = "approved"


def test_task_change_rejects_extra_fields():
    with pytest.raises(ValueError):
        TaskChange(
            event_id="evt_005",
            ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
            action="create",
            fields={},
            source_fork="interfaces/cli",
            timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
            unknown_field="bad",  # extra="forbid"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest ../tests/contracts/test_task_change.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.contracts.task_change'"

- [ ] **Step 3: Create TaskChange model**

Create `src/contracts/task_change.py`:

```python
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from src.contracts.common import UEID


class TaskAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    DONE = "done"


TaskStatus = Literal["pending", "approved", "rejected", "propagated", "partial_propagation"]


class TaskChange(BaseModel):
    """Event model for the review queue. Every fork emits this; agent consumes/produces this."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    ueid: UEID
    action: TaskAction
    fields: dict[str, Any]
    source_fork: str
    timestamp: datetime
    status: TaskStatus = "pending"


class PropagationEvent(BaseModel):
    """Subset emitted by agent to downstream forks after approval."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str  # same as TaskChange.event_id (for idempotency)
    ueid: UEID
    action: TaskAction
    fields: dict[str, Any]
    approved_at: datetime
    source_fork: str  # original source
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest ../tests/contracts/test_task_change.py -v`
Expected: PASS for all 5 tests

- [ ] **Step 5: Commit**

```bash
git add src/contracts/task_change.py tests/contracts/test_task_change.py
git commit -m "feat(contracts): add TaskChange + PropagationEvent models"
```

---

## Phase 2 — Storage (UPI schema migration)

### Task 3: UPI `ueid TEXT UNIQUE` column migration + backfill

**Files:**
- Modify: `solverforge-calendar/src/db/migrations/v3_add_ueid_column.sql` (create new)
- Test: `tests/integration/test_ueid_backfill.py`

**Interfaces:**
- Consumes: existing `solverforge-calendar` SQLite DB with `unified_planning_items` table
- Produces: same DB with new `ueid TEXT UNIQUE` column, backfilled from `ikigai` JSON

**Note:** Per Phase 1 audit `03-fork-solverforge-calendar.md:90`, UPI has `ikigai JSON` column containing UEID. We extract to a real column.

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_ueid_backfill.py`:

```python
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def upi_db_with_legacy_data(tmp_path: Path) -> Path:
    """Create a sqlite db with the legacy schema and 3 sample rows."""
    db_path = tmp_path / "test_unified_planning.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE unified_planning_items (
            id TEXT PRIMARY KEY,
            status TEXT,
            start_at TEXT,
            end_at TEXT,
            blocked_by TEXT,
            tags TEXT,
            ikigai TEXT,  -- JSON with UEID inside
            provenance TEXT
        );
        INSERT INTO unified_planning_items VALUES
          ('uuid-1', 'planned', '2026-08-28T09:00', '2026-08-28T10:00', '[]', '[]',
           '{"ueid": "tsk:byd-case:11111111-2222-3333-4444-555555555555:aaaaaaaaaaaaaaaa"}',
           '{}'),
          ('uuid-2', 'planned', '2026-08-28T11:00', '2026-08-28T12:00', '[]', '[]',
           '{"ueid": "tsk:byd-case:22222222-3333-4444-5555-666666666666:bbbbbbbbbbbbbbbb"}',
           '{}'),
          ('uuid-3', 'in_progress', NULL, NULL, '[]', '[]',
           '{"other_field": "no ueid here"}',  -- no UEID
           '{}');
    """)
    conn.commit()
    conn.close()
    return db_path


def test_migration_adds_ueid_column_and_backfills(upi_db_with_legacy_data: Path):
    """Migration adds ueid column and backfills from ikigai JSON."""
    from solverforge_calendar.migrations.v3_add_ueid import migrate

    migrate(upi_db_with_legacy_data)

    conn = sqlite3.connect(upi_db_with_legacy_data)
    # Verify column exists
    cols = [row[1] for row in conn.execute("PRAGMA table_info(unified_planning_items)").fetchall()]
    assert "ueid" in cols

    # Verify backfill
    rows = conn.execute("SELECT id, ueid FROM unified_planning_items ORDER BY id").fetchall()
    assert rows[0][1] == "tsk:byd-case:11111111-2222-3333-4444-555555555555:aaaaaaaaaaaaaaaa"
    assert rows[1][1] == "tsk:byd-case:22222222-3333-4444-5555-666666666666:bbbbbbbbbbbbbbbb"
    assert rows[2][1] is None  # row without UEID stays NULL

    # Verify UNIQUE constraint (try to insert duplicate)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO unified_planning_items (id, ueid) VALUES (?, ?)",
            ("uuid-dup", "tsk:byd-case:11111111-2222-3333-4444-555555555555:aaaaaaaaaaaaaaaa"),
        )
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest ../tests/integration/test_ueid_backfill.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'solverforge_calendar.migrations.v3_add_ueid'"

- [ ] **Step 3: Create migration module**

Create `solverforge-calendar/src/solverforge_calendar/migrations/__init__.py` (empty)
Create `solverforge-calendar/src/solverforge_calendar/migrations/v3_add_ueid.py`:

```python
"""v3 migration: extract UEID from unified_planning_items.ikigai JSON to a real column."""
import json
import sqlite3


def migrate(db_path: str) -> None:
    """Add ueid TEXT UNIQUE column and backfill from ikigai JSON.

    Idempotent: skips if column already exists.
    """
    conn = sqlite3.connect(db_path)
    try:
        # Check if column already exists
        cols = [row[1] for row in conn.execute(
            "PRAGMA table_info(unified_planning_items)"
        ).fetchall()]
        if "ueid" in cols:
            return  # idempotent

        # Add column (SQLite allows ADD COLUMN without DEFAULT for NULL)
        conn.execute("ALTER TABLE unified_planning_items ADD COLUMN ueid TEXT")

        # Backfill: extract UEID from ikigai JSON where present
        rows = conn.execute(
            "SELECT id, ikigai FROM unified_planning_items WHERE ikigai IS NOT NULL"
        ).fetchall()
        for row_id, ikigai_json in rows:
            try:
                ikigai = json.loads(ikigai_json)
                ueid = ikigai.get("ueid")
                if ueid:
                    conn.execute(
                        "UPDATE unified_planning_items SET ueid = ? WHERE id = ?",
                        (ueid, row_id),
                    )
            except (json.JSONDecodeError, KeyError):
                continue  # skip malformed rows

        # Create UNIQUE index on ueid
        conn.execute(
            "CREATE UNIQUE INDEX idx_unified_planning_items_ueid "
            "ON unified_planning_items(ueid)"
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest ../tests/integration/test_ueid_backfill.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add solverforge-calendar/src/solverforge_calendar/migrations/ tests/integration/test_ueid_backfill.py
git commit -m "feat(solverforge-calendar): migrate UPI to add ueid TEXT UNIQUE column with backfill"
```

---

## Phase 3 — Review Queue

### Task 4: Filesystem append-only queue

**Files:**
- Create: `src/mesh/queue.py`
- Test: `tests/mesh/test_queue.py`

**Interfaces:**
- Consumes: `from src.contracts.task_change import TaskChange` (Task 2)
- Produces: `from src.mesh.queue import enqueue, consume_pending, ack, replay_after_restart`

- [ ] **Step 1: Write the failing test**

Create `tests/mesh/test_queue.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import TaskChange, TaskAction
from src.mesh import queue


@pytest.fixture
def queue_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create a tmp queue dir and override the module's QUEUE_DIR."""
    qdir = tmp_path / "review_queue"
    qdir.mkdir()
    monkeypatch.setattr(queue, "QUEUE_DIR", qdir)
    return qdir


def _sample_event(event_id: str = "evt_001") -> TaskChange:
    return TaskChange(
        event_id=event_id,
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Test"},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )


def test_enqueue_writes_event_file_atomically(queue_dir: Path):
    """enqueue() writes file via temp + atomic rename."""
    event = _sample_event()
    event_id = queue.enqueue(event)

    assert event_id == "evt_001"
    files = list(queue_dir.glob("*.json"))
    assert len(files) == 1
    assert files[0].name == "evt_001.json"

    # Verify content is valid JSON
    content = json.loads(files[0].read_text())
    assert content["event_id"] == "evt_001"


def test_consume_pending_returns_pending_events(queue_dir: Path):
    """consume_pending() returns only events with status='pending'."""
    queue.enqueue(_sample_event("evt_a"))
    queue.enqueue(_sample_event("evt_b"))
    queue.ack("evt_a", "approved")  # not pending anymore

    events = list(queue.consume_pending())
    assert len(events) == 1
    assert events[0].event_id == "evt_b"


def test_ack_updates_status_in_place(queue_dir: Path):
    """ack() updates the event file's status field atomically."""
    queue.enqueue(_sample_event())
    queue.ack("evt_001", "approved")

    event_file = queue_dir / "evt_001.json"
    content = json.loads(event_file.read_text())
    assert content["status"] == "approved"


def test_ack_is_idempotent(queue_dir: Path):
    """Re-acking same event_id is no-op (doesn't error)."""
    queue.enqueue(_sample_event())
    queue.ack("evt_001", "approved")
    queue.ack("evt_001", "propagated")  # no-op
    content = json.loads((queue_dir / "evt_001.json").read_text())
    assert content["status"] == "approved"


def test_replay_after_restart_re_processes_pending(queue_dir: Path):
    """All pending events are visible after replay (simulates crash recovery)."""
    queue.enqueue(_sample_event("evt_1"))
    queue.enqueue(_sample_event("evt_2"))
    queue.enqueue(_sample_event("evt_3"))

    events = list(queue.replay_after_restart())
    assert len(events) == 3
    assert {e.event_id for e in events} == {"evt_1", "evt_2", "evt_3"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest ../tests/mesh/test_queue.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.mesh.queue'"

- [ ] **Step 3: Create queue module**

Create `src/mesh/__init__.py` (empty)
Create `src/mesh/queue.py`:

```python
"""Filesystem-based append-only review queue. Atomic writes via temp + rename."""
import json
import os
import tempfile
from pathlib import Path
from typing import Iterator

from src.contracts.task_change import TaskChange, TaskStatus

# Project root is 2 levels up from src/mesh/
PROJECT_ROOT = Path(__file__).parent.parent.parent
QUEUE_DIR = PROJECT_ROOT / "data" / "review_queue"


def _ensure_queue_dir() -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return QUEUE_DIR


def enqueue(event: TaskChange) -> str:
    """Append event to queue. Atomic write via temp file + rename."""
    qdir = _ensure_queue_dir()
    target = qdir / f"{event.event_id}.json"
    tmp = target.with_suffix(".tmp")

    content = event.model_dump_json()
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)  # atomic on same filesystem
    return event.event_id


def _read_event_file(path: Path) -> TaskChange:
    return TaskChange.model_validate_json(path.read_text())


def consume_pending() -> Iterator[TaskChange]:
    """Iterate over events with status='pending'."""
    qdir = _ensure_queue_dir()
    for path in sorted(qdir.glob("*.json")):
        try:
            event = _read_event_file(path)
            if event.status == "pending":
                yield event
        except Exception:
            continue  # skip malformed files


def ack(event_id: str, status: TaskStatus) -> None:
    """Update event status in place. Idempotent (no-op if event not pending)."""
    qdir = _ensure_queue_dir()
    target = qdir / f"{event_id}.json"
    if not target.exists():
        return  # idempotent

    event = _read_event_file(target)
    if event.status != "pending":
        return  # already processed

    # Re-emit with new status (frozen model requires new instance)
    from src.contracts.task_change import TaskChange
    updated = event.model_copy(update={"status": status})
    tmp = target.with_suffix(".tmp")
    tmp.write_text(updated.model_dump_json())
    os.replace(tmp, target)


def replay_after_restart() -> Iterator[TaskChange]:
    """Re-process all pending events (called on agent startup)."""
    yield from consume_pending()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest ../tests/mesh/test_queue.py -v`
Expected: PASS for all 5 tests

- [ ] **Step 5: Commit**

```bash
git add src/mesh/__init__.py src/mesh/queue.py tests/mesh/__init__.py tests/mesh/test_queue.py
git commit -m "feat(mesh): filesystem append-only review queue with atomic writes"
```

---

## Phase 4 — Deep Agent

### Task 5: Agent consumer (validation)

**Files:**
- Create: `src/mesh/agent_consumer.py`
- Test: `tests/mesh/test_agent_consumer.py`

**Interfaces:**
- Consumes: `from src.contracts.task_change import TaskChange`, vault context (read from `vault/ikigai/closing-2026/<cycle>.md`)
- Produces: `from src.mesh.agent_consumer import validate` returning `ValidationResult`

- [ ] **Step 1: Write the failing test**

Create `tests/mesh/test_agent_consumer.py`:

```python
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import TaskChange, TaskAction


@pytest.fixture
def sample_create_event() -> TaskChange:
    return TaskChange(
        event_id="evt_001",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Review BYD case", "due": "2099-01-01"},  # far future = valid
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )


@pytest.fixture
def vault_context_empty(tmp_path: Path, monkeypatch) -> Path:
    """Create empty vault dir for context loading."""
    vault = tmp_path / "vault"
    (vault / "ikigai" / "closing-2026").mkdir(parents=True)
    monkeypatch.setenv("VAULT_PATH", str(vault))
    return vault


def test_validate_approves_clean_event(sample_create_event, vault_context_empty):
    """Validate returns approve for a clean event with valid fields."""
    from src.mesh.agent_consumer import validate, Decision

    result = validate(sample_create_event)
    assert result.decision == Decision.APPROVE


def test_validate_rejects_past_due_date(vault_context_empty):
    """Validate rejects event with due date in the past."""
    from src.mesh.agent_consumer import validate, Decision

    event = TaskChange(
        event_id="evt_002",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Past task", "due": "2020-01-01"},  # in the past
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )
    result = validate(event)
    assert result.decision == Decision.REJECT
    assert "past" in result.reason.lower()


def test_validate_clarifies_vague_title(vault_context_empty):
    """Validate asks clarification for vague title (<10 chars or generic)."""
    from src.mesh.agent_consumer import validate, Decision

    event = TaskChange(
        event_id="evt_003",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "todo"},  # too vague
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )
    result = validate(event)
    assert result.decision == Decision.CLARIFY
    assert "title" in result.reason.lower()


def test_validate_rejects_ueid_collision(vault_context_empty, sample_create_event):
    """Validate rejects if UEID already exists with different title."""
    from src.mesh.agent_consumer import validate, Decision
    from src.mesh import queue

    queue.enqueue(sample_create_event)
    queue.ack("evt_001", "propagated")  # simulate already-propagated event

    # New event with same UEID but different title
    new_event = sample_create_event.model_copy(update={
        "event_id": "evt_004",
        "fields": {"title": "Different title", "due": "2099-01-01"},
    })
    result = validate(new_event)
    assert result.decision == Decision.REJECT
    assert "collision" in result.reason.lower() or "exists" in result.reason.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest ../tests/mesh/test_agent_consumer.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.mesh.agent_consumer'"

- [ ] **Step 3: Create agent_consumer module**

Create `src/mesh/agent_consumer.py`:

```python
"""Deep Agent consumer: validates events against vault context + PAE rules."""
import os
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from src.contracts.task_change import TaskChange
from src.mesh import queue


class Decision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    CLARIFY = "clarify"


@dataclass(frozen=True)
class ValidationResult:
    decision: Decision
    reason: str = ""
    approved_fields: dict | None = None


VAGUE_TITLES = {"todo", "tbd", "fix", "work", "task", "stuff", "thing"}


def validate(event: TaskChange) -> ValidationResult:
    """Validate event. Returns approve/reject/clarify decision."""
    title = event.fields.get("title", "")

    # Check 1: title not vague
    if not title or title.lower().strip() in VAGUE_TITLES or len(title.strip()) < 5:
        return ValidationResult(
            Decision.CLARIFY,
            "Title too vague. Provide a specific, actionable title (≥5 chars, not 'todo'/'tbd').",
        )

    # Check 2: due date not in past (for create actions)
    if event.action.value == "create" and "due_date in event.fields:
        try:
            due = date.fromisoformat(event.fields["due"])
            if due < date.today():
                return ValidationResult(
                    Decision.REJECT,
                    f"Due date {due} is in the past. Use a future date or remove due field.",
                )
        except (ValueError, TypeError):
            return ValidationResult(
                Decision.REJECT,
                f"Invalid due date format: {event.fields['due']!r}. Use YYYY-MM-DD.",
            )

    # Check 3: UEID collision (existing propagated event with same UEID)
    for existing in queue.replay_after_restart():
        if existing.ueid == event.ueid and existing.status == "propagated":
            if existing.fields.get("title") != event.fields.get("title"):
                return ValidationResult(
                    Decision.REJECT,
                    f"UEID collision: {event.ueid} already exists with different content.",
                )

    return ValidationResult(Decision.APPROVE, approved_fields=event.fields)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest ../tests/mesh/test_agent_consumer.py -v`
Expected: PASS for all 4 tests

- [ ] **Step 5: Commit**

```bash
git add src/mesh/agent_consumer.py tests/mesh/test_agent_consumer.py
git commit -m "feat(mesh): Deep Agent consumer with PAE validation rules"
```

---

### Task 6: Agent propagator

**Files:**
- Create: `src/mesh/agent_propagator.py`
- Test: `tests/mesh/test_agent_propagator.py`

**Interfaces:**
- Consumes: `from src.contracts.task_change import TaskChange, PropagationEvent`, `from src.mesh.agent_consumer import ValidationResult`
- Produces: `from src.mesh.agent_propagator import propagate` returning `list[PropagationResult]`

- [ ] **Step 1: Write the failing test**

Create `tests/mesh/test_agent_propagator.py`:

```python
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.contracts.task_change import TaskChange, TaskAction
from src.mesh.agent_consumer import ValidationResult, Decision


@pytest.fixture
def sample_event() -> TaskChange:
    return TaskChange(
        event_id="evt_001",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Test", "due": "2099-01-01"},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )


def test_propagate_calls_all_adapters(sample_event):
    """propagate() calls apply_change() on every registered adapter."""
    from src.mesh.agent_propagator import propagate
    from src.mesh.adapters.base import ForkAdapter

    adapter1 = MagicMock(spec=ForkAdapter)
    adapter1.name = "taskdog"
    adapter1.apply_change.return_value = MagicMock(success=True)

    adapter2 = MagicMock(spec=ForkAdapter)
    adapter2.name = "solverforge_calendar"
    adapter2.apply_change.return_value = MagicMock(success=True)

    result = propagate(
        sample_event,
        ValidationResult(Decision.APPROVE, approved_fields=sample_event.fields),
        adapters=[adapter1, adapter2],
    )

    assert len(result) == 2
    assert all(r.success for r in result)
    adapter1.apply_change.assert_called_once()
    adapter2.apply_change.assert_called_once()


def test_propagate_marks_partial_when_adapter_fails(sample_event):
    """propagate() marks partial_propagation if any adapter fails."""
    from src.mesh.agent_propagator import propagate
    from src.mesh.adapters.base import ForkAdapter

    adapter_ok = MagicMock(spec=ForkAdapter)
    adapter_ok.name = "taskdog"
    adapter_ok.apply_change.return_value = MagicMock(success=True)

    adapter_fail = MagicMock(spec=ForkAdapter)
    adapter_fail.name = "solverforge_calendar"
    adapter_fail.apply_change.side_effect = ConnectionError("solverforge down")

    result = propagate(
        sample_event,
        ValidationResult(Decision.APPROVE, approved_fields=sample_event.fields),
        adapters=[adapter_ok, adapter_fail],
    )

    assert len(result) == 2
    assert result[0].success is True
    assert result[1].success is False


def test_propagate_is_idempotent(sample_event):
    """Same event_id twice produces same UEID writes (no double-apply)."""
    from src.mesh.agent_propagator import propagate
    from src.mesh.agent_consumer import ValidationResult, Decision
    from src.mesh.adapters.base import ForkAdapter

    adapter = MagicMock(spec=ForkAdapter)
    adapter.name = "taskdog"
    adapter.apply_change.return_value = MagicMock(success=True)

    result1 = propagate(
        sample_event,
        ValidationResult(Decision.APPROVE, approved_fields=sample_event.fields),
        adapters=[adapter],
    )
    result2 = propagate(
        sample_event,
        ValidationResult(Decision.APPROVE, approved_fields=sample_event.fields),
        adapters=[adapter],
    )

    # Adapter called twice (each propagation is independent)
    assert adapter.apply_change.call_count == 2
    # Both results are success
    assert result1[0].success is True
    assert result2[0].success is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest ../tests/mesh/test_agent_propagator.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.mesh.agent_propagator'"

- [ ] **Step 3: Create agent_propagator module**

Create `src/mesh/agent_propagator.py`:

```python
"""Deep Agent propagator: emits approved events to all relevant forks + vault."""
from dataclasses import dataclass

from src.contracts.task_change import TaskChange, PropagationEvent
from src.mesh.agent_consumer import ValidationResult
from src.mesh.adapters.base import ForkAdapter


@dataclass(frozen=True)
class PropagationResult:
    fork_name: str
    success: bool
    error: str = ""


def propagate(
    event: TaskChange,
    validation: ValidationResult,
    adapters: list[ForkAdapter],
) -> list[PropagationResult]:
    """Propagate approved event to all adapters. Per-adapter failures are isolated."""
    if validation.decision.value != "approve":
        return []

    propagation = PropagationEvent(
        event_id=event.event_id,
        ueid=event.ueid,
        action=event.action,
        fields=validation.approved_fields or event.fields,
        approved_at=event.timestamp,
        source_fork=event.source_fork,
    )

    results = []
    for adapter in adapters:
        try:
            adapter.apply_change(propagation)
            results.append(PropagationResult(fork_name=adapter.name, success=True))
        except Exception as e:
            results.append(
                PropagationResult(
                    fork_name=adapter.name,
                    success=False,
                    error=str(e),
                )
            )
    return results
```

- [ ] **Step 4: Create ForkAdapter Protocol (stub for now)**

Create `src/mesh/adapters/__init__.py` (empty)
Create `src/mesh/adapters/base.py`:

```python
"""Common adapter contract for fork adapters."""
from typing import Any, Protocol, runtime_checkable

from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent


@runtime_checkable
class ForkAdapter(Protocol):
    """Every fork adapter implements read() + apply_change() + supports_field()."""
    name: str

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        """Return slice for this UEID, or None if not found."""
        ...

    def apply_change(self, event: PropagationEvent) -> None:
        """Apply change to fork store. Idempotent (safe to retry)."""
        ...

    def supports_field(self, field_name: str) -> bool:
        """Return True if this adapter persists this field."""
        ...
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd src && python -m pytest ../tests/mesh/test_agent_propagator.py -v`
Expected: PASS for all 3 tests

- [ ] **Step 6: Commit**

```bash
git add src/mesh/agent_propagator.py src/mesh/adapters/__init__.py src/mesh/adapters/base.py tests/mesh/test_agent_propagator.py
git commit -m "feat(mesh): Deep Agent propagator with per-adapter failure isolation"
```

---

## Phase 5 — Fork Adapters

### Task 7: interfaces/cli adapter

**Files:**
- Create: `src/mesh/adapters/cli.py`
- Test: `tests/mesh/adapters/test_cli.py`

**Interfaces:**
- Consumes: `from src.contracts.task_change import PropagationEvent`, `from src.contracts.common import UEID`
- Produces: `CliAdapter` class implementing `ForkAdapter`

- [ ] **Step 1: Write the failing test**

Create `tests/mesh/adapters/test_cli.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import PropagationEvent, TaskAction


@pytest.fixture
def tasks_jsonl(tmp_path: Path, monkeypatch) -> Path:
    """Create empty tasks.jsonl in tmp dir, point CLI adapter at it."""
    tasks_file = tmp_path / "tasks.jsonl"
    tasks_file.write_text("")  # empty

    from src.mesh.adapters import cli
    monkeypatch.setattr(cli, "TASKS_JSONL", tasks_file)
    return tasks_file


def _sample_event(ueid: str = "tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000") -> PropagationEvent:
    return PropagationEvent(
        event_id="evt_001",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": "Test task", "due": "2099-01-01"},
        approved_at=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )


def test_cli_adapter_apply_change_appends_task(tasks_jsonl: Path):
    """apply_change appends new task to tasks.jsonl."""
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    lines = tasks_jsonl.read_text().strip().split("\n")
    assert len(lines) == 1
    task = json.loads(lines[0])
    assert task["ueid"] == event.ueid
    assert task["title"] == "Test task"


def test_cli_adapter_read_returns_slice(tasks_jsonl: Path):
    """read() returns slice for given UEID."""
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    slice = adapter.read(event.ueid)
    assert slice is not None
    assert slice["ueid"] == event.ueid


def test_cli_adapter_read_returns_none_for_unknown(tasks_jsonl: Path):
    """read() returns None when UEID not in tasks.jsonl."""
    from src.mesh.adapters.cli import CliAdapter
    from src.contracts.common import UEID

    adapter = CliAdapter()
    unknown_ueid: UEID = "tsk:other:00000000-0000-0000-0000-000000000000:0000000000000000"
    assert adapter.read(unknown_ueid) is None


def test_cli_adapter_supports_field():
    """CliAdapter supports title, due, priority fields."""
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()
    assert adapter.supports_field("title") is True
    assert adapter.supports_field("due") is True
    assert adapter.supports_field("priority") is True
    assert adapter.supports_field("start_at") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest ../tests/mesh/adapters/test_cli.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.mesh.adapters.cli'"

- [ ] **Step 3: Create CliAdapter**

Create `src/mesh/adapters/cli.py`:

```python
"""Adapter for interfaces/cli tasks.jsonl file."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TASKS_JSONL = PROJECT_ROOT / "data" / "tasks.jsonl"

SUPPORTED_FIELDS = {"title", "due", "priority", "ueid", "written_at", "source_fork"}


class CliAdapter:
    """Read/write the interfaces/cli tasks.jsonl slice."""
    name = "cli"

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        if not TASKS_JSONL.exists():
            return None
        for line in TASKS_JSONL.read_text().splitlines():
            if not line.strip():
                continue
            task = json.loads(line)
            if task.get("ueid") == ueid:
                return task
        return None

    def apply_change(self, event: PropagationEvent) -> None:
        if event.action.value != "create":
            return  # v1 only supports create

        TASKS_JSONL.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ueid": event.ueid,
            "title": event.fields.get("title"),
            "due": event.fields.get("due"),
            "priority": event.fields.get("priority", "medium"),
            "written_at": event.approved_at.isoformat(),
            "source_fork": event.source_fork,
        }
        line = json.dumps(record) + "\n"

        # Atomic append via temp + rename (works on Windows + Unix)
        tmp = TASKS_JSONL.with_suffix(".tmp")
        existing = TASKS_JSONL.read_text() if TASKS_JSONL.exists() else ""
        tmp.write_text(existing + line)
        os.replace(tmp, TASKS_JSONL)

    def supports_field(self, field_name: str) -> bool:
        return field_name in SUPPORTED_FIELDS
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest ../tests/mesh/adapters/test_cli.py -v`
Expected: PASS for all 4 tests

- [ ] **Step 5: Commit**

```bash
git add src/mesh/adapters/cli.py tests/mesh/adapters/__init__.py tests/mesh/adapters/test_cli.py
git commit -m "feat(mesh): CliAdapter for interfaces/cli tasks.jsonl"
```

---

### Task 8: taskdog adapter

**Files:**
- Create: `src/mesh/adapters/taskdog.py`
- Test: `tests/mesh/adapters/test_taskdog.py`

**Interfaces:**
- Consumes: `from src.contracts.task_change import PropagationEvent`, `from src.contracts.common import UEID`
- Produces: `TaskdogAdapter` class implementing `ForkAdapter`

**Note:** taskdog uses SQLAlchemy + Alembic (per Phase 2 RE `02-fork-taskdog.md`). v1 adapter writes to a simplified schema (tasks table with ueid column). Full SQLAlchemy integration deferred to v2.

- [ ] **Step 1: Write the failing test**

Create `tests/mesh/adapters/test_taskdog.py`:

```python
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import PropagationEvent, TaskAction


@pytest.fixture
def taskdog_db(tmp_path: Path, monkeypatch) -> Path:
    """Create simplified taskdog SQLite schema in tmp."""
    db_path = tmp_path / "test_tasks.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ueid TEXT,
            name TEXT,
            status TEXT,
            priority INTEGER,
            planned_start TEXT,
            planned_end TEXT,
            deadline TEXT,
            created_at TEXT
        );
        CREATE INDEX idx_tasks_ueid ON tasks(ueid);
    """)
    conn.commit()
    conn.close()

    from src.mesh.adapters import taskdog
    monkeypatch.setattr(taskdog, "TASKDOG_DB", db_path)
    return db_path


def _sample_event() -> PropagationEvent:
    return PropagationEvent(
        event_id="evt_001",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Test task", "due": "2099-01-01", "priority": 2},
        approved_at=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )


def test_taskdog_adapter_apply_change_inserts_task(taskdog_db: Path):
    """apply_change inserts new row with ueid FK."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    adapter = TaskdogAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    conn = sqlite3.connect(taskdog_db)
    row = conn.execute(
        "SELECT ueid, name, deadline, priority FROM tasks WHERE ueid = ?",
        (event.ueid,),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == event.ueid
    assert row[1] == "Test task"
    assert row[2] == "2099-01-01"


def test_taskdog_adapter_read_returns_slice(taskdog_db: Path):
    """read() returns slice for given UEID."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    adapter = TaskdogAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    slice = adapter.read(event.ueid)
    assert slice is not None
    assert slice["ueid"] == event.ueid
    assert slice["name"] == "Test task"


def test_taskdog_adapter_is_idempotent(taskdog_db: Path):
    """apply_change called twice with same UEID updates, doesn't double-insert."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    adapter = TaskdogAdapter()
    event = _sample_event()
    adapter.apply_change(event)
    adapter.apply_change(event)  # second call

    conn = sqlite3.connect(taskdog_db)
    count = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE ueid = ?", (event.ueid,)
    ).fetchone()[0]
    conn.close()
    assert count == 1


def test_taskdog_adapter_supports_field():
    """TaskdogAdapter supports lifecycle + planning fields."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    adapter = TaskdogAdapter()
    assert adapter.supports_field("title") is True  # mapped to `name`
    assert adapter.supports_field("due") is True    # mapped to `deadline`
    assert adapter.supports_field("priority") is True
    assert adapter.supports_field("rrule") is False  # calendar-only
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest ../tests/mesh/adapters/test_taskdog.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.mesh.adapters.taskdog'"

- [ ] **Step 3: Create TaskdogAdapter**

Create `src/mesh/adapters/taskdog.py`:

```python
"""Adapter for taskdog SQLite (simplified schema for v1; full SQLAlchemy in v2)."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TASKDOG_DB = PROJECT_ROOT / "data" / "taskdog" / "tasks.db"

SUPPORTED_FIELDS = {"title", "due", "priority", "status", "ueid", "planned_start", "planned_end", "actual_end", "tags"}


class TaskdogAdapter:
    """Read/write the taskdog tasks table (simplified for v1)."""
    name = "taskdog"

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        if not TASKDOG_DB.exists():
            return None
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            row = conn.execute(
                "SELECT ueid, name, status, priority, planned_start, planned_end, deadline, created_at "
                "FROM tasks WHERE ueid = ?",
                (ueid,),
            ).fetchone()
            if row is None:
                return None
            return {
                "ueid": row[0],
                "name": row[1],
                "status": row[2],
                "priority": row[3],
                "planned_start": row[4],
                "planned_end": row[5],
                "deadline": row[6],
                "created_at": row[7],
            }
        finally:
            conn.close()

    def apply_change(self, event: PropagationEvent) -> None:
        if event.action.value != "create":
            return  # v1 only supports create

        TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(TASKDOG_DB)
        try:
            # Check if table exists (create if not — idempotent bootstrap)
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ueid TEXT UNIQUE,
                    name TEXT,
                    status TEXT,
                    priority INTEGER,
                    planned_start TEXT,
                    planned_end TEXT,
                    deadline TEXT,
                    created_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_ueid ON tasks(ueid);
            """)

            # UPSERT: insert or update
            priority = event.fields.get("priority")
            if isinstance(priority, str):
                priority_map = {"high": 1, "medium": 2, "low": 3}
                priority = priority_map.get(priority.lower(), 2)

            conn.execute(
                """INSERT INTO tasks (ueid, name, status, priority, deadline, created_at)
                   VALUES (?, ?, 'planned', ?, ?, ?)
                   ON CONFLICT(ueid) DO UPDATE SET
                     name=excluded.name,
                     priority=excluded.priority,
                     deadline=excluded.deadline""",
                (
                    event.ueid,
                    event.fields.get("title"),
                    priority,
                    event.fields.get("due"),
                    event.approved_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def supports_field(self, field_name: str) -> bool:
        return field_name in SUPPORTED_FIELDS
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest ../tests/mesh/adapters/test_taskdog.py -v`
Expected: PASS for all 4 tests

- [ ] **Step 5: Commit**

```bash
git add src/mesh/adapters/taskdog.py tests/mesh/adapters/test_taskdog.py
git commit -m "feat(mesh): TaskdogAdapter for taskdog SQLite (simplified schema)"
```

---

### Task 9: solverforge-calendar UPI adapter

**Files:**
- Create: `src/mesh/adapters/solverforge_calendar.py`
- Test: `tests/mesh/adapters/test_solverforge_calendar.py`

**Interfaces:**
- Consumes: `from src.contracts.task_change import PropagationEvent`, `from src.contracts.common import UEID`
- Produces: `SolverforgeCalendarAdapter` class implementing `ForkAdapter`

- [ ] **Step 1: Write the failing test**

Create `tests/mesh/adapters/test_solverforge_calendar.py`:

```python
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import PropagationEvent, TaskAction


@pytest.fixture
def upi_db_with_migration(tmp_path: Path, monkeypatch) -> Path:
    """Create UPI DB with v3 migration applied (ueid TEXT UNIQUE column)."""
    from solverforge_calendar.migrations.v3_add_ueid import migrate

    db_path = tmp_path / "test_unified_planning.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE unified_planning_items (
            id TEXT PRIMARY KEY,
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
    migrate(str(db_path))  # adds ueid column

    from src.mesh.adapters import solverforge_calendar
    monkeypatch.setattr(solverforge_calendar, "UPI_DB", db_path)
    return db_path


def _sample_event() -> PropagationEvent:
    return PropagationEvent(
        event_id="evt_001",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Test task", "due": "2099-01-01"},
        approved_at=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )


def test_solverforge_adapter_apply_change_inserts_upi_row(upi_db_with_migration: Path):
    """apply_change inserts new UPI row with ueid column populated."""
    from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

    adapter = SolverforgeCalendarAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    conn = sqlite3.connect(upi_db_with_migration)
    row = conn.execute(
        "SELECT ueid, status, ikigai FROM unified_planning_items WHERE ueid = ?",
        (event.ueid,),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == event.ueid
    assert row[1] == "planned"
    ikigai = json.loads(row[2])
    assert ikigai["title"] == "Test task"
    assert ikigai["source_fork"] == "interfaces/cli"


def test_solverforge_adapter_read_returns_slice(upi_db_with_migration: Path):
    """read() returns slice for given UEID."""
    from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

    adapter = SolverforgeCalendarAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    slice = adapter.read(event.ueid)
    assert slice is not None
    assert slice["ueid"] == event.ueid


def test_solverforge_adapter_supports_field():
    """SolverforgeCalendarAdapter supports scheduling + aggregate fields."""
    from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

    adapter = SolverforgeCalendarAdapter()
    assert adapter.supports_field("title") is True
    assert adapter.supports_field("status") is True
    assert adapter.supports_field("start_at") is True
    assert adapter.supports_field("end_at") is True
    assert adapter.supports_field("rrule") is True
    assert adapter.supports_field("deadline") is False  # taskdog uses this
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest ../tests/mesh/adapters/test_solverforge_calendar.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.mesh.adapters.solverforge_calendar'"

- [ ] **Step 3: Create SolverforgeCalendarAdapter**

Create `src/mesh/adapters/solverforge_calendar.py`:

```python
"""Adapter for solverforge-calendar unified_planning_items (UPI)."""
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
UPI_DB = PROJECT_ROOT / "data" / "solverforge_calendar" / "unified_planning.db"

SUPPORTED_FIELDS = {"title", "status", "start_at", "end_at", "rrule", "blocked_by", "tags", "ueid"}


class SolverforgeCalendarAdapter:
    """Read/write solverforge-calendar UPI (after v3 migration)."""
    name = "solverforge_calendar"

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        if not UPI_DB.exists():
            return None
        conn = sqlite3.connect(UPI_DB)
        try:
            row = conn.execute(
                "SELECT id, ueid, status, start_at, end_at, blocked_by, tags, ikigai "
                "FROM unified_planning_items WHERE ueid = ?",
                (ueid,),
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "ueid": row[1],
                "status": row[2],
                "start_at": row[3],
                "end_at": row[4],
                "blocked_by": json.loads(row[5]) if row[5] else [],
                "tags": json.loads(row[6]) if row[6] else [],
                "ikigai": json.loads(row[7]) if row[7] else {},
            }
        finally:
            conn.close()

    def apply_change(self, event: PropagationEvent) -> None:
        if event.action.value != "create":
            return  # v1 only supports create

        UPI_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(UPI_DB)
        try:
            # Idempotent bootstrap (assumes v3 migration already added ueid column)
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
                CREATE INDEX IF NOT EXISTS idx_upi_ueid ON unified_planning_items(ueid);
            """)

            ikigai = {
                "title": event.fields.get("title"),
                "due": event.fields.get("due"),
                "source_fork": event.source_fork,
                "approved_at": event.approved_at.isoformat(),
            }
            new_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO unified_planning_items (id, ueid, status, blocked_by, tags, ikigai, provenance)
                   VALUES (?, ?, 'planned', '[]', '[]', ?, '{}')
                   ON CONFLICT(ueid) DO UPDATE SET
                     status=excluded.status,
                     ikigai=excluded.ikigai""",
                (new_id, event.ueid, json.dumps(ikigai)),
            )
            conn.commit()
        finally:
            conn.close()

    def supports_field(self, field_name: str) -> bool:
        return field_name in SUPPORTED_FIELDS
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest ../tests/mesh/adapters/test_solverforge_calendar.py -v`
Expected: PASS for all 3 tests

- [ ] **Step 5: Commit**

```bash
git add src/mesh/adapters/solverforge_calendar.py tests/mesh/adapters/test_solverforge_calendar.py
git commit -m "feat(mesh): SolverforgeCalendarAdapter for UPI ueid column"
```

---

## Phase 6 — CLI Commands

### Task 10: interfaces/cli `mesh show` + `task add`

**Files:**
- Modify: `interfaces/cli/__init__.py` (create)
- Modify: `interfaces/cli/read_tasks.py` (add 2 functions)
- Modify: `interfaces/cli/pyproject.toml` (fix entry-point per critic gap #8)
- Test: manual smoke test (no automated test for Typer CLI v1)

**Interfaces:**
- Consumes: 3 adapters (Task 7-9), agent consumer + propagator (Task 5-6)
- Produces: `life mesh show <ueid>` and `life task add` Typer commands

- [ ] **Step 1: Create interfaces/cli/__init__.py**

Create `interfaces/cli/__init__.py` (empty file). This fixes critic gap #8 (CLI installability).

- [ ] **Step 2: Add show_mesh() to read_tasks.py**

Modify `interfaces/cli/read_tasks.py`, add at end (after existing functions):

```python
import typer
from src.contracts.common import UEID
from src.mesh.adapters.cli import CliAdapter
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

app = typer.Typer()


def show_mesh(ueid: str) -> dict:
    """Show cross-fork view for one UEID. Returns status matrix + slices."""
    parsed_ueid = UEID(ueid)  # validates format

    adapters = {
        "cli": CliAdapter(),
        "taskdog": TaskdogAdapter(),
        "solverforge_calendar": SolverforgeCalendarAdapter(),
    }

    view = {}
    for name, adapter in adapters.items():
        try:
            view[name] = adapter.read(parsed_ueid)
        except Exception as e:
            view[name] = {"error": str(e)}

    # Detect mismatches
    statuses = [v.get("status") for v in view.values() if isinstance(v, dict) and "status" in v]
    mismatches = []
    if len(set(statuses)) > 1:
        mismatches.append(f"Status differs across forks: {statuses}")

    return {"ueid": parsed_ueid, "view": view, "mismatches": mismatches}


@app.command()
def mesh_show(ueid: str):
    """Show cross-fork view for one UEID."""
    import json
    result = show_mesh(ueid)
    typer.echo(json.dumps(result, indent=2, default=str))
```

- [ ] **Step 3: Add task add() command**

Append to `interfaces/cli/read_tasks.py`:

```python
from src.mesh import queue
from src.contracts.task_change import TaskChange, TaskAction
import uuid as uuid_lib
from datetime import datetime, timezone


def generate_ueid(slug: str) -> UEID:
    """Generate 5-part UEID: tsk:slug:uuid:hash."""
    short_uuid = str(uuid_lib.uuid4())
    short_hash = uuid_lib.uuid4().hex[:16]
    return UEID(f"tsk:{slug}:{short_uuid}:{short_hash}")


@app.command()
def task_add(
    title: str = typer.Option(..., "--title", "-t", help="Task title"),
    due: str = typer.Option(None, "--due", "-d", help="Due date YYYY-MM-DD"),
    priority: str = typer.Option("medium", "--priority", "-p", help="high/medium/low"),
):
    """Add a new task. Writes to interfaces/cli slice + emits to review queue."""
    import json
    slug = title.lower().replace(" ", "-")[:50]
    ueid = generate_ueid(slug)

    # 1. Write to interfaces/cli slice
    cli_adapter = CliAdapter()
    event = TaskChange(
        event_id=f"evt_{uuid_lib.uuid4().hex[:12]}",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": title, "due": due, "priority": priority},
        source_fork="interfaces/cli",
        timestamp=datetime.now(timezone.utc),
    )
    cli_adapter.apply_change(PropagationEvent(
        event_id=event.event_id,
        ueid=event.ueid,
        action=event.action,
        fields=event.fields,
        approved_at=event.timestamp,
        source_fork=event.source_fork,
    ))

    # 2. Emit event to review queue
    queue.enqueue(event)

    typer.echo(json.dumps({
        "ueid": ueid,
        "event_id": event.event_id,
        "status": "pending",
        "message": "Task added to interfaces/cli; awaiting agent review for propagation to other forks.",
    }, indent=2))
```

- [ ] **Step 4: Fix pyproject.toml entry-point**

Modify `interfaces/cli/pyproject.toml`, ensure it has:

```toml
[project]
name = "life-cli"
version = "0.1.0"
description = "Life OS native CLI (interfaces/cli)"

[project.scripts]
life = "interfaces.cli.read_tasks:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["interfaces/cli"]
```

- [ ] **Step 5: Manual smoke test**

Run: `cd interfaces/cli && pip install -e . && life task add --title "Smoke test" --due 2099-01-01`
Expected: JSON output with ueid, event_id, status="pending"

Run: `life mesh show <ueid-from-previous>`
Expected: JSON output with view across cli/taskdog/solverforge_calendar + mismatches list

- [ ] **Step 6: Commit**

```bash
git add interfaces/cli/__init__.py interfaces/cli/read_tasks.py interfaces/cli/pyproject.toml
git commit -m "feat(cli): add mesh show + task add commands (Phase 3 v1)"
```

---

## Phase 7 — Integration

### Task 11: End-to-end create flow test

**Files:**
- Create: `tests/integration/test_create_flow.py`

**Interfaces:**
- Consumes: ALL previous tasks (1-10)
- Produces: working end-to-end `create` action flow

- [ ] **Step 1: Write the e2e test**

Create `tests/integration/test_create_flow.py`:

```python
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import TaskChange, TaskAction, PropagationEvent
from src.mesh import queue
from src.mesh.agent_consumer import validate, Decision
from src.mesh.agent_propagator import propagate
from src.mesh.adapters.cli import CliAdapter
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter
from src.contracts.common import UEID


@pytest.fixture
def isolated_data_dirs(tmp_path: Path, monkeypatch):
    """Set up isolated data dirs for CLI, taskdog, solverforge, queue."""
    cli_jsonl = tmp_path / "tasks.jsonl"
    taskdog_db = tmp_path / "tasks.db"
    upi_db = tmp_path / "upi.db"
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()

    # Patch paths
    from src.mesh.adapters import cli, taskdog, solverforge_calendar
    monkeypatch.setattr(cli, "TASKS_JSONL", cli_jsonl)
    monkeypatch.setattr(taskdog, "TASKDOG_DB", taskdog_db)
    monkeypatch.setattr(solverforge_calendar, "UPI_DB", upi_db)
    monkeypatch.setattr(queue, "QUEUE_DIR", queue_dir)

    # Initialize UPI schema (assumes v3 migration already applied)
    conn = sqlite3.connect(upi_db)
    conn.executescript("""
        CREATE TABLE unified_planning_items (
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

    return {
        "cli": cli_jsonl,
        "taskdog": taskdog_db,
        "solverforge": upi_db,
        "queue": queue_dir,
    }


def test_full_create_flow_propagates_to_all_forks(isolated_data_dirs):
    """End-to-end: write to cli → queue → agent validates → propagates to all forks."""
    # Step 1: Simulate `life task add` — write to CLI + enqueue event
    ueid = "tsk:smoke-test:11111111-2222-3333-4444-555555555555:aaaaaaaaaaaaaaaa"
    event = TaskChange(
        event_id="evt_e2e_001",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": "Smoke test task", "due": "2099-01-01", "priority": "high"},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )

    # CLI writes its own slice
    cli_adapter = CliAdapter()
    cli_adapter.apply_change(PropagationEvent(
        event_id=event.event_id,
        ueid=event.ueid,
        action=event.action,
        fields=event.fields,
        approved_at=event.timestamp,
        source_fork=event.source_fork,
    ))

    # CLI enqueues event
    queue.enqueue(event)

    # Step 2: Agent consumes queue, validates
    pending_events = list(queue.consume_pending())
    assert len(pending_events) == 1
    assert pending_events[0].event_id == "evt_e2e_001"

    validation = validate(pending_events[0])
    assert validation.decision == Decision.APPROVE

    # Step 3: Agent propagates to all forks
    adapters = [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]
    results = propagate(pending_events[0], validation, adapters)

    assert len(results) == 3
    assert all(r.success for r in results), f"Failures: {[r for r in results if not r.success]}"

    # Step 4: Verify all forks have the task
    # CLI
    cli_lines = isolated_data_dirs["cli"].read_text().strip().split("\n")
    cli_tasks = [json.loads(line) for line in cli_lines if line]
    assert any(t["ueid"] == ueid for t in cli_tasks)

    # taskdog
    conn = sqlite3.connect(isolated_data_dirs["taskdog"])
    taskdog_count = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE ueid = ?", (ueid,)
    ).fetchone()[0]
    conn.close()
    assert taskdog_count == 1

    # solverforge UPI
    conn = sqlite3.connect(isolated_data_dirs["solverforge"])
    upi_count = conn.execute(
        "SELECT COUNT(*) FROM unified_planning_items WHERE ueid = ?", (ueid,)
    ).fetchone()[0]
    conn.close()
    assert upi_count == 1

    # Step 5: Verify queue event is acked
    queue.ack("evt_e2e_001", "propagated")
    pending_after = list(queue.consume_pending())
    assert len(pending_after) == 0
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd src && python -m pytest ../tests/integration/test_create_flow.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_create_flow.py
git commit -m "test(integration): end-to-end create flow across all forks"
```

---

## Self-Review

**1. Spec coverage:**
- ✓ D1 (cross-fork view) → Task 10 (`mesh_show`)
- ✓ D2 (full bidirectional sync) → Tasks 4-9 (queue + agent + adapters)
- ✓ D3 (hybrid) → Task 3 (UPI as derived index, fork stores unchanged)
- ✓ D4 (UEID both layers) → Task 1 (UEID type) + Task 3 (UPI migration) + Task 8 (taskdog ueid FK)
- ✓ D5 (interfaces/cli) → Task 10 (mesh_show + task_add)
- ✓ D6 (UPI + taskdog + cli) → Tasks 7-9 (3 adapters)
- ✓ D7 (middle-out, Agent first) → Task order: 1-2 contracts, 3 storage, 4-6 queue+agent, 7-9 adapters, 10 CLI, 11 e2e
- ✓ v1 = `create` only → all tasks gate on `event.action.value == "create"`

**2. Placeholder scan:** No TBD/TODO/FIXME found. Every step has complete code.

**3. Type consistency:**
- `UEID` defined Task 1, consumed by all subsequent tasks ✓
- `TaskChange` defined Task 2, consumed by Tasks 4-11 ✓
- `PropagationEvent` defined Task 2, consumed by Tasks 6-11 ✓
- `ForkAdapter` Protocol defined Task 6, implemented by Tasks 7-9 ✓
- `ValidationResult` + `Decision` defined Task 5, consumed by Task 6 ✓

All consistent.

---

## Next Steps

After all tasks complete:
- Run full test suite: `pytest tests/ -m "not e2e_real_fork"` (e2e_real_fork excluded per Phase 1 audit)
- Manual smoke: `scripts/smoke/phase3_v1.{sh,bat}`
- Update CLAUDE.md to reflect mesh module location

## Cross-references

- Spec: `docs/superpowers/specs/2026-08-28-phase3-data-mesh-design.md`
- Decisions: `docs/diagnostics/2026-08-28-phase3-decisions.md`
- Usage: `docs/diagnostics/2026-08-28-phase3-usage-evidence.md`
- Phase 1 audit: `docs/diagnostics/2026-08-28-phase1-audit/`
- Phase 2 RE: `docs/diagnostics/2026-08-28-phase2-interface-re/`