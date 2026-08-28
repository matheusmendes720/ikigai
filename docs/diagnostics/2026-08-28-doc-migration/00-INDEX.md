---
title: "Doc Migration Plan — life/ — 2026-08-28"
date: 2026-08-28
workflow: wmnt1gvu2 (85 agents, 4.8M tokens, ~20 min)
---

# Doc Migration Plan — `life/` — 2026-08-28

Inventory + classify all `.md` docs against the canonical master-branch architecture
(deep-agent ⇄ forks-prontas ⇄ vault `.db.markdown`; PAV desativado; IKIGAi em design).
Propose trailer patches for stale docs using the pattern from
`docs-superseded-trailer-2026-08-28` memory.

**Token cost:** ~4.8M tokens, 85 agents, ~1287 tool calls, ~20 min
**Session:** `5abe0d4a-04e2-43c6-aa22-bd7f3c3baf63`
**Workflow run:** `wf_1a9f4843-51b`

---

## Executive Summary

- **95 docs inventoried** across `docs/`, `code-docs/`, `specs/`, `strategics/` (proxies),
  `vault/` (proxies), `CLUSTER_*.md`, `README.md`s
- **Breakdown by classification:**
  - CURRENT: 18
  - INFRASTRUCTURE: 26
  - AMBIGUOUS: 17
  - STALE: 34
- **Actions proposed:** **37 trailers** (32 GENERAL + 5 ADR), **3 rewrites**, **5 FLAG_FOR_REVIEW**, **1 DELETE_REPLACE**, **49 KEEP**
- **Estimated total diff lines:** ~225 (range 2–22 per trailer; rewrites excluded)

> **Independent verification (main session, 2026-08-28):** All 23 named docs
> exist with sizes matching audit estimates. `docs/PAV_INVENTORY.md` spot-check
> confirmed — title, paths (`life-ops/operational/`, `apps/cli/`, `apps/tui/`),
> entry points (`pav`, `pav-os`) all match pre-2026-08-26 era, validating the
> CRITICAL STALE classification.

---

## Trailer Pattern Used

Standard GENERAL banner (per `docs-superseded-trailer-2026-08-28`):

```markdown
> **[SUPERSEDED 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> This document describes the PAV TUI/CLI + auto-performace era (pre-2026-08-26),
> which has been retired. Kept by append-only invariant. **Do NOT use the
> conclusions of this doc for new work.** Current architecture:
> deep-agent (AI-native) operating bidirectional sync between forks-prontas
> (tuiboard / taskdog / solverforge-calendar) ↔ vault local `.db.markdown`.
```

ADR variant for Architecture Decision Records:

```markdown
> **[SUPERSEDED 2026-08-28 — ADR superseded; see master-branch-carro-chefe-2026-08-28]**
> Decision was reversed 2026-08-26 (AI-native pivot). Kept for audit trail.
> **Do NOT cite this ADR as current.**
```

---

## Per-Doc Action Table (sorted HIGH → LOW severity)

