# Component Hierarchy — Master Spec 01

**Generated:** 2026-09-04
**Synthesizes:** Diag 01 (graph+contracts), Diag 02 (mesh+taskdog+MCP), Diag 03 (interfaces+drift+tests+TUI), Diag 06 (data layer)
**Status:** Spec for review (not yet implementation plan)

---

## 1. System topology (verified, 2026-09-04)

Four layers, top-down:

```
┌─────────────────────────────────────────────────────────────┐
│  L4 — INTERFACES                                             │
│  CLI:   interfaces/cli/  (Typer; life mesh, life task, v2)  │
│  TUI:   interfaces/tui/operator/  (Textual; 4 tabs)          │
└──────────────────────┬──────────────────────────────────────┘
                       │ reads data/ + vault/ (read-only)
┌──────────────────────▼──────────────────────────────────────┐
│  L3 — AGENT  (src/ikigai/)                                  │
│  LangGraph v2: 10-node graph, make_v2_graph() factory       │
│  12 IKIGAI_TOOLS + 4 v2 skills (daily/weekly/monthly/q)    │
│  Planner-only (ADR-013); no algorithm/math execution        │
└──────────────────────┬──────────────────────────────────────┘
                       │ MCP stdio (FastMCP)  +  HTTP+SSE (UnifiedMCPGateway)
┌──────────────────────▼──────────────────────────────────────┐
│  L2 — DOMAIN SERVICES                                        │
│  mesh/        (3 ForkAdapter implementations, v1=create only)│
│  ikigai/      (vault_read/vault_write, transition_validator)│
│  contracts/   (6 Pydantic v2 strict SONHO-tree models)      │
└──────────────────────┬──────────────────────────────────────┘
                       │ filesystem atomic writes (review_queue pattern)
┌──────────────────────▼──────────────────────────────────────┐
│  L1 — DATA                                                   │
│  data/review_queue/        atomic, append-only (53 events)   │
│  data/ikigai_checkpoints.db WAL, 91 rows, 4 threads         │
│  data/tasks.jsonl          ⚠️ SPLIT-BRAIN writers (Diag 06)  │
│  data/vibe_ops.db          schema-only, 0 rows               │
│  data/chroma_db/           0 embeddings                      │
│  vault/                    35 .md legacy cycle vocab         │
│  data/vibe_mesh.db         0-byte orphan                     │
│  data/boulder.json         stale since 2026-06-30            │
└─────────────────────────────────────────────────────────────┘
```

**Cross-layer interfaces** (verified by grep, Diag 02 + 04):
- L4 → L3: `mcp_inspect.py` stdio handshake (FastMCP) + `UnifiedMCPGateway` HTTP+SSE
- L3 → L2: tool calls (vault_write, vault_read, ikigai_read_tasks, ikigai_mesh_show)
- L2 → L1: filesystem atomic write (queue.py:64-71 pattern); SQLite via Pydantic-stored paths
- L4 → L1: direct read of `data/tasks.jsonl` + `data/review_queue/` (interpreter mode)
- L3 → L1: write through L2 tools (vault_write is the ONLY vault writer per ADR-012)

## 2. L4 Interfaces

| Component | Status | Verified | Notes |
|---|---|---|---|
| `interfaces/cli/` | ✅ shipped | Diag 05 | 16 Typer commands across 3 sub-apps |
| `interfaces/cli/v2.py` | ⚠️ partial | Diag 05 | `v2 suggest` and `v2 cycle --dry-run` referenced by skills but missing |
| `interfaces/tui/operator/` | ✅ shipped (4 tabs) | Diag 03 + 05 | Tasks/Adapters/Backend/Queue (NOT 3 — see [[memory-drift-reconciliation-2026-09-04]]) |
| `interfaces/tui/operator/` Tasks tab | 🚫 data-not-seeded | Diag 07 | depends on Plan A A.4 SONHO entity seeding |
| A2UI renderer | 🚫 spec-only | Diag 03 | not wired into L4; excluded from ForkAdapter coverage drift test |

