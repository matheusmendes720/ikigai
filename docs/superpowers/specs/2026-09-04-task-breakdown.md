# Task Breakdown — Master Spec 02

**Generated:** 2026-09-04
**Synthesizes:** Diag 04 (47 backend tasks), Diag 05 (25 frontend tasks T01-T25)
**Status:** Spec for review (not yet implementation plan)

---

## 1. Backend task taxonomy (47 tasks, Diag 04)

Source: `docs/superpowers/specs/2026-09-04-diag-04-backend-tasks.md`

### B-G* — Graph shell (5 tasks)
- B-G01 — pytest collection infra (fix `src.ikigai.src.*` namespace) — **PENDING, 6h, blocks all v2 tests** (Diag 03: 2-4h via `consider_namespace_packages = true`)
- B-G02 — graph.invoke() smoke test with real Claude — **PENDING, blocked by B-G01, 4h, API 529 risk**
- B-G03 — skill binding daily/weekly/monthly/quarterly as entry points — **PENDING, 10-12h, needs ADR-014**
- B-G04 — CLI wrapper that triggers graph.invoke() → taskdog — **PENDING, 8h, blocked by B-G03**
- B-G05 — E2E smoke: chat → tag_and_persist → commit_node → vault + taskdog.exe → fork reflects — **PENDING, 4h, blocked by B-G04**

### B-N* — v2 graph nodes (11 tasks)
- B-N01–N11 — node implementations + try/except + state update contracts
- **9 of 11 SHIPPED** (observe, score_vectors, heuristics, balance, decompose, plan, reflect, commit, surface_intentions)
- **2 PENDING:** B-N10 (sub-agent dispatch node, B.1 critical path) + B-N11 (stateful subgraph consumer, B.2 critical path)

### B-C* — Contracts (8 tasks)
- B-C01–C06 — 6 Pydantic v2 strict SONHO-tree models — **ALL SHIPPED** (Sonho, Objetivo, Meta, Projeto, Entrega, Tarefa)
- B-C07 — BasePlanContract + subset validator — **SHIPPED**
- B-C08 — Transition matrix 6×6 — **PARTIAL** (SONHO.user-only enforced; per-tier logic NOT implemented per Diag 04)

### B-M* — MCP tools (16 tasks)
- 12 IKIGAI_TOOLS — **12 SHIPPED** (verified `tools.py:556-584` per Diag 02)
- 4 fork tools (sf_* + tuiboard_*) in separate UnifiedMCPGateway — **4 SHIPPED**

### B-D* — Drift invariants (9 tasks)
- B-D01 — `IKIGAI_TOOLS = 12` — **SHIPPED** (Diag 02)
- B-D02 — vault_write actor enforcement — **SHIPPED** (Plan A)
- B-D03 — transition_validator SONHO.user-only — **SHIPPED**
- B-D04 — full SONHO tree coverage — **🚫 STUBBED** (Plan A Task 10 deferred; no `drift_invariants.py` file)
- B-D05 — kill switch + review queue wiring — **PENDING** (B.5 critical path, needs ADR-018)
- B-D06 — ExternalRootsConfig path traversal — **SHIPPED** (Plan B)
- B-D07 — review_queue append-only — **SHIPPED** (Phase 9)
- B-D08 — UEID 4-part regex — **SHIPPED** (Phase 9)
- B-D09 — audit-log test for vault_write — **🚫 ABSENT** (Diag 04)

### B-T* — Transition matrix (4 tasks)
- B-T01 — SONHO.user-only enforcement — **SHIPPED**
- B-T02 — 6×6 transition matrix per-tier logic — **PENDING, 3h**
- B-T03 — audit log shape — **PENDING, 3h**
- B-T04 — phase FSM — **PENDING, 3h**

**Total backend: 18/47 shipped (38%)**

## 2. Frontend task taxonomy (25 tasks T01-T25, Diag 05)

Source: `docs/superpowers/specs/2026-09-04-diag-05-frontend-tasks.md`

### CLI (Typer, 16 commands across 3 sub-apps)
- T01-T03 — `life mesh` commands (show, list, propagate) — **2/3 missing tests** ⚠️
- T04-T06 — `life task` commands (add, today, done) — tests mostly present
- T07-T08 — `life v2` entry commands — **NEEDS TESTS** ⚠️
- T09-T10 — `life daily/weekly` cycle wrappers — wired, but `v2 suggest` and `v2 cycle --dry-run` referenced in skills but **DO NOT EXIST** in `v2.py`
- T11-T16 — skill wiring (daily/weekly/monthly/quarterly hooks) — 4 of 7 expected entry points **UNWIRED** (Diag 05)
- T17 — `interfaces/tui/operator/` Tasks tab — depends on T18-T19 (data seeding)
- T18-T19 — SONHO seed + template — **NEEDS VAULT TEMPLATES** (Plan A A.4 gap)
- T20-T25 — UX polish (sorting, filtering, export) — **DEFERRED**

