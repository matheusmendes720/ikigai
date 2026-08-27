# Data-Mesh Architecture for life-ops

**Date:** 2026-08-25
**Status:** Design approved (4/4 sections)
**Author:** brainstorm session with user

---

## 1. Context

`life-ops` orchestrates personal productivity across 8 apps (ikigai, operational, taskdog, calcure, tuiboard, vault-tasks, journalot, questionary, tui-journal) that today have **no shared data model**. Each app has its own schema, storage, and concept of truth.

The goal is to enable a **conversational planning agent** (Claude Code MCP) to read and write across all apps through a unified contract layer — without forcing any app to migrate.

### Constraints

- **Cross-language:** Python (ikigai, operational, taskdog), Rust (vault-tasks, rifact), TypeScript/Bun (tuiboard)
- **HITL mandatory** for all writes (agent suggests, user confirms)
- **Append-only event log** as source of truth (CQRS-lite)
- **Per-app projections** (each app keeps its own storage, syncs from event log)

---

## 2. Architecture (Section 1)

### Directory Layout

```
life-ops/data-contracts/          # uv workspace member
├── schemas/
│   ├── common/                   # ueid, enums, timestamp
│   │   ├── ueid.schema.json
│   │   ├── enums.schema.json
│   │   └── timestamp.schema.json
│   ├── plan/                     # plan-base + 6 specialized
│   │   ├── plan-base.schema.json
│   │   ├── plan-task.schema.json
│   │   ├── plan-project.schema.json
│   │   ├── plan-objective.schema.json
│   │   ├── plan-goal.schema.json
│   │   ├── plan-dream.schema.json
│   │   └── plan-deliverable.schema.json
│   ├── event-log/                # envelope + payload union
│   │   ├── event.schema.json
│   │   ├── event-types.schema.json
│   │   └── payloads/
│   │       ├── plan-task-created.schema.json
│   │       ├── plan-task-updated.schema.json
│   │       ├── plan-task-status-changed.schema.json
│   │       └── plan-task-deleted.schema.json
│   └── README.md
├── tests/
│   ├── plan/                     # per-entity schema tests
│   ├── event-log/                # envelope + payload tests
│   └── conformance/              # per-app projection tests
├── examples/                     # golden examples (fixtures)
├── event-log/                    # append-only JSONL storage
│   ├── current/
│   │   └── events-YYYY-MM-DD.jsonl
│   ├── snapshots/
│   └── .rotation-policy
├── src/data_contracts/           # Python helpers (validation, projection)
└── pyproject.toml
```

### Cross-App Projection Flow

```
ikigai-mcp (canonical writer)
  → emit PlanTaskCreated event
  → event_log.append()
  → data-contracts/event-log/current/events-2026-08-25.jsonl
  → poll/subscribe
  → taskdog-mcp / calcure / operational / vault-tasks (projections)
```

### Cross-Language Validation Tooling

| Language | Validator | Usage |
|----------|-----------|-------|
| Python | `jsonschema` + `referencing.Registry` | Test-time validation |
| Python | `Pydantic v2` (re-generate from schema) | Runtime type-safe IO |
| Rust | `schemars` (derive JSON Schema) | Validate serde_json |
| TypeScript/Bun | `json-schema-to-ts` + `ajv` | Compile-time types |

---

## 3. Canonical Entities

### Plan Hierarchy (IKIGAi as canonical writer)

| Level | entity_type | UEID prefix | Horizon |
|-------|-------------|-------------|---------|
| 1 | `dream` | `ikigai:dream:` | 3650 days |
| 2 | `goal` | `ikigai:goal:` | 1095 days |
| 3 | `objective` | `ikigai:objective:` | 365 days |
| 4 | `project` | `ikigai:project:` | 90 days |
| 5 | `task` | `ikigai:task:` | 1-7 days |
| 6 | `deliverable` | `ikigai:deliverable:` | 1 day |

### Other Canonical Entities (Future)

| Entity | Canonical App | UEID prefix |
|--------|---------------|-------------|
| Daily allocation | taskdog | `taskdog:allocation:` |
| Calendar event | calcure | `calcure:event:` |
| Habit | operational | `operational:habit:` |
| Pomodoro session | operational | `operational:pomodoro:` |
| Sleep/Energy/Mood | operational | `operational:metric:` |
| Journal entry | journalot | `journalot:entry:` |

---

## 4. Plan Base Schema (Section 2)

