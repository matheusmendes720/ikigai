# Phase 3 Usage Evidence — Practical Day-to-Day Map

**Date:** 2026-08-28
**Phase:** 3 of `2026-08-28-backend-audit-data-mesh`
**Purpose:** Granularity analysis per interface, day-to-day scenarios, implications for architecture.
**Status:** INPUT to Phase 3 decision re-evaluation (user concern 2026-08-28: granularity gap).

---

## 5 daily-use scenarios

### Scenario 1 — Morning review (7-9 AM)
**User intent:** Plan the day. What's most important? What blocks time when?

**Interface flow:**
1. **solverforge-calendar** — opens calendar view. Sees day's events on time grid + "today's objective" summary. Time blocks visible.
2. **tuiboard** — opens kanban. Sees current column distribution (today / in-progress / done). What's queued for the day.
3. **taskdog** — checks dependencies between today's tasks. Expected outcomes for top 3 priorities.
4. **CLI** — runs `life tasks today --json` for terminal-based snapshot.

**Data needs:**
| Interface | Granularity | What they show |
|-----------|-------------|----------------|
| calendar | AGGREGATE | day summary, time blocks, event count, "today's objective" |
| tuiboard | OVERVIEW | column distribution, in-progress, board-level |
| taskdog | DETAIL (top 3) | dependencies, expected outcomes |
| CLI | FLEXIBLE | whatever user asks for |

### Scenario 2 — Mid-day execution (10 AM - 5 PM)
**User intent:** Work through tasks. Mark done. Adjust on the fly.

**Interface flow:**
1. **tuiboard** — drag card from "today" to "in progress". Edit card markdown inline (notes, checklists).
2. **taskdog** — when stuck, open full task detail. Checklist progress, dependencies, expected result, audit.
3. **calendar** — quick check on time blocks when interruption comes.
4. **CLI** — `life task done <id>` to mark done (writes feedback.jsonl).

**Data needs:**
| Interface | Granularity | What they show |
|-----------|-------------|----------------|
| tuiboard | LIVE (atomic-rename) | board state, markdown edits |
| taskdog | DETAIL | full task lifecycle, audit trail |
| calendar | PASSIVE | time-block awareness only |
| CLI | MINIMAL | done marks, feedback writes |

### Scenario 3 — Cross-tool sanity check (rare, 1-2x/week)
**User intent:** Why does this task look different in calendar vs tuiboard? What's canonical?

**Interface flow:**
1. **CLI** — runs `life mesh show <ueid>` (PHASE 3 deliverable).
2. Sees status matrix: UPI says `done at 14:30`; taskdog says `in progress`.
3. Identifies mismatch; decides whether to trigger reconciliation or accept lag.
4. (Operator-only tool; not user-facing daily.)

**Data needs:**
| Interface | Granularity | What they show |
|-----------|-------------|----------------|
| CLI mesh view | SUMMARY (per UEID) | status per fork, mismatch highlights, provenance |

### Scenario 4 — End-of-day reflection (6-7 PM)
**User intent:** What got done? What's tomorrow? Update vault.

**Interface flow:**
1. **CLI** — `life tasks done today` to see completed.
2. **taskdog** — audit log for the day (when was each task started/completed/paused?).
3. **vault** — Deep Agent or manual update to `vault/ikigai/closing-2026/Q3.md`.
4. **calendar** — review what events passed, plan tomorrow's blocks.

**Data needs:**
| Interface | Granularity | What they show |
|-----------|-------------|----------------|
| CLI | PER-TASK | done state, completion timestamps |
| taskdog | AUDIT | per-task event log |
| vault | HUMAN-WRITTEN | reflection (not data-synced) |
| calendar | SUMMARY | day-end rollup |

### Scenario 5 — Weekly review (Sunday)
**User intent:** How was the week? Patterns? Adjustments?

**Interface flow:**
1. **vault** — review weekly planning doc.
2. **Deep Agent** — analyzes vault + tasks.jsonl + UPI provenance.
3. **interfaces** — overview of week's state per fork.
4. **CLI** — `life tasks weekly` for aggregate.

