# Review L6 — Consumer-Facing Layers (vibe-ops + interfaces + drift net + langgraph registry)

**Task:** T-11.7 (M11 IKIGAI Agentic System Top-Down Review)
**Branch:** master
**Date:** 2026-09-12
**Scope:** `vibe-ops/`, `interfaces/`, drift net tests (`src/ikigai/tests/`), `langgraph.json` (read-only inspection)

---

## Summary

| Check | Result |
|------|--------|
| `data/vibe_ops.db` exists | YES — 143 360 bytes, mtime 2026-06-03 (stale — pre-archive) |
| PAV kernel archived | YES — `archive/legacy-pav/src-operational/` per ADR-024 |
| PAV constants in `vibe-ops/src/` | PARTIAL — still referenced inside the registered `pae_maintainer` LangGraph graph (not fully cleared) |
| `interfaces/cli/` subcommands | 19 (8 top-level + 5 kill-switch + 5 server + 1 v2) |
| `interfaces/tui/operator/` tabs | **5** (Tasks / Adapters / Backend / Queue / KillSwitch) — CLAUDE.md says 4 (drift) |
| `kill_switch` operational | YES — `sys_ikigai/security/kill_switch.py` (494 L) + `interfaces/cli/kill_switch.py` (514 L) + TUI 5th tab |
| Drift net invariant count | **34** (23 + 7 + 4) — matches expected |
| `langgraph.json` graphs | **3** (pae_maintainer, ikigai_maintainer_v2, ikigai_fork_smoke) — CLAUDE.md says 5 (drift) |
| Provisional gaps | 7 (see §6) |

---

## 1. `vibe-ops/` State — Cybernetic Engine

### 1.1 `data/vibe_ops.db`

- Exists at `data/vibe_ops.db` — 143 360 bytes (SQLite)
- mtime 2026-06-03 11:36 — **stale** relative to current code (5-month-old snapshot, no live writer active on master)
- Implication: `vibe_ops.db` is treated as a historical artifact; live cybernetic loop is dormant on master per the
  "PAV desativated" decision in MEMORY (`legacy-pav-ui-era-2026-08-28.md`)

### 1.2 `vibe-ops/` directory inventory

Top-level dirs (only those relevant for review):

| Dir | Role | Notes |
|-----|------|-------|
| `src/agents/pae_maintainer/` | LangGraph `pae_maintainer` graph | **STILL LIVE** — registered in `langgraph.json`; imports Q_HE constants |
| `src/agents/__init__.py` | Marker | — |
| `src/models/habit_entities.py` | Habit Pydantic models | References `weight_in_qhe` field |
| `src/pipeline/ikigai_scorer.py` | Q_HE scorer | Reads metrics table, returns 0–1 scale |
| `src/langgraph_entry.py` | LangGraph entry factory | Only exports `make_pae_graph` |
| `architecture/`, `artifacts/`, `base/`, `context/`, `contracts/`, `doc/`, `dry_run.py`, `migrations/`, `planning/`, `schema_registry/`, `scratch/`, `scripts/` | legacy / spec / scaffolding | Not exercised at runtime |

### 1.3 PAV constants still present in `vibe-ops/src/`

Even after `archive/legacy-pav/src-operational/` archival (per ADR-024, `pav-kernel-archived-2026-08-31.md`), the
PAV constants remain imported inside the registered `pae_maintainer` graph:

| File | PAV identifier | Usage |
|------|---------------|-------|
| `vibe-ops/src/agents/pae_maintainer/state.py` | `Q_HE`, `PAVConstants.DEFAULT` | Constants module, RECOVER threshold logic |
| `vibe-ops/src/agents/pae_maintainer/nodes.py` | `Q_HE`, `PAVConstants.QHE_RECOVER_THRESHOLD` | Workload-vs-capacity + Q_HE hysteresis |
| `vibe-ops/src/agents/pae_maintainer/graph.py` | `Q_HE` | Linked ADR-006 period schema |
| `vibe-ops/src/agents/pae_maintainer/main.py` | `Q_HE` | Linked ADR-006 constants |
| `vibe-ops/src/agents/pae_maintainer/__init__.py` | `Q_HE` | Linked ADR-006 constants |
| `vibe-ops/src/models/habit_entities.py` | `weight_in_qhe` | Pydantic field |
| `vibe-ops/src/pipeline/ikigai_scorer.py` | `Q_HE` | Scorer read path |