### `plan/plan-base.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://life-ops.local/schemas/plan/plan-base/v1.json",
  "title": "PlanEntityBase",
  "type": "object",
  "required": ["ueid", "entity_type", "title", "status", "created_at", "updated_at"],
  "properties": {
    "ueid": { "$ref": "../common/ueid.schema.json" },
    "entity_type": { "$ref": "../common/enums.schema.json#/definitions/EntityType" },
    "title": { "type": "string", "minLength": 1, "maxLength": 200 },
    "parent_ueid": { "$ref": "../common/ueid.schema.json" },
    "status": { "$ref": "../common/enums.schema.json#/definitions/StatusType" },
    "phase_at_creation": { "$ref": "../common/enums.schema.json#/definitions/Phase" },
    "horizon_days": { "type": "integer", "minimum": 1, "maximum": 3650 },
    "ikigai_vectors": { "$ref": "./ikigai-vectors.schema.json" },
    "vector_weights_snapshot": {
      "type": "object",
      "additionalProperties": { "type": "number", "minimum": 0.0, "maximum": 1.5 }
    },
    "tags": {
      "type": "array",
      "items": { "type": "string", "minLength": 1, "maxLength": 50, "pattern": "^[a-z0-9-]+$" },
      "maxItems": 20,
      "uniqueItems": true
    },
    "source": { "$ref": "../common/enums.schema.json#/definitions/SourceType" },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" }
  },
  "additionalProperties": false
}
```

### `plan/plan-task.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://life-ops.local/schemas/plan/plan-task/v1.json",
  "title": "TaskEntity",
  "allOf": [
    { "$ref": "./plan-base.schema.json" },
    {
      "type": "object",
      "required": ["entity_type", "priority", "rice_reach", "rice_impact", "rice_confidence", "rice_effort_h"],
      "properties": {
        "entity_type": { "const": "task" },
        "horizon_days": { "enum": [1, 2, 3, 4, 5, 6, 7] },
        "priority": { "$ref": "../common/enums.schema.json#/definitions/TaskPriority" },
        "rice_reach": { "type": "number", "minimum": 1, "maximum": 10 },
        "rice_impact": { "type": "number", "enum": [0.25, 0.5, 1.0, 2.0, 3.0] },
        "rice_confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "rice_effort_h": { "type": "number", "minimum": 0.5 },
        "due_date": { "type": ["string", "null"], "format": "date" },
        "tw_uuid": { "type": ["string", "null"] }
      },
      "additionalProperties": false
    }
  ]
}
```

### Status FSM (16 IKIGAi ↔ 4 taskdog ↔ 4 calcure ↔ N operational)

| IKIGAi | taskdog | calcure | operational |
|--------|---------|---------|-------------|
| seed | PENDING | NORMAL | pending |
| draft | PENDING | NORMAL | pending |
| planned | PENDING | NORMAL | pending |
| active | IN_PROGRESS | NORMAL | in_progress |
| in_progress | IN_PROGRESS | NORMAL | in_progress |
| blocked | PENDING (+note) | IMPORTANT | blocked |
| paused | PENDING | NORMAL | paused |
| done | COMPLETED | DONE | done |
| completed | COMPLETED | DONE | done |
| fulfilled | COMPLETED | DONE | done |
| achieved | COMPLETED | DONE | done |
| mastered | COMPLETED | DONE | done |
| cancelled | CANCELED | UNIMPORTANT | cancelled |
| abandoned | CANCELED | UNIMPORTANT | abandoned |
| archived | CANCELED | UNIMPORTANT | archived |

---

## 5. Event Log Envelope (Section 3)

### `event-log/event.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://life-ops.local/schemas/event-log/event/v1.json",
  "title": "LifeOpsEvent",
  "type": "object",
  "required": ["event_id", "envelope_version", "event_type", "occurred_at", "source_app", "actor", "schema_version", "payload"],
  "properties": {
    "event_id": { "type": "string", "format": "uuid", "description": "UUIDv7 (timestamp-ordered)" },
    "envelope_version": { "const": "1.0" },
    "event_type": { "type": "string", "pattern": "^[A-Z][a-zA-Z]+(?:[A-Z][a-zA-Z]+)*$" },
    "occurred_at": { "type": "string", "format": "date-time" },
    "recorded_at": { "type": "string", "format": "date-time" },
    "source_app": {
      "type": "string",
      "enum": ["ikigai-mcp", "operational-mcp", "taskdog-mcp", "calcure-mcp", "vault-tasks-mcp", "tuiboard-mcp", "planner-agent", "user", "system"]
    },
    "actor": {
      "type": "object",
      "required": ["type", "id"],
      "properties": {
        "type": { "enum": ["user", "agent", "system", "import"] },
        "id": { "type": "string" }
      }
    },
    "correlation_id": { "type": ["string", "null"], "format": "uuid" },
    "causation_id": { "type": ["string", "null"], "format": "uuid" },
    "schema_version": { "type": "integer", "minimum": 1 },
    "payload": { "description": "Discriminated union (see event-types.schema.json)" }
  },
  "additionalProperties": false
}
```

### `event-log/event-types.schema.json` (discriminated union via `oneOf`)

```json
{
  "$id": "https://life-ops.local/schemas/event-log/event-types/v1.json",
  "oneOf": [
    {
      "type": "object",
      "required": ["event_type", "payload"],
      "properties": {
        "event_type": { "const": "PlanTaskCreated" },
        "payload": { "$ref": "./payloads/plan-task-created.schema.json" }
      }
    },
    {
      "type": "object",
      "required": ["event_type", "payload"],
      "properties": {
        "event_type": { "const": "PlanTaskUpdated" },
        "payload": { "$ref": "./payloads/plan-task-updated.schema.json" }
      }
    },
    {
      "type": "object",
      "required": ["event_type", "payload"],
      "properties": {
        "event_type": { "const": "PlanTaskStatusChanged" },
        "payload": { "$ref": "./payloads/plan-task-status-changed.schema.json" }
      }
    },
    {
      "type": "object",
      "required": ["event_type", "payload"],
      "properties": {
        "event_type": { "const": "PlanTaskDeleted" },
        "payload": { "$ref": "./payloads/plan-task-deleted.schema.json" }
      }
    }
  ]
}
```

### Payload Schemas

#### `payloads/plan-task-created.schema.json` (full snapshot)

```json
{
  "$id": "https://life-ops.local/schemas/event-log/payloads/plan-task-created/v1.json",
  "type": "object",
  "required": ["task"],
  "properties": {
    "task": { "$ref": "../../plan/plan-task/v1.json" }
  },
  "additionalProperties": false
}
```

#### `payloads/plan-task-status-changed.schema.json` (delta)

```json
{
  "$id": "https://life-ops.local/schemas/event-log/payloads/plan-task-status-changed/v1.json",
  "type": "object",
  "required": ["ueid", "from_status", "to_status", "transition_reason"],
  "properties": {
    "ueid": { "$ref": "../../common/ueid.schema.json" },
    "from_status": { "$ref": "../../common/enums.schema.json#/definitions/StatusType" },
    "to_status": { "$ref": "../../common/enums.schema.json#/definitions/StatusType" },
    "transition_reason": { "type": "string", "maxLength": 500 }
  },
  "additionalProperties": false
}
```

### Storage Layout

```
data-contracts/event-log/
├── current/
│   └── events-YYYY-MM-DD.jsonl     # append-only, daily rotation
├── snapshots/
│   └── snapshot-YYYY-MM-DD.jsonl   # periodic full-state snapshots (for fast rebuild)
└── .rotation-policy                # daily at 00:00 UTC, keep 30 days hot, archive cold
```

### Conflict Resolution: Last-Write-Wins with Version Vector

Each entity tracks a version vector per source app:

```json
{
  "ueid": "ikigai:task:write-proposal:a1b2c3d4:e5f6g7h8",
  "version_vector": { "ikigai-mcp": 42, "taskdog-mcp": 7, "user": 1 },
  "last_write": {
    "app": "ikigai-mcp",
    "actor": "user:mathe",
    "event_id": "0192c5e8-7b3a-7def-9012-3456789abcde",
    "timestamp": "2026-08-25T10:30:00Z"
  }
}
```

**Tie-breaker rule:** if `timestamp` collides, compare `event_id` (UUIDv7 is timestamp-ordered, so later event wins).

---

## 6. Per-App Projection Conformance (Section 4)

### Subscription Matrix

| Event Type | IKIGAi | Taskdog | Calcure | Operational | Vault-tasks | Tuiboard |
|---|---|---|---|---|---|---|
| **PlanTaskCreated** | W | R | R | R | R | R |
| **PlanTaskUpdated** | W | R | R | R | R | R |
| **PlanTaskStatusChanged** | W | R | R | R | R | R |
| **PlanTaskDeleted** | W | R | R | R | R | R |
| **PlanProjectCreated** | W | ✗ | ✗ | R | R | R |
| **PlanGoalCreated** | W | ✗ | ✗ | R | R | � |

W = canonical writer; R = subscriber; ✗ = ignore

### Per-App Projection Behavior

| App | Storage | Projection |
|-----|---------|------------|
| IKIGAi | markdown + SQLite | writes to `plan_entities`, emits events |
| Taskdog | SQLite (flat) | maps PlanTask → Task with status enum translation |
| Calcure | CSV | appends row with `{item_id: hash(ueid), name: title, status: NORMAL/DONE, date}` |
| Operational | SQLite (JSON blobs) | aggregates into `DailyLog.tasks_pending`, derives metrics |
| Vault-tasks | markdown files | writes checkable `- [ ]` items |
| Tuiboard | markdown | creates kanban card, moves across columns on status change |

### Test Suite Structure

```
tests/conformance/
├── __init__.py
├── conftest.py                        # shared fixtures
├── _helpers/
│   ├── projection_runner.py           # test consumer of event log
│   ├── event_factory.py                # builds valid events
│   └── invariant_checker.py            # asserts invariants after projection
├── test_ikigai_canonical.py           # IKIGAi as canonical writer
├── test_taskdog_projection.py          # IKIGAi event → Taskdog Task
├── test_calcure_projection.py          # IKIGAi event → Calcure CSV row
├── test_operational_projection.py     # IKIGAi event → DailyLog
├── test_vault_tasks_projection.py     # IKIGAi event → markdown
├── test_round_trip.py                  # IKIGAi → Taskdog → IKIGAi (no info loss)
└── test_conflict_resolution.py         # LWW semantics
```

### Key Test Patterns

1. **Single-app projection:** emit `PlanTaskCreated`, run projection, assert target app state matches expected.
2. **Status mapping:** for every IKIGAi status, assert taskdog/calcure/operational mapping is correct.
3. **Round-trip:** IKIGAi → Taskdog (status change) → IKIGAi; assert shared fields preserved, status translated correctly.
4. **Conflict resolution:** concurrent edits → LWW picks later timestamp; identical timestamp → event_id breaks tie.

### Example: `test_taskdog_projection.py`

```python
def test_plan_task_created_projects_to_taskdog_task(repo):
    event = make_plan_task_created(
        ueid="ikigai:task:write-proposal:a1b2c3d4:e5f6g7h8",
        title="Write proposal",
        status="active",
        priority="HIGH",
        rice_effort_h=4.0,
        tags=["writing", "q3-goal"]
    )

    runner = ProjectionRunner(subscribers=[TaskdogProjection(repo)])
    runner.consume(event)

    task = repo.get_by_ueid(event.payload.task.ueid)
    assert task.name == "Write proposal"
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.priority == 1
    assert task.estimated_duration == 4.0
    assert task.tags == ["writing", "q3-goal"]

