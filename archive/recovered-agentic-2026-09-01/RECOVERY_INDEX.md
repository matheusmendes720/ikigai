# RECOVERY INDEX — file-by-file inventory

Source: 3 commits from the 2026-08-31 algo-strip cascade + 1 earlier commit.
All files: **READ-ONLY REFERENCE** — do NOT import into live code.

## Group A: ikigai_maintainer (8-node LangGraph) — 13 files

The orchestration architecture user wants to KEEP and refactor.

| File | Lines | Purpose | Refactor target |
|------|-------|---------|-----------------|
| `src_ikigai_src_agents/ikigai_maintainer/graph.py` | 392 | 8-node LangGraph composition: observe→reflect→plan→decompose→score_vectors→heuristics→balance→commit (+ error node) | KEEP structure, REPLACE each node's math with prompt-chain/MCP-tool dispatch |
| `src_ikigai_src_agents/ikigai_maintainer/state.py` | 230 | PAE-style state container with cycle tracking, balancer state, observation history | KEEP structure, REPLACE math fields with planning observations |
| `src_ikigai_src_agents/ikigai_maintainer/nodes/observe.py` | — | Node 1: collect metrics, increment iteration | KEEP — already observation, not math |
| `src_ikigai_src_agents/ikigai_maintainer/nodes/reflect.py` | — | Node 2: reflect on cycle state | REFACTOR — was math-driven, replace with prompt-chain over vault observations |
| `src_ikigai_src_agents/ikigai_maintainer/nodes/plan.py` | — | Node 3: produce next cycle plan | KEEP structure — replace math with LLM prompt chain |
| `src_ikigai_src_agents/ikigai_maintainer/nodes/decompose.py` | — | Node 4: decompose plan into deliverable structure | REFACTOR — was math-driven, replace with vault_read + taskdog_create_task |
| `src_ikigai_src_agents/ikigai_maintainer/nodes/score_vectors.py` | 161 | Node 5: compute IKIGAI vectors (math) | REPLACE — `compute_score()` → `vault_read()` + prompt chain |
| `src_ikigai_src_agents/ikigai_maintainer/nodes/heuristics.py` | — | Node 6: H1-H6 heuristics (math) | REPLACE — `H1..H6()` → `ikigai_read_strategics()` + prompt chain |
| `src_ikigai_src_agents/ikigai_maintainer/nodes/balance.py` | — | Node 7: balancer decision (PUSH/MAINTAIN/REDUCE/RECOVER) | REPLACE — was math FSM, replace with LLM judgment on observations |
| `src_ikigai_src_agents/ikigai_maintainer/nodes/commit.py` | — | Node 8: commit cycle state | KEEP — persistence only |
| `src_ikigai_src_agents/ikigai_maintainer/nodes/error.py` | — | Error node | KEEP — structural |

## Group B: core/scoring — 5 files (math surface to REMOVE)

| File | Lines | Purpose | Refactor target |
|------|-------|---------|-----------------|
| `src_ikigai_src_ikigai/core/scoring/meta_vector.py` | 98 | Compute IKIGAI composite vector | REMOVE — replace with vault observation of PAV-computed value |
| `src_ikigai_src_ikigai/core/scoring/qhe.py` | 103 | Compute Q_HE (Hesitância Emocional Quântica) | REMOVE — math lives in PAV (qhe formula inlined in `contracts/` per `c542ff9`) |
| `src_ikigai_src_ikigai/core/scoring/rice.py` | 74 | RICE prioritization | REMOVE — replace with LLM-driven prioritization in decompose node |
| `src_ikigai_src_ikigai/core/scoring/vector_scores.py` | 186 | Per-dimension vector scoring | REMOVE — replace with `ikigai_read_strategics` + prompt chain |
| `src_ikigai_src_ikigai/core/scoring/__init__.py` | 39 | Re-exports | REMOVE |

## Group C: core/heuristics — 7 files (math surface to REMOVE)

