# B5.0 — Graph & Agent-Loop Audit (infrastructure-only)

**Date:** 2026-08-29
**Author:** Claude (main session, code-verified)
**Scope:** infrastructure ONLY (graph topology, agent loops, harness wiring, MCP transport, per-adapter failure isolation at transport layer)
**Hard scope fence:** no edits to `**/scoring/**`, `**/formula**`, `**/qhe**`, `**/regime**`, `**/weight**`

---

## 1. Topology Map (verified in main session)

### 1.1 Two parallel graph registries (RED FLAG)

The repo has **two langgraph.json files** declaring the **same 6 graphs** via different entrypoints:

| File | Graph | Entrypoint factory | Status |
|---|---|---|---|
| `./langgraph.json` | `ikigai_maintainer` | `./vibe-ops/src/langgraph_entry.py:make_ikigai_graph` | **BROKEN** — line 27 references `life-ops/ikigai/src` (renamed to `src/ikigai/`) |
| `./langgraph.json` | `pae_maintainer`, `quarterly_replan`, `correction_protocol`, `dream_falsification`, `test_de_fogo_rollup` | `./vibe-ops/src/langgraph_entry.py:make_*` | Real (5 graphs from `_make_workflow_dispatcher_graph`) |
| `./src/ikigai/langgraph.json` | `ikigai_maintainer` | `./src/ikigai_wrapper.py:graph` | Real — wraps `agents.ikigai_maintainer.graph.graph()` |

**Finding B5.0-F1 (MEDIUM):** Dual graph registry creates confusion. `make dev-graph NAME=ikigai_maintainer` per memory uses root `langgraph.json` and hits the BROKEN path. The actual working factory is in `src/ikigai/langgraph.json`. **Fix:** consolidate to one registry; canonical entry is `src/ikigai/langgraph.json`. Root `langgraph.json` should either be removed or its `ikigai_maintainer` entry repointed to the working wrapper.

### 1.2 IKIGAi-Maintainer graph topology

`src/ikigai/src/agents/ikigai_maintainer/graph.py:make_ikigai_graph()` builds 8 nodes in linear chain:

```
[START]
   ↓
   observe_node          (collect context from vault/data)
   ↓
   score_vectors_node    (compute 5-vector scores — DEFERRED per scope fence)
   ↓
   heuristics_node       (emit H1-H6 corrections)
   ↓
   balance_node          (workload/capacity check)
   ↓
   decompose_node        (UEID hierarchy walk)
   ↓
   plan_node             (produce plan_cycle output)
   ↓
   reflect_node          (meta-evaluation)
   ↓
   commit_node           (write to vault)
   ↓
   [END]
```

**Conditional edges declared but NOT wired:**
- `_route_after_observe` → kill_switch → commit
- `_route_after_balance` → is_hysteresis_active → plan (skip decompose)
- `_route_after_plan` → ALWAYS reflect (per code; declared alternatives unused)
- `_route_after_reflect` → ALWAYS commit (declared `commit or END` but always returns `"commit"`)

**Finding B5.0-F2 (LOW):** Conditional edge functions exist but several have only ONE return path. The "conditional" name implies a branch that doesn't exist. Dead code or future intent — needs decision (delete or wire).

**Finding B5.0-F3 (MEDIUM):** No error/timeout nodes. Any node that raises an exception will crash the graph run. No retry, no circuit breaker, no fallback to a "partial_commit" terminal.

**Finding B5.0-F4 (HIGH):** SqliteSaver is created inside `make_ikigai_graph` but the connection is NEVER closed. Connection leak on every graph compile + singleton pattern (`graph()` module-level) means connection lives forever. On Windows, `sqlite3.connect(check_same_thread=False)` with no close handler will eventually block under concurrent invocations.

**Finding B5.0-F5 (MEDIUM):** `_graph_tracer.start_as_current_span` is initialized at module import via `init_tracing()`. If `init_tracing()` fails (per comment: "missing OTel libs or empty env vars mean no exporters"), the graph factory still runs but with broken observability. Silent failure mode — no startup check verifies tracing is actually emitting.

### 1.3 Mesh worker + agent loop topology