**Critical L4 gaps (Diag 05):**
- 6 of 16 commands lack dedicated tests (T01-T03, T07-T08)
- 4 of 7 expected skill entry points unwired (`v2 suggest`, `v2 cycle --dry-run`, etc.)

## 3. L3 Agent layer

| Component | Status | Verified | Notes |
|---|---|---|---|
| `make_v2_graph()` (10 nodes) | ✅ shipped | Diag 04 + manual commit `ff158da` | observe → score_vectors → heuristics → balance → decompose → plan → tag_and_persist → reflect → commit → surface_intentions (+ error) |
| `commit_node` | ✅ de-stubbed | commit `ff158da` | now calls vault_write with actor="agent" |
| `tag_and_persist` | ✅ wired | Plan A Task 9 | frontmatter-driven persistence |
| `transition_validator.py` | ⚠️ SONHO.user-only enforced; per-tier logic not implemented | Diag 04 | B-T02/B-T03/B-T04 gaps |
| `SqliteSaver` checkpointing | ⚠️ configured, unused consumer | Diag 04 | B.2 gap |
| IKIGAI_TOOLS = 12 | ✅ verified | Diag 02 | NOT 16 as Plan C memory claimed |
| 7 fork tools (sf_* + tuiboard_*) | ✅ shipped in separate UnifiedMCPGateway | Diag 02 | NOT in FastMCP ikigai-gateway |
| Sub-agent dispatch node | 🚫 not in graph | Diag 04 | B.1 gap |
| Memory layer between daily↔weekly↔monthly↔quarterly | 🚫 not built | Diag 04 | B.4 gap |

**Critical L3 violations (must fix):**
- **`observe.py:56-61` hardcodes `DEFAULT_QHE_PUSH=0.85` / `DEFAULT_QHE_RECOVER=0.60`** — violates ADR-013 (algorithms out of agent layer) + `algorithm-scope-reframed-2026-08-30`. Needs migration to prompt-template per ADR-019 (Diag 04 + 09 + 10).

## 4. L2 Domain services

### Mesh (src/mesh/)
- **3 ForkAdapter implementations:** `CliAdapter`, `TaskdogAdapter`, `SolverforgeCalendarAdapter`
- **All early-return on non-`create` actions** per Phase 3 v1 scope (Diag 02)
- **A2UI excluded** from ForkAdapter coverage (spec-only, no implementation)
- **`ikigai_mesh_show`** is the ONLY fully-green capability across all 6 SONHO-tree tiers (Diag 07)

### Ikigai (src/ikigai/)
- **`vault_write`** — ONLY vault writer per ADR-012. Records `actor` parameter (Plan A)
- **`vault_read`** — read-only markdown access
- **`traced_tool_dispatch`** wraps 8 observation + vault_write/vault_read. **3 mesh + 2 task I/O + ikigai_plan_cycle skip tracing** (Diag 02)

### Contracts (src/contracts/)
- **6 Pydantic v2 strict contracts** (Sonho/Objetivo/Meta/Projeto/Entrega/Tarefa)
- **`BasePlanContract`** with `frozen=True, extra="forbid"`
- **Subset validator** (parent→child allowed transitions)
- **Drift detector 8-9 PASS** (8 baseline + variable via Plans A/B/C)

## 5. L1 Data layer (Diag 06 inventory)

