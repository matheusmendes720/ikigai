# Backend Topology Diagnosis — 2026-08-30

**Author:** main session (post compaction, autonomous scan)
**Scope:** `life/` repo — backend phase B0-B6+ (master branch @ `fb69618`)
**Inputs:** [[b5-0-audit-findings-2026-08-29]], [[combo-a-whole-branch-review-backlog-2026-08-29]], [[backend-phase-reordering-2026-08-28]], [[master-branch-carro-chefe-2026-08-28]], [[fork-connection-defer-2026-08-30]]
**Audience:** matheus (operator)
**Purpose:** Honest end-to-end state of the backend, layer by layer, with explicit gaps and dependencies.

---

## 1. Topology (canonical)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Layer 4 — INTERFACE LAYER (consumer-facing)                              │
│                                                                          │
│  interfaces/cli/                          interfaces/tui/                 │
│   ├─ list, done, stats  ✅                   (EMPTY — STALE README only) │
│   ├─ mesh-show         ✅ B5.B                                          │
│   ├─ task-add          ✅ B5.B                                          │
│   └─ server ls/inspect/status ✅          ← start/stop = STUBS ❌       │
│                                                                          │
│  ── User-facing VIEWS live in forks (tuiboard/taskdog/solverforge-cal) ──┤
│  ── Natives here = backend control plane ONLY per [[interfaces-…]] ──────┤
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                              Typer CLI / stdio
                                       │
┌──────────────────────────────────────▼───────────────────────────────────┐
│  Layer 3 — DEEP AGENT (orchestrator)                                      │
│                                                                          │
│  src/ikigai/src/agents/                                                  │
│   ├─ ikigai_maintainer graph ✅ registered in langgraph.json             │
│   ├─ pae_maintainer graph     ✅ REAL (Q1-Q4 stub removal done)          │
│   ├─ 4 declared graphs        ⚠️ spec-only stubs (nervous system)        │
│   └─ HITL via interrupt_on={write_file:True} ✅                          │
│                                                                          │
│  src/mesh/                                                               │
│   ├─ agent_consumer.py    ⚠️ MVP (75 lines; F6 fixed)                    │
│   └─ agent_propagator.py  ⚠️ MVP (103 lines; partial_prop ack added)     │
│                                                                          │
│  ── F4 SqliteSaver leak ❌ F9 FilesystemBackend=Path.home() ❌ ──────────┤
│  ── F13 zero retry/timeout ❌ F14 zero per-node smoke tests ❌ ───────────┤
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                              Pydantic v2 strict contracts
                                       │
┌──────────────────────────────────────▼───────────────────────────────────┐
│  Layer 2 — KERNEL / CONTRACTS                                            │
│                                                                          │
│  src/contracts/                                                           │
│   ├─ common.py     UEID, Period, Priority, EntityType, RegimeState     ✅│
│   ├─ task.py       Task, Subtask, ChecklistItem, Project, Milestone    ✅│
│   ├─ task_change.py TaskChange, PropagationEvent, TaskAction          ✅│
│   ├─ planning.py   PlanningCycle, Wave, Sprint, VaultEvent             ✅│
│   └─ metrics.py    Burndown, ExecutionRate, QHEScore                  ✅│
│       (formulas DEFERRED per [[algorithm-gate-system-readiness-not-…]])   │
│                                                                          │
│  src/mesh/adapters/                                                      │
│   ├─ CliAdapter              ✅ JSONL append-only                       │
│   ├─ TaskdogAdapter          ✅ SQLite UPSERT (B5.B E2E)               │
│   └─ SolverforgeCalendarAdapter ✅ UPI ueid column (B5.B E2E)         │
│       (tuiboard adapter MISSING — not needed per fork-connection-defer) │
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                                  filesystem / SQLite
                                       │
