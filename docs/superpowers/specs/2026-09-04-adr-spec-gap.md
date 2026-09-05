# ADR / Spec Gap — Master Spec 04

**Generated:** 2026-09-04
**Synthesizes:** Diag 09 (ADR gap), Diag 10 (spec gap)
**Status:** Spec for review (not yet implementation plan)

---

## 1. Existing ADRs (7 cross-cutting, verified)

Source: `code-docs/adr/`

| ADR | Title | Status | Covers |
|---|---|---|---|
| ADR-007 | vault_write as canonical writer | Accepted | vault/ write authority |
| ADR-008 | (deprecated) | Superseded | trailer-marked, do-not-re-litigate |
| ADR-009 | (deprecated) | Superseded | trailer-marked, do-not-re-litigate |
| ADR-010 | (deprecated) | Superseded | trailer-marked, do-not-re-litigate |
| ADR-011 | HTTP+SSE backend topology | Proposta | (1 Proposta open) |
| ADR-012 | vault_write sole vault writer | Accepted | locks vault/ write path |
| ADR-013 | Canonical scope discipline | Accepted | agent layer = planner-only, math out |

**Distribution: 3 Accepted, 1 Proposta, 3 Superseded.**

## 2. Roadmap tasks needing NEW ADRs (6 of 17)

Source: Diag 09 cross-ref of roadmap [[roadmap-2026-09-04-harness-mvp]]

| ADR | Title | Roadmap Task | Effort | Priority |
|---|---|---|---|---|
| **ADR-014** | Skill binding mechanism | A.3 (B-G03) | 10-12h | **CRITICAL PATH** (blocks B-scenario) |
| **ADR-015** | Sub-agent dispatch protocol | B.1 (B-N10) | 8-12h | **CRITICAL PATH** |
| **ADR-016** | Stateful subgraph strategy | B.2 (B-N11) | 16-20h | **CRITICAL PATH** — locks checkpoint schema for ADR-017 |
| **ADR-017** | Memory layer across cycles | B.4 | 8-12h | **CRITICAL PATH** (depends on ADR-016) |
| **ADR-018** | Kill switch + review queue wiring | C.2 (B-D05) | 9-11h | important (Scenario C gate) |
| **ADR-019** | Empirical algorithm tuning approach | C.4 | 6-8h | important (Scenario C gate) — **MUST reference `algorithm-scope-reframed-2026-08-30`** |

**Write order:** ADR-016 → ADR-015 → ADR-017 → ADR-014 → ADR-018 → ADR-019. The first four unblock the A/B-scenario critical path.

## 3. Implicit decisions to formalize (5 ADRs, 020-024)

| ADR | Title | Currently lives in | Recommendation |
|---|---|---|---|
| **ADR-020** | Deep-Agent as canonical carro-chefe | `master-branch-carro-chefe-2026-08-28` memory | Promote memory → ADR |
| **ADR-021** | Default-deny external folder access | Plan B shipped but no ADR | Promote plan → ADR (already cites path-traversal-guard design) |
| **ADR-022** | Two-queue architecture (review_queue + investigation_queue) | Implementation + memory | Promote → ADR; **must note Plan C investigation_queue unexecuted** |
| **ADR-023** | UEID canonical format (4-part vs 5-part adjudication) | Regex in ADR-012, semantics only in memory | **ADR needed**: adjudicate drift-detector's 4-part enforcement vs CLAUDE.md's 5-part claim |
| **ADR-024** | PAV kernel archive | memory + ADR-013 scope section | Promote → ADR (clarifies `archive/legacy-pav/` is read-only) |

**Write order:** ADR-023 (urgent, blocks UEID work) → ADR-020 → ADR-021 → ADR-022 → ADR-024.

## 4. Coverage matrix — 47 backend tasks × spec/ADR (Diag 10)

| Status | Count | Tasks |
|---|---|---|
| Fully covered + shipped | 18 | B-C01..C07, B-N01..N09, B-D01, B-D02, B-D03, B-D06, B-D07, B-D08, B-T01, B-M01..M12, B-M13, B-M15, B-M16 |
| Partial coverage (spec exists, sub-detail missing) | 16 | various |
| **GAP (no spec/ADR/plan)** | 13 | **B-G01, B-G03, B-N10, B-N11, B-M14, B-D04, B-D05, B-T02, B-T03, B-T04 + 5 subprocess-wiring sub-tasks under B-N01/N05/N08** |

**Coverage rate: 38% shipped / 34% partial / 28% GAP.**

## 5. Spec orphans (8 found by Diag 10)

Specs that reference code/symbols that do NOT exist or are stale:

1. 3 SUPERSEDED specs — refs to deprecated code paths
2. 1 stale §4 — references deleted agentic_writer
3. 1 harness reference — points to non-existent module
4. 1 Go TUI design (forward-looking, not yet built)
5. 2 SUPERSEDED plans
6. 1 archive reference — to `archive/legacy-pav/` for context only

**Action:** add SUPERSEDED trailers per ADR-master §7.3 anti-patterns; no rewrite needed.

