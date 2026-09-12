# Review L3 — Data Mesh Cross-Fork Sync Layer

**Task:** T-11.4 (M11 IKIGAI Agentic System Top-Down Review)
**Branch:** master
**Date:** 2026-09-12
**Scope:** `src/mesh/` (read-only inspection)

---

## Summary

| Check | Result |
|------|--------|
| ForkAdapter Protocol methods | exactly 4 (`name`, `read`, `apply_change`, `supports_field`) + adapters add non-Protocol helpers |
| Create-only v1 scope | enforced in all 3 adapters (0 violations of `update`/`delete`/`done` action paths) |
| Review queue atomic write | YES — temp + fsync + rename, wrapped in retry decorator |
| Review queue directory | exists at `data/review_queue/` with 32+ JSON event files |
| PAE rule outcomes | APPROVE / REJECT / CLARIFY (3-validation gating in `agent_consumer.validate`) |
| Provisional gaps | 4 (see §6) |

---

## 1. File Inventory

### `src/mesh/` — review-queue + agent-consumer/propagator + CLI surfaces (1 581 LOC, 9 files)

| File | LOC | Role |
|------|-----|------|
| `__init__.py` | 1 | Module marker |
| `queue.py` | 125 | Filesystem append-only review queue (atomic temp+rename) |
| `agent_consumer.py` | 78 | Deep Agent validation (APPROVE/REJECT/CLARIFY) |
| `agent_propagator.py` | 101 | Emit PropagationEvents to all adapters + optional vault_write |
| `review_queue_worker.py` | 302 | Drains queue (run_once + daemon via pidfile) |
| `review_queue_cli.py` | 291 | Read-only CLI (list/status/show) |
| `mesh_cli.py` | 202 | `life mesh show <ueid>` (cross-fork join) |
| `cli_cli.py` | 273 | CLI fork-side adapter (enqueue side) |
| `taskdog_cli.py` | 275 | taskdog fork-side CLI (enqueue side) |
| `investigation_queue.py` | 204 | Plan C investigation queue (parallel to `queue.py`) |

### `src/mesh/adapters/` — 3 fork adapters + Protocol + a2ui schema (376 LOC, 5 files)

| File | LOC | Role |
|------|-----|------|
| `__init__.py` | 23 | Re-exports `ForkAdapter`, `CliAdapter`, `TaskdogAdapter`, `SolverforgeCalendarAdapter` |
| `base.py` | 25 | `ForkAdapter` Protocol (`@runtime_checkable`) |
| `cli.py` | 71 | `CliAdapter` — `data/tasks.jsonl` slice |
| `taskdog.py` | 129 | `TaskdogAdapter` — `data/taskdog/tasks.db` SQLite |
| `solverforge_calendar.py` | 141 | `SolverforgeCalendarAdapter` — UPI SQLite |
| `a2ui_schema.py` | 131 | A2UI JSON-schema helpers (orthogonal to fork sync) |

**Note:** `a2ui_schema.py` is in the adapters dir for namespace proximity but is NOT a `ForkAdapter`; it is consumed by other mesh code paths.

---

## 2. ForkAdapter Protocol Verification

**File:** `src/mesh/adapters/base.py` (25 lines, full file)

```python
@runtime_checkable
class ForkAdapter(Protocol):
    """Every fork adapter implements read() + apply_change() + supports_field()."""
    name: str
    def read(self, ueid: UEID) -> dict[str, Any] | None: ...
    def apply_change(self, event: PropagationEvent) -> None: ...
    def supports_field(self, field_name: str) -> bool: ...
```

**Exactly 4 members.** All 3 adapters implement the full set:

| Adapter | name | read | apply_change | supports_field | non-Protocol extras |
|---------|------|------|--------------|----------------|---------------------|
| `CliAdapter` | `"cli"` | yes | yes | yes | (none) |
| `TaskdogAdapter` | `"taskdog"` | yes | yes | yes | `list_all()` (enumeration helper) |
| `SolverforgeCalendarAdapter` | `"solverforge_calendar"` | yes | yes | yes | `list_all()` (enumeration helper) |