| Path | Class. | Sev. | Action | Trailer? | Risk |
|---|---|---|---|---|---|
| `docs/PAV_INVENTORY.md` | STALE | CRITICAL | TRAILER (GEN) | YES | med |
| `docs/ARCHITECTURE_INDEX.md` | STALE | HIGH | TRAILER (GEN) | YES | high |
| `docs/SYSTEMS_TOPOLOGY.md` | STALE | HIGH | TRAILER (GEN) | YES | low |
| `docs/CONCEPTUAL_MODEL.md` | STALE | HIGH | TRAILER (GEN) | YES | med |
| `docs/LANGRAPH_DEV.md` | STALE | HIGH | TRAILER (GEN) | YES | med |
| `docs/DEPLOY.md` | STALE | HIGH | TRAILER (GEN) | YES | med |
| `docs/README.md` | STALE | HIGH | **REWRITE** | NO | high |
| `CLUSTER_PLAN.md` | STALE | HIGH | FLAG_FOR_REVIEW | NO | med |
| `CLUSTER_PROJ.md` | STALE | HIGH | FLAG_FOR_REVIEW | NO | high |
| `code-docs/adr/ADR-008-ikigai-vector-count.md` | STALE | HIGH | TRAILER (ADR) | YES | low |
| `code-docs/adr/ADR-009-pydantic-strict-mode-invariance.md` | STALE | HIGH | TRAILER (ADR) | YES | med |
| `code-docs/adr/2026-08-28-adr-008-011-decision-package.md` | AMBIG | HIGH | TRAILER (ADR) | YES | med |
| `code-docs/adr/2026-08-27-cross-cutting-triage.md` | AMBIG | HIGH | TRAILER (GEN) | YES | high |
| `code-docs/diagnostic/2026-08-27-architecture-diagrams.md` | STALE | HIGH | TRAILER (GEN) | YES | med |
| `code-docs/diagnostic/2026-08-27-github-issues-backlog.md` | STALE | HIGH | TRAILER (GEN) | YES | med |
| `code-docs/diagnostic/2026-08-27-issue-dependencies.md` | STALE | HIGH | TRAILER (GEN) | YES | low |
| `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` | STALE | HIGH | TRAILER (GEN) | YES | med |
| `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md` | STALE | HIGH | TRAILER (GEN) | YES | med |
| `code-docs/diagnostic/2026-08-27-pending-constructions-detail.md` | STALE | HIGH | TRAILER (GEN) | YES | med |
| `code-docs/diagnostic/2026-08-27-sprint1-diagrams.md` | STALE | HIGH | TRAILER (ADR) | YES | low |
| `code-docs/diagnostic/2026-08-27-sprint1-implementation-plan.md` | STALE | HIGH | TRAILER (GEN) | YES | med |
| `code-docs/observability/05-dashboard-design.md` | STALE | HIGH | FLAG_FOR_REVIEW | NO | high |
| `code-docs/observability/06-external-mcp-otel-plan.md` | STALE | HIGH | **REWRITE** | NO | high |
| `docs/ÍNDICE PROGRESSIVO.md` | STALE | MED | TRAILER (GEN) | YES | low |
| `code-docs/adr/2026-08-28-adr-008-011-decision-package-appendix.md` | STALE | MED | TRAILER (ADR) | YES | med |
| `code-docs/adr/2026-08-27-decision-questionnaire.md` | AMBIG | MED | TRAILER (GEN) | YES | low |
| `code-docs/adr/OPERATIONAL.md` | STALE | MED | **REWRITE** | NO | low |
| `code-docs/diagnostic/2026-08-27-error-catalog.md` | AMBIG | MED | KEEP+TRAILER (ADR) | YES | med |
| `code-docs/diagnostic/2026-08-27-ikigai-bootstrap-runbook.md` | AMBIG | MED | TRAILER (GEN) | YES | low |
| `code-docs/diagnostic/2026-08-27-incident-response-runbook.md` | AMBIG | MED | TRAILER (GEN) | YES | med |
| `code-docs/diagnostic/2026-08-27-pre-merge-checklist.md` | AMBIG | MED | TRAILER (GEN) | YES | med |
| `code-docs/diagnostic/2026-08-27-risk-effort-matrix.md` | AMBIG | MED | TRAILER (GEN) | YES | med |
| `code-docs/diagnostic/2026-08-27-test-coverage-strategy.md` | AMBIG | MED | TRAILER (GEN) | YES | low |
| `code-docs/ard/README.md` | STALE | MED | **DELETE_REPLACE** | NO | low |
| `docs/superpowers/specs/2026-08-25-ikigai-vault-layers-design.md` | AMBIG | MED | TRAILER (GEN) | YES | med |
| `docs/superpowers/specs/2026-08-26-data-model-unification-design.md` | AMBIG | MED | TRAILER (ADR) | YES | med |
| `docs/superpowers/specs/2026-08-28-phase3-data-mesh-design.md` | AMBIG | MED | TRAILER (GEN) | YES | low |
| `docs/superpowers/plans/2026-08-25-ikigai-vault-layers.md` | AMBIG | MED | TRAILER (GEN) | YES | low |
| `docs/superpowers/plans/2026-08-26-phase-mcp-unified-planning.md` | AMBIG | MED | TRAILER (ADR) | YES | low |
| `docs/superpowers/glossaries/ikigai-pav-glossary.md` | AMBIG | MED | TRAILER (GEN) | YES | low |
| `CLUSTER_STUDY.md` | STALE | MED | FLAG_FOR_REVIEW | NO | med |
| `code-docs/adr/ADR-010-dual-claude-md-scope.md` | AMBIG | LOW | FLAG_FOR_REVIEW | NO | low |
| 49× KEEP (CURRENT + INFRASTRUCTURE) | — | — | KEEP | NO | — |

---

## Quick Wins (HIGH severity + LOW risk + GENERAL trailer)

All 10 are **additive only** (zero existing-line mutation), all live outside
the append-only protected set (`vault/`, `strategics/`, `vibe-ops/`,
`data/review_queue/`).

