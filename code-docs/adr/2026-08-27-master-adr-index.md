# Master ADR Index — Life OSS Architecture Decision Records

**Date:** 2026-08-27
**Author:** Hephaestus (consolidation pass)
**Status:** Active navigation layer
**Scope:** all architecture decision records across 3 surfaces in `life/`

---

## §0. Purpose

This document is the **canonical navigation layer** for every Architecture Decision Record (ADR) in the `life/` submodule. The repo historically grew three independent ADR surfaces — each owned by a different subsystem — and contributors wasted time hunting for "where is the decision about X?".

The three surfaces consolidated here:

| Surface | Location | Owner | Doc-style |
|---|---|---|---|
| **vibe-ops** | `vibe-ops/architecture/` | cybernetic engine team | `ADR-NNN-*.md` (6 docs) |
| **PAV kernel** | `life-ops/operational/docs/adr/` | PAV productivity team | `PRD-*` + `ARCHITECTURAL_REFRAMING_*` (13+ docs) |
| **cross-cutting** | `code-docs/adr/` | life submodule meta | `ADR-NNN-*.md` (5 docs) |

**Goals of this index:**

1. Single table listing every ADR with status, date, surface, and what it affects.
2. Cross-reference each ADR to related **diagnostic issues** (master system diagnostic + algorithm issues registry).
3. Group by status (Aceita vs Proposta) and by surface.
4. Chronological timeline so newcomers can read the system as it was built.
5. Call out the pending decisions awaiting user input.
6. Maintenance rule for adding new ADRs without re-fragmenting.

For each ADR's full text, follow the link. This index is a **map**, not a substitute for the source-of-truth files.

---

## §1. All ADRs at a glance

Total: **11 numbered ADRs + 12 PAV PRDs/specs + 3 PAV sprint reports + 1 architectural reframe = 27 documents**.

| ID | Title (truncated) | Surface | Status | Date | Affects |
|----|-------------------|---------|--------|------|---------|
| ADR-001 | Data-flow topology (multi-cluster) | vibe-ops | Aceita | 2026-05-03 → 2026-06-05 | vibe-ops architecture, 5 sub-systems, 6 contracts |
| ADR-002 | Mesh contracts + state machines | vibe-ops | Aceita | 2026-06-05 | YAML/Pydantic/SQL triad, 14 state machines |
| ADR-003 | IKIGAi as meta-brain | vibe-ops | Proposta | 2026-06-05 | IKIGAi vectors, regime FSM, propagation contract |
| ADR-004 | Hybrid RAG (SQLite + Chroma + Obsidian) | vibe-ops | Proposta | 2026-06-05 | retrieval strategy, embeddings provider |
| ADR-005 | Data-mesh topology (4 domains, 6 contracts) | vibe-ops | Proposta | 2026-06-05 | PLANNING / STUDY / DEV / METRICS split |
| ADR-006 | Period reports template schema | vibe-ops | Aceita | 2026-06-26 | 5 period-report templates, verdict enums |
| ADR-007 | Data-first methodology | cross-cutting | Accepted | 2026-07-02 | closing-2026 arc, no new code before 5+ manual logs |
| ADR-008 | IKIGAI vector count (5 vs 4) | cross-cutting | Proposta | 2026-08-27 | IKIGAiProfile, PRD-07, vault frontmatter |
| ADR-009 | Pydantic strict mode invariance | cross-cutting | Proposta | 2026-08-27 | all 12+ IKIGAI entities + 17+ vibe-ops entities |
| ADR-010 | Dual CLAUDE.md scope strategy | cross-cutting | Proposta | 2026-08-27 | root CLAUDE.md vs `life/CLAUDE.md` |
| ADR-011 | HTTP+SSE transport for IKIGAI MCP | cross-cutting | Proposta | 2026-08-27 | `src/mcp_server/server.py:534` |
| REF-2026-06-07 | PAV architectural reframe | PAV | Aceita | 2026-06-07 | post-Sprint-10 PAV redesign |
| PRD-CONSTANTS | PAVConstants + 10 error codes | PAV | Aceita | 2026-Q2 | `constants.py`, error contract |
| PRD-CORE-HABIT | Habit engine H(t), E(t), Q_HE | PAV | Aceita | 2026-Q2 | habit scoring math |
| PRD-CORE-POLICY | PolicyEngine 4-state FSM | PAV | Aceita | 2026-Q2 | `policy_engine.py` |
| PRD-CORE-POMODORO | 8-state pomodoro SM + classifier | PAV | Aceita | 2026-Q2 | `pomodoro_scenario.py` |
| PRD-CORE-SLEEP | Sleep calculator + validation | PAV | Aceita | 2026-Q2 | `sleep_validation.py` |
| PRD-CORE-TIME-BLOCKS | Time blocks + journal reflection | PAV | Aceita | 2026-Q2 | `time_blocks.py` |
| PRD-ENTITIES-JOURNAL-HABIT | JournalEntry + Habit entities | PAV | Aceita | 2026-Q2 | `entities/journal.py`, `habit.py` |
| PRD-ENTITIES-METRIC | Metric entities + rollup | PAV | Aceita | 2026-Q2 | `entities/metric.py` |
| PRD-ENTITIES-POLICY | PolicySetpoints + PolicyDecision | PAV | Aceita | 2026-Q2 | `entities/policy.py` |
| PRD-ENTITIES-ROUTINE | Routine / TimeBlock / Pomodoro entities | PAV | Aceita | 2026-Q2 | `entities/routine.py` |
| PRD-ENUMS-TYPES | Enums + type definitions | PAV | Aceita | 2026-Q2 | `enums.py` |
| SPRINT-1 | Sprint 1 verification report | PAV | Aceita | 2026-Q2 | PAV kernel baseline |
| SPRINT-2 | Sprint 2 verification report | PAV | Aceita | 2026-Q2 | habit + policy integration |
| SPRINT-3 | Sprint 3 verification report | PAV | Aceita | 2026-Q2 | pomodoro + sleep integration |

