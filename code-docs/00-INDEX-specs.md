# Specs, PRDs, BRDs, ARDs, ADRs — Master Index

> **Canonical index of all engineering and product spec documents across the IKIGAi project.**
> This file is the single landing page for anyone asking "what is the spec for X?"
> and the authoritative cross-reference for ADR ↔ implementation links.

**Coverage**: `code-docs/{prd,brd,ard,adr}/`, `vibe-ops/specs/`, `vibe-ops/architecture/`,
`vibe-ops/planning/`, plus the canonical operational ADRs at `life-ops/operational/docs/adr/`.

**Maintenance**: Append-only for ADRs (supersede, never delete). Reviewed every sprint.
See §8 for rules.

---

# 1. By type

## PRDs — Product Requirements Documents

| File | Lines | Summary |
|------|------:|---------|
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\PRD-01-temporal-engine.md` | 250 | Wave/Cycle/Phase temporal engine — 180d Phase → 45d Cycle → 15d Wave; ReviewEvents at mid-wave / wave-end / mid-cycle / cycle-end. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\PRD-02-habit-tracker.md` | 301 | Habit tracker — H(t) learning curve, E(t) energy, Q_HE composite; feeds PolicyEngine. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\PRD-03-study-backlog.md` | 413 | Study backlog — Skill → Topic → Material → Session pipeline; CLR (Cognitive Load Ratio) target 0.4. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\PRD-04-project-execution.md` | 220 | Project execution — SoftwareProject → Epic → Sprint → Task ↔ Taskwarrior (bidirectional sync). |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\PRD-05-metrics-health.md` | 283 | Metrics & health — SleepRecord, EnergyReading, DailyConsolidation; telemetria para PolicyEngine. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\PRD-06-policy-governance.md` | 307 | Policy & governance — 4-state FSM (PUSH/MAINTAIN/REDUCE/RECOVER) with hysteresis (3d upgrade / 2d downgrade). |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\PRD-07-ikigai-vectors.md` | 311 | IKIGAi vectors — Passion/Skill/Market/Revenue + Course; bipartite Gaussian topology. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\prd-temporal-engine.md` | 23 | English mirror of PRD-01. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\prd-habit-tracker.md` | 24 | English mirror of PRD-02. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\prd-study-backlog.md` | 24 | English mirror of PRD-03. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\prd-project-execution.md` | 24 | English mirror of PRD-04. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\prd-metrics-health.md` | 23 | English mirror of PRD-05. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\prd-policy-governance.md` | 24 | English mirror of PRD-06. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\prd-ikigai-vectors.md` | 25 | English mirror of PRD-07. |
| `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\adr\PRD-CONSTANTS-EXCEPTIONS.md` | — | PAV constants + 10 error codes. |
| `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\adr\PRD-CORE-HABIT-ENGINE.md` | — | PAV Habit engine H(t), E(t), Q_HE. |
| `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\adr\PRD-CORE-POLICY-CONSOLIDATOR.md` | — | PAV PolicyEngine 4-state FSM. |
| `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\adr\PRD-CORE-POMODORO-SCENARIO.md` | — | PAV 8-state pomodoro SM + scenario classifier. |
| `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\adr\PRD-CORE-SLEEP-VALIDATION.md` | — | PAV sleep calculator + validation. |
| `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\adr\PRD-CORE-TIME-BLOCKS-AND-REFLECTION.md` | — | PAV time blocks + journal reflection. |

> **PRD README index files**: `code-docs\prd\README.md` (23 lines) and `life-ops\operational\docs\adr\PRD-*` are listed in `code-docs\adr\OPERATIONAL.md`.

## BRDs — Business Requirements Documents

