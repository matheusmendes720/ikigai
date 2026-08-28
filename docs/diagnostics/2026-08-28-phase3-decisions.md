# Phase 3 Decisions Log — Data Mesh Unification

**Date:** 2026-08-28
**Phase:** 3 of `2026-08-28-backend-audit-data-mesh`
**Status:** ACTIVE — pending granularity re-evaluation per user feedback 2026-08-28
**Inputs:** Phase 1 audit + Phase 2 RE outputs (5 forks/interfaces)

---

## Locked decisions

### D1. Phase 3 anchor — Cross-fork task view
**Locked:** 2026-08-28 (turn: Phase 3 anchor question)
**Question:** What's the FIRST end-to-end capability you want from data mesh unification?
**Answer:** Cross-fork task view — query one task across all forks (UEID join working end-to-end).
**Rationale:** Smallest unit that exercises every layer (UEID contract + adapters + interface). Validates OQ-7 (UEID), OQ-1 (storage topology), and proves the mesh substrate is workable. Other anchors (timeline view, sync_map dashboard, UEID retrofit) all require this foundation first.
**Alternatives considered:**
- Single timeline view (calendar+kanban+task list) — bigger blast radius, needs interfaces/cli + interfaces/tui
- Sync_map dashboard — operational visibility, no user-visible win
- UEID retrofit all forks — foundation only, no query yet
**Future check:** Does the cross-fork view prove UEID join works? Does it scale to more forks?