The `@runtime_checkable` decorator allows `isinstance(adp, ForkAdapter)` checks; non-Protocol methods (`list_all`) are pure helpers and do not affect Protocol conformance. **`mesh_cli.py` and `review_queue_worker.py` rely on Protocol conformance** (`for adapter in adapters: adapter.apply_change(...)`).

---

## 3. Create-Only v1 Scope Enforcement

The `TaskAction` enum (`src/contracts/task_change.py:17-23`) defines 4 values:
```python
class TaskAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    DONE = "done"
```

**All 3 adapters enforce create-only via identical guard pattern:**

| Adapter | File:line | Guard |
|---------|-----------|-------|
| `CliAdapter` | `cli.py:34-35` | `if event.action.value != "create": return  # v1 only supports create` |
| `TaskdogAdapter` | `taskdog.py:83-84` | `if event.action.value != "create": return  # v1 only supports create` |
| `SolverforgeCalendarAdapter` | `solverforge_calendar.py:58-59` | `if event.action.value != "create": return  # v1 only supports create` |

**Violations of create-only scope: 0.** All non-CREATE actions early-return before any side effect.

**Subtle observation (gap G-3 below):** `SolverforgeCalendarAdapter.apply_change` uses an internal `UPDATE unified_planning_items SET status='planned', ikigai=? WHERE ueid=?` to re-write the `ikigai` JSON column when the row already exists. This is **idempotency-driven re-write of an internal JSON blob, not a v1.2 UPDATE action pathway** — the guard above still fires for non-create `event.action` values. The agent layer is unchanged. But this is a semantic nuance worth flagging for the reviewer.

---

## 4. PAE Rules in `agent_consumer.py`

`validate(event) -> ValidationResult` returns one of `APPROVE` / `REJECT` / `CLARIFY`:

1. **Title plausibility** (CLARIFY): `not title` OR title in `VAGUE_TITLES = {"todo", "tbd", "fix", "work", "task", "stuff", "thing"}` OR `len(title.strip()) < 5` → CLARIFY
2. **Due date validity** (REJECT for create only): past date or malformed ISO → REJECT
3. **UEID collision** (REJECT): existing `propagated` event with same UEID + different title → REJECT (with try/except + logger.warning for missing queue module — fixes the silent-pass B5.0-F6 bug)

The **decision is applied** in `review_queue_worker.run_once()`:
- `APPROVE` → `propagate(event, validation, adapters)` then `queue.ack(event_id, "propagated")` (or `"partial_propagation"` if any adapter failed)
- `REJECT` → `queue.ack(event_id, "rejected")`
- `CLARIFY` → `queue.ack(event_id, "clarified")`

