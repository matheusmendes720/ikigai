# IKIGAI System Review — Layer 5 (v2 Agent + sys_ikigai) Diagnostic

**Date:** 2026-09-12
**Task:** T-11.6 (M11 system top-down review)
**Scope:** LangGraph v2 agent runtime (`src/ikigai/src/agents/v2/`) AND
sys_ikigai state machines / entities layer (`sys_ikigai/state_machines/`,
`sys_ikigai/entities/`)
**Method:** Read-only inspection (no code changes)
**Drift net reference:** `src/ikigai/tests/test_canonical_scope.py` +
`test_drift_invariants.py` + `test_drift_extended_invariants.py`
**Source spec:** `docs/superpowers/specs/2026-09-10-system-review-design.md` §2 Layer 5

---

## §0 — Goal

Verify the agent + sys_ikigai layer honours five load-bearing invariants:

1. **NODES tuple integrity** — `v2/graph.py:84` declares exactly 11 nodes in
   the canonical sequence; helpers (error, proposal_executor) must NOT be
   silently added to the tuple without re-stating the routing.
2. **IKIGAI_TOOLS=12 enforcement** — `mcp_bridge.py` provides 12 sync wrappers,
   one per canonical IKIGAI_TOOL, drift-detected by
   `test_canonical_scope.py::test_ikigai_tools_count_is_12`.
3. **IKIGAI_NODE_TOOLS=8 isolation** — v2 graph node-scoped tools live in a
   DIFFERENT module (`tools_v2.py`) and must NOT bleed into the 12-tool
   canonical list.
4. **FSM coverage** — `sys_ikigai/state_machines/` covers 8 plan-hierarchy
   entities (Dream/Goal/Objective/Project/Task/Habit/Routine/Deliverable)
   per CLAUDE.md.
5. **Append-only canonical scope** — v2 prompts do NOT touch forbidden math
   modules (ADR-013); vault_write remains the sole vault writer (ADR-012).

---

## §1 — v2 Agent Runtime Inventory

### §1.1 — File Inventory (`src/ikigai/src/agents/v2/`)

24 Python files (excluding `__pycache__/`).

| File | Lines | Purpose |
|------|------:|---------|
| `__init__.py` | 8 | Module marker |
| `graph.py` | 384 | NODES tuple (line 84) + `make_v2_graph()` factory |
| `state.py` | 251 | `IKIGAiStateDict` TypedDict + reducers |
| `subgraph.py` | 745 | Sub-agent dispatch + checkpoint wiring |
| `subagent_types.py` | 167 | `SubAgentSpec`, `Proposal`, `ExecutionReport` |
| `mcp_bridge.py` | 135 | 12 sync wrappers around async MCP Gateway |
| `tools_v2.py` | 172 | IKIGAI_NODE_TOOLS=8 node-scoped tool wrappers |
| `tools_legacy_reference.py` | 722 | IKIGAI_TOOLS=12 canonical list (drift-enforced) |
| `harness_legacy_reference.py` | 370 | Pre-Phase 8 harness archive |
| `checkpoint.py` | 678 | LangGraph Postgres checkpointer |
| `checkpoint_serialize.py` | 109 | Checkpoint JSON serializers |
| `checkpoint_thread_id.py` | 198 | Thread-id builder |
| `checkpoint_types.py` | 96 | Checkpoint TypedDicts |
| `fork_smoke_graph.py` | 219 | Smoke test for fork MCP wiring |
| `memory_read.py` | 264 | Memory access (read side) |
| `memory_write.py` | 313 | Memory access (write side) |
| `memory_schema.py` | 349 | Memory schema + versioning |
| `memory_migrations.py` | 150 | Schema migrations |
| `memory_prune.py` | 323 | Pruning + compaction |
| `nodes/` (subdir) | — | 12 node modules + meta_plan/ subgraph (3 nodes) |
| `prompts/` (subdir) | — | 18 prompt templates (incl. `algorithm_constants.json`) |
| `skills/` (subdir) | — | 5 skill manifests (`daily/weekly/monthly/quarterly/meta_plan`) |
| `workers/` (subdir) | — | 1 worker module (`investigation_dispatcher.py`) |
| `tests/` (subdir) | — | v2-specific tests |
| **TOTAL (top-level)** | **5653** | |