**Data needs:**
| Interface | Granularity | What they show |
|-----------|-------------|----------------|
| vault | NARRATIVE | human-written weekly notes |
| Deep Agent | ANALYTIC | cross-source pattern detection |
| interfaces | SUMMARY | weekly rollup per fork |
| CLI | AGGREGATE | weekly aggregation |

---

## Granularity matrix (per interface × scenario)

| Interface | S1 (Morning) | S2 (Mid-day) | S3 (Cross-tool) | S4 (EOD) | S5 (Weekly) |
|-----------|--------------|--------------|------------------|----------|-------------|
| **calendar (solverforge)** | AGGREGATE day | PASSIVE time-block | (not used) | SUMMARY day-end | AGGREGATE week |
| **tuiboard** | OVERVIEW column | LIVE board state | (not used) | (passive) | (passive) |
| **taskdog** | DETAIL top-3 | DETAIL full | STATUS per fork | AUDIT per-task | (analytics) |
| **CLI** | FLEXIBLE | MINIMAL done | SUMMARY cross-fork | PER-TASK done | AGGREGATE week |
| **vault** | (passive) | (human writes) | (read-only) | HUMAN-WRITEN | NARRATIVE |
| **interfaces/tui** | (planned) | (planned) | (planned) | (planned) | (planned) |

---

## Insights from granularity analysis

### 1. Different forks = different granularities

| Fork | Granularity role | What it owns |
|------|------------------|--------------|
| **calendar** | AGGREGATE layer | events, time blocks, day summaries, recurrence |
| **tuiboard** | OVERVIEW layer | board state, columns, markdown round-trip, live kanban |
| **taskdog** | DETAIL layer | per-task fields, lifecycle, dependencies, audit, notes |
| **CLI** | FLEXIBLE operator tool | query-side only, joins across forks when needed |

### 2. No fork needs another fork's data for daily use

- calendar doesn't need taskdog's checklist or audit log
- tuiboard doesn't need taskdog's dependency graph
- taskdog doesn't need tuiboard's board position
- each fork's daily operation is INDEPENDENT

This means: **mesh is NOT in the daily execution path** — it sits beside, for diagnostic/operator use only.

### 3. PHASE 3 cross-fork view = operator tool (not user-facing rendering)

- Used rarely (1-2x/week for sanity check, more for debugging)
- Goal: "did the system get the right answer, even if user doesn't see the mesh?"
- The mesh doesn't replace fork rendering — interfaces still render from their own fork
- Cross-fork view is OBSERVABILITY, not USER EXPERIENCE

### 4. Granularity gap is REAL but doesn't invalidate decisions

| Concern | Resolution |
|---------|-----------|
| Different interfaces need different data | Adapters expose per-fork data; each interface renders its own slice |
| Calendar shows aggregates, taskdog shows detail | Mesh doesn't aggregate — it joins; aggregation is per-interface |
| Fork-internal ids differ (int/UUID/position) | UEID is row identity, not data; fork-internal id exposed separately |
| Update frequency differs (live vs daily) | Read-only mesh = always current (reads live); doesn't need freshness model |

### 5. What's MISSING from current architecture (v2 considerations)

| Missing concept | Why it matters | When to add |
|-----------------|----------------|-------------|
| Per-fork slice in Pydantic | Each adapter has different return shape; need common envelope | Phase 3 v1 (D5) |
| "What user sees" model | UX is interface-specific; mesh is opaque to user | NOT Phase 3 (separate UX design) |
| Data freshness contract | Some forks lag (UPI is derived); operators need staleness indicators | Phase 4+ if needed |
| Sync event schema (for v2 write path) | When forks write, what's the minimum event payload? | NOT Phase 3 (read-only) |
| Vault-feedback integration | `feedback.jsonl` from interfaces/cli → vault merge | NOT Phase 3 (orthogonal) |

---

## Implications for locked decisions

### D2 (read-only) — VALIDATED
"Read-only" applies to the **mesh view**, not the entire system. Each fork continues to write its own slice. Interfaces still render from their own fork. The mesh observes + joins. No conflict with user's granularity insight.