```
[CLI / MCP tool call] → enqueue(TaskChange) → data/review_queue/<event_id>.json
                                                            ↓
                          review_queue_worker.run_once() — drain loop
                                                            ↓
                          for each pending event:
                              ↓
                          agent_consumer.validate(event)
                              ↓
                              ├── APPROVE  → agent_propagator.propagate()
                              │                              ↓
                              │              for each ForkAdapter (3):
                              │                  try: adapter.apply_change(propagation)
                              │                  except: collect error (PER-ADAPTER ISOLATION ✅)
                              │                  ↓
                              │              if any failed: ack(event_id, "partial_propagation")
                              │              else: ack(event_id, "propagated")
                              │
                              ├── REJECT    → ack(event_id, "rejected")
                              └── CLARIFY   → ack(event_id, "clarified")
```

**Verified per-adapter failure isolation:** `agent_propagator.py:40-51` — each `adapter.apply_change(propagation)` wrapped in try/except; failure collected, doesn't propagate. ✅

**Verified idempotency at queue layer:** `queue.py:39-48` `consume_pending()` only yields `status=="pending"` events; ack flips to terminal status, re-iteration skips them. ✅

**Verified dedup at CLI fork:** `cli.py:51-62` reads existing JSONL before write, skips if UEID present. ✅

**Finding B5.0-F6 (LOW):** `agent_consumer.py:51-65` "UEID collision" check has silent failure mode — `except (ImportError, AttributeError): pass`. If the queue module disappears, the collision check is silently skipped. Should at least log a warning.

**Finding B5.0-F7 (MEDIUM):** `agent_propagator.py:53-54` — on partial_propagation, ack but no DLQ or retry mechanism. Event is lost if all adapters keep failing. Future v1.2+ work.

### 1.4 MCP gateway transport topology

`src/ikigai/src/mcp_server/server.py` (FastMCP-decorated, 13 tools + 6 resources per B3.6 contract).

Transport chain:
```
[External client] ↔ stdio MCP ↔ [server.py:_TOOL_DISPATCH] ↔ [handler function]
                                                                     ↓
                                                              [contracts/<model>]
                                                                     ↓
                                                       [adapters or queue operations]
```

**Finding B5.0-F8 (MEDIUM):** MCP dispatch gap (B1 fix from reorg-bugs-p0) was verified repaired per `reorg-bugs-p0-fixed-2026-08-27`. But there's no regression test that exercises multi-tool chains. The original bug was "8 tools mapped, 2 missing" — current count is 13, but coverage matrix is undocumented.

### 1.5 DeepAgent harness wiring (`deepagents_harness.py`)

**Verified:** harness uses `create_deep_agent` from `deepagents` package with:
- 8 IKIGAi tools (from `agents/tools.py:IKIGAI_TOOLS`)
- `FilesystemBackend(root_dir=Path.home(), virtual_mode=False)` — **full system access**
- `SqliteSaver` checkpointer (same singleton issue as F4)
- Optional `interrupt_on={"write_file": True}` for HITL
- `ChatAnthropic(model=model_name, base_url=base_url, ...)` — MiniMax API

**Finding B5.0-F9 (HIGH):** `FilesystemBackend(root_dir=Path.home(), virtual_mode=False)` grants the agent UNRESTRICTED read/write to the user's entire home directory. This is a **blast radius risk** if the LLM misfires. Should be scoped to `data/` + `vault/` only via virtual_mode=True OR an allowlist.

**Finding B5.0-F10 (MEDIUM):** Default checkpoint DB is `~/.ikigai/ikigai_checkpoints.db` (per memory `life-ops-ikigai-lock-2026-08-27`, this path is **Windows-locked** when the directory exists with stray tilde-prefixed files). Should default to a project-local path inside `data/` instead of user home.

**Finding B5.0-F11 (MEDIUM):** `run_chat()` is a 270-line monolithic REPL. Command parsing is inlined; no command registry, no abstraction. Hard to test, hard to extend. Refactor candidate for B5.2 if scope allows.

### 1.6 State persistence (`IKIGAiStateDict`)

**Verified:** Pydantic `TypedDict` with `Annotated[list, operator.add]` for accumulation fields (prospective_buffer, retrospective_log, corrections, messages). LangGraph merges these via `operator.add` across node returns.

**Finding B5.0-F12 (LOW):** `IKIGAiStateDict` is `TypedDict, total=False` (all fields optional). Any node that returns `None` for a required field will silently corrupt state on next node. Should be `total=True` for required identity fields (`cycle_id`, `iteration`).

---

## 2. Failure Mode Table