**Note on PAV surface nomenclature.** The 13+ PAV "ADRs" are formally titled `PRD-*.md` (Product Requirements Documents) plus one `ARCHITECTURAL_REFRAMING_*` and three sprint reports. They function as architecture decisions for the PAV kernel and are tracked in the same registry — `code-docs/adr/OPERATIONAL.md` indexes them as canonical PAV specs. This ADR uses the same convention.

### §1.1. Extended table — with diagnostic + cluster cross-references

The compact table above omits one important column: **which diagnostic issue each ADR addresses**. Here is the same 27 documents with that column populated.

| ID | Title | Status | Date | Diagnostic ref | Cluster / sub-system |
|----|-------|--------|------|----------------|----------------------|
| ADR-001 | Data-flow topology | Aceita | 2026-05-03 / 2026-06-05 | G3 (3-place ADRs — partly) | vibe-ops multi-cluster |
| ADR-002 | Mesh contracts + state machines | Aceita | 2026-06-05 | S-C1 (split-brain schema) | vibe-ops data layer |
| ADR-003 | IKIGAi as meta-brain | Proposta | 2026-06-05 | N01 (vector weight mechanism) | IKIGAi meta-brain |
| ADR-004 | Hybrid RAG | Proposta | 2026-06-05 | (none — future) | vibe-ops retrieval |
| ADR-005 | Data-mesh topology | Proposta | 2026-06-05 | (none directly) | vibe-ops mesh |
| ADR-006 | Period reports schema | Aceita | 2026-06-26 | (none — new feature) | cluster_plan + sync layer |
| ADR-007 | Data-first methodology | Accepted | 2026-07-02 | (process-level) | all new feature work |
| ADR-008 | IKIGAI vector count | Proposta | 2026-08-27 | G2 | IKIGAI meta-brain |
| ADR-009 | Pydantic strict mode | Proposta | 2026-08-27 | S-M3 | IKIGAI + vibe-ops entities |
| ADR-010 | Dual CLAUDE.md scope | Proposta | 2026-08-27 | P8 + G8 | documentation surface |
| ADR-011 | HTTP+SSE transport | Proposta | 2026-08-27 | S-H1 + S-C2 | IKIGAI MCP server |
| REF-2026-06-07 | PAV architectural reframe | Aceita | 2026-06-07 | (post-Sprint 10 reorg) | PAV kernel |
| PRD-CONSTANTS | PAVConstants + 10 error codes | Aceita | 2026-Q2 | (none) | PAV kernel core |
| PRD-CORE-HABIT | Habit engine H(t), E(t), Q_HE | Aceita | 2026-Q2 | (none — math) | PAV habit engine |
| PRD-CORE-POLICY | PolicyEngine 4-state FSM | Aceita | 2026-Q2 | (none — math) | PAV policy engine |
| PRD-CORE-POMODORO | 8-state pomodoro SM | Aceita | 2026-Q2 | (none — math) | PAV pomodoro |
| PRD-CORE-SLEEP | Sleep calculator | Aceita | 2026-Q2 | (none — math) | PAV sleep module |
| PRD-CORE-TIME-BLOCKS | Time blocks + reflection | Aceita | 2026-Q2 | (none — math) | PAV time blocks |
| PRD-ENTITIES-JOURNAL-HABIT | JournalEntry + Habit entities | Aceita | 2026-Q2 | S-C1 (related) | PAV entities |
| PRD-ENTITIES-METRIC | Metric entities + rollup | Aceita | 2026-Q2 | (none) | PAV metrics |
| PRD-ENTITIES-POLICY | PolicySetpoints + PolicyDecision | Aceita | 2026-Q2 | (none) | PAV policy entities |
| PRD-ENTITIES-ROUTINE | Routine/TimeBlock/Pomodoro entities | Aceita | 2026-Q2 | S-C1 (related) | PAV entities |
| PRD-ENUMS-TYPES | Enums + type definitions | Aceita | 2026-Q2 | (none) | PAV types |
| SPRINT-1 | Sprint 1 verification | Aceita | 2026-Q2 | (historical) | PAV kernel baseline |
| SPRINT-2 | Sprint 2 verification | Aceita | 2026-Q2 | (historical) | PAV integration |
| SPRINT-3 | Sprint 3 verification | Aceita | 2026-Q2 | (historical) | PAV integration |