def test_round_trip_ikigai_taskdog_ikigai(repo, ikigai_store):
    # IKIGAi writes original
    original = make_plan_task_created(title="Write proposal", status="active", priority="HIGH")
    ikigai_store.apply(original)

    # Taskdog projection receives event
    ProjectionRunner(subscribers=[TaskdogProjection(repo)]).consume(original)

    # User marks task complete in Taskdog
    task = repo.get_by_ueid(original.payload.task.ueid)
    task.mark_completed()
    repo.update(task)

    # Taskdog emits back to IKIGAi
    back_event = make_taskdog_task_status_changed(
        ueid=original.payload.task.ueid,
        from_status="IN_PROGRESS",
        to_status="COMPLETED",
        actor="user:mathe"
    )
    ikigai_store.apply(back_event)

    # IKIGAi state updated without losing shared fields
    final = ikigai_store.get(original.payload.task.ueid)
    assert final.title == "Write proposal"
    assert final.priority == "HIGH"
    assert final.status == "completed"
```

### Example: `test_conflict_resolution.py`

```python
def test_concurrent_edits_resolved_by_lww():
    base_event = make_plan_task_created(ueid="...", title="Original")
    edit_a = make_plan_task_updated(delta={"title": "Edit from A"}, timestamp=ts_100)
    edit_b = make_plan_task_updated(delta={"title": "Edit from B"}, timestamp=ts_101)

    store = EventLogStore()
    store.append(base_event)
    store.append(edit_a)
    store.append(edit_b)

    final = IkigaiProjection(store).rebuild_state(ueid="...")
    assert final.title == "Edit from B"  # LWW: later timestamp wins