**Verdict:** "PAV archived" applies to the **kernel source** (`archive/legacy-pav/src-operational/`); the LangGraph
graph `pae_maintainer` itself still embeds PAV constants in-state. The graph is dormant (no live caller) but the
constants are load-bearing inside the compiled StateGraph. **Incomplete archive** — see Gap G-1.

### 1.4 Cybernetic engine (composition paths)

Per attribution §3, the daily-loop composition paths in `vibe-ops/src/cybernetics/daily_loop.py` raise
`NotImplementedError`. Confirmed by MEMORY (`master-branch-carro-chefe-2026-08-28.md`): IKIGAI agent observes
feedback only — does NOT execute the Target→Sensor→Adjuster loop. No drift here.

---

## 2. `interfaces/` Consumer Layers

### 2.1 `interfaces/cli/` — Typer CLI hub (2 045 LOC, 6 files)

| File | LOC | Role |
|------|-----|------|
| `__init__.py` | 46 | Path fixup + `app` composition |
| `__main__.py` | 6 | `python -m interfaces.cli <cmd>` |
| `read_tasks.py` | 529 | Top-level commands (`list`, `done`, `stats`, `mesh-show`, `task-add`, `plan-add`, `plan-list`, `deep-agent-tasks`) + wires kill-switch sub-app |
| `kill_switch.py` | 514 | `kill-switch` sub-app (`status`, `history`, `pause`, `resume`, `recover`) |
| `server.py` | 548 | `server` sub-app (`ls`, `inspect`, `status`, `start`, `stop`) |
| `v2.py` | 193 | `v2` sub-app (`plan` only — V5-F inlined `_v2_plan.py`) |
| `_kill_switch_helpers.py` | 209 | Pure helpers (paths, atomic write, audit, history read) |

### 2.2 CLI command inventory (19 commands)

**Top-level (`python -m interfaces.cli ...`)** — 8 commands
- `list` — read tasks from `data/tasks.jsonl`
- `done <task_id>` — append `data/feedback.jsonl`
- `stats` — aggregate by horizon / priority
- `mesh-show <ueid>` — cross-fork join (CLI + taskdog + solverforge-calendar)
- `task-add` — producer (CliAdapter slice + enqueue TaskChange)
- `plan-add` — write to `data/plan_queue/`
- `plan-list` — read plan queue
- `deep-agent-tasks` — filter Deep Agent output

**Sub-app `kill-switch`** — 5 commands (W5.3 SHIPPED 2026-09-06)
- `status`, `history`, `pause`, `resume`, `recover`

**Sub-app `server`** — 5 commands
- `ls`, `inspect <name>`, `status`, `start <name>`, `stop <name>`

**Sub-app `v2`** — 1 command (V5-F post-cleanup)
- `plan` (Plan D meta-planner — V5-D retired daily/weekly/today)

### 2.3 `interfaces/tui/operator/` — Textual 5-tab operator (5 tabs, NOT 4)

**File:** `interfaces/tui/operator/app.py` (460 L) + `_kill_switch_tab.py` + `data.py` + `styles.tcss`

**Tab bindings (Textual `Binding` lines 91–95):**

| Key | Tab | Source |
|-----|-----|--------|
| `1` | Tasks | Phase 9 |
| `2` | Adapters | Phase 9 |
| `3` | Backend | Phase 9 |
| `4` | Queue | Phase 9 |
| `5` | KillSwitch | W5.3 (2026-09-06) |

**Drift vs CLAUDE.md:** The CLAUDE.md table reads "Textual 4-tab operator (Chat / Tasks / State / KillSwitch)"
but the actual code defines **5 tabs** and the names are **Tasks / Adapters / Backend / Queue / KillSwitch**
(no `Chat`, no `State`). See Gap G-2.

### 2.4 `kill_switch` Operational Verification

**YES — operational on all 3 surfaces:**