### D2. Full bidirectional sync (Deep Agent as gateway)
**Locked:** 2026-08-28; **REVISED 2026-08-28** (user: read-only doesn't match vision)
**REVISED AGAIN 2026-08-28** (user: "adicionar uma tarefa manualmente... precisa ser propagado... ainda que so depois da revisao de um agente, atualizando tambem o vault")

**Question:** Is Phase 3 cross-fork task view read-only or read-write?
**Original answer:** Read-only.
**First revision:** Read-only + limited "done" write path.
**Final answer:** Full bidirectional sync via Deep Agent gateway.

**Rationale:**
- User clarified: "e se eu quiser adicionar uma tarefa manualmente de hoje para amanha.. isso precisa ser propagado nas outras interfaces ainda que so depois da revisao de um agente, atualizando tambem o vault"
- "Read-only" doesn't match CLAUDE.md canonical flow:
  > vault (NL planning) → Deep Agent (interpreta, aplica PAE, gera tasks)
  > → MCP Gateway (sincroniza vault ↔ interfaces)
  > → Interfaces preenchem com tasks ricas pro usuário marcar
  > → Input manual (burndown, execution rate) → Deep Agent observa gap
  > → Atualiza planejamento → ciclo contínuo
- The whole point of the system is bidirectional flow — user inputs in interfaces MUST feed back to vault
- "ainda que so depois da revisao de um agente" = agent review is the gate, NOT a barrier

**Mechanism (full bidirectional sync):**
- User adds/updates/deletes/done task in fork X (any fork)
- Fork X writes to its own state (atomic — markdown rename / SQLite UPDATE)
- Fork X emits `task_change` event: `{ueid, action: create/update/delete/done, fields: {...}, source_fork, timestamp}`
- Event written to **REVIEW QUEUE** (filesystem-based: `data/review_queue/<event_id>.json`)
- Deep Agent consumes queue, validates against:
  - vault planning context (does this fit current sprint/cycle?)
  - PAE methodology (priority score, effort estimate, dependencies)
  - User intent (does this match user's stated goals?)
  - Conflict detection (does UEID exist? status consistency?)
- If approved: Agent emits `propagation` events to all relevant forks + writes vault update
- If rejected: Agent sends feedback to user (reason, suggestion)
- Vault stays canonical (Agent writes to vault on approval)

**What propagates per action:**

| Action | User intent | Origin | Propagation |
|--------|-------------|--------|-------------|
| **create** | "Add a task" | Any fork | All forks + vault |
| **update** | "Edit task fields" | Any fork | All forks + vault |
| **delete** | "Remove task" | Any fork | All forks + vault (tombstone) |
| **done** | "Mark complete" | Any fork | All forks + vault |

**What "looks done" per fork:**
- tuiboard: card moves to done column (markdown round-trip preserves it)
- taskdog: `tasks.status='complete'`, `actual_end=completed_at`
- solverforge-calendar UPI: `status='complete'`, `completed_at`, `provenance.source`
- vault: feedback.jsonl append event; Deep Agent merges into planning

**Conflict resolution:**
- Agent is the arbiter (deterministic rules + LLM judgment)
- For status conflicts: "earliest done timestamp wins" (deterministic)
- For field conflicts: Agent merges based on source authority (e.g., taskdog for lifecycle, calendar for scheduling)
- For semantic conflicts: Agent asks user

**v1 implementation scope (per "test smallest unit first"):**
- v1.1: `create` action ONLY — full flow (fork write → review queue → agent approve → fork propagate → vault write)
- v1.2: add `done` action (reuses v1.1 plumbing)
- v1.3: add `update` action
- v1.4: add `delete` action

**Alternatives considered:**
- Read-only (original) — user feedback: doesn't match vision
- Limited "done" only (1st revision) — user feedback: too restrictive, misses "add task" use case
- Mesh as authority (bypass agent) — violates CLAUDE.md invariant, removes agent intelligence
**Future check:** Does the agent review add real value (or just delay)? Does the review queue scale? When do we add LLM-driven suggestions (vs just rule-based approval)?

### D3. Hybrid architecture (vault upstream, UPI as derived index, each fork owns execution)
**Locked:** 2026-08-28 (after user clarification on calendar-as-index vs decoupling)
**Question:** Calendar (UPI) as primary index or decoupled federation?
**Answer:** Hybrid. solverforge-calendar UPI as **derived query index**, each fork owns execution, vault stays upstream.
**Rationale:**
- Calendar/UPI as index = good for queries (user's first intuition)
- Decoupled execution per fork = good for extensibility (user's second intuition)
- No SPOF (each fork owns its state)
- Vault stays upstream (CLAUDE.md invariant intact)
- Schema evolution per fork (add taskdog field without breaking others)

**Mechanism:**
- Each fork emits "I changed X at time T" events
- solverforge-calendar consumes events → updates UPI status/time as DERIVED state (not authoritative)
- Cross-fork view = read UPI as index → resolve details via sync_map (system, board_card_id)
- Vault unchanged as upstream (CLAUDE.md invariant preserved)

**Alternatives considered:**
- Option A: UPI authoritative (breaks CLAUDE.md)
- Option B: Pure federation (no calendar-as-index intuition)
**Future check:** Does the hybrid survive a fork outage? Does UPI stay in sync? Does the index lag cause wrong answers?

### D4. UEID both layers (UPI column + Pydantic v2 contract)
**Locked:** 2026-08-28
**Question:** Where does the canonical UEID live?
**Answer:** Both layers cross-reference same UEID.
**Rationale:**
- Type-safe (Pydantic validation at interfaces/cli boundary)
- Queryable in UPI (column, not JSON blob)
- DB-level uniqueness (one row per UEID)
- sync_map preserved (no fork retrofit for UEID lookup; fork-internal ids still local)
- One canonical UEID format (5-part `tsk:slug:uuid:hash` in `src/contracts/common.py:UEID`)

**Mechanism:**
- Canonical format = 5-part UEID in `src/contracts/common.py:UEID` (Pydantic v2 strict)
- UPI gets new `ueid TEXT UNIQUE` column (migrated from `ikigai` JSON)
- `data/tasks.jsonl` validates via same Pydantic contract
- Mesh reads UPI by `ueid` (no JSON extraction)
- Forks write internal id; solverforge-calendar `upi_sync` translates to UEID
- `sync_map (system, board_card_id)` still bridges fork-internal ids

**Alternatives considered:**
- UPI only (no Pydantic, JSON blob, no DB uniqueness) — weaker validation
- interfaces/cli only (UEIDs in tasks.jsonl, UPI doesn't know) — adapters per fork
**Future check:** Does the migration complete cleanly? Does backfill work? Do both layers stay in sync?

### D5. Run interface = `interfaces/cli` command
**Locked:** 2026-08-28
**Question:** Where does the user invoke 'show cross-fork view for task X'?
**Answer:** `interfaces/cli` command (e.g., `life mesh show <ueid>`).
**Rationale:** Aligns with CLAUDE.md (interfaces/cli = native operator control plane, per `[[interfaces-architecture-2026-08-27]]`). Lightweight, no gateway change required for v1. Can be wrapped by MCP tool in v2 if agents need it.
**Alternatives considered:**
- MCP tool via gateway — heavier setup, gateway bugs (B-01 + 4 others) still pending
- Ad-hoc Python script — not user-facing
- Both interfaces/cli + MCP — more work, more surfaces
**Future check:** Is interfaces/cli sufficient for operator use? Does MCP tool become necessary for agent-driven queries?

### D6. Coverage v1 = solverforge-calendar UPI + taskdog adapter
**Locked:** 2026-08-28
**Question:** Minimum viable cross-fork view for v1: which fork(s)?
**Answer:** UPI + taskdog. Solves schema migration + adapter pattern with one second fork.
**Rationale:** Smallest unit that exercises both the schema migration (UPI gets ueid column) and the adapter pattern (taskdog exposes fork-internal id ↔ UEID). Adding tuiboard adapter is bigger lift (Bun + markdown atomic-rename); defer to v2 per data-first gate.
**What's NOT in v1:**
- tuiboard adapter (defer to v2)
- interfaces/tui (no code exists per `05-interfaces-tui.md:11-44`)
- Write path / sync events (read-only — D2)
- Multi-task batch view (single UEID at a time per D1)
- Live refresh / watch (one-shot query)

**Alternatives considered:**
- UPI only — doesn't validate adapter pattern, Phase 3 design under-tested
- All 3 forks + interfaces/cli — heaviest scope, 5 adapters minimum
- Ad-hoc script — not committed
**Future check:** Does the UPI+taskdog pair expose all the data-join challenges? What breaks when adding tuiboard?

### D7. Middle-out implementation approach (REVISED for D2 full bidirectional)
**Locked:** 2026-08-28; **REVISED 2026-08-28** (per D2 revision to full bidirectional)
**Question:** Bottom-up, middle-out, or top-down?
**Answer:** Middle-out (REVISED to put Agent FIRST in the sequence).
**Rationale:** With D2 = full bidirectional via Deep Agent, the Agent is the orchestrator. Sequence becomes: define UEID contract → build Agent review loop → build fork adapters → wire emit/propagate → test end-to-end with smallest action (`create`).
**Sequence (REVISED, v1 = `create` action only):**
1. Define `src/contracts/common.py:UEID` (5-part Pydantic v2 strict)
2. Define `src/contracts/task.py:TaskChange` (Pydantic v2 model for review queue events)
3. Migrate UPI schema (`ueid TEXT UNIQUE` column, backfill from `ikigai` JSON)
4. Build review queue (`data/review_queue/` filesystem-based, append-only)
5. Build fork-side emitter: `interfaces/cli task add <ueid>` writes task + emits `task_change` event to queue
6. Build Deep Agent consumer: reads queue, validates against vault/PAE, approves/rejects
7. Build propagation emitter: Agent writes to UPI + other forks + vault on approval
8. Build `taskdog_adapter.py` (consumes Agent's propagation events)
9. Build `solverforge_calendar_adapter.py` (consumes Agent's propagation events)
10. Build `interfaces/cli/read_tasks.py:show_mesh(ueid)` (read-only operator view per D5)
11. Bootstrap with seed task via new minimal writer
12. Test end-to-end: fork add → queue → agent approve → fork+UPI+vault propagate

**v1.1 = `create` action flow only** — smallest unit that exercises full bidirectional.
**v1.2 = `done` action** — reuses v1.1 plumbing; just changes event payload.
**v1.3 = `update` action** — adds field merge logic.
**v1.4 = `delete` action** — adds tombstone semantics.

**Alternatives considered:**
- Bottom-up (adapters first) — agent without data plumbing; rework risk
- Top-down (CLI first with synthetic data) — visible result, fixture maintenance, weakest integration
- Full v1 (all 4 actions) — too big; validate cycle first with 1 action
**Future check:** Does the Agent-first ordering minimize rework? Does Step 4 (review queue) scale beyond filesystem? Does the agent validation add latency users complain about?

---

## PENDING RE-EVALUATION (raised 2026-08-28)

### Granularity gap (user concern)
**Question:** Are we making architecture decisions without considering data granularity per interface?
**Concern:**
- Calendar shows: summaries, day objectives, task counts (aggregate level)
- Tuiboard shows: project overview, time allocation, day blocks (overview level)
- Taskdog shows: detailed descriptions, checklists, expected results (detail level)
- CLI shows: mixed (per-task detail + per-day summary)

**Implications for current decisions:**
- D2 "Read-only" applies to mesh view, not entire system — confirmed by user
- D5 "Status matrix + slices" — slices per fork may have different granularity requirements
- D6 "UPI + taskdog" — taskdog has detail data, UPI has aggregate data; need adapter that exposes both appropriately

**Action:** Practical usage analysis per interface — see `2026-08-28-phase3-usage-evidence.md`.

---

## Cross-references

### Phase 1 audit anchors
- `docs/diagnostics/2026-08-28-phase1-audit/01-verified.md` — 8 verified items
- `docs/diagnostics/2026-08-28-phase1-audit/02-critic-gaps.md` — 10 NEW gaps
- `docs/diagnostics/2026-08-28-phase1-audit/03-priority-matrix.md` — PR-1..PR-5 ranking
- `docs/diagnostics/2026-08-28-phase1-audit/04-sequencing.md` — Steps 0..8
- `docs/diagnostics/2026-08-28-phase1-audit/05-open-questions.md` — OQ-1..OQ-10

### Phase 2 RE outputs
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` — markdown kanban
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md` — Python uv workspace
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` — Rust rmcp
- `docs/diagnostics/2026-08-28-phase2-interface-re/04-interfaces-cli.md` — Typer CLI
- `docs/diagnostics/2026-08-28-phase2-interface-re/05-interfaces-tui.md` — README-only
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` — synthesis

### Memory references
- `[[data-first-methodology]]` — SONHO 1/5; data-first gate
- `[[interfaces-architecture-2026-08-27]]` — native = operator control plane
- `[[ai-native-strategic-model-migration]]` — AI-native MCP contracts only
- `[[ag3-gateway-orphan-2026-08-27]]` — gateway unmerged (OQ-10)