### D3 (hybrid architecture) — VALIDATED
Hybrid = each fork owns its slice + UPI is derived index. Calendar (UPI) shows aggregates; taskdog shows detail. The granularity difference is INTRINSIC to the architecture, not a problem.

### D5 (status matrix + slices) — VALIDATED with refinement
"Status matrix" = summary per fork (one row per fork: status, last_updated, fork_internalid).
"Slices" = per-fork detail data. The slice shape differs per fork:
- UPI slice: `{ueid, status, start_at, end_at, blocked_by, tags, provenance}` (aggregate)
- taskdog slice: `{fork_id: int, status, priority, planned_start/end, deadline, actual_*, tags, dependencies, notes, audit}` (detail)

This is fine — mesh returns a heterogeneous shape, each slice is opaque except for `status` + `fork_internalid` (matrix columns).

### D6 (UPI + taskdog coverage) — VALIDATED
- UPI = aggregate (calendar-flavor)
- taskdog = detail (taskdog-flavor)
- Together they cover the diagnostic use case (Scenario 3)
- Tuiboard detail (board position, markdown edits) NOT needed for cross-fork VIEW — it's UI-state, not data

### D7 (middle-out sequence) — VALIDATED
Sequence unchanged. Granularity concerns are absorbed by adapter return shape, not by ordering.

---

## What's in scope (Phase 3 v1)

- Cross-fork VIEW via `interfaces/cli mesh show <ueid>`
- UPI + taskdog adapters only
- Status matrix (per-fork summary) + slices (per-fork detail)
- Read-only operation
- One UEID at a time

## What's out of scope (deferred)

- tuiboard adapter (UI state, not data)
- interfaces/tui (no code exists)
- Per-interface rendering design (orthogonal to mesh)
- ~~Write path / sync events~~ **← PROMOTED TO SCOPE per D2 revision 2026-08-28**
- Multi-task batch view
- Live refresh / watch
- Vault-feedback merge logic
- Sync event schema for non-done events (started/paused/etc — v2)
- Conflict resolution beyond "earliest done timestamp wins" (v2)

---

## Write path scenarios (added 2026-08-28)

Per D2 revision, the mesh has a limited write path: "done" event propagation.

### Scenario W1 — Mark done from tuiboard
**User intent:** Drag card to "done" column. Other interfaces should reflect this.

**Flow:**
1. User drags card to "done" column in tuiboard
2. tuiboard atomic-rename of markdown (column change)
3. tuiboard emits `done` event: `{ueid, completed_at: 2026-08-28T14:30:00, source: "tuiboard"}`
4. Mesh routes:
   - solverforge-calendar UPI: `status='complete'`, `completed_at=2026-08-28T14:30:00`, `provenance.source='tuiboard'`
   - taskdog: lookup `ueid` → `tasks.id`, `tasks.status='complete'`, `actual_end=2026-08-28T14:30:00`
   - vault: `feedback.jsonl` append event for Deep Agent
5. Other forks update (eventual consistency ~1s)

### Scenario W2 — Mark done from taskdog
Same flow, but origin is taskdog. tuiboard + UPI + vault receive propagation.

### Scenario W3 — Mark done from CLI
**User intent:** Mark done from terminal. Most explicit flow.

**Flow:**
1. User runs `life task done <ueid>` (CLI)
2. CLI looks up fork-internal id mapping via UEID registry (built from Phase 1 contracts)
3. CLI chooses origin fork: if taskdog has the task, origin = taskdog; if not, origin = tuiboard; if not, origin = UPI
4. Fork writes its own state
5. Fork emits `done` event via mesh (same as W1)

### Scenario W4 — Bulk done at EOD
**User intent:** End of day. Mark all today's tasks done in batch.

**Flow:**
1. User runs `life tasks done today --bulk` (CLI)
2. CLI iterates over today's tasks (read from UPI by date range)
3. For each task: emit "done" event with timestamp = now (or "completed_at" from task data)
4. Mesh routes each event to other forks
5. Idempotency: if task already done, skip

