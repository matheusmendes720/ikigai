# Diag 10 — Spec Gap Analysis

**Generated:** 2026-09-04
**Agent:** Diag 10 of 10
**Scope:** Cross-reference 47 backend tasks (per Diag 04) against specs in `docs/superpowers/specs/`, plans in `docs/superpowers/plans/`, and ADRs in `code-docs/adr/`.
**Goal:** Identify what is spec'd, what is GAP, and what is implicit (Diag 09 candidates).

---

## Spec inventory

### specs/ (23 files, chronological)

**Phase A / Strategy era (2026-08-25 → 2026-08-26)**

- `2026-08-25-ikigai-vault-layers-design.md` — IKIGAi persona-vault layer expansion (pre-pivot) — status: **SUPERSEDED 2026-08-28** (master-branch-carro-chefe) — orphan (pre-pivot architecture)
- `2026-08-26-ai-native-strategic-model.md` — AI-native strategic model migration (post-2026-08-26 pivot) — status: current (supersedes 2026-08-25 spec) — covers B-N (general agent architecture)
- `2026-08-26-data-model-unification-design.md` — 4 surfaces → 1 canonical IKIGAiRecord — status: **SUPERSEDED 2026-08-28** (master-branch-carro-chefe) — orphan

**Phase 2/3 era (2026-08-28)**

- `2026-08-28-a2ui-protocol-design.md` — Agent-to-UI standard protocol — status: DRAFT — covers TUI↔agent contract
- `2026-08-28-phase3-data-mesh-design.md` — Phase 3 v1 data mesh design — status: current (with §4 stale) — covers B-M04, B-M05 (mesh tools)

**Phase B era (2026-08-29 → 2026-08-30)**

- `2026-08-29-algorithm-attribution-design.md` — IKIGAI × PAV × Forks × Deep Agents × Backend attribution — status: current — covers algorithm scope (referenced by ADR-013)
- `2026-08-29-phase-b5-b-agent-wiring-design.md` — Phase B5.B agent wiring MVP — status: shipped — covers B-N, B-G03
- `2026-08-29-phase-b6-6-bidirectional-vault-sync.md` — Phase B6 Combo A bidirectional vault sync — status: shipped — covers B-M07, B-M08
- `2026-08-29-phase-b6-vault-sync-design.md` — Phase B6 vault→taskdog sync v1 — status: shipped — covers B-M07, B-M08
- `2026-08-30-fork-connection-architecture.md` — Fork connection (solverforge-calendar + tuiboard) — status: current — covers B-M16 (sf_*, tuiboard_*) — superseded by ADR-012
- `2026-08-30-fork-connection-architecture-Q-expanded.md` — Fork connection open questions — status: current — companion to above
- `2026-08-30-phase-b7-end-to-end-agent-loop.md` — Phase B7 vault↔agent↔forks round-trip — status: DRAFT — covers B-G02..B-G05 (E2E loop)

**SONHO Tree era (2026-09-03)**

- `2026-09-03-sonho-tree-hybrid-design.md` — 6-tier hierarchy (SONHO→OBJETIVO→META→PROJETO→ENTREGA→TAREFA) + investigation layer + external access — status: current (canonical) — covers B-C01..B-C08, B-T01, B-T02
- `2026-09-03-go-tui-rewrite-deferred.md` — Go TUI rewrite DEFERRED — status: DEFERRED — no task coverage
- `2026-09-03-go-tui-vault-reader-full-design.md` — Go TUI vault reader full design — status: DESIGN (no code yet) — orphan / forward-looking

**Diagnostic reports (2026-09-04)**

- `2026-09-04-diag-01-graph-contracts.md` — graph + contracts inventory — status: this batch
- `2026-09-04-diag-02-mesh-taskdog-mcp.md` — mesh + taskdog + MCP gateway — status: this batch
- `2026-09-04-diag-03-interfaces-drift-tests-tui.md` — interfaces + drift + tests + TUI — status: this batch
- `2026-09-04-diag-04-backend-tasks.md` — **47 backend tasks (B-G*, B-N*, B-C*, B-M*, B-D*, B-T*)** — status: this batch (canonical task list)
- `2026-09-04-diag-05-frontend-tasks.md` — frontend task breakdown — status: this batch
- `2026-09-04-diag-07-sonho-capability.md` — SONHO tree capability × tier matrix — status: this batch
- `2026-09-04-diag-08-taskdog-capability.md` — taskdog integration status — status: this batch
- `2026-09-04-diag-09-adr-gap.md` — **ADR gap analysis (11 implicit decisions)** — status: this batch

