# Phase 3 Data Mesh Unification — Design Spec

**Date:** 2026-08-28
**Phase:** 3 of `2026-08-28-backend-audit-data-mesh`
**Status:** Design — pending spec self-review + user approval before writing-plans
**Inputs:**
- Phase 1 audit: `docs/diagnostics/2026-08-28-phase1-audit/`
- Phase 2 RE: `docs/diagnostics/2026-08-28-phase2-interface-re/`
- Phase 3 decisions: `docs/diagnostics/2026-08-28-phase3-decisions.md`
- Phase 3 usage evidence: `docs/diagnostics/2026-08-28-phase3-usage-evidence.md`

---

## Decisions (D1..D7, locked)

### D1. Anchor = Cross-fork task view
First end-to-end capability: query one task across all forks via UEID join.

### D2. Full bidirectional sync via Deep Agent gateway
**Final answer (revised twice from "read-only"):**
- ALL writes (create/update/delete/done) go through Deep Agent review queue
- Agent validates against vault + PAE; approves/rejects/clarifies
- Vault stays canonical (Agent writes on approval)
- Origin fork writes its own state first; emits `task_change` event to queue
- Agent propagates to other forks + vault on approval
- v1 implementation = `create` action ONLY (v1.2-v1.4 add other actions)

### D3. Hybrid architecture
- vault = source of truth (CLAUDE.md invariant)
- solverforge-calendar UPI = derived index (queries)
- Each fork owns execution slice
- sync_map (system, board_card_id) bridges fork-internal ids

### D4. UEID both layers
- Canonical format: 5-part `tsk:slug:uuid:hash` in `src/contracts/common.py:UEID` (Pydantic v2 strict)
- UPI gets new `ueid TEXT UNIQUE` column (migration from `ikigai` JSON)
- `data/tasks.jsonl` validates via same Pydantic contract
- taskdog gets nullable FK column `ueid TEXT`

### D5. Run interface = `interfaces/cli` command
- `life mesh show <ueid>` (read view)
- `life task add/update/done/delete <ueid>` (write operations via agent)

### D6. Coverage v1 = UPI + taskdog + interfaces/cli
- 3 adapters in v1
- tuiboard deferred to v2 (markdown atomic-rename complexity)

### D7. Middle-out, Agent FIRST in sequence
1. UEID contract (`src/contracts/common.py`)
2. TaskChange event model (`src/contracts/task_change.py`)
3. UPI schema migration (`ueid TEXT UNIQUE` column, backfill)
4. Review queue (`src/mesh/queue.py`, `data/review_queue/`)
5. Agent consumer (`src/mesh/agent_consumer.py`)
6. Agent propagator (`src/mesh/agent_propagator.py`)
7. Fork-side emitters (CLI first, taskdog + solverforge UPI second)
8. Fork-side consumers (`apply_change()` per adapter)
9. `interfaces/cli/read_tasks.py:show_mesh(ueid)` (read view)
10. Bootstrap + e2e tests

---

## Section 1: Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  INTERFACE LAYER (Layer 4)                                       │
│  └── interfaces/cli                                              │
│       ├── life mesh show <ueid>          (read — D5)             │
│       ├── life task add <ueid>           (write — D2)            │
│       ├── life task update <ueid>        (write — D2)            │
│       ├── life task done <ueid>          (write — D2)            │
│       └── life task delete <ueid>        (write — D2)            │
└─────────────────────────────────────────────────────────────────┬─────────────────────────────────┘ │
┌─────────────────────────────────▼─────────────────────────────────┐
│  REVIEW QUEUE (Layer 3.5)                                        │
│  └── data/review_queue/<event_id>.json (append-only filesystem)  │
└─────────────────────────────────────────────────────────────────┬─────────────────────────────────┘ │
┌─────────────────────────────────▼─────────────────────────────────┐
│  DEEP AGENT (Layer 3) — orchestrator (CLAUDE.md canonical) │
│  ├── consumes queue                                              │
│  ├── validates against vault + PAE                              │
│  ├── approves / rejects / asks clarification                     │
│  └── emits propagation events (forks + vault)                    │
└────────┬─────────────────┬────────────────────┬───────────────────┘
         │                 │                    │