### Idempotency guarantees
- Each fork's "done" handler checks current state before writing
- If already done with EARLIER timestamp, accept new (it's a valid re-done; rare)
- If already done with LATER timestamp, reject (eventual consistency wins; "earliest wins" rule)
- Mesh retries on fork unavailability; no duplicate writes

### v2 write path (out of scope)
- "started" event (task moved to in-progress)
- "paused" event (task paused)
- "resumed" event (task unpaused)
- "note added" event (per-fork notes)
- Generic field updates (more than status)

---

## Agent review scenarios (added 2026-08-28)

Per D2 second revision, ALL writes go through Deep Agent review queue before propagation.

### Scenario R1 — Agent approves "create" task
**Flow:**
1. User runs `life task add "Review BYD case analysis"` in CLI (origin fork: interfaces/cli)
2. CLI writes to `data/tasks.jsonl` (interfaces/cli's slice)
3. CLI emits `task_change` event to `data/review_queue/event_001.json`:
   ```json
   {
     "event_id": "evt_001",
     "ueid": "tsk:byd-case-review:uuid:hash",
     "action": "create",
     "fields": {"title": "Review BYD case analysis", "due": "2026-08-29", ...},
     "source_fork": "interfaces/cli",
     "timestamp": "2026-08-28T14:30:00",
     "status": "pending"
   }
   ```
4. Deep Agent consumes queue; reads vault planning (Q3 sprint context), PAE rules
5. Agent validates: title fits current sprint, due date reasonable, no duplicate UEID
6. Agent approves → emits `propagation` events:
   - solverforge UPI: write `unified_planning_items` row with UEID, title, due, provenance
   - taskdog: create `tasks` row with new `int` id, UEID FK, fields
   - vault: append to `vault/ikigai/closing-2026/Q3.md` (cycle doc)
7. Agent marks event `status: propagated` in queue

### Scenario R2 — Agent rejects "create" task (asks user)
**Flow:**
1. User adds task with conflicting UEID or invalid priority
2. Agent detects conflict (UEID already exists with different title)
3. Agent emits `feedback` event to user (CLI notification)
4. Event stays in queue with `status: rejected`, `feedback_reason: "UEID collision with task X"`

### Scenario R3 — Agent asks user for clarification
**Flow:**
1. User adds task with vague title: "Work on stuff"
2. Agent can't validate (too vague for PAE scoring)
3. Agent emits `clarification_request` to user
4. User clarifies: "Work on BYD Camacari case analysis"
5. Agent validates, approves, propagates

### Scenario R4 — User edits task across forks (concurrent)
**Flow:**
1. User edits task in tuiboard at 14:00 (origin: tuiboard)
2. Agent approves; propagates to UPI + taskdog + vault
3. User edits SAME task in taskdog at 14:05 (different field)
4. Agent validates; detects concurrent edit (timestamp within 5min)
5. Agent merges: tuiboard's title + taskdog's actual_start (last-write-wins per field)
6. Agent emits propagation with merged state

### Idempotency (Agent-aware)
- Event has unique `event_id`
- Agent checks `event_id` not already processed (skip duplicates)
- Fork handlers check `task_version` or `updated_at` (skip stale writes)
- Vault merge uses `[[wikilink]]` semantics (append, don't overwrite)

### Failure modes (Agent-aware)
- Agent down → queue grows; forks wait for agent; vault writes happen on agent recovery
- Fork down → propagation queues at agent; retries on fork availability
- Both down → events stay in queue; replay on restart reconciles
- Agent approves bad change → user feedback rejects in next cycle; vault history preserved

---

## Cross-references

### Decisions log
- `docs/diagnostics/2026-08-28-phase3-decisions.md` — D1..D7 with rationale

### Phase 1 + Phase 2 inputs
- `docs/diagnostics/2026-08-28-phase1-audit/` — verified + open questions
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` — markdown kanban
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md` — taskdog RE
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` — calendar RE
- `docs/diagnostics/2026-08-28-phase2-interface-re/04-interfaces-cli.md` — CLI RE
- `docs/diagnostics/2026-08-28-phase2-interface-re/05-interfaces-tui.md` — TUI (planned)
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` — synthesis

### Memory
- `[[data-first-methodology]]` — SONHO 1/5
- `[[interfaces-architecture-2026-08-27]]` — operator control plane