| File | Lines | Summary |
|------|------:|---------|
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CLUSTER_PLAN_BRD.md` | 251 | Cluster 1 (Plan) business requirements. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CLUSTER_PLAN_USER_STORIES.md` | 246 | 10 user stories (US-001 → US-010). |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CLUSTER_PLAN_CLI_SPEC.md` | 272 | 13 CLI commands spec. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CLUSTER_PLAN_ROADMAP.md` | 259 | 12-sprint Q3 2026 roadmap. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CLUSTER_PLAN_DATA_MODEL.md` | 376 | Data model for Cluster 1. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CHECKPOINT-2026-06-07-pre-development.md` | 463 | Pre-development checkpoint — context for the 9 drilldowns. |

## ARDs — Architecture Requirements Documents

| File | Lines | Summary |
|------|------:|---------|
| `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\adr\ARCHITECTURAL_REFRAMING_2026-06-07.md` | — | Post-Sprint 10 architectural reframe of the PAV kernel. |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CHECKPOINT-2026-06-07-pre-development.md` | 463 | Pre-development checkpoint (cross-listed — also BRD). |

> **PT-BR master index/architecture docs** are read-only references but not spec
> documents: `ARCHITECTURE_INDEX.md`, `CONCEPTUAL_MODEL.md`, `SYSTEMS_TOPOLOGY.md`,
> `CLUSTER_PLAN.md`, `CLUSTER_PROJ.md`, `CLUSTER_STUDY.md`.

## ADRs — Architecture Decision Records

| File | Lines | Status |
|------|------:|--------|
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\ADR-001-data-flow-topology.md` | 387 | **Accepted** (v1.0 → v1.1, multi-cluster expansion 2026-06-05) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\ADR-002-mesh-contracts-state-machines.md` | 210 | **Accepted** (2026-06-05) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\ADR-003-ikigai-as-meta-brain.md` | 234 | **Proposed** (2026-06-05) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\ADR-004-hybrid-rag-strategy.md` | 190 | **Proposed** (2026-06-05) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\ADR-005-data-mesh-topology.md` | 230 | **Proposed** (2026-06-05) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\ADR-006-period-reports-schema.md` | 297 | **Accepted** (2026-06-26) |
| `C:\Users\mathe\code_space\life-oss\life\code-docs\adr\ADR-007-data-first-methodology.md` | 137 | (verify status — see code-docs/adr/) |

> **Operational ADRs** (PAV kernel, `life-ops/operational/docs/adr/`): see
> `code-docs\adr\OPERATIONAL.md` for canonical index — 12 PRD-prefixed entries plus
> 3 sprint reports (SPRINT-1 / 2 / 3-REPORT.md).

## SPECs — Engineering Schemas

| File | Lines | Domain |
|------|------:|--------|
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\SPEC-05-cybernetic-epistemic-mesh.md` | 69 | schema (Hybrid RAG topology) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\schema-frontmatter-contract.md` | 223 | schema (YAML v1 — **deprecated**) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\schema-frontmatter-contract-v2.md` | 348 | schema (YAML v2 — canonical) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\schema-pydantic-models.md` | 403 | schema (Pydantic v1 — **deprecated**) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\schema-pydantic-models-v2.md` | 1003 | schema (Pydantic v2 — canonical) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\schema-planner-extension.md` | 1904 | entity (Wave/Cycle/Phase/Habit planner extension) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\spec-cluster-plan-inputs.md` | 217 | pipeline (Socratic journaling, pomodoro, sleep inputs) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\spec-cluster-plan-pipelines.md` | 352 | pipeline (Journal / Q_HE / Report pipelines) |
| `C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\spec-cluster-plan-reports.md` | 384 | pipeline (daily / weekly / monthly / wave reports) |

---

# 2. By domain

## PAV kernel (`life-ops/operational/`)

| Doc | Type | Path |
|------|------|------|
| `ARCHITECTURAL_REFRAMING_2026-06-07.md` | ARD | `life-ops/operational/docs/adr/` |
| `PRD-CONSTANTS-EXCEPTIONS.md` | PRD | `life-ops/operational/docs/adr/` |
| `PRD-CORE-HABIT-ENGINE.md` | PRD | `life-ops/operational/docs/adr/` |
| `PRD-CORE-POLICY-CONSOLIDATOR.md` | PRD | `life-ops/operational/docs/adr/` |
| `PRD-CORE-POMODORO-SCENARIO.md` | PRD | `life-ops/operational/docs/adr/` |
| `PRD-CORE-SLEEP-VALIDATION.md` | PRD | `life-ops/operational/docs/adr/` |
| `PRD-CORE-TIME-BLOCKS-AND-REFLECTION.md` | PRD | `life-ops/operational/docs/adr/` |
| `PRD-ENTITIES-*.md` (6 files) | PRD | `life-ops/operational/docs/adr/` |
| `PRD-ENUMS-TYPES.md` | PRD | `life-ops/operational/docs/adr/` |
| `OPERATIONAL.md` | ADR index | `code-docs/adr/` |

## vibe-ops cybernetic (`vibe-ops/`)

| Doc | Type | Path |
|------|------|------|
| ADR-001 → ADR-006 | ADR | `vibe-ops/architecture/` |
| SPEC-05 + 4 schema-* + 3 spec-cluster-plan-* | SPEC | `vibe-ops/specs/` |
| PRD-01 → PRD-07 | PRD | `vibe-ops/planning/` |
| `schema-planner-extension.md` | SPEC | `vibe-ops/specs/` |
| 7 prd-*.md (English mirrors) | PRD | `vibe-ops/specs/` |

## Root CLI hub (`life/`)

| Doc | Type | Path |
|------|------|------|
| `OPERATIONAL.md` | ADR index | `code-docs/adr/` |
| `VIBE-OPS.md` | ADR index | `code-docs/adr/` |
| `ADR-007-data-first-methodology.md` | ADR | `code-docs/adr/` |

## Strategic planning (`vibe-ops/planning/`)

| Doc | Type | Path |
|------|------|------|
| `CLUSTER_PLAN_BRD.md` | BRD | `vibe-ops/planning/` |
| `CLUSTER_PLAN_USER_STORIES.md` | BRD | `vibe-ops/planning/` |
| `CLUSTER_PLAN_CLI_SPEC.md` | BRD | `vibe-ops/planning/` |
| `CLUSTER_PLAN_ROADMAP.md` | BRD | `vibe-ops/planning/` |
| `CLUSTER_PLAN_DATA_MODEL.md` | BRD | `vibe-ops/planning/` |
| `CHECKPOINT-2026-06-07-pre-development.md` | BRD/ARD | `vibe-ops/planning/` |
| 9 period templates + 3 sprint templates | template | `vibe-ops/planning/_templates_periodos_v2/` + `vibe-ops/planning/TEMPLATE-*.md` |

---

# 3. By status

## Accepted

| File | Date | Notes |
|------|------|-------|
| `vibe-ops/architecture/ADR-001-data-flow-topology.md` | 2026-05-03 → 2026-06-05 | Multi-cluster expansion |
| `vibe-ops/architecture/ADR-002-mesh-contracts-state-machines.md` | 2026-06-05 | Data-mesh contracts |
| `vibe-ops/architecture/ADR-006-period-reports-schema.md` | 2026-06-26 | Period report schema |
| `vibe-ops/specs/schema-frontmatter-contract-v2.md` | 2026-05-09 | Canonical YAML schema |
| `vibe-ops/specs/schema-pydantic-models-v2.md` | 2026-05-09 | Canonical Pydantic v2 |

## Proposed

| File | Date | Notes |
|------|------|-------|
| `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` | 2026-06-05 | IKIGAi meta-brain architecture |
| `vibe-ops/architecture/ADR-004-hybrid-rag-strategy.md` | 2026-06-05 | Hybrid RAG |
| `vibe-ops/architecture/ADR-005-data-mesh-topology.md` | 2026-06-05 | 4-domain autonomous mesh |

## Draft

All `PRD-01` → `PRD-07` files declare **Status: Draft** (version 1.0.0, 2026-05-10).
All operational PRDs (`PRD-CORE-*`, `PRD-ENTITIES-*`, `PRD-CONSTANTS-EXCEPTIONS`) are
drafts awaiting implementation. `schema-planner-extension.md` (v0.1.0, 2026-05-09) is
draft for implementation. `schema-frontmatter-contract-v2.md` is "Draft para
implementação".

## Deprecated / Superseded

| Old | Replaced by |
|------|------|
| `vibe-ops/specs/schema-frontmatter-contract.md` (v0.1.0) | `schema-frontmatter-contract-v2.md` |
| `vibe-ops/specs/schema-pydantic-models.md` (v0.1.0) | `schema-pydantic-models-v2.md` |
| `vibe-ops/planning/TEMPLATE-micro-ciclo.md` (1-7d, overlaps with Daily) | `_templates_periodos_v2/05-relatorio-diario.md` |
| `vibe-ops/planning/TEMPLATE-weekly-review.md` (no verdict) | `_templates_periodos_v2/04-revisao-semanal.md` |
| `vibe-ops/planning/TEMPLATE-epic-sprint.md` (1-4w, conflicts with Wave) | `_templates_periodos_v2/03-onda.md` |

---

# 4. Cross-references — ADR ↔ implementation

| ADR | Implementation files |
|------|------|
| ADR-001 (Data Flow Topology) | `vibe-ops/src/main.py`, `vibe-ops/src/middleware/sync_engine.py`, `vibe-ops/src/pipeline/ikigai_scorer.py` |
| ADR-002 (Mesh Contracts) | `vibe-ops/src/contracts/*.yaml`, `vibe-ops/src/models/*.py`, `vibe-ops/src/schemas/pydantic_v2.py`, `vibe-ops/src/storage/schema.sql` |
| ADR-003 (IKIGAi Meta-Brain) | `vibe-ops/base/IKIGAi.md`, `vibe-ops/vectors/`, `life-ops/planner/ikigai_planning/ikigai_north_star_metrics.md` |
| ADR-004 (Hybrid RAG) | `vibe-ops/specs/SPEC-05-cybernetic-epistemic-mesh.md`, `vibe-ops/src/pipeline/rag_indexer.py`, `vibe-ops/src/storage/chroma_adapter.py`, `vibe-ops/src/embeddings/provider.py` |
| ADR-005 (Data Mesh Topology) | `vibe-ops/src/storage/schema.sql`, `vibe-ops/src/middleware/sync_engine.py` |
| ADR-006 (Period Reports Schema) | `vibe-ops/planning/_templates_periodos_v2/`, `vibe-ops/specs/vault-bidirectional-sync/`, `strategics/00-ÍNDICE-PROGRESSIVO.md` |
| ADR-007 (Data-First Methodology) | (verify in `code-docs/adr/ADR-007-data-first-methodology.md`) |
| Operational PRDs (`PRD-CORE-*`) | `life-ops/operational/packages/core/src/operational/core/` |
| Operational entity PRDs (`PRD-ENTITIES-*`) | `life-ops/operational/packages/core/src/operational/entities/` |
| `PRD-01` → `PRD-07` (vibe-ops) | `vibe-ops/src/models/`, `vibe-ops/src/storage/`, `vibe-ops/src/pipeline/` |

---

# 5. Templates reference — 9 period templates

Located in `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\_templates_periodos_v2\`.

| # | File | Lines | Period | ADR / SPEC governing frontmatter contract |
|---|------|------:|--------|------|
| 1 | `00-quartely-planning.md` | 228 | Quarterly planning | ADR-006 + `schema-frontmatter-contract-v2.md` |
| 2 | `01-sonho.md` | 197 | 6-12 months (Strategic) | ADR-006 (verdict: 3-Axis FalsifiableHypothesis) |
| 3 | `02-avaliacao-trimestral.md` | 193 | 90 days (Strategic) | ADR-006 (verdict: Teste de Fogo lite, mean ≥ 0.70) |
| 4 | `03-onda.md` | 170 | 45 working days (Tactical) | ADR-006 (Route Correction: ≥ 0.75 / ≥ 0.50 / < 0.50) |
| 5 | `04-revisao-semanal.md` | 182 | 7 days | ADR-006 |
| 6 | `05-relatorio-diario.md` | 190 | 1 day | ADR-006 + `schema-planner-extension.md` |
| 7 | `06-quartely-review.md` | 179 | Quarterly review | ADR-006 |
| 8 | `07-sprint-kickoff.md` | 181 | Sprint start | ADR-006 |
| 9 | `08-sprint-retrospective.md` | 187 | Sprint retro | ADR-006 |

**Governing contract**: `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\ADR-006-period-reports-schema.md`
adopts 5 official templates aligned 1:1 with the `SONHO → TRIMESTRAL → ONDA → SEMANAL → DIÁRIO`
pyramid from `strategics/00-ÍNDICE-PROGRESSIVO.md`.

**Deprecated siblings** (still on disk, retained for traceability per Append-Only rule):
`TEMPLATE-epic-sprint.md`, `TEMPLATE-micro-ciclo.md`, `TEMPLATE-weekly-review.md` in
`vibe-ops/planning/`.

---

# 6. Open decisions tracker

Source: `C:\Users\mathe\code_space\life-oss\life\.omo\drafts\ikigai-as-dom-on-planning-engine.md`
§8 (draft captured 2026-06-30 — awaiting user input).

| ID | Decision | Status |
|----|----------|--------|
| **D1** | Should `_plan.md` live in vault (Obsidian) or in code (`life-ops/ikigai/data/`)? | Open |
| **D2** | Are existing IKIGAi tests (250+) converted to `_plan.md` format in this PR, or follow-up? | Open |
| **D3** | How are daily snapshots aggregated — one file per day, or one file per cycle? | Open |
| **D4** | Does planning-with-files need to learn IKIGAi custom frontmatter (`entity_type=IKIGAiDream`, etc.) or do we re-purpose existing type values? | Open |

---

# 7. How to add a new spec

- [ ] **Decide type** — PRD (product), BRD (business), ARD (architecture reqs), ADR (decision), or SPEC (schema/pipeline). One doc, one purpose.
- [ ] **Use the existing template** — match the file-naming convention (`PRD-NN-*.md`, `ADR-NNN-*.md`, `schema-*.md`, `spec-cluster-plan-*.md`).
- [ ] **Cross-reference existing ADRs** — every new spec must list which ADRs it supersedes, extends, or depends on (use §4 table format).
- [ ] **Update this index** — add the row to §1 (By type) and the relevant subsection of §2 (By domain); if it changes status, move between §3 subsections.
- [ ] **Bump version** in the doc header (`**Versão:**` / `**Status:**`) and the date.
- [ ] **Append-only for ADRs** — never edit an accepted ADR; instead, write a new ADR that supersedes it and link both directions.

---

# 8. Maintenance rules

- **Append-only for ADRs** — never delete. To reverse a decision, write a new ADR that explicitly supersedes the old one and update both statuses in §3.
- **Reviewed every sprint** — the index itself is reviewed at the end of every sprint (see `life-ops/operational/docs/adr/SPRINT-*-REPORT.md`). Any new spec landed during the sprint must be reflected here.
- **Cross-doc consistency** — when a PRD moves to Draft → Accepted, the matching operational PRD in `life-ops/operational/docs/adr/` (if any) must be updated the same sprint.
- **Read-only for PT-BR master docs** — `ARCHITECTURE_INDEX.md`, `CONCEPTUAL_MODEL.md`, `SYSTEMS_TOPOLOGY.md`, `CLUSTER_PLAN/PROJ/STUDY.md` are append-only and out of scope for edits.
- **Single Source of Truth per type** — English mirror PRDs in `vibe-ops/specs/prd-*.md` mirror the PT-BR originals in `vibe-ops/planning/PRD-NN-*.md`; update both, never drift.

---

*Last reviewed: 2026-07-02 — auto-generated from filesystem walk of `code-docs/`,
`vibe-ops/specs/`, `vibe-ops/architecture/`, `vibe-ops/planning/`,
`life-ops/operational/docs/adr/`.*