| Async tool call | Timeout | Retry | Circuit breaker | Failure sink | Status |
|---|---|---|---|---|---|
| `adapter.apply_change()` | none | none | none | per-adapter result (isolated) | OK for v1 |
| `queue.enqueue()` (atomic write) | none | none | none | exception propagates to caller | Needs call-site handling |
| `queue.ack()` (atomic write) | none | none | none | silent no-op if event missing | OK (idempotent) |
| `queue.consume_pending()` | none | none | none | `continue` on malformed file | OK |
| `agent_consumer.validate()` | none | none | none | returns Decision.CLARIFY | OK |
| `agent_propagator.propagate()` | none | none | none | ack as `partial_propagation` | OK for v1, but no DLQ |
| `langgraph graph.invoke()` | none | none | none | exception crashes graph run | **NEEDS HANDLING (F3)** |
| `langgraph SqliteSaver` checkpoint | none | none | none | exception crashes run | **NEEDS HANDLING (F4)** |
| `MCP tool call` | none | none | none | exception returned to client | OK for v1 |
| `deepagents agent.invoke()` | none | none | none | `run_chat` catches and tries fallback | OK but verbose |

**Cross-cutting finding B5.0-F13 (HIGH):** Zero retry/timeout/circuit-breaker at the graph and queue transport layers. Any transient failure (DB lock, file system pressure, SQLite busy) becomes a hard crash. B5.1 must add at minimum: per-node try/except with state-aware fallback, SqliteSaver connection lifecycle, and queue ack retry on EBUSY.

---

## 3. Wiring Audit (tool → node → state)

### 3.1 Mesh worker (✅ wired end-to-end)

| Component | What it does | Verified |
|---|---|---|
| `interfaces/cli/read_tasks.py` plan-add | builds TaskChange + enqueues | ✅ B5.1 smoke |
| `interfaces/cli/read_tasks.py` plan-list | joins 3 adapter slices | ✅ B5.1 smoke |
| `mesh/queue.py` enqueue | atomic write to data/review_queue/ | ✅ |
| `mesh/review_queue_worker.py` run_once | drain loop | ✅ B4 e2e |
| `mesh/agent_consumer.py` validate | APPROVE/REJECT/CLARIFY | ✅ |
| `mesh/agent_propagator.py` propagate | per-adapter dispatch | ✅ |
| `mesh/adapters/cli.py` apply_change | JSONL append with dedup | ✅ v1.2 fix |
| `mesh/adapters/taskdog.py` apply_change | SQLite UPSERT | ✅ |
| `mesh/adapters/solverforge_calendar.py` apply_change | SQLite UPSERT (UPI column) | ✅ |
| `src/ikigai/src/mcp_server/server.py` ikigai_task_create | builds TaskChange + enqueues | ✅ B3.6 contract |

### 3.2 IKIGAi-Maintainer graph (PARTIALLY wired)

| Tool | Calls | Wired to | Status |
|---|---|---|---|
| `ikigai_score` | scoring modules (DEFERRED) | `score_vectors_node` | ⚠️ deferred |
| `ikigai_regime` | regime + hysteresis | `balance_node` | partial |
| `ikigai_phase` | phase iteration | `plan_node` | partial |
| `ikigai_corrections` | H1-H6 heuristics | `heuristics_node` | partial |
| `ikigai_decompose` | UEID walk | `decompose_node` | partial |
| `ikigai_plan_cycle` | full 8-node invoke | `make_ikigai_graph()` | partial |
| `ikigai_sync_vault` | write vault markdown | `commit_node` | partial |
| `ikigai_checkpoint` | checkpoint thread mgmt | `SqliteSaver` | partial |

**Finding B5.0-F14 (HIGH):** None of the 8 nodes has a smoke test that exercises it in isolation. Tools call `invoke({"thread_id": ...})` on the whole graph, but there's no per-node regression test. If `decompose_node` regresses, the failure shows up as "plan_cycle returned nothing useful" — no targeted diagnostic.

### 3.3 deepagents harness (WIRED but risky)

| Component | Status |
|---|---|
| `_make_agent()` factory | ✅ |
| `IKIGAI_TOOLS` registry (8 tools) | ✅ per system prompt |
| `FilesystemBackend` | ⚠️ full system access (F9) |
| `SqliteSaver` checkpointer | ⚠️ connection leak (F4) |
| `run_chat()` REPL | ✅ but monolithic (F11) |
| HITL `interrupt_on={"write_file": True}` | ✅ opt-in flag |

---

## 4. Pre-B5.1 Blockers (must address before integration)