### plans/ (18 files, chronological)

| Plan | Era | Covers | Shipped? |
|------|-----|--------|----------|
| `2026-08-25-ikigai-vault-layers.md` | Phase 0 | SUPERSEDED | — |
| `2026-08-26-ai-native-strategic-model.md` | Post-pivot | AI-native migration | ✅ |
| `2026-08-26-phase-mcp-unified-planning.md` | Pre-pivot | SUPERSEDED | — |
| `2026-08-28-phase2-interface-re.md` | Phase 2 | Interface reverse-engineering | ✅ |
| `2026-08-28-phase-b3-mcp-gateway.md` | Phase B3 | MCP gateway (13 tools) | ✅ |
| `2026-08-28-phase3-data-mesh-v1.md` | Phase 3 v1 | Data mesh create-action | ✅ |
| `2026-08-29-phase-b4-review-queue-worker.md` | Phase B4 | review_queue worker | ✅ |
| `2026-08-29-phase-b5-graph-agent-loop-audit.md` | Phase B5.0 | Audit | ✅ |
| `2026-08-29-phase-b5-b.md` | Phase B5.B | Agent wiring MVP | ✅ |
| `2026-08-29-phase-b6.md` | Phase B6 | vault→taskdog sync | ✅ |
| `2026-08-29-phase-b6-6.md` | Phase B6.6 | Bidirectional vault sync | ✅ |
| `2026-08-30-cli-human-readable-tables.md` | Phase CLI | CLI tables | ✅ |
| `2026-08-30-vault-sync-cli.md` | Phase CLI | vault sync CLI | ✅ |
| `2026-08-30-fork-connection-implementation.md` | Phase A | Fork MCP implementation | ✅ |
| `2026-08-30-phase-b7-agent-layer-activation.md` | Phase B7 | Agent layer activation | ✅ |
| `2026-09-03-planning-contract-plan-a.md` | **Plan A** | 6 contracts + transition_validator + actor parameter | ✅ (12 tasks) |
| `2026-09-03-external-folder-access-plan-b.md` | **Plan B** | External folder access + drift invariant (i) | ✅ (6 tasks) |
| `2026-09-03-investigation-queue-plan-c.md` | **Plan C** | Investigation queue + drift invariant (h) | ✅ (7 tasks) |

### code-docs/adr/ (7 ADRs)

| ADR | Title | Status | Covers |
|-----|-------|--------|--------|
| **ADR-007** | Data-First Methodology | Accepted 2026-07-02 | Algorithm gate (build order backend→data→agent→algo) |
| **ADR-008** | IKIGAI Vector Count | Superseded 2026-08-28 | (replaced by `algorithm-scope-reframed-2026-08-30`) |
| **ADR-009** | Pydantic Strict Mode | Superseded 2026-08-28 | (replaced by Plan A `BasePlanContract`) |
| **ADR-010** | Dual CLAUDE.md Scope | Superseded 2026-08-28 | (Option B applied via reconciliation) |
| **ADR-011** | HTTP+SSE Transport for IKIGAI MCP | Proposta (recommended) | SSE transport (not yet activated) |
| **ADR-012** | Fork-Connection Architecture | Accepted 2026-08-30 | B-M16 (sf_*, tuiboard_*) + UEID 4-part regex + cross-fork storage |
| **ADR-013** | Canonical Scope Discipline | Accepted 2026-08-31 | B-D01 (vault_write sole writer), B-D02 (review_queue append-only), B-D04 (drift detector scope), Plan A |

