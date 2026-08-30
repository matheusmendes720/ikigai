# System-Readiness ADR — Algorithm Gate Evaluation

**Date:** 2026-08-30
**Status:** PROPOSED
**Author:** Phase B7 implementer (post-B7.4 E2E green)
**Predecessor:** [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] (CANONICAL)
**Reviewers:** user (gate-keeper), downstream algorithm work blocked

---

## 1. Context

Per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] (CANONICAL), the build order is strictly:

```
backend → data → agent → algorithms (LAST)
```

Phase B0–B6 closed the backend + data layers. Phase B7 closes the **agent layer**. This ADR evaluates whether the system is "ready" for algorithm work (M01/N01/A02/A06, IKIGAI weights, scoring math) — and answers **NO for all 5 algorithm components** as of 2026-08-30.

---

## 2. Layer status (verified)

| Layer | Status | Evidence |
|---|---|---|
| **Backend** (mesh, queue, MCP gateway, CLI, server mgmt) | ✅ FUNCTIONAL | Phase B0-B5.B closed; B2 start/stop real subprocess (`0e82e4e`) |
| **Data** (vault/data/, sync contracts, persistence) | ✅ FUNCTIONAL | Phase B6 vault sync + Combo A bidirectional SHIPPED |
| **Agent** (Deep Agent harness, vault-grounded) | ✅ FUNCTIONAL after B7 | Phase B7.1-B7.4 close this; E2E round-trip green |

All 3 layers green ⇒ system is "ready" by the [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] checklist. **However**, algorithm work has additional requirements (per-component math, user decisions on divergent formulas) that are NOT yet met.

---

## 3. Per-component verdict

| Component | Verdict | Reason |
|---|---|---|
| **A02** (Q_HE formula) | **DEFER, BLOCKING** | 3 divergent formulas in repo: `src/ikigai/.../qhe.py:4` (additive weights), `src/contracts/metrics.py:139` (multiplicative), `src/operational/.../habit_engine.py:430` (independent). User must pick 1 canonical before any Q_HE-using code ships. |
| **M01** (vector scoring) | **DEFER** | Depends on N01 (5 vs 4 vectors undecided) and user-vs-persona weight conflict (Revenue ≥ all per [[user-revenue-weight-preference]] vs Revenue=3 in persona). |
| **N01** (regime FSM) | **DEFER** | 3 divergent RECOVER rules (threshold 0.30 / 0.60+sleep_debt / 0.60+consec_misses); math auditing WIP per [[algorithm-issues-registry]]. |
| **A06** (kill conditions) | **DEFER, dependent** | Depends on M01+N01+A02. Cannot define kill thresholds until scoring + regime math is canonical. |
| **IKIGAI weights** | **DEFER** | Triple conflict: user pref (Revenue ≥ all), persona (Revenue=3), defer framework (codified defaults). User explicit override pending per [[user-revenue-weight-preference]]. |

**Gate verdict:** OPEN for [none], CLOSED for [all 5]. Algorithm work stays DEFERRED per memory.

---

## 4. Open ADR questions for user

These do NOT block B7 execution. They block algorithm work.

1. **A02** — pick 1 canonical Q_HE formula (additive weights, multiplicative, or independent)?
2. **N01** — 5 vectors (template edits) or 4 (fold Course→Skill into Skill)?
3. **N01** — which RECOVER trigger rule (0.30 threshold / sleep_debt / consec_misses)?
4. **IKIGAI weights** — hard-rule (Revenue ≥ all enforced), soft-pref (Revenue preferred), or codified-default (current)?
5. **A06** — define kill thresholds (Q_HE floor, regime dwell, vector collapse triggers)?
6. **B7.4 E2E green-light** — does the round-trip meet your "agent layer functional" bar?

---

## 5. References

- [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] — gate criterion (CANONICAL)
- [[algorithm-attribution-decisions-2026-08-29]] — vault_write ONLY writer
- [[algorithm-issues-registry]] — 31 issues pending user decision
- [[user-revenue-weight-preference]] — Revenue weight user pref
- [[master-branch-carro-chefe-2026-08-28]] — canonical agent flow
- [[phase-b7-spec-4-questions-resolved-2026-08-30]] — B7 spec decisions

---

## 6. Status

**PROPOSED 2026-08-30.** Awaiting user review on:
- Layer status verdicts (§2)
- Per-component verdicts (§3)
- Open ADR questions enumeration (§4)

Algorithm work continues DEFERRED until user explicitly unblocks per-component.