### TUI (Textual, 4 tabs)
- Tabs: Tasks / Adapters / Backend / Queue — verified per Diag 03 + 05
- **Tasks tab data not seeded** — T17 blocked by T18-T19
- Adapter/Backend/Queue tabs — operational, functional

**Total frontend: 14/25 shipped (56%)**

## 3. Critical path (sequential, blocks all scenarios)

```
A.1 [B-G01] pytest infra (2-6h)
  └── A.2 [B-G02] smoke test (4h)
       └── A.3 [B-G03] skill binding (10-12h, needs ADR-014)
            └── A.5 [B-G04] CLI wrapper (8h)
                 └── A.6 [B-G05] E2E smoke (4h)
                      └── B.1 [B-N10] sub-agent dispatch (12-16h, needs ADR-015)
                           └── B.2 [B-N11] stateful subgraph (12-16h, needs ADR-016)
                                └── B.4 memory layer (8-12h, needs ADR-017)
                                     └── B.6 multi-level E2E (8h)
                                          └── C.1 feedback loop (1 week)
                                               └── C.2 kill switch + review queue (3-4d, needs ADR-018)
                                                    └── C.3 SONHO logs (ongoing, user action)
                                                         └── C.4 algorithm tuning (4-8 weeks, needs ADR-019)
```

**Total critical path: 32-44h to "Scenario A functional" + 2-3 weeks to "Scenario B functional" + 4-6 weeks to "Scenario C usable" + 4-8 weeks to "Scenario C eficaz".**

## 4. Parallelization waves (5 waves, Diag 05)

### Wave 1 — Tests first (~5h, safe to ship now)
- T01-T03: add tests for `life mesh` commands
- T07-T08: add tests for `life v2` entry commands
- B-D09: audit-log test for vault_write
- **No dependencies.** Independent. Can ship as one PR.

### Wave 2 — v2 skill entry points (~11h, after Wave 1)
- T09: implement `v2 suggest` (referenced by `daily.md:24`)
- T10: implement `v2 cycle --dry-run` flag (referenced by weekly/monthly/quarterly.md)
- T11-T16: wire 4 unwired skill entry points (daily/weekly/monthly/quarterly hooks)
- **Depends on Wave 1.**

### Wave 3 — Critical path block 1 (~32h, A scenario)
- A.1 → A.2 → A.3 → A.5 → A.6 (B-G01 → B-G05)
- **Depends on Wave 2 (so T09-T16 are tested).**

### Wave 4 — Critical path block 2 (~32-44h, B scenario)
- B.1 → B.2 → B.4 → B.6 (B-N10 → B-N11)
- **Depends on Wave 3 + ADR-014..017 written.**

### Wave 5 — Critical path block 3 (~12 weeks, C scenario)
- C.1 → C.2 → C.3 → C.4
- **Depends on Wave 4 + ADR-018..019 + 5+ SONHO logs.**

## 5. Effort totals

| Scenario | Tasks | Effort | Calendar (focused) |
|---|---|---|---|
| Scenario A (Narrow MVP) | A.1-A.6 + Wave 1+2 | ~50h | 3-5 working days |
| Scenario B (End-to-end) | A + B.1-B.6 + Wave 3+4 | ~120h | 2-3 weeks |
| Scenario C (On-the-fly eficaz) | A + B + C.1-C.8 + Wave 5 | ~280h + 4-8wk calibration | 4-6 weeks + 4-8 weeks |

## 6. Spec self-review

- ✅ All 47 backend tasks + 25 frontend tasks enumerated with status.
- ✅ Critical path matches roadmap file [[roadmap-2026-09-04-harness-mvp]].
- ✅ Wave parallelization matches Diag 05's recommendation.
- ⚠️ **Ambiguity:** B-N10 (sub-agent dispatch) and B-N11 (stateful subgraph) are sequential — Diag 04 doesn't say so explicitly. **Assumption:** B-N11 must come after B-N10 because B-N11 needs B-N10's subgraph to attach to. Confirm in user review.

## 7. Open questions for user

1. Should Wave 1 ship TODAY as a low-risk PR while the bigger ADRs are being written?
2. Confirm B-N10 → B-N11 sequential ordering.
3. Confirm Scenario A = "3-5 days" or extend to "5-7 days" given B-G01 estimated at 2-6h vs roadmap's 1 day?