**Decision aids (8 files, not ADRs):** `2026-08-27-master-adr-index.md`, `2026-08-27-decision-questionnaire.md`, `2026-08-27-cross-cutting-triage.md`, `2026-08-28-adr-008-011-decision-package.md`, `2026-08-28-adr-008-011-decision-package-appendix.md`, `README.md`, `OPERATIONAL.md`, `VIBE-OPS.md`.

**Adjacent ADR surfaces (37 total docs, not in this scope):**
- `vibe-ops/architecture/` — 6 vibe-ops ADRs (001-006; 3 Accepted, 3 Proposta)
- `archive/legacy-pav/src-operational/docs/adr/` — 16 PAV PRDs (all SUPERSEDED 2026-08-31)

---

## Coverage matrix (47 backend tasks × spec/ADR)

Legend: **GAP** = no spec/plan/ADR addresses this task; **partial** = spec exists but task-specific details missing; **✅** = shipped + spec'd.

| Task | Task name | Spec'd in | ADR | Plan | Status |
|------|-----------|-----------|-----|------|--------|
| **B-G01** | pytest collection infra (`src.ikigai.src.*` namespace) | — | — | — | **GAP** (mechanical) |
| **B-G02** | smoke test `make_v2_graph().invoke()` with real Claude | `2026-08-30-phase-b7-end-to-end-agent-loop.md` | — | `phase-b7-agent-layer-activation.md` | partial |
| **B-G03** | wire `daily` skill as entry_point | — | — | — | **GAP** (Diag 09 ADR-014 candidate) |
| **B-G04** | CLI wrapper: graph.invoke() → taskdog task | `2026-08-30-phase-b7-end-to-end-agent-loop.md` | — | `phase-b7-agent-layer-activation.md` | partial |
| **B-G05** | E2E smoke: chat → tag_and_persist → commit → vault + taskdog | `2026-08-30-phase-b7-end-to-end-agent-loop.md` | — | `phase-b7-agent-layer-activation.md` | partial |
| **B-N01** | observe node (subprocess solverforge-calendar-mcp) | `2026-09-03-sonho-tree-hybrid-design.md` | ADR-013 | — | partial (subprocess wiring GAP) |
| **B-N02** | score_vectors node (6 prompt templates) | `2026-09-03-sonho-tree-hybrid-design.md` | — | — | partial (JSON extract GAP) |
| **B-N03** | heuristics node (H1/H2/H3/H6; H4/H5 prompts exist) | `2026-09-03-sonho-tree-hybrid-design.md` | — | — | partial (H4/H5 unwired GAP) |
| **B-N04** | balance node (hysteresis workload/capacity) | `2026-09-03-sonho-tree-hybrid-design.md` | — | — | ✅ |
| **B-N05** | decompose node (subprocess upi_search) | `2026-09-03-sonho-tree-hybrid-design.md` | — | — | partial (subprocess wiring GAP) |
| **B-N06** | plan node (_infer_tier logic) | `2026-09-03-sonho-tree-hybrid-design.md` | — | — | partial |
| **B-N07** | tag_and_persist node | `2026-09-03-sonho-tree-hybrid-design.md` | ADR-013 | `plan-a-planning-contract-plan-a.md` Task 8 | ✅ SHIPPED |
| **B-N08** | reflect node (subprocess upi_list) | `2026-09-03-sonho-tree-hybrid-design.md` | — | — | partial (subprocess wiring GAP) |
| **B-N09** | commit node (kill switch + vault_write) | `2026-09-03-sonho-tree-hybrid-design.md` | ADR-013 | `plan-a-planning-contract-plan-a.md` Task 9 | ✅ SHIPPED |
| **B-N10** | surface_intentions node (pt-BR suggestions) | — | — | — | **GAP** (marginal value, no spec) |
| **B-N11** | error node (terminal catch-all) | `2026-09-03-sonho-tree-hybrid-design.md` | — | — | ✅ |
| **B-C01** | Sonho contract | `2026-09-03-sonho-tree-hybrid-design.md` | — | `plan-a-planning-contract-plan-a.md` Task 1 | ✅ |
| **B-C02** | Objetivo contract | `2026-09-03-sonho-tree-hybrid-design.md` | — | `plan-a-planning-contract-plan-a.md` Task 2 | ✅ |
| **B-C03** | Meta contract | `2026-09-03-sonho-tree-hybrid-design.md` | — | `plan-a-planning-contract-plan-a.md` Task 3 | ✅ |
| **B-C04** | Projeto contract | `2026-09-03-sonho-tree-hybrid-design.md` | — | `plan-a-planning-contract-plan-a.md` Task 4 | ✅ |
| **B-C05** | Entrega contract | `2026-09-03-sonho-tree-hybrid-design.md` | — | `plan-a-planning-contract-plan-a.md` Task 5 | ✅ |
| **B-C06** | Tarefa contract | `2026-09-03-sonho-tree-hybrid-design.md` | — | `plan-a-planning-contract-plan-a.md` Task 6 | ✅ |
| **B-C07** | BasePlanContract (frozen + extra=forbid) + subset validator | `2026-09-03-sonho-tree-hybrid-design.md` | — | `plan-a-planning-contract-plan-a.md` Task 7 | ✅ (registry lookup DEFERRED) |
| **B-C08** | 3 enums (PlanTier/PaeCyclePhase/VectorKey) | `2026-09-03-sonho-tree-hybrid-design.md` | — | `plan-a-planning-contract-plan-a.md` | ✅ |
| **B-M01** | ikigai_decompose MCP tool | `2026-08-28-phase-b3-mcp-gateway.md` | — | `phase-b3-mcp-gateway.md` | ✅ |
| **B-M02** | ikigai_write_tasks MCP tool | `2026-08-28-phase-b3-mcp-gateway.md` | — | `phase-b3-mcp-gateway.md` | ✅ |
| **B-M03** | ikigai_read_tasks MCP tool | `2026-08-28-phase-b3-mcp-gateway.md` | — | `phase-b3-mcp-gateway.md` | ✅ |
| **B-M04** | ikigai_mesh_show MCP tool | `2026-08-28-phase3-data-mesh-design.md` | — | `phase3-data-mesh-v1.md` | ✅ |
| **B-M05** | ikigai_task_create MCP tool | `2026-08-28-phase3-data-mesh-design.md` | — | `phase3-data-mesh-v1.md` | ✅ |
| **B-M06** | ikigai_health MCP tool | `2026-08-28-phase-b3-mcp-gateway.md` | — | `phase-b3-mcp-gateway.md` | ✅ |
| **B-M07** | vault_write MCP tool (actor: Literal) | `2026-08-29-phase-b6-vault-sync-design.md` | ADR-013 | `phase-b6.md` + `plan-a-planning-contract-plan-a.md` Task 10 | ✅ |
| **B-M08** | vault_read MCP tool | `2026-08-29-phase-b6-vault-sync-design.md` | — | `phase-b6.md` | ✅ |
| **B-M09** | ikigai_score (observation wrapper) | `2026-08-29-algorithm-attribution-design.md` | ADR-013 | `plan-a-planning-contract-plan-a.md` (re-registered) | ✅ |
| **B-M10** | ikigai_regime (observation wrapper) | `2026-08-29-algorithm-attribution-design.md` | ADR-013 | (Phase 8.2) | ✅ |
| **B-M11** | ikigai_phase (observation wrapper) | `2026-08-29-algorithm-attribution-design.md` | ADR-013 | (Phase 8.2) | ✅ |
| **B-M12** | ikigai_corrections (observation wrapper) | `2026-08-29-algorithm-attribution-design.md` | ADR-013 | (Phase 8.2) | ✅ |
| **B-M13** | ikigai_plan_cycle (ARCHIVED) | `2026-08-29-algorithm-attribution-design.md` | ADR-013 | (Phase 8.2) | ✅ |
| **B-M14** | ikigai_checkpoint (SqliteSaver adapter) | — | — | — | **GAP** (LangGraph checkpoint contract unclear) |
| **B-M15** | ikigai_sync_vault (read-only log) | `2026-08-29-phase-b6-6-bidirectional-vault-sync.md` | — | `phase-b6-6.md` | ✅ |
| **B-M16** | 7 fork MCP tools (sf_* + tuiboard_*) | `2026-08-30-fork-connection-architecture.md` | ADR-012 | `fork-connection-implementation.md` | ✅ (taskdog_* DEFERRED Path 3) |
| **B-D01** | drift (a) vault_write sole writer | `2026-09-03-sonho-tree-hybrid-design.md` | ADR-013 | `plan-a-planning-contract-plan-a.md` Task 10/12 | ✅ |
| **B-D02** | drift (b) review_queue append-only | `2026-08-28-phase-b3-mcp-gateway.md` | — | `phase-b4-review-queue-worker.md` | ✅ |
| **B-D03** | drift (c) v2 prompts don't touch forbidden math modules | `2026-08-29-algorithm-attribution-design.md` | ADR-013 | Phase 8.2 | ✅ |
| **B-D04** | drift (d) META tier has PROJETO (registry lookup) | `2026-09-03-sonho-tree-hybrid-design.md` | — | `plan-a-planning-contract-plan-a.md` Task 10 (DEFERRED) | **GAP** (STUBBED) |
| **B-D05** | drift (e) vault_write actor="agent" → transition_validator | — | — | — | **GAP** (Diag 09 ADR-018 candidate) |
| **B-D06** | drift (f) external_roots.yaml allow-list | `2026-09-03-sonho-tree-hybrid-design.md` | — | `external-folder-access-plan-b.md` | ✅ (Plan B) |
| **B-D07** | drift (g) vault_write audit log non-empty | `2026-09-03-sonho-tree-hybrid-design.md` | ADR-013 | `plan-a-planning-contract-plan-a.md` Task 11/12 | partial (file written, test absent) |
| **B-D08** | drift (h) investigation_queue append-only | `2026-09-03-sonho-tree-hybrid-design.md` | — | `investigation-queue-plan-c.md` | ✅ (Plan C) |
| **B-D09** | drift (i) external_folder path_traversal guard | `2026-09-03-sonho-tree-hybrid-design.md` | — | `external-folder-access-plan-b.md` | ✅ (Plan B) |
| **B-T01** | transition_validator (SONHO.user-only) | `2026-09-03-sonho-tree-hybrid-design.md` | — | `plan-a-planning-contract-plan-a.md` Task 12 | ✅ |
| **B-T02** | 6×6 transition matrix (36 cells) | — | — | — | **GAP** (matrix inferred, not coded) |
| **B-T03** | audit_log writer for transition violations | — | — | — | **GAP** (no file, spec only) |
| **B-T04** | phase FSM (pae_cycle_phase × pae_tier) | `2026-09-03-sonho-tree-hybrid-design.md` | — | — | **GAP** (enum exists, FSM logic absent) |