| # | Severity | Issue | Minimum fix |
|---|---|---|---|
| F4 | HIGH | SqliteSaver connection leak | wrap with context manager OR explicit `.close()` in graph singleton reset |
| F9 | HIGH | FilesystemBackend root = home dir | scope to `data/` + `vault/` via virtual_mode=True |
| F13 | HIGH | No retry/timeout/circuit-breaker at graph layer | wrap `graph.invoke()` in retry decorator; document timeout policy |
| F3 | MEDIUM | No error/timeout nodes in graph | add `error_node` terminal; route exceptions there |
| F10 | MEDIUM | Default checkpoint DB in user home (Windows lock risk) | default to `data/ikigai_checkpoints.db` |
| F1 | MEDIUM | Dual langgraph.json | consolidate to `src/ikigai/langgraph.json` |
| F11 | MEDIUM | run_chat() monolithic REPL | extract command registry |

## 5. Pre-B5.1 Nice-to-haves (B5.2 candidates)

| # | Severity | Issue |
|---|---|---|
| F2 | LOW | Unused conditional edge branches — delete or wire |
| F6 | LOW | Silent failure in UEID collision check |
| F8 | MEDIUM | No MCP multi-tool chain regression test |
| F12 | LOW | TypedDict total=False allows required field omission |
| F14 | HIGH | No per-node smoke tests for IKIGAi-Maintainer graph |

## 6. Smoke Test Plan for B5.4 (infrastructure-only)

| Test | Verifies |
|---|---|
| `test_graph_compile_idempotent` | `make_ikigai_graph()` called twice produces two compilations without leaking connections |
| `test_graph_observe_to_commit_e2e` | Mock all 8 nodes, assert state shape passes through linearly |
| `test_graph_kill_switch_routes_to_commit` | `state["kill_switch_triggered"]=True` → `_route_after_observe` returns "commit" |
| `test_worker_per_adapter_isolation` | Mock 1 adapter to raise, others succeed → event acked as `partial_propagation`, results list has 1 failure + 2 success |
| `test_queue_ack_idempotent` | ack twice with same status → no exception, no double-write |
| `test_mcp_dispatch_coverage` | All 13 tools have entries in `_TOOL_DISPATCH`; contract test asserts full coverage |
| `test_filesystem_backend_scoped` | After F9 fix, agent cannot `ls` outside data/ + vault/ |
| `test_savereaper_lifecycle` | `make_ikigai_graph` then `del _graph_instance` → connection closed (or documented as leaked) |

## 7. Out-of-Scope Reminder

**DO NOT TOUCH** (deferred per system-readiness gate):
- `src/ikigai/src/agents/ikigai_maintainer/nodes/score_vectors.py` (vector math)
- `src/contracts/metrics.py` (QHE formulas)
- `src/ikigai/src/agents/ikigai_maintainer/nodes/heuristics.py` (H1-H6 thresholds)
- `src/ikigai/src/agents/ikigai_maintainer/nodes/balance.py` (regime FSM math)
- `src/ikigai/src/agents/ikigai_maintainer/state.py` (constants `DEFAULT_QHE_PUSH=0.85`, etc.)
- Any `**/scoring/**`, `**/formula**`, `**/weight**`, `**/regime/**` (math)
- `src/ikigai/data/matheus/ikigai_state/profile-2026-07-03.md` (vector scores)

---

## 8. Recommendation for B5.1

**Sequence (decreasing severity):**

1. **F9 (HIGH):** Scope FilesystemBackend to `data/` + `vault/` — security blast radius.
2. **F4 (HIGH):** SqliteSaver connection lifecycle — fix leak before more code depends on it.
3. **F13 (HIGH):** Add retry/timeout wrapper for `graph.invoke()` — production resilience.
4. **F3 (MEDIUM):** Add `error_node` terminal + exception routing in graph factory.
5. **F10 (MEDIUM):** Move default checkpoint DB off `~/.ikigai/` to `data/`.
6. **F1 (MEDIUM):** Consolidate langgraph.json (delete root or repoint `ikigai_maintainer` to working wrapper).

**B5.2 candidates:** F11 (run_chat refactor) — only if B5.1 has spare capacity.

**B5.3 prerequisite:** F14 (per-node smoke tests) should be added incrementally during B5.3 wiring, not all upfront.

**Estimated effort:** F9+F4+F13 = ~3-4h. F3+F10+F1 = ~2h. Total B5.1 = ~5-6h.