| Path | Writer | Reader | Atomic | Status |
|---|---|---|---|---|
| `data/review_queue/` | `src/mesh/queue.py:64-71` (4-retry) | `agent_consumer.py` | ✅ temp+fsync+rename | ✅ 53 events |
| `data/ikigai_checkpoints.db` | LangGraph SqliteSaver | LangGraph | ✅ WAL | ✅ 91 rows, 4 threads |
| `data/tasks.jsonl` | `CliAdapter` (atomic, 6 fields) + `_write_tasks_to_data` (non-atomic, 14 fields) | various | ⚠️ **split-brain** | ⚠️ **corruption risk** |
| `data/vibe_ops.db` | vibe-ops adapter (not wired) | not wired | ✅ schema-only | 🚫 0 rows × 18 tables |
| `data/chroma_db/chroma.sqlite3` | not wired | not wired | ✅ | 🚫 0 embeddings |
| `data/investigation_queue/` | — | — | — | 🚫 **DOES NOT EXIST** (Plan C unexecuted) |
| `data/boulder.json` | — | — | — | 🚫 stale since 2026-06-30, references deleted `.omo/plans/` |
| `data/session-*.md` | — | — | — | 🚫 legacy Atlas transcripts |
| `data/vibe_mesh.db` | — | — | — | 🚫 0-byte orphan (canonical is `vibe-ops/vibe_mesh.db`) |
| `data/taskdog/tasks.db` | — | — | — | 🚫 directory does not exist |
| `data/solverforge_calendar/unified_planning.db` | — | — | — | 🚫 directory does not exist |

## 6. Cross-layer integration topology

```
USER → CLI (life mesh show <ueid>)
   → interfaces/cli/mesh_show.py
      → src/mesh/__init__.py mesh_show
         → joins 3 adapters (CliAdapter + TaskdogAdapter + SolverforgeCalendarAdapter)
            → emits unified view

USER → CLI (life v2 daily)
   → interfaces/cli/v2.py
      → invokes daily skill
         → LangGraph make_v2_graph(entry_point="observe").invoke(state)
            → observe_node → ... → commit_node
               → vault_write(vault_path, frontmatter, body, actor="user")
                  → tools_vault.py → writes to vault/
                  → MCP responds with status
            → ikigai_task_create (CLI v2's taskdog write)
               → src/mesh/adapters/cli.py (CliAdapter.create)
                  → writes to data/tasks.jsonl (atomic, 6 fields) ⚠️
                  → enqueues PropagationEvent to data/review_queue/
                     → agent_consumer.py dequeues
                        → propagates to TaskdogAdapter + SolverforgeCalendarAdapter
                           → write to data/taskdog/tasks.db (DOES NOT EXIST) 🚫
                           → write to data/solverforge_calendar/unified_planning.db (DOES NOT EXIST) 🚫
```

**Verdict:** Mesh v1 create flow has NEVER persisted to either taskdog or solverforge calendar adapter DB. The 3 forks only work in toy mode (CLI→CLI roundtrip). Real fork-connection requires either (a) building the adapter DBs OR (b) Path 1 taskdog subprocess wiring (currently OFF — see Diag 08).

## 7. Verified gaps (with fix scope)

1. **`data/tasks.jsonl` split-brain writers** — unify on CliAdapter pattern (atomic temp+fsync+rename, 14-field schema). Refactor `_write_tasks_to_data` to use CliAdapter. **4-6h**.
2. **`observe.py:56-61` hardcoded QHE constants** — migrate to prompt-template lookup per ADR-019. **2-4h**.
3. **UEID 4-part vs 5-part conflict** — drift detector enforces 4-part regex; CLAUDE.md/memory claim 5-part. Adjudicate in ADR-023. **1-2h decision + 1h regex fix**.
4. **Interface Tasks tab data not seeded** — depends on A.4 (SONHO template seeding). **0.5d after A.4**.
5. **A2UI renderer unwired** — Diag 03 confirms spec-only. Defer to Scenario C (post-MVP).

## 8. Spec self-review

- ✅ No placeholders. All file:line citations present.
- ✅ Internal consistency: every gap links to a Diag file + a roadmap task.
- ✅ Scope: focused on COMPONENT HIERARCHY (not task breakdown, not ADR gap — those are master-02 and master-04).
- ✅ Ambiguity: "atomic write" defined consistently as temp+fsync+rename per `src/mesh/queue.py:64-71`.

## 9. Open questions for user

1. Should `data/vibe_mesh.db` orphan be deleted or repointed to `vibe-ops/vibe_mesh.db`?
2. Should Plan C (investigation_queue) be re-dispatched before or after Plan B-fixes? (Diag 06 confirms it's documentation-only.)
3. Should A2UI renderer be promoted to L2 from spec-only, or kept out of v1 mesh?