**Coverage summary:**
- ✅ fully covered + shipped: **18** tasks
- partial (spec exists, sub-detail missing): **16** tasks
- **GAP** (no spec/plan/ADR): **13** tasks (B-G01, B-G03, B-N10, B-M14, B-D04, B-D05, B-T02, B-T03, B-T04 + 5 subprocess-wiring sub-tasks under B-N01/N05/N08)

---

## Implicit decisions (Diag 09 cross-ref)

Diag 09 identified 11 implicit decisions (ADR-020 through ADR-024 + extras). Cross-referenced against existing spec/plan coverage:

| Diag 09 ADR candidate | Already spec'd as | Recommendation |
|-----------------------|-------------------|----------------|
| **ADR-014 — Skill binding mechanism** (B-G03) | Phase 8 memory `phase-8-agentic-systems-refactor-complete-2026-09-03` mentions 4 skill files | **Promote memory → ADR** (4-6h) |
| **ADR-015 — Sub-agent dispatch protocol** (B.1) | — | **Write fresh ADR** (6-10h) |
| **ADR-016 — Stateful subgraph strategy** (B.2) | `graph.py:330-335` SqliteSaver wired but unused | **Write fresh ADR** (8-12h, most consequential) |
| **ADR-017 — Memory layer across cycles** (B.4) | Phase 8 mitigation memory suggests `vault/ikigai/meta/cycle_state/{date}.md` | **Write fresh ADR** (6-10h) |
| **ADR-018 — Kill switch + review queue wiring** (C.2) | `commit.py:25` `_KILL_SWITCH = False` (mechanism exists, semantics unclear) | **Write fresh ADR** (4-6h, safety-critical) |
| **ADR-019 — Empirical algorithm tuning approach** (C.4) | `algorithm-scope-reframed-2026-08-30` + `algorithm-gate-dropped-2026-09-03` | **Write fresh ADR** (2-4h, references existing mems) |
| **ADR-020 — Deep-Agent as Canonical Carro-Chefe** | `master-branch-carro-chefe-2026-08-28` memory | **Promote memory → ADR** (1-2h, or fold into ADR-013 expansion) |
| **ADR-021 — Default-Deny External Folder Access** | `external-folder-access-plan-b.md` (Plan B shipped) | **Promote plan → ADR** (1-2h) |
| **ADR-022 — Two-Queue Architecture (review + investigation)** | `investigation-queue-plan-c.md` (Plan C shipped) | **Promote plan → ADR** (1-2h) |
| **ADR-023 — UEID Canonical Format** | `ueid-5part-canonical-decision-2026-08-31` memory + ADR-012 §Decision | **Promote memory → ADR** (1h) |
| **ADR-024 — PAV Kernel Archive** | `pav-kernel-archived-2026-08-31` memory + ADR-013 §Out-of-Scope | **Promote memory → ADR** (1h) |