1. **Canonical activation engine:** `sys_ikigai/security/kill_switch.py` (494 L)
   - 14 functions: `_now_epoch`, `_generate_event_id`, `_make_kill_ueid`, `_generate_timestamp_slug`,
     `_parse_vault_frontmatter`, `_check_env_var_active`, `_check_vault_file_active`,
     `_check_data_file_active`, `check_kill_switch`, `_recovery_path_for_reason`, `_atomic_write_json`,
     `_append_audit_log`, `fire_kill_switch`, `build_kill_switch_event`, `recover_kill_switch`
   - 4 activation sources: env_var (`IKIGAI_KILL_SWITCH=1`), vault_file, data_file, multiple-priority resolver
   - Exit code contract (per docstring lines 28–32): `status` exit 1 when active / 0 otherwise;
     `pause` exit 1 refuses when active / 0 writes when inactive; `resume` exit 2 without `--confirm`,
     exit 3 with empty `--reason`, exit 0 on confirm; etc.

2. **CLI consumer:** `interfaces/cli/kill_switch.py` (514 L)
   - Pure consumer of `sys_ikigai.security.kill_switch` — does NOT redefine activation logic
   - 5 subcommands: `status`, `history`, `pause`, `resume`, `recover`
   - Imports from canonical: `check_kill_switch`, `fire_kill_switch`, `recover_kill_switch`, `build_kill_switch_event`

3. **TUI 5th tab:** `interfaces/tui/operator/_kill_switch_tab.py`
   - W5.3 KillSwitch consumer UX
   - Persistent banner on active state

---

## 3. Drift Net Invariant Matrix

Three test files in `src/ikigai/tests/` form the Drift net:

| File | LOC | Test fns | Coverage domains |
|------|-----|---------|-----------------|
| `test_canonical_scope.py` | 1 129 | **23** | IKIGAI planner-only scope (ADR-013), IKIGAI_TOOLS count = 12, UEID 4-part regex (ADR-014), fork adapter protocol, review queue append-only, investigation queue invariants, skill manifest validation, checkpointer, subagent thread ID, memory schema v1, meta-plan invariants, planning note template |
| `test_drift_invariants.py` | 297 | **7** | kill_switch keys + constants + defensive default, vault_write wrapper canonical API, vault_write actor-agent bypass validator, legacy drift invariants a-d, wrapper module loading in sys.modules |
| `test_drift_extended_invariants.py` | 295 | **4** | vault_write sole writer (extended), review_queue append-only (extended), v2 prompts don't touch forbidden math modules, self-check |
| **TOTAL** | **1 721** | **34** | — |

### 3.1 Canonical scope invariants (`test_canonical_scope.py` — 23 tests)

```
test_no_forbidden_imports
test_no_forbidden_function_calls_or_defs
test_no_forbidden_class_references
test_no_forbidden_mcp_tool_wrappers
test_no_algorithm_constants_in_agent_code
test_ikigai_tools_count_is_12
test_ueid_canonical_regex_enforced
test_fork_adapter_protocol_coverage
test_review_queue_append_only
test_investigation_queue_invariants
test_skill_manifest_has_entry_point       (parametrized over skill_name)
test_skill_entry_point_is_valid_node       (parametrized)
test_skill_manifest_has_actor_field        (parametrized)
test_subagent_spec_ueid_validation
test_ikigai_checkpointer_class_exists
test_default_db_filename_matches_adrr027_r135
test_subgraph_uses_build_subagent_thread_id_from_checkpoint
test_memory_schema_version_constant_is_one
test_memory_schema_module_defines_default_db_filename
test_meta_plan_no_direct_vault_writes
test_meta_plan_approval_required_for_writes
test_meta_plan_pydantic_v2_strict
test_planning_note_template_exists
```

**Domains:** canonical scope discipline (5) · IKIGAI_TOOLS contract (1) · UEID format (1) · mesh protocol (1) · queue
discipline (2) · skill manifest (3, parametrized) · subagent spec (1) · checkpointer (1) · memory schema (2) · meta-plan
invariants (3) · planning note template (1) · DB filename (1)

### 3.2 Drift invariants (`test_drift_invariants.py` — 7 tests)