┌────────▼──────┐ ┌────────▼─────────┐ ┌────────▼─────────────────┐
│  CONTRACT │ │  ADAPTER         │ │  DATA │
│  common.py    │ │  taskdog_         │ │  vault (canonical)        │
│   :UEID       │ │  solverforge_    │ │  UPI (derived index)      │
│  task.py      │ │  cli_            │ │  taskdog SQLite            │
│  task_change  │ │  tuiboard_ (v2)  │ │  cli tasks.jsonl           │
│   .py         │ │                  │ │  tuiboard markdown (v2)    │
└───────────────┘ └──────────────────┘ └────────────────────────────┘
```

### What this matches

- CLAUDE.md canonical flow: vault → Deep Agent → MCP Gateway → interfaces → user → cycle
- Phase 1 invariants: append-only vault, pydantic strict, zero LLM in pipelines (agent IS the LLM, but in orchestration not in arithmetic)
- Phase 2 synthesis: hybrid architecture with UPI as derived index

---

## Section 2: Components

### NEW modules

| Path | Purpose | Key exports |
|------|---------|-------------|
| `src/contracts/task_change.py` | TaskChange Pydantic v2 model | `TaskChange`, `PropagationEvent` |
| `src/mesh/__init__.py` | Mesh module marker | — |
| `src/mesh/queue.py` | Filesystem append-only queue | `enqueue()`, `consume_pending()`, `ack()`, `replay_after_restart()` |
| `src/mesh/agent_consumer.py` | Deep Agent validation | `validate(event, vault_context)` |
| `src/mesh/agent_propagator.py` | Deep Agent propagation | `propagate(event, approved_fields)` |
| `src/mesh/adapters/base.py` | Adapter Protocol contract | `ForkAdapter` |
| `src/mesh/adapters/taskdog.py` | taskdog adapter | `read()`, `apply_change()` |
| `src/mesh/adapters/solverforge_calendar.py` | solverforge UPI adapter | `read()`, `apply_change()` |
| `src/mesh/adapters/cli.py` | interfaces/cli adapter | `read()`, `apply_change()` |
| `src/mesh/adapters/tuiboard.py` | tuiboard adapter (v2 only) | `read()`, `apply_change()` |
| `tests/mesh/` | Mesh test suite | — |
| `tests/integration/` | Integration test suite | — |
| `tests/e2e/test_real_fork_e2e.py` | One slow E2E test | — |
| `data/review_queue/` | Queue directory (gitignored) | — |
| `scripts/smoke/phase3_v1.{sh,bat}` | Manual smoke test | — |

### MODIFIED files

| Path | Change | Why |
|------|--------|-----|
| `src/contracts/common.py` | Add `UEID = Annotated[str, Field(pattern=r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")]` | Canonical 5-part UEID |
| `src/contracts/task.py` | Add `mesh_ueid: UEID \| None` to Task | Enable join key |
| `interfaces/cli/read_tasks.py` | Add `show_mesh(ueid)`, `add_task(args)`, `update_task(args)`, `done_task(ueid)`, `delete_task(ueid)` | D5 + D2 |
| `interfaces/cli/__init__.py` | NEW (was missing per critic gap #8) | CLI installability |
| `interfaces/cli/pyproject.toml` | Fix `[project.scripts]` + hatch config | Per critic gap #8 |
| `solverforge-calendar/migrations/v3_*.sql` (or Rust) | `ALTER TABLE unified_planning_items ADD COLUMN ueid TEXT UNIQUE;` + backfill | D4 |
| `taskdog-core/src/taskdog_core/infrastructure/persistence/database/models/task.py` | Add `ueid = Column(String, nullable=True, index=True)` | D4 |

---

## Section 3: Data Flow

### Read path — `life mesh show <ueid>`

```
User → CLI → adapters[*].read(ueid) → fork stores
   ↑                                    │
   └──── JSON response ←── assemble ────┘
```

1. CLI parses ueid, validates against `UEID` regex
2. CLI calls each adapter's `read(ueid)` in parallel (sequential fallback if needed)
3. Adapters return slice or None (None = fork offline / not present)
4. CLI assembles status matrix + slices
5. CLI prints JSON (or formatted table)

### Write path — `life task add "..." --due YYYY-MM-DD`

```
User → CLI ──→ fork write ──→ queue.enqueue ──→ agent.consume
                                                 │
                            ┌────────────────────┼────────────────────┐
                            ▼                    ▼                    ▼
                         approve              reject              clarify
                            │                    │                    │
                            ▼                    ▼                    ▼
                  agent.propagate ──→ CLI feedback  CLI feedback  user clarifies
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
            taskdog_    solverforge_    cli_
              adapter     adapter      adapter
                │           │           │
                ▼           ▼           ▼
            taskdog       UPI       tasks.jsonl
              SQLite       SQLite    (append)
                            │
                            ▼
                       vault append
```

1. CLI generates new UEID via Pydantic
2. CLI writes to `data/tasks.jsonl` (atomic, append-only)
3. CLI emits `TaskChange` to `data/review_queue/<uuid>.json` with `status: pending`
4. Agent consumes queue, validates against vault context + PAE rules
5. Agent returns `approve | reject | clarify`
6. On approve: Agent emits propagation events to all adapters + writes vault append
7. Each adapter's `apply_change(event)` writes to its fork store (idempotent)
8. Agent marks event `status: propagated`

### Failure paths

- **Queue disk full**: Agent halts; forks retry; operator alerted
- **Agent down**: Queue grows; on restart, `replay_after_restart()` re-processes
- **Single fork down**: Marked `partial_propagation`; retry cron
- **Vault unwritable**: Propagate to forks anyway; alert operator
- **UEID collision**: Agent rejects with reason (existing + different content)

### Concurrency model

- Multiple users (single-user system): each `life task` atomic at CLI level
- Multiple forks writing concurrently: queue serializes via filesystem append
- Agent is single-consumer (no race conditions)
- Forks handle `apply_change` idempotently (UEID + updated_at check)

---

## Section 4: Error Handling

### Error taxonomy

| Class | Example | Response | Recovery |
|-------|---------|----------|----------|
| Validation | UEID malformed, missing field | Reject at CLI | User fixes input |
| Conflict | UEID exists with different content | Agent rejects | User picks new UEID |
| Conflict (semantic) | Deadline in past | Agent clarifies | User clarifies |
| Infrastructure (transient) | Fork locked, network blip | Retry 3x backoff | Auto-recovers |
| Infrastructure (persistent) | Fork disk full | Mark partial, alert | Operator investigates |
| Agent down | Process crashed | Queue grows | Auto-recover via replay |
| Vault unreachable | Permissions changed | Log critical, propagate forks | Operator fixes, replays vault |
| Schema drift | Fork has new field | Log unknown, preserve | Update adapter |

### Per-component error handling

- **CLI**: Pydantic validation fail-fast; JSON error responses; exit codes 0/1/2/3
- **Queue**: temp + atomic rename; `enqueue()` raises on disk-full; `ack()` idempotent
- **Agent consumer**: Validation errors → reject + CLI feedback; LLM errors → rule-based fallback
- **Agent propagator**: Per-adapter exceptions caught; `partial_propagation` status
- **Adapters**: Validate fork invariants; retry transient; preserve unknown fields

### Recovery playbooks

- **PB-1: Queue growing**: `ls data/review_queue/ | wc -l`; restart agent
- **PB-2: Partial propagation**: `cat data/review_queue/_retry/<event>.json`; `pav agent retry`
- **PB-3: Vault out of sync**: `pav agent vault-replay --since <ts>`
- **PB-4: Bad agent decisions**: `tail data/review_queue/_decisions.log`; rollback model or rules

### Observability

- Decisions logged: timestamp, event_id, decision_reason
- Fork writes logged: timestamp, fork, ueid, action
- Errors logged: stack trace + context
- Metrics: events/day, decision distribution, propagation latency
- Dashboard: `pav agent status --since 24h`

---

## Section 5: Testing

### Test pyramid

- **Unit (~50 tests)**: per-function/per-adapter; fast
- **Integration (~10 tests)**: per-flow; medium
- **E2E (1 test)**: real fork subprocesses; slow; `@pytest.mark.e2e`

### Unit tests

- `tests/contracts/test_common.py`: UEID validation (regex cases)
- `tests/contracts/test_task_change.py`: TaskChange model (frozen, Literal actions)
- `tests/mesh/test_queue.py`: enqueue/consume/ack/replay; atomic guarantees
- `tests/mesh/test_agent_consumer.py`: validation (approve/reject/clarify); LLM fallback
- `tests/mesh/test_agent_propagator.py`: propagation; idempotency; partial failure
- `tests/mesh/adapters/test_taskdog.py`: read by UEID; apply_change create/update/done
- `tests/mesh/adapters/test_solverforge_calendar.py`: read by UEID; apply_change; backfill
- `tests/mesh/adapters/test_cli.py`: read JSONL; apply_change append

### Integration tests

- `tests/integration/test_create_flow.py` (v1.1): fork add → queue → agent → all forks → vault
- `tests/integration/test_done_flow.py` (v1.2): pre-existing task; mark done from tuiboard; all forks reflect
- `tests/integration/test_concurrent_edit.py` (v1.3): two forks update simultaneously; agent merges
- `tests/integration/test_recovery.py`: queue corruption → restart → no double-process

### E2E test

- `tests/e2e/test_real_fork_e2e.py`: real solverforge-calendar subprocess + taskdog subprocess; `life task add` → `life mesh show`

### Manual smoke test

- `scripts/smoke/phase3_v1.{sh,bat}`: 8-step happy path verification

### CI gates (additions to existing)

- `pytest tests/mesh/`
- `pytest tests/integration/`
- `pytest tests/migrations/test_ueid_backfill.py`

### Coverage targets

- `src/mesh/`: 90% line coverage
- `src/contracts/`: 95% (Pydantic models)
- Integration: every action type covered

### Test data strategy

- Synthetic UEIDs: `tsk:test:00000000-0000-0000-0000-000000000000:00000000`
- Per-test isolated tmp dirs for fork stores + queue + vault
- After-test cleanup: `shutil.rmtree(tmp_dir)`

---

## What's in scope (Phase 3 v1)

- UEID contract (Pydantic v2 strict)
- TaskChange event model
- UPI schema migration (ueid column + backfill)
- Review queue (filesystem, append-only)
- Deep Agent consumer + propagator
- 3 fork-side adapters (CLI, taskdog, solverforge UPI)
- `life mesh show <ueid>` (read view)
- `life task add` (write CLI, v1.1 only)

## What's out of scope (deferred)

- `update`, `delete`, `done` actions (v1.2-v1.4)
- tuiboard adapter (v2 — markdown atomic-rename)
- interfaces/tui (no code)
- Per-interface rendering design (UX concern, orthogonal)
- LLM-driven agent validation (v2)
- Live refresh / watch
- Sync event schema beyond `TaskChange`
- Conflict resolution beyond "earliest done wins"

---

## Cross-references

### Phase 1 audit anchors
- `docs/diagnostics/2026-08-28-phase1-audit/00-INDEX.md`
- `docs/diagnostics/2026-08-28-phase1-audit/01-verified.md` (8 verified items)
- `docs/diagnostics/2026-08-28-phase1-audit/02-critic-gaps.md` (10 NEW gaps, esp. #8 CLI install drift)
- `docs/diagnostics/2026-08-28-phase1-audit/03-priority-matrix.md` (PR-1..PR-5)
- `docs/diagnostics/2026-08-28-phase1-audit/04-sequencing.md` (Steps 0..8)
- `docs/diagnostics/2026-08-28-phase1-audit/05-open-questions.md` (OQ-1..OQ-10)

### Phase 2 RE outputs
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/04-interfaces-cli.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/05-interfaces-tui.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`

### Phase 3 decisions + evidence
- `docs/diagnostics/2026-08-28-phase3-decisions.md` (D1..D7 with rationale)
- `docs/diagnostics/2026-08-28-phase3-usage-evidence.md` (5 scenarios + 4 write-path + 4 agent-review)

### CLAUDE.md invariants preserved
- "Deep Agent is the only writer to vault/" — Agent writes to vault on approval
- "Append-only" — review queue append-only; tasks.jsonl append-only
- "Contracts in src/contracts/" — UEID + TaskChange canonical
- "Zero LLM in pipelines" — agent IS LLM but orchestrating, not in arithmetic
- "Pydantic v2 strict" — all schemas frozen=True, extra="forbid"
- "Fully local" — SQLite + filesystem only

### Memory references
- `[[data-first-methodology]]` — SONHO 1/5
- `[[interfaces-architecture-2026-08-27]]` — native = operator control plane
- `[[ai-native-strategic-model-migration]]` — AI-native MCP contracts
- `[[ag3-gateway-orphan-2026-08-27]]` — gateway unmerged (OQ-10, partial concern)
- `[[reorg-bugs-p0-fixed-2026-08-27]]` — 8 P0 bugs fixed in prior reorg