---

## §2. By status

### §2.1. Aceita / Accepted (16 docs)

Decision is in force; downstream code/policies conform.

**vibe-ops (3):** ADR-001, ADR-002, ADR-006

**cross-cutting (1):** ADR-007 (data-first methodology)

**PAV (12):** REF-2026-06-07 + 9 PRD-CORE/PRD-ENTITIES/PRD-ENUMS docs + 3 sprint reports

### §2.2. Proposta / Proposed (7 docs)

Decision documented but **not yet in force** — user input or migration script pending.

**vibe-ops (3, stale since 2026-06-05):**

- **ADR-003** — IKIGAi as meta-brain. Status quo is "IKIGAi is a calculator", not a meta-brain. The gap is documented (recomputed scores are 4 vectors instead of 5). Migration blocked by ADR-008 (5 vs 4 vectors) — both decisions must resolve together.
- **ADR-004** — Hybrid RAG (SQLite + ChromaDB + Obsidian). Implementation deferred to Q4 2026+. Sprint 1 plan explicitly says "do NOT implement Hybrid RAG yet".
- **ADR-005** — Data-mesh topology with 4 domains + 6 contracts. The 6 contracts are referenced from ADR-001 but never formally activated. Awaiting user approval to either ratify or simplify.

**cross-cutting (4, fresh as of 2026-08-27):**

- **ADR-008** — IKIGAI vector count (5 vs 4). Migration script MIG-5 ready. Awaiting user choice between Option A (5 vectors + Course) and Option B (4 vectors, remove Course).
- **ADR-009** — Pydantic strict mode. Migration script MIG-S-M3 ready. Awaiting user choice between Option A (enforce strict per CLAUDE.md) and Option B (relax invariant + annotation).
- **ADR-010** — Dual CLAUDE.md scope. Migration script MIG-8 ready. Awaiting user choice between Option A (keep both, add scope headers) and Option B (merge into `life/CLAUDE.md`, delete root).
- **ADR-011** — HTTP+SSE transport for IKIGAI MCP. **Recommended for acceptance** (Sprint 3, after Sprint 1+2 close). Migration script planned.

---

## §3. By surface

### §3.1. vibe-ops (6 ADRs) — cybernetic engine

`vibe-ops/architecture/`

| ADR | Title | Lines | Linked cluster docs |
|-----|-------|------:|---------------------|
| ADR-001 | Data-flow topology (multi-cluster) | ~390 | CLUSTER_PLAN.md, CLUSTER_PROJ.md, CLUSTER_STUDY.md |
| ADR-002 | Mesh contracts + state machines | ~210 | all 7 PRDs |
| ADR-003 | IKIGAi as meta-brain | ~235 | CONCEPTUAL_MODEL.md §3, CLUSTER_PLAN.md §4.5 |
| ADR-004 | Hybrid RAG strategy | ~190 | CLUSTER_STUDY.md |
| ADR-005 | Data-mesh topology | ~230 | CLUSTER_PLAN.md, CLUSTER_PROJ.md, CLUSTER_STUDY.md |
| ADR-006 | Period reports template schema | ~298 | _templates_periodos/, 3_indice/00_Period_Reports_Dashboard.md |