```
test_kill_switch_keys_present_in_json
test_kill_switch_keys_mirrored_in_defensive_default
test_no_kill_switch_python_constants_in_agent_code
test_vault_write_wrapper_imports_and_exposes_canonical_api
test_drift_invariant_e_vault_write_actor_agent_bypasses_validator
test_legacy_drift_invariants_a_d_still_pass
test_wrapper_modules_loaded_in_sys_modules
```

**Domains:** kill_switch keys (2) · kill_switch constants hygiene (1) · vault_write canonical API (2) · legacy drift
a-d (1) · wrapper module loading (1)

### 3.3 Extended drift invariants (`test_drift_extended_invariants.py` — 4 tests)

```
test_vault_write_sole_writer
test_review_queue_append_only
test_v2_prompts_dont_touch_forbidden_math_modules
test_drift_extended_invariants_self_check
```

**Domains:** vault_write sole-writer (1) · review_queue append-only (1) · v2 prompts + forbidden math isolation (1) ·
self-check (1)

### 3.4 Total invariant count

**34 invariants** (matches expected 23 + 7 + 4 = 34).

### 3.5 Coverage gap (drift net does NOT cover)

- **langgraph.json graph registry** — no test enforces the graphs list vs CLAUDE.md or against an allowed-set.
  Drift G-4 below is invisible to drift net. (See Gap G-5.)
- **`vibe-ops/` Q_HE / PAVConstants references** — no drift test greps `vibe-ops/src/` for `Q_HE|PAVConstants`.
  Drift G-1 below is invisible. (See Gap G-6.)

---

## 4. `langgraph.json` Graph Registry

**File:** `langgraph.json` (master) — actual content:

```json
{
  "$schema": "https://langchain-ai.github.io/langgraph/schemas/langgraph.json",
  "dependencies": ["."],
  "graphs": {
    "pae_maintainer": "./vibe-ops/src/langgraph_entry.py:make_pae_graph",
    "ikigai_maintainer_v2": "./src/ikigai/src/agents/v2/graph.py:make_v2_graph",
    "ikigai_fork_smoke": "./src/ikigai/src/agents/v2/fork_smoke_graph.py:make_fork_smoke_graph"
  },
  "env": ".env",
  "python_version": "3.11"
}
```

**3 graphs registered** (NOT 5 as CLAUDE.md "LangGraph Graphs" table claims):

| Graph key | Entry factory | Status |
|-----------|---------------|--------|
| `pae_maintainer` | `./vibe-ops/src/langgraph_entry.py:make_pae_graph` | **SHIPPED** (only `make_*` factory in entry file) |
| `ikigai_maintainer_v2` | `./src/ikigai/src/agents/v2/graph.py:make_v2_graph` | **SHIPPED** (Phase 8.1, commit `fb41578`) — NOT in CLAUDE.md table |
| `ikigai_fork_smoke` | `./src/ikigai/src/agents/v2/fork_smoke_graph.py:make_fork_smoke_graph` | **SHIPPED** (Phase 8.2) — NOT in CLAUDE.md table |

**CLAsUDE.md "LangGraph Graphs" table claims 5 graphs** (`pae_maintainer`, `quarterly_replan`, `correction_protocol`,
`dream_falsification`, `test_de_fogo_rollup`). Of these, only `pae_maintainer` is registered in `langgraph.json`.
The other 4 are documented as if they exist but are NOT registered. The CLAUDE.md note correctly states
"`ikigai_maintainer` foi removido no attribution §3" — but the 4 others in the same table are equally
non-registered.

**Confirmed in `vibe-ops/src/langgraph_entry.py`:** only `make_pae_graph` factory exists. No other `make_*_graph`
factories in that file.

---

## 5. Cross-Layer Summary

| Layer | Lives | Owner | Active? |
|-------|-------|-------|---------|
| Cybernetic engine kernel | `archive/legacy-pav/src-operational/` (ADR-024) | archived | NO |
| LangGraph `pae_maintainer` | `vibe-ops/src/agents/pae_maintainer/` | live but dormant | YES (registered, dormant on master) |
| LangGraph v2 graph | `src/ikigai/src/agents/v2/graph.py` | live | YES (registered, Phase 8.7+ wires daily/weekly) |
| CLI consumer | `interfaces/cli/` | live | YES (19 subcommands, all surfaces) |
| TUI consumer | `interfaces/tui/operator/` | live | YES (5 tabs, kill_switch as 5th) |
| `kill_switch` engine | `sys_ikigai/security/kill_switch.py` | live | YES (494 L, 14 fns) |
| Drift net | `src/ikigai/tests/test_*_invariants*.py` | live | YES (34 invariants, 1 721 L) |

