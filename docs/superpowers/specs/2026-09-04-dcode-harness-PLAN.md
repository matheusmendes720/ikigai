# dcode Harness — Implementation Plan

**Generated:** 2026-09-04
**Methodology:** spec-kit (manual application; per user choice 2026-09-04)
**Inputs:** 4 master specs from `docs/superpowers/specs/2026-09-04-*.md` + 10 diagnostic files (`2026-09-04-diag-{01..10}-*.md`) + `roadmap-2026-09-04-harness-mvp` memory
**Status:** Plan for review

---

## 1. Goal (the "why")

Get `dcode` to a state where the user can run it interactively to plan/execute/refine against the SONHO tree, with multi-day state, fork-connection, and minimal manual orchestration. Three scenarios, sequential:

- **A — Narrow MVP (5-7 days):** one CLI call works, taskdog receives tasks. Functional but dumb — no learning, no feedback loop, no subgraphs.
- **B — End-to-end (2-3 weeks):** sub-agents run workflows, state persists, `dcode weekly` knows what `dcode daily` produced.
- **C — On-the-fly eficaz (4-6 weeks + 4-8 weeks calibration):** system learns from use. Requires 5+ SONHO logs first.

## 2. Architecture summary (from master-01)

Four layers (verified top-to-bottom, with concrete fixes per layer):

| Layer | Current state | Target state | Owner |
|---|---|---|---|
| L4 Interfaces | 4-tab TUI + 16 Typer commands; 6 commands untested; 4 skill entry points unwired | All tests pass, all entry points wired, Tasks tab data seeded | TUI/CLI team |
| L3 Agent (ikigai) | 10-node v2 graph, IKIGAI_TOOLS=12, de-stubbed commit_node, hardcoded QHE constants | QHE constants migrated to prompt-template per ADR-019; sub-agent dispatch + stateful subgraph added per ADR-015/016 | Core agent team |
| L2 Domain services | 6 Pydantic contracts, vault_write sole writer, 3 ForkAdapter implementations (create-only) | 6×6 transition matrix wired per ADR-018; kill switch + review queue integration | Mesh/security team |
| L1 Data | review_queue atomic ✅; checkpoints WAL ✅; tasks.jsonl SPLIT-BRAIN; investigation_queue ABSENT | tasks.jsonl unified on CliAdapter pattern; Plan C re-dispatched; dead data orphans cleaned | Data layer team |

## 3. Phased delivery (5 waves, master-02)

### Wave 1 — Test hardening + audit log (5h, safe now)

**Goal:** Lock down what already works; no new features.

| # | Task | Source | Effort |
|---|---|---|---|
| W1.1 | Add tests for `life mesh` commands (T01-T03) | Diag 05 | 1.5h |
| W1.2 | Add tests for `life v2` entry commands (T07-T08) | Diag 05 | 1.5h |
| W1.3 | B-D09: audit-log test for vault_write | Diag 04 | 2h |
| **Total** | | | **5h** |

**Dependencies:** None. **Risk:** Minimal. **Ship as:** single PR `wave-1-tests`.

### Wave 2 — Skill entry points + v2 commands (11h)

**Goal:** Wire what the skills reference but don't have code for.

| # | Task | Source | Effort |
|---|---|---|---|
| W2.1 | Implement `v2 suggest` (referenced by `daily.md:24`) | Diag 05 | 3h |
| W2.2 | Implement `v2 cycle --dry-run` flag | Diag 05 | 3h |
| W2.3 | Wire 4 unwired skill entry points (daily/weekly/monthly/quarterly hooks) | Diag 05 | 5h |
| **Total** | | | **11h** |

**Dependencies:** Wave 1 (so new code is tested). **Risk:** Low. **Ship as:** single PR `wave-2-skills`.

### Wave 3 — Scenario A: Critical path to functional MVP (32-44h)

**Goal:** `dcode daily` works end-to-end through tag_and_persist → commit_node → vault + taskdog.exe → fork reflects.

| # | Task | Roadmap | ADR needed | Effort |
|---|---|---|---|---|
| W3.1 | Fix pytest collection infra (`consider_namespace_packages = true` + conftest cleanup) | A.1 / B-G01 | — | 2-6h |
| W3.2 | Migrate `observe.py:56-61` QHE constants to prompt-template (MUST precede W3.4 to unblock ADR-019 alignment) | NEW pre-A | ADR-019 | 2-4h |
| W3.3 | Smoke test `make_v2_graph().invoke()` with real Claude | A.2 / B-G02 | — | 4h |
| W3.4 | Wire `daily` skill as `entry_point` (skill binding mechanism) | A.3 / B-G03 | **ADR-014** | 10-12h |
| W3.5 | CLI wrapper that triggers `graph.invoke()` → taskdog task | A.5 / B-G04 | — | 8h |
| W3.6 | E2E smoke: chat → tag_and_persist → commit_node → vault + taskdog.exe → fork reflects | A.6 / B-G05 | — | 4h |
| W3.7 | Unify `data/tasks.jsonl` writers (CliAdapter pattern, 14-field schema) | NEW data fix | — | 4-6h |
| **Total** | | | | **34-50h** |

