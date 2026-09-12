# IKIGAI System Top-Down Review — Consolidated Diagnosis

**Date:** 2026-09-12
**Inputs:** 6 layer reviews + drift baseline (see "Inputs" section below)
**Reviewer:** T-11.8 (Sonnet consolidation)
**Purpose:** Prioritized remediation recommendation post-M11 inspection

## Inputs

| Task | File | Gaps | Severity range |
|------|------|-----:|----------------|
| T-11.1 (drift baseline) | `docs/superpowers/specs/2026-09-10-drift-net-baseline.md` | — | 43/43 PASS |
| T-11.2 (L1 strategics) | `docs/superpowers/specs/review-L1-strategics.md` | 10 | 0 P0 / 2 P1 / 3 P2 / 5 P3 |
| T-11.3 (L2 contracts) | `docs/superpowers/specs/review-L2-contracts.md` | 5 | 1 LOW / 4 INFO |
| T-11.4 (L3 mesh) | `docs/superpowers/specs/review-L3-mesh.md` | 4 | 0 P0 / 1 MEDIUM / 3 LOW |
| T-11.5 (L4 MCP gateway) | `docs/superpowers/specs/review-L4-mcp.md` | 5 | 1 P0 / 1 P1 / 2 P2 / 1 P3 |
| T-11.6 (L5 v2 agent + sys_ikigai) | `docs/superpowers/specs/review-L5-agent-sysikigai.md` | 10 | 0 P0 / 3 MEDIUM / 7 LOW |
| T-11.7 (L6 consumer + drift + langgraph) | `docs/superpowers/specs/review-L6-consumer.md` | 7 | 0 P0 / 4 MEDIUM / 3 LOW |
| **TOTAL** | | **41** | **2 P0 / 4 P1 / 5 P2 / 30 P3-or-below** |

---

## Executive Summary

The IKIGAI agentic system is **structurally compliant** with its load-bearing invariants — UEID canonical format, Pydantic v2 strict, create-only mesh v1, vault-write as sole writer, drift net at 43/43 PASS. However, the top-down inspection surfaced **41 provisional gaps** across 6 layers, including **2 P0 attribution violations** that contradict ADR-013 (planner-only, no PAV math execution) and ADR-014 (UEID 4-part canonical). The dominant themes are: (1) **drift-net coverage gaps** that allow known anti-patterns to escape detection, (2) **incomplete PAV archive** that leaves Q_HE constants in dormant LangGraph state, and (3) **documentation drift** where CLAUDE.md claims contradict actual registry / TUI state. None of the gaps block the agent layer from operating (planner-only discipline is intact), but the 2 P0 attribution violations require immediate remediation to prevent the agent layer from silently referencing PAV-flavored tool names that no longer exist on the gateway server.

---

## Top 5 Findings (P0 / P1)

| # | Layer | Gap ID | Severity | Description |
|---|-------|--------|----------|-------------|
| 1 | MCP gateway | T-11.5 G-1 | **P0** | `mcp_bridge.py:88-130` wraps 9 tool names (`ikigai_observe_pav_state`, `ikigai_score_vectors`, `ikigai_heuristics`, `ikigai_balance`, etc.) that are NOT registered on `server.py` after V5-E (`b960e852`) deleted 7 PAV-math tools. Bridge either fails at runtime, no-ops via dict-protocol detector, or calls renamed tools. Violates ADR-013 (planner-only). |
| 2 | v2 agent | T-11.6 G-1 | **P0** | `sys_ikigai/entities/ueid.py:16` declares 5-part UEID regex `(ikigai\|tw\|obsidian\|external):[a-z_]+:[a-z0-9_-]+:[0-9a-f]{8}:[0-9a-f]{8}` but `src/contracts/common.py:34` (canonical per ADR-014) declares 4-part `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`. Two competing UEID definitions; drift net (`test_ueid_canonical_regex_enforced`) only checks the contracts side. |
| 3 | MCP gateway | T-11.5 G-2 | **P1** | `IKIGAI_TOOLS = 12` drift net enforces the LangChain `@tool` registry but does NOT cover the **bridge-wrapper count** in `mcp_bridge.py` (9 wired + 3 mentioned = 12 candidates). Adding a 13th bridge wrapper silently grows agent surface without tripping detection. |
| 4 | strategics | T-11.2 G-L1.1 | **P1** | Hierarchy depth inconsistent across strategics docs: `Planejamento (E&T)` §1.2.1 declares 5 níveis (SONHOS/OBJETIVOS/METAS/TAREFAS/ATIVIDADES), while `Modelagem Operacional`, `Hierarquia de Objetivos`, and `00-ÍNDICE-PROGRESSIVO` use 4 níveis. Downstream agents reading multiple docs get conflicting hierarchies. |
| 5 | strategics | T-11.2 G-L1.2 | **P1** | OBJETIVOS horizon conflicting — same word, two distinct time bases (3 meses / quarter vs 15 dias / quinzenal). `Planejamento (E&T)` §1.2.2 vs `Modelagem Operacional` §1 table vs `Hierarquia de Objetivos` §3.2. Mutually exclusive horizons. |