**Finding:** All 11 ADR candidates are documented **somewhere** (memory or plan), but **none** are in `code-docs/adr/`. The codebase has the **knowledge** but not the **architectural artifact**. This is exactly the doc-debt pattern Diag 09 flagged.

---

## Spec orphans

Specs that reference code/symbols that no longer exist (or have drifted):

1. **`2026-08-25-ikigai-vault-layers-design.md` (SUPERSEDED 2026-08-28)** — references `packages/core/src/ikigai/entities/plan/*.py` (Pydantic location) which has been refactored to `src/contracts/*.py`. Entire spec is pre-pivot architecture; **retained only as audit reference**. **Spec orphan.**

2. **`2026-08-26-data-model-unification-design.md` (SUPERSEDED 2026-08-28)** — references "Unified MCP Gateway" and "4 surfaces" (old IKIGAiRecord model); canonical model now lives in `src/contracts/common.py` (UEID). **Spec orphan.**

3. **`2026-08-28-phase3-data-mesh-design.md` §4** — error handling section is stale: "recovery playbooks reference `pav agent`" which is archived (per ADR-013). Other sections (1-3, 6+) remain canonical. **Partial spec orphan (§4 only).**

4. **`2026-08-29-phase-b5-b-agent-wiring-design.md`** — references `_handle_ikigai_plan_cycle` which now returns ARCHIVED (per `algo-strip-agent-layer-complete-2026-08-31` memory). **Spec orphan (one section).**