1. `code-docs/diagnostic/2026-08-27-issue-dependencies.md` — 8 lines
2. `code-docs/diagnostic/2026-08-27-sprint1-diagrams.md` — 7 lines, ADR variant
3. `code-docs/adr/ADR-008-ikigai-vector-count.md` — 4 lines, points at memory
4. `docs/superpowers/plans/2026-08-26-phase-mcp-unified-planning.md` — 8 lines, ADR
5. `docs/superpowers/plans/2026-08-25-ikigai-vault-layers.md` — 9 lines, canonical
6. `docs/superpowers/glossaries/ikigai-pav-glossary.md` — 7 lines, canonical
7. `docs/superpowers/specs/2026-08-28-phase3-data-mesh-design.md` — 7 lines, §4 only
8. `docs/ÍNDICE PROGRESSIVO.md` — 9 lines, redirects to `strategics/`
9. `docs/LANGRAPH_DEV.md` — 5 lines, fixes graph count
10. `code-docs/diagnostic/2026-08-27-ikigai-bootstrap-runbook.md` — 7 lines

---

## Needs User Decision (FLAG_FOR_REVIEW)

| Doc | Why flagged | Options |
|---|---|---|
| `CLUSTER_PLAN.md` (89 KB) | Append-only protected; ~18 broken `life-ops/` paths | (a) keep + flag, (b) relocate to `docs/_legacy/` |
| `CLUSTER_PROJ.md` (59 KB) | Append-only protected; aspirational PMO framing orphaned | (a) keep + trailer, (b) relocate with CLUSTER_PLAN family |
| `CLUSTER_STUDY.md` (47 KB) | Append-only protected; pre-deepagent framing | (a) keep + flag for periodic review, (b) relocate |
| `code-docs/observability/05-dashboard-design.md` | 8-node graph sequence wrong (observe→score_vectors→… vs doc's observe→orient→decide→…) | (a) parallel REWRITE now, (b) wait until IKIGAi un-pauses |
| `code-docs/adr/ADR-010-dual-claude-md-scope.md` | Status=Proposta; 2026-08-28 reconciliation already converged both CLAUDE.md files | (a) accept Option B (merge + delete root), (b) Option A (boundary headers) |

---

## Execution Order

### Phase 1 — Quick-win trailers (1 commit per file)
- Group A: 10 quick-wins listed above
- Group B: 11 sibling `code-docs/diagnostic/2026-08-27-*` docs (1 commit each)
- Group C: root `docs/` — `ARCHITECTURE_INDEX`, `SYSTEMS_TOPOLOGY`, `CONCEPTUAL_MODEL`, `PAV_INVENTORY`, `DEPLOY`
- Group D: `code-docs/adr/` — 6 ADRs + 2 decision packages
- Group E: `docs/superpowers/` remaining trailers

### Phase 2 — Rewrites (after user approval)
- `docs/README.md` — REPLACE entire doc, target ~200 lines
- `code-docs/adr/OPERATIONAL.md` — path-only rewrite (`life-ops/operational/` → `src/operational/`), 14 links
- `code-docs/observability/06-external-mcp-otel-plan.md` — consolidate IKIGAI-only observability strategy; mark fork sections parked

### Phase 3 — Deletes (after user approval, with audit trail)
- `code-docs/ard/README.md` — DELETE entire typo directory (single file)

### Phase 4 — FLAG_FOR_REVIEW (await user)
- 5 docs above — present at next planning session; no commit until user decides

**Estimated total commits:** 37 trailers (1/file) + 3 rewrites + 1 delete = **41 atomic commits** over 2-3 sessions.

---

## Skipped (Append-only protected)

No docs in `vault/`, `strategics/`, `vibe-ops/`, `data/review_queue/` were classified. The 3 `CLUSTER_*.md` files at repo root are **append-only protected by extension** (`.hermes/plans/2026-08-26-openwiki-docs-restructure.md` §3.1 — "wiki points to them, doesn't replace them") and are flagged for user decision above rather than receiving trailers.

---

## Cross-references

- Workflow transcript: `AppData\Local\Temp\claude\…\tasks\wmnt1gvu2.output`
- Workflow script: `C:\Users\mathe\AppData\Local\Temp\life-doc-migration-workflow.js`
- Trailer pattern: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/docs-superseded-trailer-2026-08-28.md`
- Canonical architecture: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/master-branch-carro-chefe-2026-08-28.md`
- Companion structure audit (2026-08-28): `docs/diagnostics/2026-08-28-structure-audit/00-INDEX.md`
