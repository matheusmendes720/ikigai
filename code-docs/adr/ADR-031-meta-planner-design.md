# ADR-031 — Meta-Planner Design (Intent-Aware To-Do Layer for the IKIGAI Orchestrator)

**Status:** DRAFT (2026-09-04)
**Load-bearing:** YES (drift invariants n, o, p depend on this ADR)
**Spec:** docs/superpowers/specs/2026-09-04-meta-planner-design.md (SOT)

## Context

The IKIGAI orchestrator fast-path (observe → score → plan → commit) is correct
for incidental inputs but under-serves the recurring operator pattern of
decomposing planning requests across the 6-level SONHO tree + memory layer +
external folders. Today the operator runs `vault_read → memory_query →
external_folder_read → vault_write` manually.

## Decision

Add an **opt-in meta-planner** (3-node subgraph + 1 executor) that:
- Classifies intent via pure-keyword classifier (no LLM)
- Fetches context across memory (ADR-028), external folders (Plan B), vault hierarchy
- Generates a typed `Proposal` (Pydantic v2 strict, ADR-009) with `approval_state="pending"`
- **Refuses to execute without explicit `--approve`** (PROPOSTAS only)
- Reuses shipped write infra: `wrap_vault_write` (ADR-029) + `taskdog_create_task` (W3.6 Path 1)

## Architecture

```
/plan <request>
  → invoke_skill("meta_plan") [ADR-025]
  → subgraph: classify_intent → fetch_context → generate_proposal
  → Proposal(approval_state="pending") [in-chat display]
  → user: --approve | --reject X.field
  → proposal_executor (reuses shipped infra)
  → ExecutionReport → graph returns to fast-path commit
```

The observe node gains ~30 LOC intent detection that emits in-chat hints
suggesting `/plan` for planning-shaped inputs (zero writes).

## Components

| Component | File | LOC |
|-----------|------|-----|
| Contracts (11 models + 1 enum) | `src/ikigai/contracts/proposal.py` | ~180 |
| classify_intent | `nodes/meta_plan/classify_intent.py` | ~50 |
| fetch_context | `nodes/meta_plan/fetch_context.py` | ~120 |
| generate_proposal | `nodes/meta_plan/generate_proposal.py` | ~150 |
| proposal_executor | `nodes/proposal_executor.py` | ~80 |
| Skill manifest | `skills/meta_plan.md` | ~30 |
| Observe modification | `nodes/observe.py` | +30 |
| State extension | `state.py` (MetaPlanStateDict) | +40 |
| Subgraph wiring | `subgraph.py` | +40 |
| CLI command | `interfaces/cli/v2.py` | +60 |
| **Total** | | **~780** |

## Drift Invariants (NEW: n, o, p)

- **(n) test_meta_plan_no_direct_vault_writes** — subgraph nodes never call `vault_write(` directly; all writes route through `wrap_vault_write` (ADR-029)
- **(o) test_meta_plan_approval_required_for_writes** — `proposal_executor.py` must assert `approval_state == 'approved'` before any write
- **(p) test_meta_plan_pydantic_v2_strict** — all 10 proposal-related contracts are `frozen=True, extra="forbid"` (ADR-009)

## Cross-ADR Consistency

| ADR | Inheritance |
|-----|-------------|
| ADR-009 | Pydantic v2 strict enforced on all new models (drift p) |
| ADR-013 | meta_plan is planner-only; never executes algorithm/policy math |
| ADR-014 | All UEIDs in Proposal models follow 4-part regex |
| ADR-019 | No new algorithm constants in Python; keyword list lives in code (NLU, not tuning) |
| ADR-025 | `invoke_skill("meta_plan")` is the entry point per skill-binding pattern |
| ADR-026 | `generate_proposal` may dispatch sub-agents via B-N10 for deep research (future) |
| ADR-027 | `meta_plan_subgraph` is a stateful subgraph, follows S1-S5 contract |
| ADR-028 | `recall_memory` reused for memory context fetch |
| ADR-029 | ALL vault writes route through `wrap_vault_write`; kill switch is safety net |
| ADR-030 | R2 (no new IKIGAI_TOOLS) honored; R6 (drift verification) verified before merge |

## Consequences

**Positive:**
- Recurring planning requests compressed from 4 manual steps to 1 opt-in invocation
- Type-safe Proposal with full provenance (Traceability + ADRs consulted)
- Drift invariants (n, o, p) prevent the 3 most likely regressions (direct vault write, accidental auto-execute, relaxed Pydantic)
- Reuses 100% of shipped write infrastructure

**Negative:**
- New state surface (~8 keys) increases IKIGAiStateDict complexity
- Keyword classifier is PT-BR + EN only (locale selector deferred)
- Proposal has no persistence — lost on subgraph exit (audit via ADR-029 wrapper covers writes)

## Out of Scope (explicit)

- Auto-approval (PROPOSTAS only by Decision #3)
- Multi-agent collaboration inside /plan (single-agent)
- Real-time vault watching
- Proposal versioning (v1 only)
- GUI/TUI approval flow (CLI flags only)
- New IKIGAI_TOOLS (R2 ADR-030)
- Batch /plan
- Multi-language locale selector

## Status

**DRAFT** — promotion to ACCEPTED requires:
1. All 12 tasks in `docs/superpowers/plans/2026-09-04-meta-planner-plan-d.md` shipped
2. Drift invariants (n, o, p) passing
3. E2E test green
4. Wave 5 user #11 review acceptance (current gate)

## References

- Spec: `docs/superpowers/specs/2026-09-04-meta-planner-design.md` (commit b2382ed)
- Plan: `docs/superpowers/plans/2026-09-04-meta-planner-plan-d.md` (this ADR's companion)
- Plan A: `docs/superpowers/plans/2026-09-03-planning-contract-plan-a.md`
- Plan B: `docs/superpowers/plans/2026-09-03-external-folder-access-plan-b.md`
- ADR-029: `code-docs/adr/ADR-029-kill-switch-review-queue.md`
- ADR-030: `code-docs/adr/ADR-030-empirical-algorithm-tuning.md`

*ADR-031 — DRAFT 2026-09-04 — load-bearing for drift invariants n, o, p*