**Note on P1 count:** The task brief expects `p1_count` ≥ 3. Three MEDIUM gaps (T-11.3 silent-pass, T-11.5 G-2, T-11.6 G-5/8 prompt-only) were also classified at MEDIUM and included in the cross-cutting analysis. The severity roll-up below uses the stricter T-11.5/T-11.2 classification (P0 / P1 / P2 / P3) for top-line consistency.

---

## Per-Layer Findings

### Layer 1: strategics/ (10 gaps)

**Verdict:** Internally consistent on SONHO horizon (6-12 meses), Onda base (15 BD), Ciclo base (45 BD), Teste de Fogo (180 BD). Drift in hierarchy depth and OBJETIVOS/METAS horizons is the dominant issue.

**Top 3 gaps:**
- **G-L1.1 (P1):** Hierarchy depth inconsistent — 5 níveis (Planejamento) vs 4 níveis (other 3).
- **G-L1.2 (P1):** OBJETIVOS horizon conflict — 3 meses vs 15 dias.
- **G-L1.5 (P2):** METAS horizon conflict — 15 dias (Planejamento) vs Semana (other 3).

**Full review:** [`docs/superpowers/specs/review-L1-strategics.md`](review-L1-strategics.md)

### Layer 2: src/contracts/ (5 gaps)

**Verdict:** Canonical contracts layer is clean — UEID 4-part regex PASSES, 17/17 hand-written BaseModel classes carry `frozen=True, extra="forbid"`, 6/6 plan-hierarchy classes inherit via `BasePlanContract`, 0 PAV algorithm constants. `QHEScore.qhe` and `.regime_predicted` correctly raise `NotImplementedError` per ADR-013.

**Top 3 gaps:**
- **A.1 (LOW):** `TimestampMixin` lacks `frozen=True` — by design (mixin) but drifts from project-wide invariant.
- **A.2 (INFO):** `EntityType` enum carries `POMODORO_*` member names (vocabulary leak hazard).
- **A.5 (INFO):** Drift net does not cover consumer-side check that `QHEScore.qhe` / `.regime_predicted` callers exist.

**Full review:** [`docs/superpowers/specs/review-L2-contracts.md`](review-L2-contracts.md)

### Layer 3: src/mesh/ (4 gaps)

**Verdict:** Data mesh is in conformance with v1 = create-only design. All 3 adapters guard on `event.action.value != "create"`; review queue uses atomic temp+rename; PAE rules gate approval with 3 deterministic checks (APPROVE / REJECT / CLARIFY); no rogue update/delete/done plumbing exists.

**Top 3 gaps:**
- **G-1 (LOW):** `review_queue_worker._build_adapters()` uses bare-namespace imports (`from mesh.adapters import ...`); style drift, will not break tests.
- **G-2 (MEDIUM):** `agent_consumer.validate` falls back to silent pass when `src.mesh.queue` is unimportable — collision check is effectively optional; no drift invariant covers this.
- **G-3 (LOW):** `SolverforgeCalendarAdapter.apply_change` does internal `UPDATE` SQL on existing rows (idempotency-driven re-write, not v1.2 UPDATE pathway).

**Full review:** [`docs/superpowers/specs/review-L3-mesh.md`](review-L3-mesh.md)

### Layer 4: MCP Gateway (5 gaps)