**Dependencies:** Wave 2 (skills tested). **Risk:** Medium (API 529 risk on W3.3). **Ship as:** PR series `wave-3-scenario-a`.

### Wave 4 — Scenario B: Sub-agents + stateful subgraphs (32-44h)

**Goal:** Sub-agents dispatch via LangGraph subgraphs; state persists across daily↔weekly↔monthly↔quarterly.

| # | Task | Roadmap | ADR needed | Effort |
|---|---|---|---|---|
| W4.1 | ADR-015: Sub-agent dispatch protocol | NEW | **ADR-015** (write first) | 8-12h |
| W4.2 | ADR-016: Stateful subgraph strategy (locks checkpoint schema) | NEW | **ADR-016** (write first) | 16-20h |
| W4.3 | Sub-agent dispatch node in v2 graph | B.1 / B-N10 | (ADR-015) | 12-16h |
| W4.4 | Stateful subgraph with SqliteSaver checkpoint reading | B.2 / B-N11 | (ADR-016) | 12-16h |
| W4.5 | Memory layer between daily↔weekly↔monthly↔quarterly | B.4 | ADR-017 | 8-12h |
| W4.6 | Drift invariant (e) — vault_write actor="agent" routes through transition_validator | B.5 | (ADR-018) | 6-8h |
| W4.7 | E2E multi-level smoke (daily → weekly rollup → quarterly adjust) | B.6 | — | 8h |
| **Total** | | | | **70-92h** |

**Dependencies:** Wave 3 complete + ADRs 015/016/017 written. **Risk:** Medium-High (sub-agent protocol is novel territory). **Ship as:** PR series `wave-4-scenario-b`.

### Wave 5 — Scenario C: On-the-fly eficaz (12+ weeks)

**Goal:** System learns from use; 5+ SONHO logs collected; empirical algorithm tuning gated on real data.

| # | Task | Roadmap | ADR needed | Effort |
|---|---|---|---|---|
| W5.1 | ADR-018: Kill switch + review queue wiring | NEW | ADR-018 | 9-11h |
| W5.2 | Feedback loop: plan → execute → observe → adjust (v2 graph covers this, needs consumer) | C.1 | — | 1 week |
| W5.3 | Human-in-the-loop checkpoints (kill switch wiring, review queue) | C.2 | (ADR-018) | 3-4d |
| W5.4 | SONHO data collection ritual (user runs 5+ manual logs) | C.3 | — | ongoing |
| W5.5 | Re-dispatch Plan C: investigation_queue + 3 MCP tools | NEW | (Plan C plan) | 3-7d |
| W5.6 | ADR-019: Empirical algorithm tuning approach (PROMPT-TEMPLATE ONLY per `algorithm-scope-reframed`) | NEW | **ADR-019** | 6-8h |
| W5.7 | `mesh show` SONHO tree traversal | C.6 | — | 2-3d |
| W5.8 | Drift invariant (d) — full SONHO tree coverage (de-stubbed) | C.7 | — | 1d |
| W5.9 | Operator TUI SONHOs tab | C.8 | — | 2-3d |
| W5.10 | Empirical algorithm tuning (post-SONHO-5) | C.4 | (ADR-019) | 4-8 weeks |
| W5.11 | Real-world debugging (API rate limits, vault conflicts, taskdog hangs) | C.5 | — | 1 week |
| **Total** | | | | **~12 weeks + 4-8 weeks calibration** |

**Dependencies:** Wave 4 + 5+ SONHO logs collected. **Risk:** High (requires user participation + empirical tuning is unpredictable). **Ship as:** continuous iteration.

## 4. ADR write order (from master-04)