def test_identical_timestamps_resolved_by_event_id():
    ts = datetime(2026, 8, 25, 10, 0, 0)
    edit_a = make_plan_task_updated(delta={"title": "A"}, timestamp=ts, event_id="0192...")
    edit_b = make_plan_task_updated(delta={"title": "B"}, timestamp=ts, event_id="0193...")

    final = rebuild_state(...)
    assert final.title == "B"  # higher event_id (UUIDv7) wins
```

---

## 7. Design Decisions (Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Schema format | JSON Schema 2020-12 puro | Cross-language consistent validation |
| Conflict resolution | Last-write-wins + version vector | Simple, predictable, auditable |
| Versioning | JSON Schema `$id` versioning (v1, v2, ...) | URI-based, explicit, no migration code needed |
| Event envelope | Single envelope, polymorphic payload | One schema to evolve, one validator to maintain |
| Discriminator | `oneOf` over `event_type` field | Standard JSON Schema pattern |
| Storage | JSONL append-only + periodic snapshots | Trivial to append, easy to replay, fast to rebuild |
| Status mapping | IKIGAi as canonical FSM (16 states) | Matches existing IKIGAi Pydantic model |
| Persistence per app | Unchanged — apps keep their own storage | No migration required; only adds projection layer |
| Entity IDs | UEID (Universal Entity Identifier) format `app:type:slug:hash8:rand8` | Globally unique, sortable, app-namespaced |
| Time format | ISO 8601 UTC (`Z` suffix) | Universal, sortable as string |
| UUIDs | UUIDv7 for event_ids | Timestamp-ordered, no central coordinator |

---

## 8. Open Questions (Future Specs)

These are intentionally **out of scope** for this spec; flagged for follow-up:

1. **Snapshot strategy** — when to snapshot, how to detect corruption, rebuild from snapshot+log.
2. **Retention policy** — when to archive cold events, GDPR/right-to-delete semantics.
3. **Real-time sync** — WebSocket / file-watcher / polling interval for projections.
4. **Multi-user support** — current design assumes single user (`user:mathe`).
5. **Encryption at rest** — current event log is plaintext JSONL.
6. **Performance benchmarks** — projection throughput, snapshot rebuild time.
7. **MCP tool surface** — what `ikigai-mcp` tools look like (separate spec).
8. **HITL UX** — confirmation flow design (separate spec).

---

## 9. Acceptance Criteria

This spec is "done" when:

- [ ] `data-contracts/pyproject.toml` exists and is part of the uv workspace
- [ ] All JSON Schema files validated by `check-jsonschema` (CI gate)
- [ ] `tests/plan/` covers all 6 plan entities with at least 3 cases each (valid, invalid, boundary)
- [ ] `tests/event-log/` covers envelope + 4 payload types
- [ ] `tests/conformance/` covers all 6 subscriber apps with at least 1 projection test each
- [ ] `tests/conformance/test_round_trip.py` passes (IKIGAi → Taskdog → IKIGAi)
- [ ] `tests/conformance/test_conflict_resolution.py` passes (LWW semantics)
- [ ] At least 5 golden examples in `examples/` for fixture re-use
- [ ] Documented cross-language validation in `schemas/README.md`
- [ ] TDD order: write failing test → write schema → see test pass

---

## 10. Out of Scope (Deferred)

- **Deep-agents supervisor architecture** — separate spec (after data-contracts stabilizes)
- **MCP server implementation** (`ikigai-mcp`, `operational-mcp`) — separate specs
- **LangGraph planner wiring** — separate spec
- **HITL confirmation flow** — separate spec
- **Real-time sync protocol** — separate spec

These will be brainstormed as follow-up sessions once the data contract foundation is in place and conformance tests pass.

---

## 11. References

- IKIGAi `PlanEntity` Pydantic model: `ikigai/src/ikigai/entities/plan/`
- taskdog Task model: `taskdog-core/src/taskdog_core/domain/entities/task.py`
- calcure CSV format: `calcure/calcure/data/tasks.csv`
- operational DailyLog: `operational/operational_core/entities/daily_log.py`
- Brainstorming skill: `~/.claude/plugins/cache/superpowers-dev/superpowers/6.0.2/skills/brainstorming/`