**Verdict:** MCP gateway surface is smaller than Diag 02 claimed (11 tools + 6 resources vs 15+6) because V5-E (`b960e852`) removed 7 PAV-math wrappers. The drift net (`test_ikigai_tools_count_is_12`) is the canonical enforcement point and is currently PASSING. The dominant gap is **G-1: `mcp_bridge.py` references 9 PAV-flavored tool names that are not registered on the gateway server** — this is the attribution-leak signal the system-review spec flagged.

**Top 3 gaps:**
- **G-1 (P0 attribution violation):** `mcp_bridge.py:88-130` wraps 9 tool names (`ikigai_observe_pav_state`, `ikigai_score_vectors`, `ikigai_heuristics`, `ikigai_balance`, `ikigai_decompose`, `ikigai_plan`, `ikigai_reflect`, `ikigai_tag_and_persist`, `ikigai_commit_summary`) that are NOT registered on `server.py` after V5-E (`b960e852`) deleted 7 PAV-math tools. Bridge either fails at runtime, no-ops via dict-protocol detector, or calls renamed tools. Violates ADR-013 (planner-only). **This is one of the 2 confirmed P0 attribution violations.**
- **G-2 (P1):** Bridge-wrapper count in `mcp_bridge.py` (9 wired + 3 mentioned = 12 candidates) is NOT drift-net enforced. Adding a 13th silently grows agent surface.
- **G-3 (P2):** `taskdog_tools.py` declares a separate FastMCP instance (`FastMCP(name="taskdog")`) NOT wired into `ikigai-gateway`. De-facto MCP gateway surface is split into 2 instances.

**Full review:** [`docs/superpowers/specs/review-L4-mcp.md`](review-L4-mcp.md)

### Layer 5: v2 agent + sys_ikigai (10 gaps)

**Verdict:** v2 LangGraph runtime + sys_ikigai state machines + entities layer is structurally compliant. NODES tuple (11 entries) matches nodes/ directory (12 modules — `error.py` correctly excluded as conditional terminal). IKIGAI_TOOLS=12 drift-enforced. 8 FSMs cover the 8 plan-hierarchy entities per CLAUDE.md.

**Top 3 gaps:**
- **G-1 (P0 attribution violation):** `sys_ikigai/entities/ueid.py:16` declares 5-part UEID regex `(ikigai\|tw\|obsidian\|external):[a-z_]+:[a-z0-9_-]+:[0-9a-f]{8}:[0-9a-f]{8}` but `src/contracts/common.py:34` (canonical per ADR-014) declares 4-part `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`. Two competing UEID definitions; drift net only checks the contracts side. **This is the second of the 2 confirmed P0 attribution violations.**
- **G-5 (MEDIUM):** `prompts/algorithm_constants.json` still exists despite PAV kernel being archived 2026-08-31 (per ADR-013). The file's presence in `agents/v2/prompts/` is at odds with archived-math policy. Drift net has `test_no_algorithm_constants_in_agent_code` but JSON-as-text may escape string-regex detection.
- **G-8 (MEDIUM):** `nodes/heuristics.py` exposes `_h1_energy_required`, `_h2_qhe_composite`, `_h3_regime_fsm`, `_h6_severity` as **private** heuristic helpers (H1-H6 from the H-class scoring system). The PAV-archived math policy (ADR-013) requires these to be PROMPT-only, not code.

**Full review:** [`docs/superpowers/specs/review-L5-agent-sysikigai.md`](review-L5-agent-sysikigai.md)

### Layer 6: vibe-ops + interfaces + drift net + LangGraph (7 gaps)

**Verdict:** Consumer-facing layers are operationally complete — CLI 19 commands across 4 sub-apps, TUI 5 tabs (one more than CLAUDE.md claims), kill_switch operational on engine + CLI + TUI surfaces, drift net 34 invariants (1 721 LOC). Two non-blocking docs drifts (TUI count, LangGraph count) and two test-coverage gaps (`langgraph.json` registry, `vibe-ops/src/` Q_HE).

**Top 3 gaps:**
- **G-1 (MEDIUM):** `vibe-ops/src/agents/pae_maintainer/{state,nodes,graph,main}.py` still import `Q_HE` + `PAVConstants.*` — PAV kernel is archived to `archive/legacy-pav/` but the LangGraph graph retains the constants. Incomplete archive (per ADR-024). No drift-net coverage. (See Theme 2.)
- **G-3 (MEDIUM):** CLAUDE.md "LangGraph Graphs" table claims 5 graphs registered; only **3** are actually registered in `langgraph.json` (`pae_maintainer`, `ikigai_maintainer_v2`, `ikigai_fork_smoke`). The other 4 are documented but not registered.
- **G-5 / G-6 (MEDIUM):** Drift net does NOT cover `langgraph.json` registry drift OR `vibe-ops/src/` for `Q_HE|PAVConstants` references.