## 6. Implementation orphans (10 found by Diag 10)

Code that does something but no spec describes it:

1. `tools_v2.py` — v2 skill wrappers, no spec
2. `legacy_reference/` files — historical, need trailer
3. `FAKE_LLM` stub — used in tests, undocumented
4. **hardcoded QHE constants** in `observe.py:56-61` — violates ADR-013 (cross-cited by Diag 04 + 09)
5. kill switch semantics — `_KILL_SWITCH` module-level flag, no spec
6. `planning.py` migration drift — old + new SONHO models coexist
7. `interfaces/tui/operator/` — 4 tabs but README claims 3 (now fixed in memory)
8. `taskdog_mcp/` — Path 3 module, on-disk state OFF but referenced in Phase 9 memory
9. `review_queue` — append-only + actor; no standalone spec (covered by ADR-012 + Plan A)
10. `investigation_queue` — Plan C unexecuted, but the PLAN document references the pattern

**Action:** add spec stubs or promote to ADR candidates where appropriate.

## 7. Total effort to close the gap

| Workstream | Effort | Source |
|---|---|---|
| ADR-014..019 (6 ADRs for roadmap tasks) | 35-55h | Diag 09 |
| ADR-020..024 (5 ADRs for implicit decisions) | 12-20h | Diag 09 (estimated) |
| Spec fills (13 GAP tasks) | 13-19h | Diag 10 |
| Implementation orphan specs | 4-8h | Diag 10 |
| Spec orphan cleanup (SUPERSEDED trailers) | 2-3h | Diag 10 |
| **TOTAL** | **66-105h (~8-13 working days focused)** | Diag 09 + 10 |

## 8. Recommended write order (priority × unblock × effort)

| Step | Artifact | Why first | Effort |
|---|---|---|---|
| 1 | ADR-023 (UEID canonical, 4-part vs 5-part) | Drift detector currently blocks 5-part work; needs adjudication | 1-2h |
| 2 | ADR-016 (stateful subgraph) | Locks checkpoint schema; B-N11 + ADR-017 design against it | 16-20h |
| 3 | ADR-015 (sub-agent dispatch) | Unblocks B-N10 implementation | 8-12h |
| 4 | ADR-017 (memory layer across cycles) | Depends on ADR-016 checkpoint schema | 8-12h |
| 5 | ADR-014 (skill binding) | Unblocks A.3 + 4 unwired skill entry points | 10-12h |
| 6 | ADR-018 (kill switch + review queue) | Scenario C gate | 9-11h |
| 7 | ADR-019 (empirical algorithm tuning) | Scenario C gate; reference `algorithm-scope-reframed-2026-08-30` | 6-8h |
| 8 | ADR-020..024 (5 implicit decisions) | Lock-in work, not on critical path | 12-20h |
| 9 | Spec fills for 13 GAP tasks | Mostly mechanical | 13-19h |
| 10 | Spec/impl orphan cleanup | Hygiene | 6-11h |

## 9. ADR-019 critical constraint (Diag 09 finding)

ADR-019 (Empirical algorithm tuning approach) MUST explicitly bound algorithm work by referencing:
- `algorithm-scope-reframed-2026-08-30` — IKIGAI = planner with stochastic PAE feedback (NOT scoring engine)
- `algorithm-gate-dropped-2026-09-03` — algorithm work now permitted on explicit demand
- ADR-013 — agent layer = planner-only, math out

Specifically: algorithm tuning may modify **prompt templates** (e.g., what to observe) but MUST NOT introduce new Python constants in agent code (e.g., the `observe.py:56-61` `DEFAULT_QHE_PUSH=0.85` violation). This constraint closes the loop on the 3-agent cross-citation of that hardcoding.

## 10. Spec self-review

- ✅ All 11 candidate ADRs (014-024) enumerated with priority + effort.
- ✅ 13 GAP tasks + 8 spec orphans + 10 implementation orphans inventoried.
- ✅ Total effort estimate (66-105h) matches Diag 09 + 10.
- ✅ Write order rationale is consistent with critical path analysis from master-02.
- ⚠️ **Ambiguity:** "memory layer across cycles" (ADR-017) — could mean (a) LangGraph checkpoint memory, (b) cross-cycle knowledge persistence, (c) both. **Assumption:** (c) — both. Confirm in user review.

## 11. Open questions for user

1. **ADR-023 UEID adjudication:** drift detector wins (4-part canonical) OR CLAUDE.md wins (5-part)? This is the most consequential 1-2h decision.
2. **ADR-019 scope:** should it explicitly forbid any algorithm math in agent code, or just regulate the empirical-tuning workflow? (Diag 04 + 09 + 10 all flag `observe.py:56-61`.)
3. **ADR-022 (two-queue architecture):** should it be written given Plan C investigation_queue is unexecuted? Or wait until Plan C is re-dispatched?
4. **Implicit decision ADRs (020-024):** all 5 needed, or just the most load-bearing (020, 023)?