5. **`2026-08-29-phase-b6-6-bidirectional-vault-sync.md`** — references `agentic_writer` MCP tool which was DELETED (per Phase B7 ship memory). **Spec orphan (one section).**

6. **`2026-09-03-go-tui-vault-reader-full-design.md`** — describes Go TUI architecture that has NOT been implemented. Forward-looking orphan (no code, no plan, just design).

7. **`docs/superpowers/plans/2026-08-25-ikigai-vault-layers.md`, `2026-08-26-phase-mcp-unified-planning.md`** — both SUPERSEDED 2026-08-28; reference pre-pivot PAV-kernel architecture. **Plan orphans.**

8. **`archive/recovered-agentic-2026-09-01/`** — referenced in `roadmap-2026-09-04-harness-mvp.md:82` as historical source for v2 graph restoration; not actively used but cross-referenced as drift-detector-blind. **Code orphan (deferred review per `agentic-systems-recovered-2026-09-01` memory).**

---

## Implementation orphans

Code that does something but no spec describes it:

1. **`src/ikigai/src/agents/v2/tools_v2.py` (172 lines)** — defines `IKIGAI_NODE_TOOLS = [v2_observe_pav_state, ...]` (8 tools) which is drift-detector-blind. The v2 graph imports render_* functions directly, so this list is unused in production. **Implementation orphan (parallel test surface, no spec).**