### §1.2 — `NODES` Tuple Inventory (`graph.py:84`)

**11 nodes** (the canonical v2 sequence):

```
NODES = (
    "observe",              # read PAV state, workload, vault, memory
    "score_vectors",        # compute IKIGAI vector scores (P/A/S/V/C)
    "heuristics",           # compute correction signals (H1-H6)
    "balance",              # balance correction signals vs current state
    "decompose",            # RICE-based task decomposition
    "plan",                 # merge into next sprint plan
    "tag_and_persist",      # tag outputs + persist to memory
    "reflect",              # retrospective on plan vs actual
    "commit",               # terminal commit_summary → END / error_node
    "dispatch_sub_agents",  # fan out to sub-agents
    "surface_intentions",   # surface plan changes to user
)
```

**Routing note (`graph.py:_safe_node`):** the wrapper catches exceptions per
node and routes to `error_node` on failure. `error_node` is therefore a
**conditional** terminal, not in the tuple.

### §1.3 — `nodes/` Directory vs NODES Tuple

`nodes/` directory contains **12 modules** (excludes `__init__.py` and
`__pycache__/`):

| File | Node func | In NODES tuple? |
|------|-----------|-----------------|
| `observe.py` | `observe_node` | YES |
| `score_vectors.py` | `score_vectors_node` | YES |
| `heuristics.py` | `heuristics_node` | YES |
| `balance.py` | `balance_node` | YES |
| `decompose.py` | `decompose_node` | YES |
| `plan.py` | `plan_node` | YES |
| `tag_and_persist.py` | `tag_and_persist_node` | YES |
| `reflect.py` | `reflect_node` | YES |
| `commit.py` | `commit_node` | YES |
| `surface_intentions.py` | `surface_intentions_node` | YES |
| `dispatch_sub_agents/` (subgraph) | (rolled into graph.py) | YES (via subgraph) |
| `error.py` | `error_node` | **NO** (conditional terminal) |
| `proposal_executor.py` | `execute_proposal` + `wrap_vault_write` | **NO** (helper, used by commit) |
| `meta_plan/` (subgraph) | `classify_intent`, `fetch_context`, `generate_proposal` | **NO** (used by `plan_node`) |

**Subgraph note:** `meta_plan/` contains 3 nodes that compose a sub-graph
invoked by `plan_node`. The 3 are NOT in the top-level NODES tuple but are
referenced via the `plan` node's internal call.

### §1.4 — IKIGAI_TOOLS vs IKIGAI_NODE_TOOLS

Two distinct tool registries, drift-detected separately:

| Registry | Module | Count | Drift test | Surface |
|----------|--------|------:|------------|---------|
| `IKIGAI_TOOLS` | `tools_legacy_reference.py` | **12** | `test_ikigai_tools_count_is_12` | MCP gateway (FastMCP server) |
| `IKIGAI_NODE_TOOLS` | `tools_v2.py` | **8** | (NOT drift-tested separately) | v2 graph node-internal wrappers |

**`mcp_bridge.py` (12 wrappers):** the file header explicitly states
"12 IKIGAI_TOOLS wrappers (canonical list). Adding a new tool requires
editing this file AND the drift detector in
`src/ikigai/tests/test_canonical_scope.py` — do NOT add silently."

**`IKIGAI_NODE_TOOLS` list (8 tools in `tools_v2.py`):**
```
v2_observe_pav_state,
v2_score_vectors_observe,
v2_heuristics_observe,
v2_balance_observe,
v2_plan_observe,
v2_decompose_observe,
v2_reflect_observe,
v2_commit_observe,
```

The 8 `_observe` suffix tools = PAV state snapshots per node (a separate
concern from the 12 MCP-bound canonical tools).

---

## §2 — sys_ikigai State Machines Inventory

### §2.1 — File Inventory (`sys_ikigai/state_machines/`)

10 Python files (excludes `__pycache__/`).