---

## 6. Provisional Gaps

| ID | Severity | Layer | Description |
|----|----------|-------|-------------|
| **G-1** | medium | vibe-ops | `vibe-ops/src/agents/pae_maintainer/{state,nodes,graph,main}.py` still import `Q_HE` + `PAVConstants.*` — PAV kernel is archived to `archive/legacy-pav/` but the LangGraph graph retains the constants. Incomplete archive (per ADR-024). No drift-net coverage. |
| **G-2** | low | docs | CLAUDE.md "Textual 4-tab operator (Chat / Tasks / State / KillSwitch)" claim is wrong: actual TUI has **5 tabs** (Tasks / Adapters / Backend / Queue / KillSwitch). No `Chat`, no `State`. |
| **G-3** | medium | docs | CLAUDE.md "LangGraph Graphs" table claims 5 graphs registered; only **3** are actually registered in `langgraph.json` (`pae_maintainer`, `ikigai_maintainer_v2`, `ikigai_fork_smoke`). The other 4 (`quarterly_replan`, `correction_protocol`, `dream_falsification`, `test_de_fogo_rollup`) are documented but not registered. |
| **G-4** | low | data | `data/vibe_ops.db` is 5 months stale (mtime 2026-06-03); no live writer on master. Should be either regenerated, archived, or moved to `archive/` for clarity. |
| **G-5** | medium | tests | Drift net does NOT cover `langgraph.json` registry drift (Gap G-3 invisible). No test asserts allowed-set or required-set of graphs. |
| **G-6** | medium | tests | Drift net does NOT cover `vibe-ops/src/` for `Q_HE|PAVConstants` references (Gap G-1 invisible). The `test_no_algorithm_constants_in_agent_code` test scopes to `src/ikigai/`, not `vibe-ops/src/`. |
| **G-7** | low | docs | The 4 unregistered graphs in CLAUDE.md table are non-existent in `vibe-ops/src/langgraph_entry.py`. They were either never written or removed per attribution §3 (similar to `ikigai_maintainer`). Recommend deleting rows from CLAUDE.md table to match ground truth. |

---

## 7. Verification Commands Reproducible

```bash
# vibe-ops state
ls -la data/vibe_ops.db
ls vibe-ops/
grep -rn "Q_HE\|PAVConstants" vibe-ops/src/

# interfaces/
ls interfaces/cli/ interfaces/tui/operator/
grep -rn "kill_switch" interfaces/
ls sys_ikigai/security/

# drift net
grep -cE "^def test_" src/ikigai/tests/test_canonical_scope.py \
                         src/ikigai/tests/test_drift_invariants.py \
                         src/ikigai/tests/test_drift_extended_invariants.py

# langgraph registry
cat langgraph.json
grep -E "^def make_" vibe-ops/src/langgraph_entry.py
```

---

## 8. Conclusion

Consumer-facing layers are operationally complete and consistent:
- **CLI:** 19 commands across 4 sub-apps, all wired.
- **TUI:** 5 tabs (one more than CLAUDE.md claims).
- **`kill_switch`:** operational on engine + CLI + TUI surfaces.
- **Drift net:** 34 invariants, 1 721 LOC, mature coverage.
- **`langgraph.json`:** 3 graphs registered (2 more than CLAUDE.md acknowledges: `ikigai_maintainer_v2`,
  `ikigai_fork_smoke` from Phase 8.x).

Two non-blocking docs drifts (G-2, G-3, G-7) and two test-coverage gaps (G-5, G-6) should be tracked separately;
G-1 (incomplete PAV archive) is the most material — the `pae_maintainer` graph retains Q_HE constants in-state even
after ADR-024 archival. None of these are blocking the IKIGAI agent layer (planner-only per ADR-013) — the
`pae_maintainer` graph is dormant on master.

---

*End of L6 review — T-11.7 PASS. 7 gaps identified; no code changes (read-only inspection).*