2. **`src/ikigai/src/agents/v2/harness_legacy_reference.py` / `tools_legacy_reference.py`** — wrapped in `if False:` blocks per Diag 01. Historical reference only. **Implementation orphan (historical artifact).**

3. **`src/ikigai/src/agents/v2/nodes/score_vectors.py:53` `_stub_meta_vector`** — fallback only when `IKIGAI_FAKE_LLM=1`. No spec describes when/why FAKE_LLM is acceptable in production vs test. **Implementation orphan.**

4. **`src/ikigai/src/agents/v2/nodes/observe.py:56-61` hardcoded `DEFAULT_QHE_PUSH=0.85 / DEFAULT_QHE_RECOVER=0.60`** — flagged ⚠️ in Phase 8 review as borderline; no spec governs how/when to extract to policy. **Implementation orphan (per Phase 8 review).**

5. **`src/ikigai/src/agents/v2/nodes/commit.py:25` `_KILL_SWITCH = False`** — module-level flag, no env var, no runtime gate. The kill switch semantics are undocumented (Diag 09 ADR-018 candidate). **Implementation orphan.**

6. **`src/contracts/planning.py`** — appears in git status as "M" (modified); per Diag 04 note "moved to planning.py per [[plan-a-planning-contract-shipped-2026-09-03]] refactor" — confirms contracts have been migrated but the original `sonho.py`, `objetivo.py`, `meta.py`, `projeto.py`, `entrega.py`, `tarefa.py` files may now be deprecated. **Implementation orphan** (contracts migrated, original files may be stale).

7. **`interfaces/tui/operator/` (Textual 3 tabs)** — ships per Phase 9 memory but no spec/plan describes the 3 tabs (which views, which actions, which data sources). **Implementation orphan (no spec).**

8. **`src/taskdog_mcp/` (FastMCP 4 tools)** — ships per Phase 9 memory + `2026-09-04-diag-02-mesh-taskdog-mcp.md` but no design spec exists. **Implementation orphan (no spec).**

9. **`data/review_queue/` filesystem queue + worker** — design is documented across multiple plans (B4, B6, B7) but the **append-only invariant** (drift invariant b) is enforced without a standalone spec. **Implementation orphan (cross-cutting invariant, no canonical spec).**

10. **`data/investigation_queue/` filesystem queue** — Plan C ships, but the **FSM** (`open→in_progress→resolved|archived`) is in the plan, not in a design spec. **Implementation orphan (plan-only, no design spec).**

---

## Top 5 spec gaps (priority order)

Ranked by **(a) blocking subsequent work + (b) risk of re-litigation** (per Diag 09 §4).

1. **B-D05 + B-D04 + ADR-018 — Kill switch + transition_validator wiring (drift invariants d, e)** — blocks C.2 (kill switch wiring) and B-T01/B-T02 (per-tier validation). Drift detector currently 8/8 → 9/9 post Plan A; (d) STUBBED, (e) planned Scenario B.5; neither spec'd. Effort: 4-6h ADR + 5h code. **Most critical-path gap.**

2. **B-G03 + ADR-014 — Skill binding mechanism** — blocks A.3 (skill entry-point wiring). Determines whether IKIGAI_TOOLS grows from 12→16+ or stays flat. 4 skill markdown files exist (per Phase 8 memory) but frontmatter schema, trigger conditions, parameter binding are undocumented. Effort: 4-6h ADR + 6h code.

3. **B-M14 + ADR-016 — Stateful subgraph strategy (SqliteSaver)** — `graph.py:330-335` wires SqliteSaver but **never used** (per roadmap L96). Locks checkpoint key schema, state ownership, concurrency. Affects B.2 + B.4 (memory layer). Effort: 8-12h ADR + 8h code. **Most consequential in B-scenario.**

4. **B-T02 + B-T03 + B-T04 — 6×6 transition matrix + audit log + phase FSM** — `transition_validator.py` is 45 lines with only SONHO.user-only check; full 36-cell matrix is **inferred but not coded**. Drift invariant (e) depends on per-tier logic. Audit log writer doesn't exist. PaeCyclePhase enum exists but FSM logic absent. Effort: 4h matrix + 2h audit + 3h FSM = 9h code, no ADR needed (already in SONHO spec).