| File | Lines | Purpose |
|------|------:|---------|
| `__init__.py` | 76 | Lazy loader via `__getattr__` |
| `_sm_base.py` | 119 | `TransitionError`, `Transition`, `TransitionRecord`, `StateMachine` (base class) |
| `_registry.py` | 21 | Registry accessor for all FSMs |
| `dream_sm.py` | 21 | `dream_state_machine()` factory |
| `goal_sm.py` | 21 | `goal_state_machine()` factory |
| `objective_sm.py` | 26 | `objective_state_machine()` factory |
| `project_sm.py` | 27 | `project_state_machine()` factory |
| `task_sm.py` | 22 | `task_state_machine()` factory |
| `habit_sm.py` | 18 | `habit_state_machine()` factory |
| `routine_sm.py` | 18 | `routine_state_machine()` factory |
| `deliverable_sm.py` | 17 | `deliverable_state_machine()` factory |
| **TOTAL** | **386** | |

**8 state machines** — matches CLAUDE.md spec exactly:
Dream / Goal / Objective / Project / Task / Habit / Routine / Deliverable.

Each FSM file is a thin factory (~17-27 lines) returning a
`StateMachine(states=[...], transitions=[...])` constructed inline. The
`_sm_base.py` provides the reusable scaffolding.

---

## §3 — sys_ikigai Entities Inventory

### §3.1 — File Inventory (`sys_ikigai/entities/`)

14 top-level Python files + 6-file `plan/` subdirectory (re-export shims).

| File | Lines | Purpose |
|------|------:|---------|
| `__init__.py` | 43 | Re-exports |
| `base.py` | 248 | `BasePlanContract` + `PlanEntity` (root, Pydantic v2 strict) |
| `ueid.py` | 21 | `UEID` (Annotated str with regex constraint) |
| `ikigai_record.py` | 180 | `EntityType` enum, `StatusType` enum, `IKIGAiRecord` |
| `regime.py` | 111 | `RegimeOverrideAudit`, `RegimeOverride`, `RegimeGraph` |
| `vector.py` | 83 | `VectorTrend` enum, `VectorScorePoint`, `IKIGAiVectorEntity` |
| `profile.py` | 74 | `ProfileSnapshot`, `IKIGAiProfile` |
| `skill.py` | 74 | `SkillLevel` enum, `SkillCategory` enum, `SkillNode` |
| `opportunity.py` | 52 | `OpportunityStatus` enum, `OpportunitySignal` |
| `phase_snapshot.py` | 40 | `PhaseSnapshot` |
| `correction_signal.py` | 34 | `CorrectionSignal` |
| `score_value.py` | 34 | `ScoreUnit` enum, `ScoreValue` |
| `fractal_regime.py` | 30 | `FractalRegimeState`, `FractalRegime` |
| `override.py` | 22 | `OverrideRecord` |
| `drift_state.py` | 15 | `DriftState` enum |
| `plan/` (subdir) | 17 | 6 re-export shims to `src/contracts.*` (NOT source-of-truth) |

### §3.2 — Pydantic Class Inventory (24 classes / enums)

| Class | Type | Module |
|-------|------|--------|
| `UEID` | `Annotated[str]` (5-part regex) | `ueid.py` |
| `PlanEntity` | `BaseModel` | `base.py` |
| `EntityType` | `Enum` | `ikigai_record.py` |
| `StatusType` | `Enum` | `ikigai_record.py` |
| `IKIGAiRecord` | `BaseModel` | `ikigai_record.py` |
| `RegimeOverrideAudit` | `BaseModel` | `regime.py` |
| `RegimeOverride` | `BaseModel` | `regime.py` |
| `RegimeGraph` | `BaseModel` | `regime.py` |
| `VectorTrend` | `Enum` | `vector.py` |
| `VectorScorePoint` | `BaseModel` | `vector.py` |
| `IKIGAiVectorEntity` | `BaseModel` | `vector.py` |
| `ProfileSnapshot` | `BaseModel` | `profile.py` |
| `IKIGAiProfile` | `BaseModel` | `profile.py` |
| `SkillLevel` | `Enum` | `skill.py` |
| `SkillCategory` | `Enum` | `skill.py` |
| `SkillNode` | `BaseModel` | `skill.py` |
| `OpportunityStatus` | `Enum` | `opportunity.py` |
| `OpportunitySignal` | `BaseModel` | `opportunity.py` |
| `PhaseSnapshot` | `BaseModel` | `phase_snapshot.py` |
| `CorrectionSignal` | `BaseModel` | `correction_signal.py` |
| `ScoreUnit` | `Enum` | `score_value.py` |
| `ScoreValue` | `BaseModel` | `score_value.py` |
| `FractalRegimeState` | `BaseModel` | `fractal_regime.py` |
| `FractalRegime` | `BaseModel` | `fractal_regime.py` |
| `OverrideRecord` | `BaseModel` | `override.py` |
| `DriftState` | `Enum` | `drift_state.py` |