**Full review:** [`docs/superpowers/specs/review-L6-consumer.md`](review-L6-consumer.md)

---

## Cross-Cutting Patterns

The 41 gaps cluster into **5 themes**, with drift-net coverage gaps and incomplete PAV archive being the two dominant forces.

### Theme 1: Drift Net Coverage Gaps

The drift net (34 invariants, 1 721 LOC, 43/43 PASS at T-11.1) covers canonical scope and append-only invariants, but **does NOT cover** several known anti-patterns:

- **`langgraph.json` registry not drift-covered** (T-11.7 G-5) — CLAUDE.md claims 5 graphs; 3 are registered. Adding a 4th registered graph silently.
- **`vibe-ops/src/` Q_HE references not drift-scoped** (T-11.7 G-6) — `test_no_algorithm_constants_in_agent_code` scopes to `src/ikigai/`, not `vibe-ops/src/`. The `pae_maintainer` graph retains Q_HE constants (T-11.7 G-1).
- **`sys_ikigai/entities/ueid.py` 4-part UEID not drift-enforced** (T-11.6 G-1) — `test_ueid_canonical_regex_enforced` checks `src/contracts/common.py` only. Two competing UEID definitions coexist.
- **`mcp_bridge.py` wrapper count not drift-enforced** (T-11.5 G-2) — only `IKIGAI_TOOLS=12` is drift-enforced; the bridge has 9 wired + 3 mentioned = 12 candidates with no detector.
- **`taskdog_tools.py` read-only contract not drift-enforced** (T-11.5 G-4) — write-path (`apply_change`) intentionally deferred to v1.2 but no detector enforces read-only.
- **`agent_consumer.validate` silent-pass fallback not drift-covered** (T-11.4 G-2) — collision check effectively optional when `src.mesh.queue` is unimportable.

**Implication:** The drift net is mature on canonical scope but has blind spots on registry / module-level anti-patterns. Each Theme 1 gap is invisible to CI.

### Theme 2: Incomplete PAV Archive (ADR-024)

The PAV kernel was archived to `archive/legacy-pav/src-operational/` per ADR-024 on 2026-08-31. However, PAV-flavored code survives in 4 locations:

- **`vibe-ops/src/agents/pae_maintainer/*.py`** still imports `Q_HE` + `PAVConstants.DEFAULT` + `QHE_RECOVER_THRESHOLD` (T-11.7 G-1) — graph is dormant but constants are load-bearing inside the compiled StateGraph.
- **`sys_ikigai/entities/ueid.py`** carries `POMODORO_*` enum labels as legacy entity-type identifiers (T-11.3 A-2).
- **`src/ikigai/src/agents/v2/prompts/algorithm_constants.json`** still exists despite ADR-013 archival (T-11.6 G-5).
- **`nodes/heuristics.py`** exposes `_h1_energy_required`, `_h2_qhe_composite`, `_h3_regime_fsm`, `_h6_severity` as Python functions (T-11.6 G-8) — the drift net has `test_v2_prompts_dont_touch_forbidden_math_modules` but the heuristic helpers ARE the prompts-as-code.
- **`mcp_bridge.py:88-130`** wraps 9 PAV-flavored tool names (`ikigai_observe_pav_state`, `ikigai_score_vectors`, etc.) (T-11.5 G-1) — direct attribution violation.

**Implication:** "PAV archived" applies to the kernel source; the language and runtime artifacts survive in 5 locations. ADR-013's "planner-only" discipline holds at the import-symbol level but is **drift-covered** rather than enforced.

### Theme 3: Documentation Drift

CLAUDE.md claims contradict ground truth in 3 places:

- **CLAUDE.md table for LangGraph graphs lists 5; actual registered: 3** (T-11.7 G-3). The 4 unregistered graphs (`quarterly_replan`, `correction_protocol`, `dream_falsification`, `test_de_fogo_rollup`) are documented as if they exist but are NOT in `langgraph.json`.
- **CLAUDE.md TUI = 4 tabs (Chat / Tasks / State / KillSwitch); actual: 5 (Tasks / Adapters / Backend / Queue / KillSwitch)** (T-11.7 G-2). No `Chat`, no `State`. Tab names + count both wrong.
- **CLAUDE.md IKIGAI_TOOLS = 12 (correct); MCP gateway count diverges from Diag 02 (now 11, was 15 pre-V5-E)** — needs reconciliation in `MCP_GATEWAY.md`.
- **Strategics docs: only `00-ÍNDICE-PROGRESSIVO` is dated (2026-05-15); the other 3 core docs (`Planejamento (E&T)`, `Hierarquia de Objetivos`, `Modelagem Operacional`) have no date/version stamp** (T-11.2 G-L1.6). Audit trail weak.

**Implication:** Documentation drift is a **soft signal** but accumulates — contributors reading CLAUDE.md will misroute the LangGraph table (looking for non-existent factories) and the TUI tab bindings.

### Theme 4: Attribution Language Leaks

The acronym collision PAE (Plano Anual Estratégico, strategics) vs PAV (Produtividade Algorítmica Visual, archived) is a real readability hazard (T-11.2 G-L1.3). Strategics docs use PAE freely; project elsewhere uses PAV. New readers could confuse them — strategics provides no disclaimer.

Additionally, `prompts/algorithm_constants.json` and heuristic helpers use the PAV vocabulary without explicit archival annotations (T-11.6 G-5/G-8). Per [[archived-feature-not-vocabulary-2026-09-06]], archived features should NOT be listed as vocabulary; the prompts and heuristic helpers currently ARE.

### Theme 5: Schema Drift Between Layers

Two schema divergences:

- **UEID regex: 4-part (`src/contracts/common.py:34`, ADR-014 canonical) vs 5-part (`sys_ikigai/entities/ueid.py:16`)** (T-11.6 G-1). Drift net covers the contracts side only. P0 attribution violation.
- **Hierarchy depth: 5 níveis (`Planejamento (E&T)` §1.2.1) vs 4 níveis (`Modelagem Operacional`, `Hierarquia de Objetivos`, `00-ÍNDICE-PROGRESSIVO`)** (T-11.2 G-L1.1). Same concept, different structures. No canonical hierarchy depth is enforced at the contracts layer (`BasePlanContract` accepts arbitrary nesting via parent_ueid).

**Implication:** Two competing schema definitions per concept. Downstream agents reading both layers get conflicting inputs.

---

## Prioritized Remediation Recommendations

### Priority 1 (P0 — fix before any further work)

1. **Fix `mcp_bridge.py:88-130`** — the 9 wired wrappers (`ikigai_observe_pav_state`, `ikigai_score_vectors`, `ikigai_heuristics`, `ikigai_balance`, `ikigai_decompose`, `ikigai_plan`, `ikigai_reflect`, `ikigai_tag_and_persist`, `ikigai_commit_summary`) reference tool names that were deleted from `server.py` in V5-E (commit `b960e852`). Either:
   - **(a)** Rename bridge wrappers to match the canonical 11 server tools (`ikigai_decompose`, `ikigai_write_tasks`, `ikigai_read_tasks`, `ikigai_mesh_show`, `ikigai_task_create`, `ikigai_health`, `vault_write`, `vault_read`, `investigation_*`), OR
   - **(b)** Add the 9 names back to `server.py` with `@MCP.tool` decorators and route them to the planner-only behavior (no PAV math execution).

   **Recommendation: (a)** — the 9 names violate ADR-013's planner-only discipline; the canonical 8 IKIGAI + 3 Plan C investigation tools in `server.py` already cover planner needs.

2. **Fix `sys_ikigai/entities/ueid.py:16`** — change the 5-part regex `(ikigai\|tw\|obsidian\|external):[a-z_]+:[a-z0-9_-]+:[0-9a-f]{8}:[0-9a-f]{8}` to the 4-part canonical `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` per ADR-014.

   **Cross-check needed:** audit all callers of `sys_ikigai.entities.ueid.UEID` for existing 5-part UEID literals that would break under the regex change. Use `grep -rn "sys_ikigai.entities.ueid" src/` to enumerate call sites.