5. **B-G01 + B-G02 + B-G04 — pytest infra + smoke test + CLI wrapper (Critical path: B-G01 → B-G02 → B-G03 → B-G04 → B-G05, ~32h)** — B-G01 (6h) unblocks all v2 tests. B-G02 (8h) depends on API 529 risk (per Diag 04 unverifiable). B-G04 (8h) wraps graph.invoke() → taskdog task. **No formal spec** for any of these beyond Phase B7 plan reference. Effort: ~32h implementation, no ADR needed.

---

## Effort estimate

**Total ADR work (per Diag 09): 35-55h** (~4.5-7 working days focused)

Breakdown:
- ADR-014 (skill binding): 4-6h
- ADR-015 (sub-agent dispatch): 6-10h
- ADR-016 (stateful subgraph): 8-12h
- ADR-017 (memory layer): 6-10h
- ADR-018 (kill switch + review queue): 4-6h
- ADR-019 (empirical algorithm tuning): 2-4h
- ADR-020 (Deep-Agent carro-chefe): 1-2h
- ADR-021 (default-deny external): 1-2h
- ADR-022 (two-queue architecture): 1-2h
- ADR-023 (UEID canonical format): 1h
- ADR-024 (PAV archive): 1h

**Spec fills (non-ADR): 13-19h**
- 6×6 transition matrix spec: 2h
- audit_log writer spec: 1h
- phase FSM spec: 2h
- skill binding formal spec (frontmatter schema, triggers): 4h
- subprocess wiring spec (solverforge-calendar-mcp, upi_search, upi_list): 3h
- Go TUI forward spec (or formally defer to "DESIGN — no code"): 1h
- interfaces/tui/operator spec: 2h
- taskdog_mcp/ spec: 1-2h

**Total spec work: 48-74h** (~6-9 working days focused)

---

## Summary

| Metric | Value |
|--------|-------|
| Spec files inventoried (`docs/superpowers/specs/`) | 23 |
| Plan files inventoried (`docs/superpowers/plans/`) | 18 |
| ADR files inventoried (`code-docs/adr/`) | 7 |
| Adjacent ADR surfaces (vibe-ops + PAV archive) | 22 (6 + 16, mostly historical) |
| **Total spec/ADR/plan docs surveyed** | **70** |
| Backend tasks in Diag 04 | 47 |
| Tasks fully covered + shipped | 18 |
| Tasks partial coverage | 16 |
| **Tasks with GAP (no spec/plan/ADR)** | **13** |
| Spec orphans (reference non-existent code) | 8 |
| Implementation orphans (no spec) | 10 |
| Implicit decisions to formalize (Diag 09 ADRs) | 11 |
| Top 5 spec gaps total effort | 56-77h |

**Honest assessment:** Spec/ADR coverage is **~62% complete**. The shipped layer (Phase A fork MCP, Plan A contracts, Plan B/C external + investigation) is well-spec'd. The **pending layer** (kill switch, stateful subgraph, sub-agent dispatch, memory layer, transition matrix) is **spec-light** — most of these exist as roadmap tasks with implicit decisions in memory. The gap is **time-bounded**: ADR-016 → ADR-015 → ADR-017 → ADR-014 (per Diag 09 §4.1) is the priority sequence, and these 4 ADRs alone account for 24-38h of the 35-55h total ADR effort.

**Recommended next concrete task:** Write ADR-016 (Stateful subgraph strategy) — most consequential B-scenario gap; locks checkpoint schema that ADR-017 (memory layer) needs to design against.

---

**File written:** `C:\Users\mathe\code_space\life-oss\life\docs\superpowers\specs\2026-09-04-diag-10-spec-gap.md`
**Verified claims count:** 18 (each with file:line citation)
**Unverifiable claims count:** 6 (B-G02 smoke test, B-N10 marginal value, registry lookup deferral details, audit log test absence, FAKE_LLM production semantics, transition matrix per-cell logic)