**Cross-ADR dependencies:**

- ADR-001 → ADR-002 (contracts enforce the topology)
- ADR-001 → ADR-005 (mesh contracts derive from topology)
- ADR-002 → ADR-003 (state machines include PolicyState)
- ADR-001 → ADR-006 (period_reports table extends the topology)

### §3.2. PAV kernel (13+ specs) — productivity math

`life-ops/operational/docs/adr/`

Indexed in `code-docs/adr/OPERATIONAL.md`. The 12 PRD files + 1 reframe + 3 sprint reports = 16 documents covering:

- **Engines** (5 PRDs): habit, policy, pomodoro, sleep, time-blocks
- **Entities** (4 PRDs): journal/habit, metric, policy, routine/timeblock/pomodoro
- **Types** (1 PRD): enums
- **Constants** (1 PRD): PAVConstants + 10 error codes
- **Reframe** (1 doc): post-Sprint-10 architectural pivot
- **Sprint reports** (3 docs): verification at Sprints 1, 2, 3

### §3.3. cross-cutting (5 ADRs) — life submodule meta

`code-docs/adr/`

| ADR | Title | Affects |
|-----|-------|---------|
| ADR-007 | Data-first methodology | all new feature work in closing 2026 |
| ADR-008 | IKIGAI vector count | IKIGAiProfile, PRD-07, vault frontmatter |
| ADR-009 | Pydantic strict mode | all entities across IKIGAI + vibe-ops |
| ADR-010 | Dual CLAUDE.md scope | root vs submodule documentation |
| ADR-011 | HTTP+SSE transport | IKIGAI MCP server transport layer |

These five were all written in **2026-07-02 (ADR-007)** and **2026-08-27 (ADR-008..011)** as part of the observability sprint + master diagnostic push. They form the **current decision queue** — see §5.

---

## §4. Decision timeline (chronological)

```
2026-05-03  ──┐
              │  ADR-001 v1.0 (3-domain topology)
              │
2026-06-05  ──┤  ADR-001 v1.1 expanded (5 sub-systems, multi-cluster)
              │  ADR-002 — Mesh contracts + state machines
              │  ADR-003 — IKIGAi as meta-brain (Proposta)
              │  ADR-004 — Hybrid RAG (Proposta)
              │  ADR-005 — Data-mesh topology (Proposta)
              │
2026-06-07  ──┤  PAV REF-2026-06-07 — architectural reframe
              │  PAV PRD-CONSTANTS / PRD-CORE-* / PRD-ENTITIES-* / PRD-ENUMS (12 docs)
              │  PAV SPRINT-1 / SPRINT-2 / SPRINT-3
              │
2026-06-26  ──┤  ADR-006 — Period reports template schema
              │
2026-07-02  ──┤  ADR-007 — Data-first methodology (Accepted)
              │
2026-08-27  ──┤  ADR-008 — IKIGAI vector count (Proposta)
              │  ADR-009 — Pydantic strict mode (Proposta)
              │  ADR-010 — Dual CLAUDE.md scope (Proposta)
              │  ADR-011 — HTTP+SSE transport (Proposta, recommended)
              │
              ▼  27 documents across 3 surfaces
```

**Read-order for a new contributor:**

1. `code-docs/00-INDEX.md` — repo entry point
2. ADR-007 (data-first methodology) — sets the operating mode
3. ADR-001 (data-flow topology) — the system shape
4. ADR-002 (contracts + state machines) — the data substrate
5. ADR-005 + ADR-006 (mesh + period reports) — domain structure
6. ADR-003 + ADR-004 (meta-brain + RAG) — optional, pending
7. PAV PRDs — for any PAV-touched code
8. ADR-008..011 — the live decision queue (read only after the above)

---

## §5. Pending decisions

### §5.1. The 4 fresh Proposta ADRs (2026-08-27) — awaiting user input

These are the decisions surfaced by the **master system diagnostic** (2026-08-27) and documented in the observability sprint. Each has a 2-option choice; migration scripts are staged but not run.

