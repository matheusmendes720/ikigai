# ADR-022 — Two-Queue Architecture (review_queue + investigation_queue)

> **Status:** Accepted (2026-09-06)
> **Deciders:** matheus (project owner)
> **Wave 5 Task 3c:** dcode-harness-PLAN.md §4 step 8
> **Sources:** Plan A (SHIPPED 2026-09-03), Plan C (SHIPPED 2026-09-05), Plan D (SHIPPED 2026-09-04)

---

## Context

The Deep Agent and its fork-adapter mesh operate two distinct classes of work that must not be mixed:

1. **Structured task lifecycle events** — `TaskChange` objects from forks that require Deep Agent validation (APPROVE / REJECT / CLARIFY) before propagation to all forks. These have a canonical UEID, a known 6-level hierarchy (SONHO / OBJETIVO / META / PROJETO / ENTREGA / TAREFA), and a finite state machine defined by the Phase 3 mesh contract.

2. **Pre-form observations** — raw signals (shadow loops, ambiguous research leads, vague intuitions) that do not fit the 6-level hierarchy and may never become tasks. These need a parking space with their own lightweight lifecycle (open → in_progress → resolved | archived) before they either crystallize into a planning tree entry or are archived.

Mixing these two concerns into a single queue would cause:
- Fork-side `TaskChange` validation logic becoming coupled to investigation FSM rules
- The investigation queue accumulating TaskChange-shaped files that the agent consumer cannot process
- Ambiguous ownership: which worker processes which entry?

**Alternatives considered:**

| Alternative | Reason for rejection |
|:------------|:--------------------|
| Single queue with a `type` tag field | Type tags are convention only — enforcement requires code; two queues make the boundary explicit and enforceable by drift invariant |
| DB-backed queue (SQLite / PostgreSQL) | DB adds an external dependency and a migration surface; filesystem append-only is canonical (mirrors `vault_write` design per ADR-012) |
| In-memory queue | Lost on restart; violates the append-only audit requirement |
| Investigation items stored as draft vault files | Premature — investigations are pre-vault; writing to vault implies a planning decision that has not yet been made |

---

## Decision

Two independent filesystem append-only queues, each with its own schema, consumer, and FSM:

### Queue 1: `review_queue` (`data/review_queue/`)

- **Purpose:** TaskChange events from forks. Deep Agent validates each event via PAE rules (APPROVE / REJECT / CLARIFY), then propagates a `PropagationEvent` to all forks.
- **Created by:** Phase 3 v1 mesh — fork adapter sends `TaskChange` via CLI enqueue path.
- **Consumer:** Deep Agent `agent_consumer.py` — the single writer allowed to mutate fork state.
- **Schema:** `TaskChange` Pydantic model (frozen=True, extra="forbid").
- **FSM:** None — events are append-only records, not stateful entities.
- **Atomic write pattern:** `tmp.write_text() + os.replace(target)` (via `src/mesh/queue.py:_atomic_write_json`). Retry decorator handles Windows EBUSY and NFS stale handles.
- **Audit log:** Per-event write is the audit — each JSON file's `event_id` + `timestamp` is the trace.
- **Drift invariant:** Invariant (e) — `test_review_queue_append_only` enforces `data/review_queue/` is append-only via `mesh.queue.enqueue()` only.
- **Lifecycle scope (v1):** `create` action only. `update` / `delete` / `done` deferred to v1.2+.

### Queue 2: `investigation_queue` (`data/investigation_queue/`)

- **Purpose:** Pre-form observations — raw data, shadow loops, ambiguous leads — that do not fit the 6-level SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA hierarchy.
- **Created by:** Deep Agent (via `investigation_enqueue` MCP tool) or cron-invoked dispatcher reading external inputs.
- **Consumer:** Cron-invoked `dispatch_pending()` worker (pure dispatch, no LLM) and the 3 MCP lifecycle tools (`investigation_enqueue` / `investigation_status` / `investigation_complete`).
- **Schema:** `Investigation` Pydantic model (frozen=True, extra="forbid") with `inq_id` (format: `inq-YYYYMMDD-NNN`), `source`, `payload`, `status`, `tags`, `actor`.
- **FSM:** `open → in_progress → resolved | archived` (terminal states sealed — no resurrection).
- **Atomic write pattern:** `tmp.write_text() + os.replace(target)` (via `src/mesh/investigation_queue.py:_atomic_write`). Mirrors `src/mesh/queue.py` pattern exactly.
- **Audit log:** Per-transition append to `data/investigation_queue/.investigation_audit.log`. Format: `{iso} inq_id={X} {from}→{to} actor={actor}`. Audit failure is non-fatal.
- **Drift invariant:** Invariant (h) — `check_investigation_queue_invariants` enforces: dir exists or absent, all `.json` files parse as `Investigation`, audit log lines contain `actor=` and `inq_id=` prefixes.
- **Dispatcher rules (v1):** `dispatch_pending()` is OBSERVE-only — reads queue, emits counts, calls `sink()` hook (stub for v2 planning-tree lift).

### Shared invariants (both queues)