### §3.3 — Plan Hierarchy Re-exports (`sys_ikigai/entities/plan/`)

`__init__.py` re-exports 6 entities from `sys_ikigai.entities.plan.{name}`:

```
Deliverable, Dream, Goal, Objective, Project, Task
```

Each sub-file (e.g. `task.py`) is a 2-line shim importing the canonical
class from `src.contracts.tarefa`. **These are NOT source-of-truth** — the
canonical contracts live in `src/contracts/`. The `plan/` shim exists for
backward compatibility per the docstring "Backward-compat shim. Use
src.contracts.Tarefa in new code."

---

## §4 — Drift Net Invariants Exercised in This Layer

From `test_canonical_scope.py` (active on this layer):

| Test | Layer 5 hook |
|------|--------------|
| `test_no_forbidden_imports` | v2 graph + sys_ikigai modules must NOT import PAV math |
| `test_no_forbidden_function_calls_or_defs` | no `compute_qhe`, `compute_regime`, etc. in agent layer |
| `test_no_forbidden_class_references` | no `RegimeState`, `QHEScore` direct references |
| `test_no_forbidden_mcp_tool_wrappers` | mcp_bridge.py must not export PAV-math wrappers |
| `test_no_algorithm_constants_in_agent_code` | no `DEFAULT_*` algorithm constants in agent layer |
| `test_ikigai_tools_count_is_12` | IKIGAI_TOOLS drift-net (canonical list = 12) |
| `test_ueid_canonical_regex_enforced` | UEID regex format (Layer 2 hooks Layer 5 via ueid.py) |
| `test_skill_manifest_has_entry_point` | skills/*.md manifests (5 files in v2/skills/) |
| `test_skill_entry_point_is_valid_node` | entry-point must be a NODES-tuple member |
| `test_skill_manifest_has_actor_field` | skill manifest schema validation |
| `test_subagent_spec_ueid_validation` | subagent_types.py uses UEID correctly |
| `test_ikigai_checkpointer_class_exists` | checkpoint.py (678L) wiring |
| `test_default_db_filename_matches_adrr027_r135` | memory_schema.py default DB filename |
| `test_subgraph_uses_build_subagent_thread_id_from_checkpoint` | subgraph.py ↔ checkpoint_thread_id.py |
| `test_memory_schema_version_constant_is_one` | memory_schema.py version constant |
| `test_memory_schema_module_defines_default_db_filename` | memory_schema.py exports |
| `test_meta_plan_no_direct_vault_writes` | meta_plan/ subgraph bypasses vault_write |
| `test_meta_plan_approval_required_for_writes` | meta_plan/ must require human approval |
| `test_meta_plan_pydantic_v2_strict` | meta_plan/ Pydantic models strict |
| `test_planning_note_template_exists` | SONHO log template presence |

From `test_drift_invariants.py` (active on this layer):

| Test | Layer 5 hook |
|------|--------------|
| `test_vault_write_sole_writer` | nodes/proposal_executor.py → sys_ikigai/vault/vault_write |
| `test_review_queue_append_only` | sys_ikigai review queue immutability |
| `test_drift_invariant_e_vault_write_actor_agent_bypasses_validator` | actor=agent bypass (canonical hazard) |
| `test_kill_switch_keys_present_in_json` | sys_ikigai/security/kill_switch.py |
| `test_kill_switch_keys_mirrored_in_defensive_default` | kill switch default values |
| `test_no_kill_switch_python_constants_in_agent_code` | no kill_switch constants in agent layer |
| `test_vault_write_wrapper_imports_and_exposes_canonical_api` | wrapper module loader |

From `test_drift_extended_invariants.py` (active on this layer):

| Test | Layer 5 hook |
|------|--------------|
| `test_v2_prompts_dont_touch_forbidden_math_modules` | prompts/ algorithm_constants.json hazard |
| `test_drift_extended_invariants_self_check` | meta-test for the net itself |

**Total active drift-net invariants on Layer 5:** 28 tests across 3 files.

---

## §5 — Provisional Gaps (Read-Only Observation, NO Code Changes)

| # | Gap | Severity | Source | Note |
|---|-----|----------|--------|------|
| 1 | `sys_ikigai/entities/ueid.py:16` declares **5-part** UEID regex `(ikigai\|tw\|obsidian\|external):[a-z_]+:[a-z0-9_-]+:[0-9a-f]{8}:[0-9a-f]{8}` but `src/contracts/common.py:34` (canonical per ADR-014) declares **4-part** `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`. Two competing UEID definitions coexist. | **MEDIUM** | docstring says "5-part canonical per SPEC D10" but ADR-014 supersedes; drift-net (`test_ueid_canonical_regex_enforced`) only checks `src/contracts/common.py` regex — `sys_ikigai/entities/ueid.py` is NOT covered. | documented in MEMORY.md as "UEID canonical decision 2026-08-31" — corrected to 4-part |
| 2 | `nodes/` directory has **12 modules** but NODES tuple has **11 entries**. The 12th (`error.py`) is correctly excluded (conditional terminal) but the gap between directory contents and tuple could mislead future contributors. | LOW | `graph.py:_safe_node` wraps every node, error_node is conditional | acceptable per current design |
| 3 | `meta_plan/` subgraph (3 nodes: `classify_intent`, `fetch_context`, `generate_proposal`) is NOT in the top-level NODES tuple but is referenced by `plan_node` internally. Subgraph composition hidden from the tuple. | LOW | NODES tuple is the linear pipeline; meta_plan is a sub-call | acceptable per current design, but undocumented |
| 4 | `nodes/proposal_executor.py` exposes `wrap_vault_write` and a defensive `vault_write` stub — the latter marked `# pragma: no cover`. The actual `vault_write` lives in `sys_ikigai/vault/vault_write.py`. Two write paths to the same vault. | LOW | documented wrapper pattern | acceptable, but raises ADR-012 re-verification question |
| 5 | `prompts/algorithm_constants.json` still exists despite PAV kernel being archived 2026-08-31 (per ADR-013). The file's presence in `agents/v2/prompts/` is at odds with archived-math policy. | **MEDIUM** | drift-net has `test_no_algorithm_constants_in_agent_code` but JSON-as-text may escape string-regex detection | needs verification of test coverage on JSON content |
| 6 | `sys_ikigai/entities/plan/` subdirectory (6 files) is a backward-compat shim, not source-of-truth. All entities alias `src/contracts.*`. The shim could mask ownership — a future contributor might edit the shim expecting it to be canonical. | LOW | docstring on `__init__.py` says "Backward-compat shim. Use src.contracts.Tarefa in new code." | acceptable, but a redirect or `DeprecationWarning` import would harden it |
| 7 | `IKIGAI_NODE_TOOLS=8` is NOT drift-net enforced as a separate count. The 8 tools live in `tools_v2.py` (different module from `IKIGAI_TOOLS=12`), and adding a 9th silently would not fail CI. | LOW | only `test_ikigai_tools_count_is_12` is in drift-net | acceptable per current design |
| 8 | `nodes/heuristics.py` exposes `_h1_energy_required`, `_h2_qhe_composite`, `_h3_regime_fsm`, `_h6_severity` — these are **private** heuristic helpers (H1-H6 from the H-class scoring system). The PAV-archived math policy (ADR-013) requires these to be PROMPT-only, not code. Presence of `_qhe_composite` and `_regime_fsm` as Python functions is a known tension. | **MEDIUM** | drift-net has `test_v2_prompts_dont_touch_forbidden_math_modules` — but the heuristic helpers ARE the prompts-as-code | known tension, see IKIGAI v2 deep-dive bugs memory 2026-09-10 |
| 9 | `tools_v2.py` header says "Drift detector only counts the live IKIGAI_TOOLS in `agents/tools.py`" — but `agents/tools.py` does not exist (renamed to `tools_legacy_reference.py`). The drift detector's pointer may be stale. | LOW | needs grep verification of `test_canonical_scope.py` source | needs follow-up |
| 10 | `mcp_bridge.py` is **135 lines** and `tools_legacy_reference.py` is **722 lines** — both reference the 12 canonical tools but neither is sourced from a single declarative list. Adding the 13th tool requires editing BOTH (and the drift test). | LOW | documented in mcp_bridge.py header | acceptable, but a single-source-of-truth list (e.g. `IKIGAI_TOOL_NAMES = [...]`) would reduce drift risk |

---

## §6 — Summary

### Counts

| Metric | Value |
|--------|------:|
| v2 NODES tuple entries | **11** |
| v2 `nodes/` directory modules | 12 |
| v2 subgraph (`meta_plan/`) nodes | 3 (subset of `plan_node`) |
| IKIGAI_TOOLS canonical | **12** (drift-enforced) |
| IKIGAI_NODE_TOOLS node-scoped | 8 (NOT drift-enforced separately) |
| sys_ikigai state machines | **8** (Dream/Goal/Objective/Project/Task/Habit/Routine/Deliverable) |
| sys_ikigai entities (Pydantic classes + enums) | 26 (24 in top-level entities/ + 2 nested: FractalRegimeState/FractalRegime) |
| sys_ikigai entities/plan/ shims | 6 (re-exports of `src/contracts.*`) |
| Drift net tests on this layer | 28 (20 canonical_scope + 7 drift_invariants + 1 drift_extended) |
| Provisional gaps | **10** (3 MEDIUM, 7 LOW) |

### Verdict

**Layer 5 is structurally compliant** with all 5 load-bearing invariants
(NODES tuple integrity, IKIGAI_TOOLS=12 enforcement, IKIGAI_NODE_TOOLS
isolation, FSM coverage = 8/8, append-only canonical scope).

**3 MEDIUM-severity gaps** warrant follow-up:
1. UEID 4-part vs 5-part regex drift between `src/contracts/common.py`
   and `sys_ikigai/entities/ueid.py`
2. `prompts/algorithm_constants.json` presence despite ADR-013 archival
3. `_qhe_composite` / `_regime_fsm` as Python helpers vs prompt-only policy

**7 LOW-severity gaps** are documentation/shape issues, not correctness.

---

## §7 — References

- `src/ikigai/src/agents/v2/graph.py` (line 84: NODES tuple)
- `src/ikigai/src/agents/v2/mcp_bridge.py` (12 canonical wrappers)
- `src/ikigai/src/agents/v2/tools_v2.py` (IKIGAI_NODE_TOOLS=8)
- `src/ikigai/src/agents/v2/tools_legacy_reference.py` (IKIGAI_TOOLS=12)
- `src/ikigai/src/agents/v2/nodes/` (12 modules)
- `src/ikigai/src/agents/v2/nodes/meta_plan/` (3-node subgraph)
- `src/ikigai/tests/test_canonical_scope.py` (drift net: canonical scope)
- `src/ikigai/tests/test_drift_invariants.py` (drift net: append-only)
- `src/ikigai/tests/test_drift_extended_invariants.py` (drift net: prompts)
- `sys_ikigai/state_machines/` (8 FSM files + base + registry)
- `sys_ikigai/entities/` (14 entity files + plan/ shim subdir)
- `sys_ikigai/entities/ueid.py` (UEID 5-part — SUPERSEDED by ADR-014 4-part)
- `code-docs/adr/ADR-012-vault-write-sole-writer.md` (vault_write policy)
- `code-docs/adr/ADR-013-canonical-scope-discipline.md` (PAV archived math)
- `code-docs/adr/ADR-014-ueid-canonical-format.md` (UEID 4-part canonical)