┌──────────────────────────────────────▼───────────────────────────────────┐
│  Layer 1 — STORAGE                                                        │
│                                                                          │
│  vault/         canonical SOT (markdown + wikilinks)               ✅     │
│  data/                                                                    │
│   ├─ review_queue/    append-only TaskChange events            ✅ B4    │
│   ├─ taskdog/tasks.db lazy-created on first adapter write        ✅     │
│   ├─ vibe_ops.db      cybernetic engine state                   ✅     │
│   ├─ tasks.jsonl      CLI adapter projection                    ✅ B5.2 │
│   ├─ boulder.json     session state                             ✅     │
│   └─ chroma_db/       vector store (vibe-ops only)               ✅     │
│  vibe-ops/       cybernetic engine (separate workspace)           ✅     │
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                              JSON-RPC 2.0 over stdio (subprocess)
                                       │
┌──────────────────────────────────────▼───────────────────────────────────┐
│  Layer 0 — MCP GATEWAY (fork transport)                                   │
│                                                                          │
│  UnifiedMCPGateway (port 8765, HTTP+SSE front)                    ✅ B3 │
│   ├─ POST /call      {namespace, tool, arguments} → JSON                │
│   ├─ GET  /health    {status: ok, adapters: [...]}                       │
│   └─ GET  /events    ✅ real streaming (chunked TE, 15s heartbeat,       │
│                    │   event bus via publish_event/subscribe_events)    │
│                                                                          │
│  StdioAdapter (per fork, subprocess JSON-RPC over stdin/stdout)   ✅     │
│   ├─ content-length framing                                              │
│   ├─ lazy spawn                                                          │
│   ├─ monotonic request IDs                                              │
│   └─ stderr ring buffer                                                 │
│                                                                          │
│  Fork clients registered (via register_default_adapters):                │
│   ├─ taskdog              ✅ installed (pip v0.23.0), gateway+mesh       │
│   ├─ solverforge-calendar ⚠️ declared, NOT installed (DEFERRED today)   │
│   └─ tuiboard              ⚠️ declared, NOT installed, no mesh adapter  │
│                             (DEFERRED today per fork-connection-defer)   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Estado por camada (matrix)

| Layer | Component | Status | Last shipped | Notes |
|-------|-----------|--------|--------------|-------|
| 0 | UnifiedMCPGateway | ✅ DONE | B3 (`phase-b3-mcp-gateway-complete-2026-08-28`) | Pure stdlib, no starlette |
| 0 | SSE real streaming | ✅ DONE | `0ebb57c` | Event bus (publish/subscribe), chunked TE, 15s heartbeat, graceful disconnect |
| 1 | vault/ canonical SOT | ✅ DONE | — | Append-only invariant enforced |
| 1 | data/review_queue/ | ✅ DONE | B4 (`phase-b4-review-queue-worker-complete-2026-08-29`) | pidfile + worker_status |
| 1 | data/taskdog/tasks.db | ✅ DONE | B5.B | Lazy SQLite UPSERT |
| 1 | data/vibe_ops.db | ✅ DONE | audit hygiene | Moved from root |
| 2 | src/contracts/ | ✅ DONE | Phase 3 | Pydantic v2 strict, all 5 modules |
| 2 | src/mesh/queue.py | ✅ DONE | B4 | Atomic writes, replay_after_restart |
| 2 | CliAdapter | ✅ DONE | B5.1+B5.2 | JSONL O(n) dedup `abb355f` |
| 2 | TaskdogAdapter | ✅ DONE | B5.B | SQLite UPSERT on ueid |
| 2 | SolverforgeCalendarAdapter | ✅ DONE | B5.B | UPI ueid column migration |
| 2 | algorithms (M01/N01/A02/A06) | ❌ DEFERRED | — | per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] |
| 3 | ikigai_maintainer graph | ✅ REAL | — | Per [[q3-q4-resolved-2026-08-27]] |
| 3 | pae_maintainer graph | ✅ REAL | — | Stubs removed in Q2 |
| 3 | agent_consumer.py | ⚠️ MVP | B5.2 | 75 lines; F6 silent-except now warns |
| 3 | agent_propagator.py | ⚠️ MVP | B5.B (`bb0edd5`) | 103 lines; partial_prop ack |
| 3 | 4 declared graphs | ⚠️ SPEC | — | quarterly_replan / correction_protocol / dream_falsification / test_de_fogo_rollup — "nervous system" stubs |
| 3 | SqliteSaver lifecycle | ❌ OPEN F4 | — | Connection leak in `make_ikigai_graph()` |
| 3 | FilesystemBackend scope | ❌ OPEN F9 | — | root_dir=Path.home() = full write |
| 3 | retry/timeout wrapper | ❌ OPEN F13 | — | partial_prop added but no retry policy |
| 3 | per-node smoke tests | ❌ OPEN F14 | — | 0 tests for 8-node IKIGAi-Maintainer |
| 3 | error_node terminal | ❌ OPEN F3 | — | Exception = crash |
| 3 | checkpoint DB off ~/.ikigai | ❌ OPEN F10 | — | Windows lock risk per [[life-ops-ikigai-lock-2026-08-27]] |
| 3 | run_chat() refactor | ❌ OPEN F11 | — | 270-line monolithic REPL |
| 4 | interfaces/cli (mesh commands) | ✅ DONE | B5.1+B5.2 | list/done/stats/mesh-show/task-add |
| 4 | interfaces/cli/server (ls/inspect/status) | ✅ DONE | B5.1 | reads `data/review_queue/` + pidfiles |
| 4 | interfaces/cli/server (start/stop) | ❌ STUBS | — | Phase B2 scaffolding only |
| 4 | interfaces/tui/ | ❌ EMPTY | — | Only STALE README (contradicts [[interfaces-architecture-2026-08-27]]) |