| Step | ADR | Why first | Effort |
|---|---|---|---|
| 1 | ADR-023 (UEID canonical 4-part vs 5-part) | Drift detector currently blocks 5-part work | 1-2h |
| 2 | ADR-016 (stateful subgraph) | Locks checkpoint schema; B-N11 + ADR-017 design against it | 16-20h |
| 3 | ADR-015 (sub-agent dispatch) | Unblocks B-N10 implementation | 8-12h |
| 4 | ADR-017 (memory layer across cycles) | Depends on ADR-016 checkpoint schema | 8-12h |
| 5 | ADR-014 (skill binding) | Unblocks A.3 + 4 unwired entry points | 10-12h |
| 6 | ADR-018 (kill switch + review queue) | Scenario C gate | 9-11h |
| 7 | ADR-019 (empirical algorithm tuning) | Scenario C gate; reference `algorithm-scope-reframed-2026-08-30` | 6-8h |
| 8 | ADR-020..024 (5 implicit decisions) | Lock-in work | 12-20h |

## 5. Critical path (master-02 dependency graph)

```
W1 → W2 → W3.1 → W3.2 → W3.3 → W3.4 → W3.5 → W3.6 → W4.3 → W4.4 → W4.5 → W4.7 → W5.2 → W5.3 → W5.4 → W5.10
```

**Critical path length:** ~5-7 days (A) + 2-3 weeks (B) + 4-6 weeks + 4-8 weeks (C) = **8-14 weeks total**.

## 6. Parallel opportunities

- W3.2 (QHE constants fix) can run in parallel with W3.1 (pytest infra)
- W4.1 + W4.2 (ADR writes) can run in parallel with W3 (Scenario A implementation)
- W5.5 (Plan C re-dispatch) can run anytime after W3 — independent of sub-agent work
- W5.11 (real-world debugging) starts as soon as W5.2 ships

## 7. Resource requirements

- **Single developer (focused, full-time):** completes Wave 1-3 in ~2 weeks, Wave 4 in ~3 weeks, Wave 5 in 8-14 weeks.
- **Two developers in parallel:** Wave 1-2 sequential, then split: dev-1 on Scenario A core, dev-2 on ADRs (014-017) → 1.5x throughput.
- **Three developers:** adds ADR-023 + cleanup in parallel → 1.8x throughput. Diminishing returns past 3.

## 8. Risk register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| API 529 rate limit during W3.3 | High | 1-2 day delay | Pre-cache prompts; have offline smoke |
| Sub-agent protocol design wrong | Medium | 2-week rework | Spike + ADR-015 review with 2nd opinion before W4.3 |
| UEID 4-part vs 5-part blocks downstream work | Medium | 1-week rework if wrong | **ADR-023 first** (1-2h decision, no code yet) |
| `data/tasks.jsonl` corruption in production | Medium | Data loss | W3.7 (unify writers) shipped before W3.6 E2E smoke |
| Plan C re-dispatch hits same documentation-only fate | Low | 3-7 day delay | Ship Plan C with same rigor as Plan A (drift invariant check) |
| 5+ SONHO logs never collected | High | Scenario C blocked indefinitely | Make SONHO log friction-zero; trigger on each dcode daily run |

## 9. Success criteria

- **Wave 1 done:** 8 → 11 tests pass; 0 new bugs.
- **Wave 2 done:** All skill entry points reference real functions; `daily.md:24` resolves to a callable.
- **Wave 3 done (Scenario A):** `dcode daily` writes a task to taskdog.exe in <2 minutes; vault frontmatter reflects cycle.
- **Wave 4 done (Scenario B):** `dcode weekly` after `dcode daily` shows the daily's outputs in weekly rollup.
- **Wave 5 done (Scenario C):** 5+ SONHO logs in vault; algorithm-tuning CLI produces 1 prompt-template update per week; kill switch tested.

## 10. Out of scope (explicit deferrals)

- A2UI renderer (spec-only; not wired)
- `data/boulder.json` revival (stale since 2026-06-30; can stay archived)
- `data/vibe_mesh.db` repointing (cosmetic; canonical already at `vibe-ops/vibe_mesh.db`)
- `data/session-*.md` Atlas transcripts (legacy; no consumer)
- Path 3 taskdog MCP revival (current effective state = OFF; Path 1+2 sufficient for now)
- All Update/Delete/Sync taskdog paths (Phase 3 v1 = create-only; deferred to v1.2+)

## 11. Open questions for user

1. **UEID 4-part vs 5-part (ADR-023):** decide NOW or defer to W3?
2. **Wave 1 ship today:** independent low-risk PR; can run while ADRs are being drafted.
3. **W3.2 (QHE constants) before W3.4:** yes, prevents algorithm-mistakes propagating.
4. **Plan C re-dispatch timing:** W3 (independent) or W5 (after Scenario A proven)?
5. **B-N10 → B-N11 sequential vs parallel:** assume sequential per master-02; confirm.
6. **Two vs three developer team:** assume single + occasional parallel spike authors.
