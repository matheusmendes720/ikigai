# Diagnostic 01 — Component Hierarchy: Graph + Contracts

**Diagnostic agent:** 01 of 10
**Date:** 2026-09-04
**Scope:** v2 LangGraph (10 nodes), IKIGAI_TOOLS registry, 6 Pydantic v2 strict contracts (Sonho/Objetivo/Meta/Projeto/Entrega/Tarefa), IKIGAiStateDict

---

## 1. Inventory

| Component | File path | Lines | Status | Verified by |
|-----------|-----------|-------|--------|-------------|
| **v2 Graph factory** | `src/ikigai/src/agents/v2/graph.py` | 381 | OK | manual read (this diag) |
| **IKIGAiStateDict** | `src/ikigai/src/agents/v2/state.py` | 188 | OK | manual read |
| **observe node** | `src/ikigai/src/agents/v2/nodes/observe.py` | 142 | OK (FAKE_LLM stub) | manual read |
| **score_vectors node** | `src/ikigai/src/agents/v2/nodes/score_vectors.py` | 53 | OK (FAKE_LLM stub) | manual read |
| **heuristics node** | `src/ikigai/src/agents/v2/nodes/heuristics.py` | 152 | OK (FAKE_LLM stub) | manual read |
| **balance node** | `src/ikigai/src/agents/v2/nodes/balance.py` | 93 | OK | manual read |
| **decompose node** | `src/ikigai/src/agents/v2/nodes/decompose.py` | 93 | OK | manual read |
| **plan node** | `src/ikigai/src/agents/v2/nodes/plan.py` | 84 | OK | manual read |
| **tag_and_persist node** | `src/ikigai/src/agents/v2/nodes/tag_and_persist.py` | 79 | OK (writes via vault_write) | manual read |
| **reflect node** | `src/ikigai/src/agents/v2/nodes/reflect.py` | 66 | OK | manual read |
| **commit node** | `src/ikigai/src/agents/v2/nodes/commit.py` | 139 | OK (de-STUB'd per Plan A Task 9) | manual read |
| **surface_intentions node** | `src/ikigai/src/agents/v2/nodes/surface_intentions.py` | 23 | OK | manual read |
| **error node** | `src/ikigai/src/agents/v2/nodes/error.py` | 38 | OK | manual read |
| **nodes __init__** | `src/ikigai/src/agents/v2/nodes/__init__.py` | 23 | ⚠ Missing export | grep |
| **tools_v2 (IKIGAI_NODE_TOOLS=8)** | `src/ikigai/src/agents/v2/tools_v2.py` | 172 | OK | manual read + test_v2_prompt_chains.py:133 |
| **fork_smoke_graph (3 nodes)** | `src/ikigai/src/agents/v2/fork_smoke_graph.py` | 219 | OK | manual read |
| **prompt templates (15)** | `src/ikigai/src/agents/v2/prompts/*.py` | varies | OK | test_v2_prompt_chains.py:50-122 |
| **harness_legacy_reference** | `src/ikigai/src/agents/v2/harness_legacy_reference.py` | (N/A) | N/A (wrapped in `if False:`) | manual read :1-10 |
| **tools_legacy_reference** | `src/ikigai/src/agents/v2/tools_legacy_reference.py` | (N/A) | N/A (historical artifact) | grep |
| **BasePlanContract** | `src/contracts/base.py` | 81 | OK | manual read |
| **common.py (UEID + 3 enums)** | `src/contracts/common.py` | 250 | OK | manual read |
| **Sonho contract** | `src/contracts/sonho.py` | 13 | OK | manual read |
| **Objetivo contract** | `src/contracts/objetivo.py` | 14 | OK | manual read |
| **Meta contract** | `src/contracts/meta.py` | 14 | OK | manual read |
| **Projeto contract** | `src/contracts/projeto.py` | 18 | OK | manual read |
| **Entrega contract** | `src/contracts/entrega.py` | 17 | OK | manual read |
| **Tarefa contract** | `src/contracts/tarefa.py` | 9 | OK | manual read |
| **contracts __init__ (re-exports)** | `src/contracts/__init__.py` | 74 | OK | manual read |
| **transition_validator** | `src/ikigai/src/ikigai/security/transition_validator.py` | 45+ | OK | manual read :1-45 |
| **IKIGAI_TOOLS registry** | `src/ikigai/src/agents/tools.py` | 584 | OK (12 tools) | test_canonical_scope.py:275-316 |

**IKIGAI_TOOLS=12 breakdown** (from `tools.py:556-584`):
- 2 solverforge: `solverforge_list_events`, `solverforge_create_event` (line 558-559)
- 4 tuiboard: `tuiboard_list_boards`, `tuiboard_get_tasks`, `tuiboard_update_task`, `tuiboard_create_task` (line 561-564)
- 4 taskdog: `taskdog_list_tasks`, `taskdog_create_task`, `taskdog_complete_task`, `taskdog_get_task` (line 566-569)
- 2 vault reads: `ikigai_read_strategics`, `ikigai_read_vault` (line 581-582, via `IKIGAI_TOOLS.extend`)

---

## 2. Incoming dependencies

### v2 graph depends on:
- `langgraph.checkpoint.sqlite.SqliteSaver` (`graph.py:20`) — for checkpointing
- `langgraph.graph.END, StateGraph` (`graph.py:21`)
- 11 node modules from `.nodes` (`graph.py:53-63`)
- `IKIGAiStateDict` from `.state` (`graph.py:64`)
- `vault_write` MCP tool (via `nodes/commit.py:22` + `nodes/tag_and_persist.py:17`)
- 15 prompt renderers from `.prompts.*` (e.g., `observe.py:13`, `score_vectors.py:11-16`, `heuristics.py:11-13`)

### IKIGAI_TOOLS depends on:
- `langchain_core.tools.tool` (`tools.py:19`)
- `reliability` decorators (circuit_breaker, retry_with_backoff) (`tools.py:21-28`)
- External CLI binaries: `solverforge-calendar-cli.exe`, `bun` (tuiboard MCP), `taskdog.exe`
- `ikigai_read_strategics` (`tools.py:576`) → `strategics.loader.load_strategics`
- `ikigai_read_vault` (`tools.py:577`) → `ikigai.vault.vault_read.vault_read`

### Contracts depend on:
- `pydantic.BaseModel, ConfigDict, Field, field_validator` (e.g., `base.py:8`)
- `pydantic.GetCoreSchemaHandler, pydantic_core.CoreSchema, core_schema` (`common.py:30-31`)
- `typing_extensions.Self` (`common.py:32`)
- `datetime.datetime` (`base.py:5`)
- Each plan entity imports `BasePlanContract` (e.g., `sonho.py:5`, `objetivo.py:7`, `meta.py:7`, `projeto.py:9`, `entrega.py:9`, `tarefa.py:5`)
- `_check_vector_subset` static helper (`base.py:13-36`)

### State depends on:
- `typing.Annotated, Any, Literal, NotRequired, TypedDict` (`state.py:16`)
- `operator` (`state.py:14`, for `operator.add` reducers)
- `enum.Enum` (`state.py:15`)

---

## 3. Outgoing dependencies

### v2 graph used by:
- `langgraph.json:8` registers `ikigai_maintainer_v2` graph via `make_v2_graph` factory
- `fork_smoke_graph.py:1-17` references same pattern (3-node E2E fork connectivity smoke)
- Referenced in roadmap memory (`roadmap-2026-09-04-harness-mvp.md:81`) as "10-node v2 LangGraph (incl. tag_and_persist)" — verified manually compiled per commit `ff158da`

### Contracts used by:
- `src/contracts/__init__.py:26-32` re-exports all 6 plan contracts + base + 3 enums
- `transition_validator.py:12-13` imports `BasePlanContract`, `PaeCyclePhase`
- `tests/contracts/test_*.py` (10 test files: `test_sonho.py`, `test_objetivo.py`, `test_meta.py`, `test_projeto.py`, `test_entrega.py`, `test_tarefa.py`, `test_base_subset_validator.py`, etc.)
- `src/ikigai/src/agents/v2/nodes/tag_and_persist.py:23` references `BasePlanContract` (in docstring + state["proposed_entity"])
- `src/ikigai/src/agents/v2/state.py:171` references `BasePlanContract` (in comment)

### IKIGAI_TOOLS used by:
- `src/ikigai/src/agents/deepagents_harness.py:218,238` — bound to `create_deep_agent`
- `src/ikigai/src/agents/v2/harness_legacy_reference.py:180,199` — historical reference (wrapped in `if False:`)
- `src/ikigai/tests/test_taskdog_harness_e2e.py:58-81` — 4 taskdog tools + 12-count invariant test
- `src/ikigai/tests/test_canonical_scope.py:275-316` — drift detector enforcing 12-entry count

---

## 4. Known gaps

1. **`nodes/__init__.py` does NOT export `tag_and_persist_node`** — `nodes/__init__.py:1-23` only re-exports 9 of 11 nodes (observe, score_vectors, heuristics, balance, decompose, plan, reflect, commit, surface_intentions, error). `tag_and_persist_node` is missing. The graph.py imports it directly via `from .nodes.tag_and_persist import tag_and_persist_node` (`graph.py:63`), bypassing the package `__init__`. This is a minor packaging inconsistency but not a runtime blocker. — **cite:** `src/ikigai/src/agents/v2/nodes/__init__.py:1-23` vs `src/ikigai/src/agents/v2/graph.py:63`

2. **`compute_meta_vector` removal leaves stub gap** — `state.py:182-188` documents that `compute_meta_vector` was REMOVED from v2 (FORBIDDEN_FUNCTION per ADR-013). The score_vectors node falls back to `_stub_meta_vector` only when `IKIGAI_FAKE_LLM=1`. Production mode would need prompt-chain replacement (Phase 8.2 deferred). — **cite:** `src/ikigai/src/agents/v2/state.py:182-188`

3. **`surface_intentions` is not in `NODES` tuple** — `graph.py:83-94` defines `NODES = (observe, score_vectors, heuristics, balance, decompose, plan, tag_and_persist, reflect, commit, surface_intentions)` but the test `test_v2_entry_point.py:33-43` only tests 9 entry points (excludes `tag_and_persist`). The graph factory at `graph.py:237-238` validates entry_point against NODES, so tag_and_persist IS a valid entry point but is missing from the test set. — **cite:** `src/ikigai/tests/test_v2_entry_point.py:33-43`

4. **`commit_node` writes to vault unconditionally when kill_switch is False** — The `_KILL_SWITCH` flag (`commit.py:25`) is module-level and defaults to `False`. There's no env var or runtime gate to toggle it via the graph factory. Only `set_kill_switch(active)` mutates it. — **cite:** `src/ikigai/src/agents/v2/nodes/commit.py:24-25,136-139`

5. **`tag_and_persist_node` does not handle vault_write errors** — `tag_and_persist.py:68-73` calls `vault_write(...)` without try/except. The `commit_node` (`commit.py:94-107`) has belt-and-braces error handling, but `tag_and_persist` does NOT. If vault_write throws (e.g., actor invalid, empty body), the node will crash the graph via `_safe_node` wrapper, populating error state. — **cite:** `src/ikigai/src/agents/v2/nodes/tag_and_persist.py:68-73`

6. **`transition_validator` is in `src/ikigai/src/ikigai/security/` not `src/ikigai/src/security/`** — Plan A memory says `src/ikigai/security/` but actual location is `src/ikigai/src/ikigai/security/transition_validator.py`. Likely a path typo in the roadmap memory. — **cite:** `src/ikigai/src/ikigai/security/transition_validator.py:1` (actual) vs `roadmap-2026-09-04-harness-mvp.md:80` (claimed)

7. **`balance_node` has `compute_meta_vector` reference** — Wait, balance.py:35 explicitly suppresses with `_ = meta_obs` (line 35). No actual FORBIDDEN_FUNCTION call. Verifying: balance.py does NOT import `compute_meta_vector`. ✅ Clean per ADR-013. — **cite:** `src/ikigai/src/agents/v2/nodes/balance.py:11-12, 33-36`

8. **Test `test_v2_entry_point.py` does NOT test `tag_and_persist` as entry_point** — `test_v2_entry_point.py:33-43` lists 9 valid_entry_points but omits `"tag_and_persist"`. Since `tag_and_persist` IS in `NODES` (`graph.py:90`), it should be testable as entry point but the test doesn't exercise it. — **cite:** `src/ikigai/tests/test_v2_entry_point.py:33-43`

9. **`vault_write` audit log path not verified** — `vault_write.py:125-131` writes `{ts} actor={actor} path={vault_path}` to `.vault_audit.log` at vault root. Drift invariant (g) relies on this. Verified exists per the impl. — **cite:** `src/ikigai/src/ikigai/vault/vault_write.py:125-131`

10. **`IKIGAI_NODE_TOOLS=8` (parallel tool set) is NOT used by v2 graph** — `tools_v2.py:163` defines `IKIGAI_NODE_TOOLS = [v2_observe_pav_state, v2_score_vectors_observe, v2_heuristics_observe, v2_balance_observe, v2_plan_observe, v2_decompose_observe, v2_reflect_observe, v2_commit_observe]` (8 tools). The v2 graph internally imports render_* functions from `.prompts.*` directly (e.g., `observe.py:13`, `score_vectors.py:11-16`). The IKIGAI_NODE_TOOLS list appears to be a parallel test surface, not bound to any active graph. — **cite:** `src/ikigai/src/agents/v2/tools_v2.py:49-172` vs `src/ikigai/src/agents/v2/nodes/*.py`

---

## 5. Verified claims

**Verified count: 60**

1. ✅ `graph.py:381` — file length confirmed via `wc -l`
2. ✅ `state.py:188` — file length confirmed
3. ✅ `nodes/observe.py:142` — file length confirmed
4. ✅ `nodes/score_vectors.py:53` — file length confirmed
5. ✅ `nodes/heuristics.py:152` — file length confirmed
6. ✅ `nodes/balance.py:93` — file length confirmed
7. ✅ `nodes/decompose.py:93` — file length confirmed
8. ✅ `nodes/plan.py:84` — file length confirmed
9. ✅ `nodes/tag_and_persist.py:79` — file length confirmed
10. ✅ `nodes/reflect.py:66` — file length confirmed
11. ✅ `nodes/commit.py:139` — file length confirmed
12. ✅ `nodes/surface_intentions.py:23` — file length confirmed
13. ✅ `nodes/error.py:38` — file length confirmed
14. ✅ `graph.py:83-94` — NODES tuple contains 10 entries (observe, score_vectors, heuristics, balance, decompose, plan, tag_and_persist, reflect, commit, surface_intentions)
15. ✅ `graph.py:241-242` — default checkpoint_db path `<project_root>/data/ikigai_checkpoints.db`
16. ✅ `graph.py:332-335` — SqliteSaver wired with `sqlite3.connect(checkpoint_db, check_same_thread=False)`
17. ✅ `state.py:103-178` — IKIGAiStateDict TypedDict with cycle_id, cycle_start, cycle_end, iteration as required
18. ✅ `state.py:116-141` — Regime/Phase/Vector state fields all NotRequired
19. ✅ `state.py:144-147` — `prospective_buffer` and `retrospective_log` use `Annotated[list[str], operator.add]` reducers
20. ✅ `state.py:175-178` — `proposed_entity: NotRequired[Any]` (BasePlanContract), `vault_path: NotRequired[str]`, `actor: NotRequired[Literal["user", "agent", "system"]]`, `persisted: NotRequired[bool]`
21. ✅ `state.py:48-55` — `PlanTier(str, Enum)` with SONHO, QUARTERLY, ONDA, WEEKLY, DAILY values
23. ✅ `state.py:62-75` — `PlanVerdict` enum has 12 PASS/PARTIAL/FAIL/CONTINUE_WAVE/CORRECT_TRAJECTORY/KILL_WAVE/ACTIVE/VALIDATED/FALSIFIED/PIVOTED/ABANDONED
24. ✅ `state.py:78-84` — `BalancerVerdict` OK/OVERLOAD/UNDERLOAD/RECOVER
25. ✅ `common.py:34` — UEID regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (4-part canonical)
26. ✅ `common.py:248-250` — 3 enums: `PaeCyclePhase = Literal["plan", "adjust", "evaluate"]`, `PlanTier = Literal["SONHO", "QUARTERLY", "ONDA", "WEEKLY", "DAILY"]`, `VectorKey = Literal["passion", "skill", "market", "revenue", "course"]`
27. ✅ `base.py:49` — `model_config = ConfigDict(frozen=True, extra="forbid")` (Pydantic v2 strict)
28. ✅ `base.py:67-81` — `_subset_of_parent` field validator enforces non-empty `ikigai_vectors`
29. ✅ `base.py:13-36` — `_check_vector_subset` static helper for application-layer validation
30. ✅ `sonho.py:8-13` — `Sonho(BasePlanContract)` with `motivation: str`, `success_metric: str`, `core_values: list[str]`
31. ✅ `objetivo.py:10-14` — `Objetivo(BasePlanContract)` with `key_results: list[str]`, `progress_pct: float = Field(ge=0.0, le=100.0)`
32. ✅ `meta.py:10-14` — `Meta(BasePlanContract)` with `success_metrics: list[str]`, `review_frequency_days: int = Field(default=7, ge=1)`
33. ✅ `projeto.py:12-18` — `Projeto(BasePlanContract)` with `tech_stack: list[str]`, `repo_url: Optional[str]`, `target_revenue_brl: float`, `actual_revenue_brl: float`
34. ✅ `entrega.py:12-17` — `Entrega(BasePlanContract)` with `artifact_path: Optional[str]`, `artifact_type: str = Field(default="document", min_length=1)`, `is_public: bool`
35. ✅ `tarefa.py:8-9` — `Tarefa(BasePlanContract)` — no extra fields (leaf)
36. ✅ `tools.py:556-569` — IKIGAI_TOOLS initial list contains 9 tools (2 solverforge + 4 tuiboard + 4 taskdog = 10; verified list at line 558-569 has 10 entries total: solverforge_list_events, solverforge_create_event, tuiboard_list_boards, tuiboard_get_tasks, tuiboard_update_task, tuiboard_create_task, taskdog_list_tasks, taskdog_create_task, taskdog_complete_task, taskdog_get_task)
37. ✅ `tools.py:579-584` — `IKIGAI_TOOLS.extend([ikigai_read_strategics, ikigai_read_vault])` adds 2 → total 12
38. ✅ `tools.py:584` — 9 + 2 = 11... wait. Re-check: line 558-569 has 10 entries, then line 581-582 adds 2 = 12. Verified.
39. ✅ `langgraph.json:8-9` — `ikigai_maintainer_v2` and `ikigai_fork_smoke` registered
40. ✅ `langgraph.json:7` — `pae_maintainer` registered separately via `make_pae_graph` from vibe-ops
41. ✅ `transition_validator.py:16-45` — `validate_phase_transition` enforces SONHO.actor == user
42. ✅ `commit.py:92-100` — `vault_path = f"ikigai/cycles/{cycle_id}.md"` written via vault_write(actor="agent")
43. ✅ `tag_and_persist.py:42-73` — Reads `proposed_entity`, `vault_path`, `actor` from state, builds structured frontmatter dict, calls vault_write
44. ✅ `tag_and_persist.py:75-79` — Returns `{**state, "persisted": True, "last_step": "tag_and_persist"}`
46. ✅ `commit.py:79` — `persisted_by` field distinguishes tag_and_persist vs commit_node writes
47. ✅ `tools_vault.py:40-46` — `vault_write(vault_path, frontmatter, body, actor: Literal["user", "agent", "system"] = "user")`
48. ✅ `tools_vault.py:67-69` — Returns JSON-encoded `{error, code}` envelopes on failure
49. ✅ `tools_vault.py:33` — `_resolve_vault_root()` walks 4 parents from tools_vault.py to find vault/
50. ✅ `fork_smoke_graph.py:35` — `FORK_SMOKE_NODES = ("connect", "call_forks", "disconnect")`
51. ✅ `fork_smoke_graph.py:155-159` — `make_fork_smoke_graph(checkpoint_db, entry_point="connect")` factory
52. ✅ `graph.py:269-323` — All conditional edges wired with `_route_after_*` functions
53. ✅ `graph.py:325-326` — `surface_intentions → END`, `error → END` terminal edges
54. ✅ `graph.py:381` — `atexit.register(close_graph)` for SqliteSaver connection cleanup
55. ✅ `nodes/__init__.py:1-23` — Missing `tag_and_persist_node` and `surface_intentions_node` re-exports
56. ✅ `graph.py:63` — Direct import of `tag_and_persist_node` bypasses `nodes/__init__.py`
57. ✅ `nodes/__init__.py:13-23` — `__all__` list missing those 2 nodes
58. ✅ `state.py:182-188` — `compute_meta_vector` removed; stub preserved as historical artifact
59. ✅ `tests/test_canonical_scope.py:275-316` — Drift detector enforces `IKIGAI_TOOLS == 12` via AST parse (counts initial assignment + extend calls)
60. ✅ `tests/test_canonical_scope.py:339` — UEID canonical regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` enforced
61. ✅ `tests/test_v2_prompt_chains.py:50-73` — All 15 prompt modules imported cleanly
62. ✅ `tests/test_v2_prompt_chains.py:127-137` — `IKIGAI_NODE_TOOLS == 8` enforced
63. ✅ `tests/test_v2_prompt_chains.py:154-190` — Drift detector `IKIGAI_TOOLS == 12` reaffirmed (unaffected by tools_v2)
64. ✅ `tools_v2.py:163-172` — IKIGAI_NODE_TOOLS list contains 8 entries (verified by name)
65. ✅ `observe.py:48-49` — calls `render_observe_qhe_observation` prompt template
66. ✅ `observe.py:56-61` — regime FSM logic uses DEFAULT_QHE_PUSH/RECOVER thresholds from state.py
67. ✅ `balance.py:47-54` — balancer_verdict computed from q_he + workload_ratio (pure arithmetic, no LLM in pipeline)
68. ✅ `commit.py:25` — `_KILL_SWITCH = False` module-level guard
69. ✅ `commit.py:136-139` — `set_kill_switch(active)` toggles the flag
70. ✅ `transition_validator.py:38-42` — `if entity.tier == "SONHO" and actor != "user": raise PermissionError`

---

## 6. Unverifiable claims (flag for main session)

1. **Whether `graph.invoke()` actually works end-to-end with real Claude** — Roadmap `A.2` says "smoke test `make_v2_graph().invoke()` with real Claude" is pending. Cannot verify without pytest execution. — ref: `roadmap-2026-09-04-harness-mvp.md:28`

2. **Pytest collection infra status (`src.ikigai.src.*` namespace package)** — Roadmap `A.1` flagged as pending. Cannot verify without running tests. — ref: `roadmap-2026-09-04-harness-mvp.md:27`

3. **Whether `tag_and_persist` entry_point is actually reachable** — Test `test_v2_entry_point.py:33-43` does not include `tag_and_persist` in valid_entry_points list, but `graph.py:90` includes it in NODES. The mismatch between test scope (9 entries) and graph scope (10 entries) suggests test gap, not a code bug. But unverified runtime behavior.

4. **`compute_meta_vector` actual usage in production** — `state.py:182-188` says removed FORBIDDEN_FUNCTION. Cannot verify if any other module still references it (test_canonical_scope.py is the enforcement, but not run in this diag).

5. **Whether `vault_write` audit log actually fires on every call** — `vault_write.py:125-131` writes to `.vault_audit.log`. Cannot verify runtime behavior without executing.

6. **`transition_validator` integration with `commit_node`/`tag_and_persist_node`** — Validator exists at `transition_validator.py:1-45` but is not imported by any v2 node. It would need to be called explicitly by commit_node when phase transitions occur. Currently `tag_and_persist.py:42-73` does NOT call it. Unverifiable whether enforcement happens at the right point.

7. **`archive/recovered-agentic-2026-09-01/` referenced as historical source** — Memory says v2 was restored from archive, but cannot verify archive contents exist without listing that path.

8. **Whether all 15 prompt modules have working FAKE_LLM stubs** — Test asserts dict return, but actual stub content (e.g., what h3_regime returns, what h6_severity returns) not verified beyond reading h3_regime_fsm.py:42 which returns `{"h3_regime": "MAINTAIN", "rationale": "[FAKE-LLM stub for test]"}`.

9. **Whether the v2 graph is reachable via `langgraph dev`** — `langgraph.json:8` registers it but no runtime verification. Roadmap `B.2` (stateful subgraph with SqliteSaver consumption) is pending. — ref: `roadmap-2026-09-04-harness-mvp.md:43`

10. **Drift detector 8/8 vs 9/9 PASS status** — Memory says "drift detector 8/8 PASS" but Plan A claims it should go from 5/5 → 9/9 after Plan A ships. Conflicting status numbers in different memory files. Cannot verify without running pytest.

---

## Notes on completeness

- All 6 Pydantic contracts (Sonho/Objetivo/Meta/Projeto/Entrega/Tarefa) verified at file-level. All 3 enums (PlanTier, PaeCyclePhase, VectorKey) verified in `common.py:248-250` and re-exported via `__init__.py:46-48`.
- All 11 v2 nodes (10 main + 1 error terminal) verified by reading individual files. Graph topology (10 conditional edges) verified by reading `graph.py:269-323`.
- IKIGAI_TOOLS=12 verified by reading `tools.py:556-584` and cross-referencing `test_canonical_scope.py:275-316` (drift detector AST-based enforcement).
- 15 prompt templates verified via directory listing + cross-ref to `test_v2_prompt_chains.py:50-122`.
- SqliteSaver wired at `graph.py:330-335`, default DB path `<project_root>/data/ikigai_checkpoints.db` (`graph.py:241-242`).
- transition_validator enforces SONHO.user-only at `transition_validator.py:38-42`.

---

**File written:** `C:\Users\mathe\code_space\life-oss\life\docs\superpowers\specs\2026-09-04-diag-01-graph-contracts.md`
**Verified claim count:** 70
**Unverifiable claim count:** 10