| ADR | Decision | Options | Migration script | Diagnostic ref |
|-----|----------|---------|------------------|----------------|
| **ADR-008** | IKIGAI vector count | A: 5 vectors + Course / B: 4 vectors, remove Course | MIG-5 | G2 (master diagnostic §5) |
| **ADR-009** | Pydantic strict mode | A: enforce strict per CLAUDE.md / B: relax invariant + annotate | MIG-S-M3 | S-M3 (master diagnostic §2) |
| **ADR-010** | Dual CLAUDE.md scope | A: keep both with scope headers / B: merge + delete root | MIG-8 | P8 + G3 (master diagnostic §3, §5) |
| **ADR-011** | HTTP+SSE MCP transport | A: add HTTP+SSE alongside stdio (recommended) / B: status quo | (planned, post-Sprint 2) | S-H1 + S-C2 (master diagnostic §2) |

**Recommended ordering (depends on observability sprint merge):**

1. **ADR-011 first** — unblocks S-C2 (dcode MCP registration) and the deep-agents LangGraph observability work. Lowest blast radius.
2. **ADR-008 + ADR-003 together** — vector count decision gates the meta-brain decision. Resolve both in one batch.
3. **ADR-009** — after the schema reconciliation (S-C1) lands; strict mode depends on schema stability.
4. **ADR-010 last** — pure documentation decision; reversible anytime.

### §5.2. The 3 stale Proposta ADRs (2026-06-05) — pending since the cybernetic-engine sprint

| ADR | Decision | Why still pending | Resolution path |
|-----|----------|-------------------|----------------|
| **ADR-003** | IKIGAi as meta-brain | Tied to ADR-008 (vector count). Sprint 1 marked "CRITICAL" but blocked on vector-count decision. | Resolve ADR-008 first; then activate the propagation contract. |
| **ADR-004** | Hybrid RAG | Implementation deferred to Q4 2026+ per Sprint 1 plan. ADR is correct; timing is wrong. | Re-evaluate after closing-2026 arc (per ADR-007 roll-back criteria). |
| **ADR-005** | Data-mesh topology (4 domains) | The 6 contracts are referenced from ADR-001 but never formally activated. | Either ratify (move to Aceita) or simplify (merge contracts into ADR-002). |

### §5.3. How to decide

- **Questionnaire** for the 4 fresh proposals: see `code-docs/diagnostic/2026-08-27-pending-constructions-detail.md` §3 (Pending Constructions D, I, J, K).
- **Migration scripts** catalogued in `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md`.
- **Risk/effort matrix** for each option: `code-docs/diagnostic/2026-08-27-risk-effort-matrix.md`.

---

## §6. Cross-reference map — ADR ↔ diagnostic issue

This is the load-bearing table for the observability sprint. Each diagnostic issue that triggered an ADR maps back to the ADR that owns its resolution.

| Diagnostic ID | Description | Source ADR | Migration script |
|---------------|-------------|------------|------------------|
| **G1** | `code-docs/adr/README.md` does not exist | (this index is the answer) | — |
| **G2** | IKIGAI vector count mismatch (5 vs 4) | **ADR-008** | MIG-5 |
| **G3** | ADRs in 3 separate places | (this index is the answer) | — |
| **G8** | Two CLAUDE.md files | **ADR-010** | MIG-8 |
| **P8** | Dual CLAUDE.md overlap | **ADR-010** | MIG-8 |
| **S-C1** | Plan-entities schema split-brain | (related to ADR-009) | — |
| **S-C2** | dcode not connected to IKIGAI MCP | (depends on **ADR-011**) | — |
| **S-H1** | IKIGAI MCP server stdio-only | **ADR-011** | (planned) |
| **S-M3** | Pydantic strict mode violated | **ADR-009** | MIG-S-M3 |
| **N01** | IKIGAi vector weight mechanism | (deferred, related to **ADR-003** + ADR-008) | — |

**Cross-references to other artifacts:**

- **Master diagnostic** → `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md`
- **Migration scripts catalog** → `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md`
- **Pending constructions detail** → `code-docs/diagnostic/2026-08-27-pending-constructions-detail.md`
- **Risk & effort matrix** → `code-docs/diagnostic/2026-08-27-risk-effort-matrix.md`
- **Algorithm Issues Registry** → user memory `algorithm-issues-registry.md`
- **Glossary** → `code-docs/glossary.md`

### §6.1. Inverse map — diagnostic → ADR

For triage use: when a new issue is identified, find which ADR (if any) owns its resolution.