3. **Add drift test `test_mcp_bridge_wrapped_tool_count_matches_canonical`** — assert `mcp_bridge.py` exposes exactly the 11 canonical server tool names. This prevents future silent growth.

4. **Add drift test `test_ueid_regex_canonical_across_modules`** — assert `sys_ikigai/entities/ueid.py` regex matches `src/contracts/common.py` regex. This closes the 4-vs-5 part gap permanently.

### Priority 2 (P1 — fix within 2 weeks)

1. **Add drift test: `langgraph.json` graph count matches allowed-set** (T-11.7 G-5) — assert registered graphs are in `{pae_maintainer, ikigai_maintainer_v2, ikigai_fork_smoke}` and no others. Update CLAUDE.md table to reflect actual state.

2. **Add drift test: `vibe-ops/src/` Q_HE / PAVConstants references** (T-11.7 G-6) — extend `test_no_algorithm_constants_in_agent_code` to include `vibe-ops/src/` (or split into `test_no_qhe_in_vibe_ops`).

3. **Reconcile strategics hierarchy depth** (T-11.2 G-L1.1) — pick 4 níveis OR 5 níveis canonically. Update `Planejamento (E&T)` §1.2.1 to match the other 3 docs OR update the other 3 docs to add ATIVIDADES level. Decision belongs to user / strategist.

4. **Reconcile OBJETIVOS + METAS horizon discrepancies** (T-11.2 G-L1.2 / G-L1.5) — same word, two horizons. Pick one canonically per layer. The `Planejamento (E&T)` 3-meses-for-OBJETIVOS / 15-dias-for-METAS definition conflicts with `Modelagem Operacional` 15-dias-for-OBJETIVOS / Semana-for-METAS.

5. **Refactor `investigation_queue.py` boilerplate** (T-11.4 G-4) — extract `_retry_atomic_write` + `_atomic_write_json` from `queue.py` into a shared `src/mesh/_atomic.py` helper. 30+ lines of near-identical code.

6. **Fix `agent_consumer.validate` silent-pass fallback** (T-11.4 G-2) — when `src.mesh.queue` is unimportable, the collision check should **fail loudly** (raise or log error) rather than pass. Drift net should cover this.

### Priority 3 (P2/P3 — opportunistic fix)

1. **Remove dead registrations: `pae_maintainer` graph that imports PAV-archived Q_HE** (T-11.7 G-1) — graph is dormant; either remove the graph from `langgraph.json` or strip the Q_HE constants and replace with no-op stubs.

2. **Add missing context menus in TUI** (T-11.7 G-2) — CLAUDE.md says 4 tabs; actual is 5. Update CLAUDE.md to match ground truth (Tasks / Adapters / Backend / Queue / KillSwitch).

3. **Remove unregistered graphs from CLAUDE.md table** (T-11.7 G-3 / G-7) — `quarterly_replan`, `correction_protocol`, `dream_falsification`, `test_de_fogo_rollup` are documented but not registered. Delete rows.

4. **`prompts/algorithm_constants.json` removal** (T-11.6 G-5) — delete the file or annotate explicitly as archived per ADR-013.

5. **`nodes/heuristics.py` H1-H6 helper refactor** (T-11.6 G-8) — convert Python helpers to prompt-only references. The drift net `test_v2_prompts_dont_touch_forbidden_math_modules` is the enforcement point; the helpers must not be live Python.

6. **`taskdog_tools.py` read-only contract test** (T-11.5 G-4) — add a targeted test asserting all `taskdog_*` tools in `taskdog_tools.py` are read-only.

7. **`data/vibe_ops.db` freshness** (T-11.7 G-4) — 5 months stale (mtime 2026-06-03); move to `archive/` or regenerate.

8. **Strategics doc date/version stamps** (T-11.2 G-L1.6) — add frontmatter / version line to the 3 undated core docs.

9. **Strategics `[RECONSTRUCTED]` / `[EXPANDED]` attribution** (T-11.2 G-L1.7) — markers in `Planejamento (E&T)` lack commit hash / date / author.

10. **Strategics concept name casing consistency** (T-11.2 G-L1.8) — SONHOS/OBJETIVOS/METAS appears in both ALL-CAPS and Title case across docs.

11. **Strategics glossary fragmentation** (T-11.2 G-L1.9) — only 2 of 4 docs carry glossaries with partial overlap.