The 3 decisions are the only branches. **No "Done" decision exists** in the consumer — task-completion is a separate pathway that does not flow through the review queue (handled at the fork-store level by each adapter's `status` field in v1.2+).

---

## 5. Append-Only Review Queue Mechanism

**File:** `src/mesh/queue.py` (125 lines)

### Atomic write primitive (`_atomic_write_json`)

```python
@_retry_atomic_write
def _atomic_write_json(target: Path, content: str) -> None:
    """Write content to target via temp + fsync + rename. Idempotent retry wrapper."""
    tmp = target.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)
```

Mechanism: temp file → fsync → `os.replace()` (atomic on POSIX + Windows since Python 3.3).

**Append-only?** The queue is append-only in the **lifecycle sense** (events are added; never deleted from disk; status transitions are atomic rewrites of the same file). It does NOT use `O_APPEND` syscall mode — every write is a full temp+rename replace. This is a deliberate trade-off (status transitions require reading the whole event, not appending), and the atomic-rename pattern still guarantees no partial writes.

### Retry decorator (`_retry_atomic_write`)

4 attempts, exponential backoff (0.1s → 2s), jitter, retries on `(OSError, PermissionError)` — handles Windows EBUSY + NFS stale handles. Per audit B5.0-F13.

### Queue dir

```
data/review_queue/   ← exists, 32+ *.json files (one per TaskChange)
```

### `consume_pending()` safety

Skips malformed files (unreadable, unparseable JSON, schema-invalid) with `logger.warning(...)` — closes the silent-skip S112 finding.

### `_retry_atomic_write` is also used by `investigation_queue.py`

Same decorator pattern, same retry budget. The investigation queue's `transition()` rewrites the record in place (status mutation), which is explicitly allowed for the Investigation FSM but NOT for the TaskChange FSM.

### `agent_propagator.propagate()` writes the event back via `queue.ack()`

After propagation, the queue event is rewritten in place with `status="propagated"` (or `"partial_propagation"`). The 3 status values that get rewritten into the same file (`approved`, `propagated`, `partial_propagation`, `rejected`, `clarified`) are all terminal — the file never becomes "pending" again.

---

## 6. Provisional Gaps

| # | Gap | Severity | Notes |
|---|-----|----------|-------|
| G-1 | `review_queue_worker._build_adapters()` uses **bare-namespace** imports (`from mesh.adapters import ...`) while the rest of the worker uses `src.mesh` prefix. Inconsistent with the `sys_ikigai` rename guidance. | low | Will not break tests because `tests/conftest.py` adds `<repo>/` to sys.path, but it's a style drift. |
| G-2 | `agent_consumer.validate` falls back to **silent pass** when `src.mesh.queue` is unimportable (`except (ImportError, AttributeError)`). The retry-then-log helps, but the collision check is effectively optional. | medium | A wiring bug in production would let colliding UEIDs through. Drift invariant does not cover this. |
| G-3 | `SolverforgeCalendarAdapter.apply_change` does an internal `UPDATE` SQL on existing rows to refresh the `ikigai` JSON column. **Not** an UPDATE action pathway, but the semantic gap (re-writing status='planned' on every CREATE re-run) is worth noting for v1.2 design. | low | Comment at `solverforge_calendar.py:88-90` acknowledges this; not currently test-flagged. |
| G-4 | The investigation queue (`src/mesh/investigation_queue.py`) duplicates the `_retry_atomic_write` + `_atomic_write_json` boilerplate from `queue.py`. 30+ lines of near-identical code. | low | Refactor candidate: extract to a shared `src/mesh/_atomic.py` helper. Not blocking. |

---

## 7. Drift Net Coverage

| Drift test | Coverage |
|------------|----------|
| `test_canonical_scope.py` | Does not cover mesh create-only enforcement directly |
| `test_drift_invariants.py` | UEID 4-part regex + append-only invariants — covers `data/review_queue/` filesystem layout |
| `test_drift_extended_invariants.py` | cross_pollution + dual_module_identity — catches the `mesh.adapters` bare-namespace import in `review_queue_worker._build_adapters()` (G-1) |

**Net:** 1 of 4 provisional gaps (G-1) is already drift-covered. G-2 / G-3 / G-4 are uncovered by the existing net — recommend adding targeted tests in a follow-up wave.

---

## 8. Verdict

**L3 data mesh layer is in conformance with the v1 = create-only design.** All three adapters guard on `event.action.value != "create"`; the review queue uses atomic temp+rename; PAE rules gate approval with three deterministic checks; no rogue `update`/`delete`/`done` plumbing exists. The 4 provisional gaps are non-blocking and recommend targeted follow-up tests + one refactor (investigation-queue de-duplication).

---

## Files Referenced

- `src/mesh/adapters/base.py`
- `src/mesh/adapters/cli.py`
- `src/mesh/adapters/taskdog.py`
- `src/mesh/adapters/solverforge_calendar.py`
- `src/mesh/agent_consumer.py`
- `src/mesh/agent_propagator.py`
- `src/mesh/queue.py`
- `src/mesh/investigation_queue.py`
- `src/mesh/review_queue_worker.py`
- `src/mesh/review_queue_cli.py`
- `src/contracts/task_change.py`
- `data/review_queue/` (32+ JSON event files)