| Invariant | review_queue | investigation_queue |
|:----------|:-------------|:-------------------|
| Filesystem append-only | Yes | Yes |
| Per-event / per-transition audit log | Yes (event_id + timestamp in JSON) | Yes (`.investigation_audit.log`) |
| Atomic write pattern (tmp + rename) | Yes (`_atomic_write_json`) | Yes (`_atomic_write`) |
| Retry decorator for transient OSError | Yes (EBUSY, PermissionError) | Yes (same pattern) |
| Pydantic v2 strict (frozen=True, extra="forbid") | Yes (`TaskChange`) | Yes (`Investigation`) |
| Drift invariant enforced | Yes — invariant (e) | Yes — invariant (h) |
| Separate ID namespace | `event_id` (UUID-based) | `inq_id` (`inq-YYYYMMDD-NNN`) |

---

## Consequences

### Positive

- **Clear ownership:** `review_queue` is fork-write / agent-validate; `investigation_queue` is agent-write / dispatcher-observe. No ambiguity about which queue a piece of work belongs to.
- **Drift enforceable:** Invariants (e) and (h) make the append-only boundary machine-verifiable. Any code that writes to either queue outside the canonical helper function fails CI.
- **Audit trail complete:** Every state transition in `investigation_queue` is logged with actor and timestamp. Every `review_queue` write is traceable via `event_id`.
- **Pattern consistency:** Both queues use the same `tmp + rename` atomic write idiom with retry decorators, making the codebase easier to reason about.
- **Plan D reuse:** `proposal_executor` in the Meta-Planner (Plan D) reuses both queues — `review_queue` for taskdog create operations triggered by fork propagation, and `investigation_queue` for parking pre-form observations that arise during proposal generation.

### Negative

- **Two queues to maintain:** Each queue has its own helper module, tests, drift invariants, and consumer logic. Adding a new feature (e.g., bulk archive) requires changes in two places.
- **Cron dependency for investigation_queue:** The `dispatch_pending()` worker must be registered in a cron schedule to advance stale investigations (stale → archive rule). If cron is not configured, stale items accumulate indefinitely. `review_queue` has no such scheduler dependency — it is purely event-driven.
- **Separate ID namespaces:** `event_id` vs `inq_id` means cross-referencing between queues requires explicit `inq_ueid` fields on `Investigation` — there is no automatic link.

---

## Queue Comparison Matrix

| Aspect | review_queue | investigation_queue |
|:-------|:-------------|:-------------------|
| **Purpose** | Structured TaskChange events from forks — Deep Agent validates (APPROVE/REJECT/CLARIFY) then propagates | Pre-form observations that don't fit the 6-level hierarchy — raw signals before a planning decision is made |
| **Created by** | Fork adapters via CLI enqueue (`mesh.queue.enqueue()`) | Deep Agent via `investigation_enqueue` MCP tool or cron dispatcher |
| **Consumer** | Deep Agent `agent_consumer.py` (single writer, PAE validation) | Cron-invoked `dispatch_pending()` worker (observe-only) + 3 MCP tools |
| **FSM** | None — append-only event records | `open → in_progress → resolved \| archived` (terminal states sealed) |
| **Audit log** | Event-level (event_id + timestamp embedded in JSON) | Per-transition append to `.investigation_audit.log` |
| **Drift invariant** | (e) `test_review_queue_append_only` — append-only via `mesh.queue.enqueue()` | (h) `check_investigation_queue_invariants` — dir valid, all files parse, audit log prefix |
| **Schema** | `TaskChange` (frozen=True, extra="forbid") | `Investigation` (frozen=True, extra="forbid") |
| **ID format** | `event_id` (UUID-based) | `inq_id` (`inq-YYYYMMDD-NNN`) |
| **Atomic write** | `_atomic_write_json` via `src/mesh/queue.py` | `_atomic_write` via `src/mesh/investigation_queue.py` |
| **Retry on transient OSError** | Yes (EBUSY, PermissionError, 4 attempts, exponential backoff) | Yes (same pattern) |
| **v1 scope** | `create` action only; update/delete/done deferred to v1.2+ | Lifecycle tools + dispatcher (observe-only); planning-tree lift deferred to v2 |

---

## Cross-References

- **Plan A** (SHIPPED 2026-09-03): `review_queue` atomic writes — `src/mesh/queue.py:_atomic_write_json` + invariant (e)
- **Plan C** (SHIPPED 2026-09-05): `investigation_queue` — `src/mesh/investigation_queue.py` + invariant (h) + 3 MCP tools
- **Plan D** (SHIPPED 2026-09-04): `proposal_executor` reuses both queues — `review_queue` for taskdog create propagation, `investigation_queue` for parking pre-form observations during proposal generation
- **Drift invariant (e):** `test_canonical_scope.py::test_review_queue_append_only` — enforces `data/review_queue/` is append-only via `mesh.queue.enqueue()`
- **Drift invariant (h):** `test_canonical_scope.py::test_drift_invariant_h_investigation_queue` — `check_investigation_queue_invariants`
- **ADR-012:** Vault write invariant (`vault_write` = sole vault writer) — same append-only principle as both queues
- **ADR-013:** Canonical scope discipline — algorithm/math execution out of scope; queues are data-layer concerns

---

*ADR-022 — Two-Queue Architecture — 2026-09-06*