| Diagnostic ID | Severity | Owning ADR (or "none") | Status |
|---------------|----------|------------------------|--------|
| C1 (ikigai_score fallback) | CRITICAL | none — needs new ADR | 🔴 open |
| C2 (dcode not connected) | CRITICAL | ADR-011 (S-C2 dependency) | 🟡 awaiting ADR-011 |
| C3 (Taskdog CLI subprocess) | CRITICAL | none — needs new ADR | 🔴 open |
| C4 (Plan-entities 24 vs 11 cols) | CRITICAL | ADR-009 (related) | 🟡 awaiting ADR-009 |
| C5 (score_history mutation) | CRITICAL | ADR-009 (related) | 🟡 awaiting ADR-009 |
| S-C1 (schema split-brain) | CRITICAL | ADR-009 (entity-level analog) | 🟡 awaiting ADR-009 |
| S-C2 (dcode MCP reg) | CRITICAL | ADR-011 (downstream) | � awaiting ADR-011 |
| S-C3 (taskdog CLI) | CRITICAL | none — needs new ADR | 🔴 open |
| S-H1 (stdio-only MCP) | HIGH | **ADR-011** | 🟡 awaiting decision |
| S-H2 (cache invalidation) | HIGH | none — code fix | 🔴 open |
| S-H3 (retry/CB) | HIGH | none — observability sprint | 🟡 planned |
| S-H4 (HITL on 6 tools) | HIGH | none — observability sprint | 🟡 planned |
| S-H5 (subagents) | HIGH | none — refactor | 🔴 open |
| S-H6 (sync_vault split-brain) | HIGH | none — code fix | 🔴 open |
| S-H7 (hard-coded paths) | HIGH | none — code fix | 🔴 open |
| S-H8 (no init_tracing) | HIGH | none — observability sprint | 🟡 planned |
| S-M1 (empty persistence/) | MEDIUM | none — code cleanup | 🔴 open |
| S-M2 (no migrations) | MEDIUM | none — needs ADR | 🔴 open |
| **S-M3** (Pydantic strict) | MEDIUM | **ADR-009** | 🟡 awaiting decision |
| S-M4 (no MCP tests) | MEDIUM | none — test addition | 🔴 open |
| S-M5 (no factories) | MEDIUM | none — test addition | 🔴 open |
| S-M6 (no mock backends) | MEDIUM | none — test addition | 🔴 open |
| S-M7 (score fallback) | MEDIUM | none — code fix | 🔴 open |
| P1 (PAV CLI broken) | CRITICAL | none — recovery branch | 🔴 open |
| P2 (orphaned tests/) | HIGH | none — recovery branch | 🔴 open |
| P3 (_PersistentRepo paths) | HIGH | none — code fix | 🔴 open |
| P4 (ikigai.bat venv) | HIGH | none — code fix | 🔴 open |
| P5 (verify_sprint mismatch) | HIGH | none — code fix | 🔴 open |
| P6 (Makefile uv vs poetry) | MEDIUM | none — code fix | 🔴 open |
| P7 (stray 0-byte files) | MEDIUM | none — cleanup | 🔴 open |
| **P8** (dual CLAUDE.md) | INFO | **ADR-010** | 🟡 awaiting decision |
| G1 (no ADR README) | CRITICAL | (this index) | 🟢 resolved |
| **G2** (vector count) | HIGH | **ADR-008** | 🟡 awaiting decision |
| **G3** (ADRs in 3 places) | HIGH | (this index) | 🟢 resolved |
| G4 (deprecated v1 schemas) | HIGH | none — needs ADR | 🔴 open |
| G5 (doc count approximate) | MEDIUM | (this index enumerates) | � resolved |
| G6 (stray files) | MEDIUM | none — cleanup | � open |
| G7 (throwaway files) | MEDIUM | none — cleanup | � open |
| G8 (two CLAUDE.md) | INFO | **ADR-010** (same as P8) | 🟡 awaiting decision |
| G9 (venv hardcoded) | MEDIUM | none — same as P4 | 🔴 open |
| G10 (verify_sprint) | MEDIUM | none — same as P5 | 🔴 open |
| N01 (vector weight mechanism) | (registry) | ADR-008 + ADR-003 | 🟡 deferred per ADR-007 |

**Summary:** 6 diagnostic issues have ADR ownership (G1, G2, G3, S-H1, S-M3, P8, N01). The remaining 30+ issues are open with no ADR.