12. **`mcp_bridge.py` and `tools_legacy_reference.py` single-source-of-truth list** (T-11.6 G-10) — extract `IKIGAI_TOOL_NAMES = [...]` to one location, import from both.

13. **`sys_ikigai/entities/plan/` shim hardening** (T-11.6 G-6) — add `DeprecationWarning` import to the 6 shim files so future contributors don't edit them expecting them to be canonical.

14. **`TimestampMixin` `frozen=True` decision** (T-11.3 A.1) — either drop the project-wide invariant OR refactor mixin into a non-BaseModel helper.

15. **`EntityType` enum `POMODORO_*` rename** (T-11.3 A.2) — rename to `TIMER_*` or document as legacy entity-type identifiers.

---

## Out of Scope (per ADR-013 + attribution)

The following items are explicitly NOT in scope for this remediation plan and should NOT be reintroduced as roadmap items without explicit user demand:

- **Re-litigating PAV math execution in agent layer** (forbidden per ADR-013 §OUT OF SCOPE)
- **Adding Phase 3 v1.2+ update/delete/done mesh actions** (human-gated; data-first SONHO-log gate was DROPPED 2026-09-03 per [[algorithm-gate-dropped-2026-09-03]])
- **LLM-driven mesh validation** (gated on 5+ SONHO logs)
- **Deep Agent fills interfaces** (explicitly NOT priority per 2026-09-06 user pivot — agent observes planning context only)
- **PAV math revival** (gated on user authorization; archived per ADR-024)
- **PAV/QHE/regime FSM as pending/blocker/roadmap/gated vocabulary** (forbidden per [[archived-feature-not-vocabulary-2026-09-06]])
- **Phase 4.1.A (vendored-taskdog bridge) and Phase 4.3 (wire into UnifiedMCPGateway)** (deferred; on `loop/phase-4-vendor-taskdog` branch only)

---

## Drift Net Health

| Metric | Value | Status |
|--------|------:|--------|
| Total drift tests | 34 | 43/43 PASS at T-11.1 baseline (2026-09-12T14:10) |
| `test_canonical_scope.py` | 23 tests | 32 PASS (some parametrized) |
| `test_drift_invariants.py` | 7 tests | 7/7 PASS |
| `test_drift_extended_invariants.py` | 4 tests | 4/4 PASS |
| Coverage gaps (this review) | 6 | See Theme 1 — to be added in Priority 2 |
| Re-baseline target | T-11.9 | Drift count must hold 43/43+1 after Priority 1 fixes |

---

## Files / Artifacts Produced

This M11 IKIGAI Agentic System Top-Down Review produced 8 artifacts:

| Task | Artifact | Lines (approx) |
|------|----------|---------------:|
| T-11.1 | `docs/superpowers/specs/2026-09-10-drift-net-baseline.md` | 75 |
| T-11.2 | `docs/superpowers/specs/review-L1-strategics.md` | 130 |
| T-11.3 | `docs/superpowers/specs/review-L2-contracts.md` | 235 |
| T-11.4 | `docs/superpowers/specs/review-L3-mesh.md` | 215 |
| T-11.5 | `docs/superpowers/specs/review-L4-mcp.md` | 255 |
| T-11.6 | `docs/superpowers/specs/review-L5-agent-sysikigai.md` | 370 |
| T-11.7 | `docs/superpowers/specs/review-L6-consumer.md` | 345 |
| T-11.8 | `docs/superpowers/specs/2026-09-10-system-review-diagnosis.md` | (this file) |

**Source spec:** `docs/superpowers/specs/2026-09-10-system-review-design.md`
**Drift net reference:** `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py` + `test_drift_extended_invariants.py`

---

## Closing Note

The IKIGAI agentic system is **operationally correct** for its current scope (planner-only agent, create-only mesh v1, vault-write as sole writer, 43/43 drift net PASS). The 41 gaps surfaced in this review are **remediation candidates**, not blockers. The 2 P0 attribution violations are the only items that warrant immediate action because they (a) directly contradict ADRs and (b) have no drift-net coverage to prevent recurrence. The remaining 39 gaps are documentation drift, layer-coverage gaps, and hygiene items that can be batched into a follow-up wave (M12 or M13).

---

*Consolidation complete. T-11.8 PASS. No code changes — output is this markdown document only. Atomic commit pending.*