---

## 3. B5.0 audit — 14 findings status

| ID | Severity | Title | Status | Closed by | Verified |
|----|----------|-------|--------|-----------|----------|
| F1 | MEDIUM | Dual langgraph.json broken path | ✅ CLOSED | B5.1 `a5837df` | ✅ |
| F2 | LOW | `_route_after_plan/reflection` dead code | ✅ CLOSED | B5.2 | ✅ |
| F3 | MEDIUM | No error/timeout nodes | ✅ CLOSED | B5.1 `a5837df` | ✅ |
| F4 | HIGH | SqliteSaver connection leak | ✅ CLOSED | B5.1 `a5837df` (close_graph + atexit) | ✅ 2026-08-30 |
| F5 | LOW | init_tracing silent failure | ✅ CLOSED | B5.2 | ✅ |
| F6 | LOW | silent `except (ImportError, AttributeError)` | ✅ CLOSED | B5.2 (now logs warning) | ✅ |
| F7 | LOW | partial propagation no DLQ | ✅ CLOSED | B5.B ack logic | ✅ |
| F8 | MEDIUM | No MCP multi-tool chain test | ❌ OPEN | — | ❌ |
| F9 | HIGH | FilesystemBackend root_dir=Path.home() | ✅ CLOSED | B5.1 `a5837df` (data/+vault/, virtual_mode=True) | ✅ 2026-08-30 |
| F10 | MEDIUM | Default checkpoint DB Windows-lock risk | ✅ CLOSED | B5.1 `a5837df` (cwd/data/) | ✅ |
| F11 | MEDIUM | run_chat() 270-line REPL | ❌ OPEN | — | ❌ |
| F12 | LOW | IKIGAiStateDict total=False | ✅ CLOSED | B5.1 | ✅ |
| F13 | HIGH | Zero retry/timeout/circuit-breaker | ✅ CLOSED | B5.1 (`_retry_atomic_write`) + B5.B partial_prop | ✅ |
| F14 | HIGH | Zero per-node smoke tests | � OPEN | — | ❌ |

**Closed: 11 of 14** (79%). **HIGH open: 1 of 4** (F14 only).

---

## 4. Cross-cutting risks (NOT Phase B scope, but blocking)

Per [[post-phase-b-audit-hygiene-2026-08-29]]:

| Issue | Severity | Source | Fix path |
|-------|----------|--------|----------|
| 49 src/operational/ collection errors | HIGH | pre-existing | src/operational/ is separately maintained workspace |
| 34 test_state_machines.py failures | HIGH | pre-existing | (commit 7cfd696) |
| 7 test_types.py failures | HIGH | pre-existing | — |
| file_harness.py:401 syntax error | HIGH (mypy blocker) | pre-existing | (commit eaa3de2) |
| §7 attribution violations (agentic_writer.py:35 + propagation/) | MEDIUM | per attribution report | aspirational; vault_write is only vault writer |
| 2/3 .bat smoke variants fail | MEDIUM | bash is canonical contract | out of scope (Windows is dev box, CI is Linux) |
| 1465 total ruff findings | LOW | bulk in src/operational/ | separately maintained |

---

## 5. Phase B status (rev.3 re-ordering)

| Phase | Description | Status | Notes |
|-------|-------------|--------|-------|
| B0 | Hygiene | ✅ DONE | Multiple waves B5.3-B5.5 |
| B1 | A2UI | ❌ NEVER BUILT | spec-only per 2026-08-28 (NOT deferred — never built) |
| B2 | Server-mgmt-CLI | ⚠️ SCAFFOLDING | ls/inspect/status work; start/stop = STUBS |
| B3 | MCP Gateway | ✅ DONE | UnifiedMCPGateway + StdioAdapter |
| B4 | Review Queue Worker | ✅ DONE | run_once + start_worker + worker_status + pidfile |
| B5 | Agent Wiring (consumer + propagator) | ✅ DONE (MVP) | 75 + 103 lines; B5.B E2E closed 1 HIGH |
| B5.0-B5.2 | Audit + hardening waves | ✅ DONE | 6/14 findings closed |
| B5.3-B5.5 | Hygiene waves | ✅ DONE | scratch cleanup, root artifacts, tracked-binary |
| B5.B | E2E for 3 adapters + dead shim removal | ✅ DONE | 47/47 regression |
| B6 | Vault Sync | ✅ DONE | 5 commits; closes Phase B per [[phase-b6-vault-sync-shipped-2026-08-29]] |
| B6 Combo A | Bidirectional sync (reverse_sync + vault_write) | ✅ DONE | vault_write is ONLY vault writer |
| Attribution | vault_write = ONLY vault writer | ✅ DONE | docs-only `dd1a286` |

---

## 6. What's BLOCKING vs what's DEFERRED

### BLOCKING (real defects that affect current functionality) — UPDATED 2026-08-30

1. ~~**B2 start/stop STUBS** (`interfaces/cli/server.py:258-290`)~~ ✅ **SHIPPED** (commit `0e82e4e`)
   - Real subprocess management with pidfile lifecycle.
   - Tests: 14 new tests, 116/116 regression in interfaces/cli/ + src/mesh/.

2. ~~**F4 SqliteSaver connection leak**~~ ✅ **ALREADY CLOSED** in B5.1 (`a5837df`)
   - Verified: `src/ikigai/src/agents/ikigai_maintainer/graph.py:334-383` has `close_graph()` + `atexit.register(close_graph)`.

3. ~~**F9 FilesystemBackend = full home write**~~ ✅ **ALREADY CLOSED** in B5.1 (`a5837df`)
   - Verified: `_FS_ROOT = _PROJECT_ROOT / "data"`, `virtual_mode=True`, comment block explains scope.

4. **F14 zero per-node smoke tests** ❌ STILL OPEN
   - Any regression in IKIGAi-Maintainer is invisible.
   - 8 nodes × ~1 test each.
   - Fix effort: 4-6h.

### DEFERRED (per explicit decision, NOT a defect)

- solverforge-calendar fork — no demand trigger yet (`[[fork-connection-defer-2026-08-30]]`)
- tuiboard fork — same
- a2ui — spec-only per 2026-08-28
- algorithms (M01/N01/A02/A06, IKIGAI weights) — per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]]
- src/operational/ test rot — separately maintained workspace

### DOC-STALE (not blocking, hygiene)