| File | Lines | Purpose | Refactor target |
|------|-------|---------|-----------------|
| `src_ikigai_src_ikigai/core/heuristics/regime.py` | 192 | Regime FSM (PUSH/MAINTAIN/REDUCE/RECOVER) | REMOVE — replace with LLM judgment from observations |
| `src_ikigai_src_ikigai/core/heuristics/cross_priority.py` | 47 | H1 cross-priority heuristic | REMOVE |
| `src_ikigai_src_ikigai/core/heuristics/opportunity_fit.py` | 72 | H2 opportunity-fit heuristic | REMOVE |
| `src_ikigai_src_ikigai/core/heuristics/phase_pivot.py` | 145 | H3 phase-pivot heuristic | REMOVE |
| `src_ikigai_src_ikigai/core/heuristics/skill_velocity.py` | 63 | H4 skill-velocity heuristic | REMOVE |
| `src_ikigai_src_ikigai/core/heuristics/weight_ucb.py` | 70 | H6 weight UCB heuristic | REMOVE |
| `src_ikigai_src_ikigai/core/heuristics/__init__.py` | 43 | Re-exports | REMOVE |

(Note: H5 was `pae_state` heuristic — folded into PAE per attribution §3.)

## Group D: pre-strip agent layer — 2 files (1020 + 566 LOC)

| File | Lines | Purpose | Refactor target |
|------|-------|---------|-----------------|
| `src_ikigai_src_agents/tools_PRE_STRIP_8992e0c.py` | 1020 | `tools.py` BEFORE 8 algo `@tool` wrappers were stripped | KEEP architecture, REMOVE all 8 algo `@tool` wrappers, keep vault_read + external MCP tools. Total: 12 IKIGAI_TOOLS (drift-detector enforced). |
| `src_ikigai_src_agents/deepagents_harness_PRE_STRIP_8992e0c.py` | 566 | `deepagents_harness.py` BEFORE CLI dispatch was stripped | KEEP `_make_agent` + `run_chat` (current shape). Math-driven `--list-checkpoints`, `--run-cycle`, default one-shot mode STRIPPED. |

## Group E: removed langgraph wrappers — 2 patches

| Patch | Lines | Purpose | Refactor target |
|-------|-------|---------|-----------------|
| `vibe_ops_src_langgraph_entry_STRIPPED_IKIGAI_WRAPPER_56cf9d7.patch` | 96 | `make_ikigai_graph` factory + 7 F401 imports stripped | REFACTOR target: rebuild as `make_ikigai_graph` where each node dispatches via MCP tools, not math |
| `langgraph_json_STRIPPED_ikigai_maintainer_entry_56cf9d7.patch` | 40 | `langgraph.json` entry removed | REFACTOR target: re-register when graph is rebuilt |

## Group F: removed MCP wrappers — 1 patch (7 @MCP.tool decorators)

| Patch | Lines | Purpose | Refactor target |
|-------|-------|---------|-----------------|
| `src_ikigai_src_mcp_server_server_STRIPPED_WRAPPERS_240ae08.patch` | 173 | 7 `@MCP.tool` decorators removed: `ikigai_score`, `ikigai_regime`, `ikigai_phase`, `ikigai_corrections`, `ikigai_plan_cycle`, `ikigai_checkpoint`, `ikigai_sync_vault` | KEEP REMOVED — these are math-output tools. The handlers (function bodies) remain in live server.py as orphan archive but never registered. If the refactor needs them again, register with vault_write behind them (read-only by definition — agent observes PAV output, never executes). |

## Group G: core/__init__.py — 1 file

| File | Lines | Purpose | Refactor target |
|------|-------|---------|-----------------|
| `src_ikigai_src_ikigai/core/__init__.py` | 39 | Module entrypoint re-exporting scoring + heuristics | REMOVE — only references deleted submodules |

---

## Total

- **28 source files** in 5 groups (A: 13, B: 5, C: 7, D: 2, G: 1)
- **3 patches** (E: 2, F: 1)
- **~2,500 LOC** of scaffolding (A) + **~1,000 LOC** of math (B+C) + **1,586 LOC** of pre-strip agent (D) + **~309 LOC** of patch context (E+F)
- **No modifications to live code** — everything is in `archive/recovered-agentic-2026-09-01/`
- **Drift detector unchanged** — `IKIGAI_TOOLS = 12` still PASS
- **vault_write invariant unchanged** — 2/2 PASS