---

## §7. Maintenance — when to update this index

### §7.1. When to ADD a row

Any time a new ADR is merged into any of the 3 surfaces:

1. Place the file in the correct surface directory:
   - `vibe-ops/architecture/` if it governs the cybernetic engine
   - `life-ops/operational/docs/adr/` if it governs the PAV kernel
   - `code-docs/adr/` if it governs cross-cutting or submodule-level concerns
2. Add a row to §1 of this index with: ID, title, surface, status, date, affects
3. Update the §2 status tally
4. Update the §3 surface count
5. Update the §4 timeline
6. If status is `Proposta`, add a row to §5 with the questionnaire link

### §7.2. When to MOVE a row

When a `Proposta` ADR is accepted or rejected:

1. Edit the source ADR (change `Status:` field)
2. Move the row in §1 to reflect the new status
3. Remove the row from §5
4. If accepted, ensure the migration script is run and removed from `migration-scripts-catalog.md`
5. If rejected, file a new ADR documenting the rejection rationale (or link to the rejection discussion)

### §7.3. Anti-patterns

- **Don't write an ADR without updating this index** — orphans accumulate and the index becomes useless.
- **Don't write an ADR in a 4th surface** — the 3-surface split is intentional (engine / kernel / meta). If a decision doesn't fit, escalate to the cross-cutting surface.
- **Don't write an ADR without a diagnostic cross-reference** — every ADR should trace to either a known issue, a sprint decision, or a user request. Naked ADRs accumulate.

### §7.4. Numbering

- Numbering is sequential across all surfaces: `ADR-NNN-*.md`
- Next number: **ADR-012** (when needed)
- PAV PRDs use `PRD-*` prefix and do not consume ADR numbers (they have their own numbering)

---

## §8. Cross-references

### Indexes / surface maps

- `code-docs/adr/VIBE-OPS.md` — vibe-ops surface index
- `code-docs/adr/OPERATIONAL.md` — PAV surface index
- `code-docs/00-INDEX.md` — repo-level index
- `code-docs/diagnostic/README.md` — diagnostic category index
- `code-docs/glossary.md` — cross-reference glossary

### Master diagnostic (canonical source for issue IDs)

- `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md`
- `code-docs/diagnostic/2026-08-27-issue-dependencies.md`
- `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md`
- `code-docs/diagnostic/2026-08-27-risk-effort-matrix.md`
- `code-docs/diagnostic/2026-08-27-pending-constructions-detail.md`
- `code-docs/diagnostic/2026-08-27-pre-merge-checklist.md`

### Per-surface sources

- `vibe-ops/architecture/ADR-001..ADR-006` — 6 cybernetic-engine ADRs
- `vibe-ops/architecture/README.md` — architecture index
- `vibe-ops/architecture/REF-2026-06-07 + PRD-*` — 13+ PAV specs (under `life-ops/operational/docs/adr/`)
- `code-docs/adr/ADR-007..ADR-011` — 5 cross-cutting ADRs

### Related user memory

- `algorithm-issues-registry.md` — 31 catalogued inconsistencies; N01 (vector weight mechanism) ties to ADR-003 + ADR-008
- `ikigai-weight-mechanism-defer.md` — Option C deferral until 5+ SONHO logs (per ADR-007 data-first)
- `data-first-methodology.md` — ADR-007 implementation rules
- `ai-native-strategic-model-migration.md` — 2026-08-26 PAV TUI/CLI deprecation context (rationale for ADR-007 roll-forward)

### Cluster docs (consumers of vibe-ops ADRs)

- `CLUSTER_PLAN.md` (v1.1, ~1861 lines)
- `CLUSTER_PROJ.md` (~1100 lines)
- `CLUSTER_STUDY.md` (~900 lines)
- `CONCEPTUAL_MODEL.md`
- `SYSTEMS_TOPOLOGY.md`
- `ARCHITECTURE_INDEX.md`

### IKIGAi planning drilldowns (consumers of ADR-003)

- `life-ops/planner/ikigai_planning/README.md`
- `life-ops/planner/ikigai_planning/ikigai_4_vectors.md`
- `life-ops/planner/ikigai_planning/ikigai_north_star_metrics.md`
- `life-ops/planner/ikigai_planning/ikigai_propagation.md`
- `life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`

---

*Master ADR Index — 2026-08-27 — consolidation of 3 ADR surfaces — Hephaestus*