- `interfaces/tui/README.md` — contradicts canonical architecture
  - Fix: SUPERSEDED trailer + redirect to [[interfaces-architecture-2026-08-27]]
  - User explicitly did NOT pick this in deferred decision today; not touching now

---

## 7. Dependency graph (what unblocks what)

```
[ B2 start/stop STUBS ] ─→ enables `life server start mcp_gateway` UX
        │
        └─→ prerequisite for any "production" smoke test of full backend

[ F9 FilesystemBackend scope ] ─→ unblocks any safe agent vault_write path
        │
        └─→ prerequisite for production agent loop (currently unsafe)

[ F4 SqliteSaver leak ] ─→ independent; any long session
[ F14 per-node tests ] ─→ independent; quality gate only
[ F13 retry/timeout ] ─→ independent; partial_prop_ack reduces urgency

[ Backend hardening complete ] ─→ enables algorithm gate per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]]
        │
        └─→ THEN, not before, M01/N01/A02/A06 work is unblocked
```

**Critical path:** F9 (security) → F4 (leak) → B2 start/stop → F14 (tests) → backend hardened → algorithm gate open.

---

## 8. Recommended work sequence (UPDATED 2026-08-30 after B2 shipped + F4/F9 verification)

| # | Task | Effort | Severity | Source | Status |
|---|------|--------|----------|--------|--------|
| 1 | B2 start/stop: implement subprocess.Popen + pidfile | 2-4h | UX blocker | [[backend-phase-reordering-2026-08-28]] | ✅ SHIPPED `0e82e4e` |
| 2 | F9 FilesystemBackend: scope to vault/ | 1-2h | SECURITY | B5.0 audit F9 | ✅ already closed B5.1 `a5837df` |
| 3 | F4 SqliteSaver: wrap in context manager | 1-2h | leak | B5.0 audit F4 | ✅ already closed B5.1 `a5837df` |
| 4 | F14 per-node smoke tests (8 nodes) | 4-6h | HIGH (quality gate) | B5.0 audit F14 | ✅ SHIPPED `fefaa52` |
| 5 | Combo A backlog: #3 ikigai_sync_vault bypass + 5 Minor | 2-3h | MEDIUM | [[combo-a-whole-branch-review-backlog-2026-08-29]] | ✅ SHIPPED `08dcb23` (#3 + #2 already-resolved); 4 Minor deferred |
| 6 | SSE real streaming (Task 14 deferred) | 4-6h | LOW | gateway.py:164-165 TODO | ✅ SHIPPED `0ebb57c` (event bus + chunked TE + heartbeat; full adapter integration still TODO) |
| 7 | interfaces/tui/README.md SUPERSEDED trailer | 5-10min | doc hygiene | user-flagged 2026-08-29 | ✅ SHIPPED `2211881` |

**Updated totals:** Items 2-3 are no-ops (already done). Realistic remaining work: 10-15h for items 4-7.

---

## 9. What is NOT in scope (per memory)

- IKIGAI vector weights (M01/N01/A02/A06) — gated on system readiness, not SONHO
- Fork connections (solverforge-calendar, tuiboard) — gated on user demand
- A2UI — spec-only
- src/operational/ test rot — separately maintained
- §7 attribution aspirational violations — vault_write enforcement is the priority

---

## Related memories

- [[backend-phase-reordering-2026-08-28]] — phase sequence B0-B6 rev.3
- [[b5-0-audit-findings-2026-08-29]] — 14 findings with severity
- [[combo-a-whole-branch-review-backlog-2026-08-29]] — Combo A post-review backlog
- [[fork-connection-defer-2026-08-30]] — fork connection scope lock
- [[interfaces-architecture-2026-08-27]] — forks vs natives architecture
- [[master-branch-carro-chefe-2026-08-28]] — master = deep-agent canonical
- [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] — algorithm work gating
- [[phase-b6-vault-sync-shipped-2026-08-29]] — Phase B close
- [[post-phase-b-audit-hygiene-2026-08-29]] — pre-existing tech debt boundaries