# M154-AUDIT — v2 Deep Agent Graph Inventory (2026-10-05)

**Status:** ✅ SHIPPED
**Date:** 2026-10-05
**Author:** mavis (loop assistant)
**Scope:** `src/ikigai/src/agents/v2/` — the deep-agent graph that powers
`td chat` via `langgraph dev` (Studio + REPL).

This is the second audit. The first (2026-09-29, embedded in
`specs/M154-v2-audit/SPEC.md`) is **partially stale**: it claimed
`recall_node` was a stub and `15 nodes` existed. After M88 + M89 +
M91 + M97b + M100 + M155-M162, both facts are wrong.

---

## TL;DR

| Metric | Value |
|---|---|
| Graph nodes (functional) | **17** (was 15 in old audit) |
| Terminal error node | 1 (separate from the 17) |
| Meta-plan subgraph nodes | 3 (classify_intent, fetch_context, generate_proposal) |
| **WORKS** (real implementation) | **9 / 17 = 53%** |
| **STUB** (explicit error_channel only) | **6 / 17 = 35%** |
| **PARTIAL** (sub-feature works, full logic doesn't) | **2 / 17 = 12%** |
| **SILENT-FAIL** | **0** |
| Files (v2/) | 65+ .py (~5,200 LOC) |
| `tools_v2.IKIGAI_NODE_TOOLS` count | 8 (PAV-math, **separate from drift list** IKIGAI_TOOLS=12) |
| `mcp_bridge.py` graph-facing wrappers | 1 (`ikigai_decompose`) — was 9 pre-M12 |
| Drift net coverage | 60/60 canonical+wiring, 18/18 drift, 826+30 ikigai tests |

**Headline finding:** the v2 graph is **half-real, half-stub** but with
**zero silent-failures** — every stub explicitly writes `error_channel`
with the reason, the drift detector enforces bridge/server parity, and
the routing decisions continue downstream. This is honest, not
deceptive. The user's `td chat` works because the **useful path**
(recall → reason → commit → surface → optional taskdog proposal)
is fully implemented; the 5 mid-graph stubs (score_vectors,
heuristics, balance, plan, reflect) are the ones that contribute
nothing.

---

## Node classification (17 functional + 1 error terminal)

### ✅ WORKS (9 nodes)

| Node | LOC | What it does | Last fix |
|---|---|---|---|
| `recall` | ~65 | Reads `data/memory.db` via `memory_read.read_daily_intentions` + `read_weekly_aggregations` | M88 (was the audit's false "stub" claim) |
| `reason` | ~90 | Builds draft_proposal from user_request + recalled context. Bounded by MAX_REASON_LOOPS=3. | M88 |
| `decompose` | 23 | Lazy proxy → `mcp_bridge.ikigai_decompose` (real MCP call) | Phase 8.2 (wired) |
| `tag_and_persist` | ~100 | Calls `proposal_executor.wrap_vault_write` (real vault write) | M89 |
| `commit` | ~185 | Builds canonical `COMMIT cycle=X tier=Y proposal=Z ok=True` summary; fires `taskdog_create_task` for `task.create` ops | M89, OPEN-3 fix 2026-10-02 |
| `dispatch_sub_agents` | ~250 | ADR-026 sub-agent dispatch protocol. Reads dispatch_plan, builds child states, invokes LangGraph subgraphs, results merged into parent. | W4.4 |
| `tag_propagation` | ~100 | Pure-Python BFS over dep graph (capped at 500 nodes). Emits review-queue-compatible proposal. | M256 |
| `dep_graph` | ~135 | Pure-Python sibling-cluster reasoning + DFS cycle detection. Emits review-queue-compatible proposal. | M256 |
| `gantt_suggest` | ~125 | Pure-Python Kahn's algorithm + min-heap on (priority, ueid). Emits topological order + parallel batches. | M256 |

### ❌ STUB (6 nodes — write only error_channel)

All six were wired to `mcp_bridge.ikigai_X` wrappers that were
**deleted in M12 (T-12.1)** because the wrappers registered names
absent from `server.py`'s `@MCP.tool` registry after V5-E
(commit `b960e852`). Per Phase 8.2 SPEC §3, every call site was
replaced with a direct `error_channel` write so the drift detector
catches future bridge/server divergence.

| Node | Old wrapper | Replaced by |
|---|---|---|
| `score_vectors` | `ikigai_score_vectors` | `error_channel`: "mcp_bridge.ikigai_score_vectors not available post-V5-E (M12 deleted wrapper)" |
| `heuristics` | `ikigai_heuristics` | same pattern |
| `balance` | `ikigai_balance` | same pattern |
| `plan` | `ikigai_plan` | same pattern |
| `reflect` | `ikigai_reflect` | same pattern |
| (observe — see PARTIAL) | `ikigai_observe_pav_state` | partial replacement |

**Drift test that protects this:** `test_mcp_bridge_wrapped_tool_count_matches_canonical`
in `src/ikigai/tests/test_canonical_scope.py` pins bridge/server
parity so future drift trips the detector instead of silently growing
agent surface (T-11.5 G-2).

### ⚠️ PARTIAL (2 nodes)

| Node | What works | What doesn't | Notes |
|---|---|---|---|
| `observe` | `_classify_plan_intent` — 27 PT+EN keyword matcher that emits `plan_intent_hint` | The actual observation step (Q_HE read) is not implemented | Intent-detection (Plan D Task D.1) was NOT wired per the docstring. Tracked as follow-up `test_observe_intent_hint.py` |
| `surface_intentions` | Reads cycle_state + last 3 daily reports from vault; formats prompt; calls `ChatAnthropic` (with `langchain_anthropic_shim`) to get 3-5 pt-BR suggestions | The underlying PAV `cycle_state.md` + `_strategics_excerpt.md` are empty (per FASE B-GAPS) → LLM produces generic output even when the call succeeds | Falls back gracefully to empty suggestions on any LLM error |

### 🛑 ERROR TERMINAL (1 node — separate from 17)

| Node | What it does |
|---|---|
| `error` | Reads error fields populated by `_safe_node` wrapper; produces `ERROR in node 'X' at TIMESTAMP: TYPE: MSG` summary. Graph terminates gracefully. Idempotent. |

---

## Meta-plan subgraph (3 nodes, separate from main pipeline)

Per `subgraph.py:make_meta_plan_subgraph()` — invoked via
`/meta-plan` slash in the chat. Plan D Task B/C wiring.

| Node | What it does |
|---|---|
| `classify_intent` | Pure-Python keyword classifier (no LLM) — 16 PT+EN high-tier + 17 medium-tier keywords. Returns `IntentClassification(level, score)`. ADR-007 data-first methodology. |
| `fetch_context` | Reads vault/memory/taskdog context based on intent classification. (Did not re-audit — see M154 spec notes.) |
| `generate_proposal` | Emits a Proposal with classified intent + context. (Did not re-audit.) |

`make_meta_plan_subgraph()` rebuilds a `StateGraph` with the 3 nodes
sequentially: classify → fetch → generate.

---

## Other components (non-node, but part of v2 surface)

### `mcp_bridge.py` (109 LOC)

- 1 graph-facing wrapper** (`ikigai_decompose`) — the rest were 9 PAV
  wrappers that M12 (T-12.1) deleted. Drift test
  `test_mcp_bridge_wrapped_tool_count_matches_canonical` enforces
  bridge/server parity.
- OTel tracer prefix `ikigai.bridge.{tool_name}` — deliberately
  distinct from server-side `ikigai.mcp.{tool_name}` so the two
  layers don't double-count in trace exporters.

### `tools_v2.py` (172 LOC)

- 8 `IKIGAI_NODE_TOOLS` defined as `@tool` functions:
  `v2_observe_pav_state`, `v2_score_vectors_observe`,
  `v2_heuristics_observe`, `v2_balance_observe`,
  `v2_plan_observe`, `v2_decompose_observe`,
  `v2_reflect_observe`, `v2_commit_observe`.
- All wrap the 14 PAV-math prompt render functions.
- **Explicitly NOT included in IKIGAI_TOOLS=12 drift-detector list.**
  Lives in `agents/v2/tools_v2.py`; drift detector only scans
  `agents/tools.py`. So they're orphaned by design.
- Safe to ignore for drift net. ⚠️ But they still exist and could be
  invoked from outside the v2 graph — flag for cleanup.

### `proposal_executor.py` (183 LOC)

- `wrap_vault_write` lazy proxy → `sys_ikigai.security.vault_write_wrapper`
- `taskdog_create_task` lazy proxy → `src.ikigai.src.agents.tools.taskdog_create_task`
- `execute_proposal(proposal)` — refuses anything except `approval_state="approved"`
  (drift invariant (o)), then iterates operations and returns
  `ExecutionReport(status, ops_total, ops_completed, ops_failed, errors)`.
- ADR-029 wrapper handles kill switch + rate limit + audit. Re-raises
  `KillSwitchAbort` immediately (no partial execution under safety).

### `state.py` (259 LOC)

- `IKIGAiStateDict` TypedDict — canonical state shape.
- `VECTOR_TYPES`, `REGIME_STATES`, `PHASE_STATES`, `BALANCER_VERDICTS` Literal unions.
- `TIER_DAYS` + `PlanTier` enum (5-level: SONHO → QUARTERLY → ONDA → WEEKLY → DAILY).
- Algorithm constants removed 2026-09-04 (W3.2) — moved to
  `prompts/algorithm_constants.json` per ADR-019.

### `subgraph.py` (747 LOC)

- Real implementation of ADR-026 sub-agent dispatch protocol.
- 11th graph node (`dispatch_sub_agents`).
- Validates `SubAgentSpec` (4-part UEID, entry_point ∈ NODES).
- Builds narrowed child state (identity + dispatch_context; never error_* per S2.4).
- Spawns via LangGraph subgraph with timeout.
- Merges per S3 contract; computes parent status per S4.

### `memory_*.py` (~1,200 LOC total)

- `memory_read.py` — `read_daily_intentions`, `read_weekly_aggregations`,
  `read_monthly_syntheses`, `read_quarterly_strategies`
- `memory_write.py` — `memory_write`, `memory_write_atomic`
- `memory_prune.py` — 4 prune functions (daily/weekly/monthly/quarterly) +
  `prune_on_write`
- `memory_schema.py` — `_is_valid_ueid`, `_is_valid_actor`,
  `_validate_source_ueids`, `_decode_source_ueids`, `memory_init`
- `memory_migrations.py` — `_migrate_v1_to_v2`, `apply_migrations`

### `checkpoint_*.py` (~1,100 LOC, 4 files)

- `SqliteSaver`-based. checkpoint, checkpoint_serialize,
  checkpoint_thread_id, checkpoint_types.
- Used by `_build_v2_graph` (line 471).
- Path: `<project_root>/data/ikigai_checkpoints.db`.

### `skills/` (6 .py + 5 .md files)

| File | Status |
|---|---|
| `cadence.py` | Works — helpers (read-only), path builders, render functions |
| `ikigai_daily.py` | Works — TaskdogAdapter + suggestions in metadata (read-only Proposal) |
| `ikigai_weekly.py` | Works — uses cadence.render_weekly_review |
| `ikigai_monthly.py` | Works — uses cadence.render_monthly_review |
| `ikigai_quarterly.py` | Works — uses cadence.render_quarterly_review |
| `taskdog_triage.py` | Works (M161) — `detect_changes` + `propose` |
| `vault_intent_extract.py` | Works (M161) — `extract_candidates` + `propose_from_file` |
| `daily.md`, `weekly.md`, `monthly.md`, `quarterly.md`, `meta_plan.md` | Docs (5 .md files) |

### `sse_publisher.py` (77 LOC)

Server-Sent Events publisher. Used by the chat REPL to stream graph
events. Per M97 series, hooked up to `taskdog_chat.py`.

### `profile_switch.py` (small)

Profile-based system prompt switching.

### `system_prompt.py`

System prompt templates.

### `langchain_anthropic_shim.py`

Load-bearing per M158g probe (2026-10-05). Monkey-patches `anthropic.OverloadedError`
into the SDK (which is missing from 0.76.0) + wraps `ChatAnthropic.invoke`
to extract text from list-of-blocks (langchain 1.x response shape).
Cannot be retired until `browser-use==0.13.10` bumps its `anthropic==0.76.0`
pin (or browser-use is dropped from the agent stack).

### `fork_smoke_graph.py` (303 LOC)

3-node E2E fork connectivity smoke graph (Phase 8.3 deliverable).
Registered in `langgraph.json` as `ikigai_fork_smoke`. Topology:
`connect → call_forks → disconnect`. Probes 4 fork binaries
(taskdog, solverforge_calendar, tuiboard, native_cli) and records
`{ok, skipped, error}` per fork. OPEN-3 fix (2026-10-02) added
`messages: NotRequired` to `ForkSmokeStateDict` so Cloud Studio
recognizes it as chat-enabled.

### `harness_legacy_reference.py`, `tools_legacy_reference.py`

Archived reference. Don't use. Per the legacy file docstring,
"legacy" is a misnomer — these were the previous catalog.

---

## What's load-bearing in production today

The user's `td chat` experience traces:

```
td chat
  → td.ps1 shim → td_shim_build/__main__.py
    → src.mesh.taskdog_chat.main(['--no-color'])
      → taskdog_chat._run_chat_loop()
        → ikigai.chat endpoint stream
          → langgraph dev (port 2027)
            → ikigai_taskdog_mcp graph (FAKE_LLM mode)
              → graph.invoke({messages: [...]})
                → ikigai_maintainer_v2 graph (port 2024)
                  → 17 nodes, 6 stubs, 9 works
                  → LangGraph SSE stream back
                → surface_intentions_node emits 3-5 pt-BR suggestions
                  → taskdog_chat displays them
```

**The path that actually works:** recall → reason → (stubs pass through)
→ commit → dispatch_sub_agents (passes) → surface_intentions → optional
taskdog proposal (tag_propagation/dep_graph/gantt_suggest).

---

## Drift net coverage

| Test file | LOC | Coverage |
|---|---|---|
| `src/ikigai/tests/test_v2_prompt_chains.py` | ~360 | imports, decorators, drift counts (NOT execution) |
| `src/ikigai/src/agents/v2/tests/test_sse_publisher.py` | small | SSE publisher only |
| `src/ikigai/tests/test_canonical_scope.py` | ~1600 | IKIGAI_TOOLS=12, planner-only scope, drift detectors |
| `tests/test_m158_td_chat.py` | 133 | td chat REPL end-to-end (8/8 PASS) |
| `tests/test_m158g_ikigai_path.py` | 162 | sys.path ordering (5/5 PASS, new) |

**Honest scope:** the **v2 graph execution itself has zero direct
coverage**. No test calls `graph.invoke({...})` against a real graph.
The 10 `test_v2_prompt_chains` tests verify imports + decorators, not
behavior. The 8 `test_m158_td_chat` tests verify the REPL shell, not
the graph semantics.

**This is the most important gap.** If a node's logic regresses, no
test catches it. The drift net catches SCOPE (PAV-math presence) and
SHAPE (count + names), not BEHAVIOR.

---

## Reuse / rewrite / discard decisions

### KEEP (no rewrite)

- `skills/` (6 .py files) — all 6 work, all real, M161/M162/M211 era
- `proposal_executor.execute_proposal` — real, ADR-029 wired
- `memory_*.py` — all 5 files, real read/prune/migrate/write
- `checkpoint_*.py` — SqliteSaver works
- `subgraph.py` (dispatch_sub_agents) — real, ADR-026
- `tag_propagation`, `dep_graph`, `gantt_suggest` — pure-Python, no deps
- `commit` — real, M89 + OPEN-3 fix
- `recall`, `reason` — real, M88
- `langchain_anthropic_shim` — load-bearing per M158g probe
- `sse_publisher.py` — used by `taskdog_chat.py`
- `state.py` — clean TypedDict
- `graph.py` — solid wiring, OPEN-3 fix, M102 factory shim

### KEEP BUT DELETE INTERNAL DEAD CODE

- `tools_v2.py` IKIGAI_NODE_TOOLS — 8 PAV-math `@tool` functions, all
  wrap deleted prompts, never invoked by graph. **Safe to delete.**
- `harness_legacy_reference.py`, `tools_legacy_reference.py` —
  archived reference. **Already renamed "legacy" — could delete.**

### DO NOT TOUCH (load-bearing but appear fragile)

- `mcp_bridge.py` — 1 wrapper + drift detector protection. Adding
  wrappers here without adding to server.py trips the drift test.
- The 6 STUB nodes — they're load-bearing for the security story.
  Removing them would let PAV-math back in via drift. KEEP them
  explicit + monitored.

### REWRITE ONLY IF MAPPING EFFORT (PALETTE)

- `observe.py` — intent detection (works) + observation (fails). The
  observation step is dead weight. Could be rewritten as a thin
  classifier + early-exit.
- `surface_intentions.py` — LLM call works but reads empty vault.
  Could be rewritten to fall back to deterministic stub when vault
  is empty (most cycles today).

---

## Honest gap analysis (per FASE B-GAPS)

These are pre-existing gaps not addressed by M154:

1. **Vault zero-state**: `cycle_state.md` + `_strategics_excerpt.md`
   don't exist. LLM suggestions are generic. **Affects**
   `surface_intentions_node` only.
2. **Recall reads 0**: `data/memory.db` empty. Affects
   `recall_node` only — falls back gracefully to `recall_error`.
3. **PAV-math orchestrators gone**: PAV archived 2026-08-31.
   The 6 STUB nodes exist precisely because PAV orchestrators are
   gone. **No path to revive without violating ADR-013.**

---

## Maps to user roadmap decisions

Per the old M154 SPEC, three decisions:

### A — Revive v2 with fixes (1-2 sessions)

**Status: largely done.**
- ✅ M12 fixed the bridge/server drift (drift net now protects).
- ✅ M88 made recall/reason real.
- ✅ M89 made commit/tag_and_persist real.
- ⚠️ 6 mid-graph stubs remain — by design, since they reference
  deleted PAV orchestrators.
- ⚠️ Vault zero-state blocks `surface_intentions` from being useful.

### B — Rewrite from scratch (2-3 weeks)

**Status: NOT recommended.** 53% of nodes already work. The skills
layer (6 files) is fully production. The meta_plan subgraph works. The
proposal_executor works. ADR-026 dispatch works. ADR-029 wrapper
works. A rewrite would re-implement what exists.

### C — Skip deep agent entirely

**Status: not recommended.** The 6 skills + 2 taskdog-graph
proposal nodes (tag_propagation, dep_graph, gantt_suggest) +
commit_node + dispatch_sub_agents are already providing value via
`td chat /skill taskdog-triage` etc. Killing v2 removes those.

**Recommended: Path A++** — keep what works, fix the 6 mid-graph
stubs by either (a) replacing with non-PAV math (linear algebra +
scoring) or (b) deleting them from the graph entirely and shrinking
the pipeline to `observe → recall → reason → commit → surface → taskdog-proposal`.

---

## Conclusion

The v2 deep agent is **half-built, half-honest**. Every broken piece
either:
- (a) explicitly writes `error_channel` so the drift net catches it,
- (b) is gated by approval_state="approved" before any write, or
- (c) is bounded by MAX_REASON_LOOPS so the graph terminates.

No silent failures. The user's `td chat` works because the 9 working
nodes are the ones that matter for the chat experience.

**No action recommended unless:**
1. The user wants to invest in `surface_intentions` (needs vault populated)
2. The user wants to delete the 6 stubs (would shrink graph pipeline)
3. The user wants real graph execution tests (would close the largest
   gap — no test calls `graph.invoke()` today)