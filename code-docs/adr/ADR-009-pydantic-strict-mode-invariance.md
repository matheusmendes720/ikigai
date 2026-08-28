> **[SUPERSEDED 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> ADR-009 (Pydantic strict mode invariance) was decided in the pre-pivot
> era. PAV is desativado; algorithm/template/registry polish deferred per
> algorithm-decisions-defer-2026-08-28. The Pydantic-strict invariant in
> \`src/contracts/\` is preserved (still load-bearing for deep-agent
> contracts) but the implementation scope (which entities it gates) is
> governed by deep-agent design, not by this ADR.

# ADR-009 — Pydantic Strict Mode Invariance for All Entities

**Status:** Proposta
**Date:** 2026-08-27
**Deciders:** human (Matheus) — **decision required**
**Consulted:** `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` §2 S-M3; CLAUDE.md §Global Conventions
**Informed:** IKIGAI team, all Pydantic entity authors
**Scope:** whether all Pydantic v2 entities must follow `frozen=True, extra="forbid"`, strict mode

---

## Status

**Proposta** — pending user decision. The CLAUDE.md invariant is currently violated across most IKIGAI entities. This ADR formalizes the decision and proposes two paths.

---

## Context

CLAUDE.md §Global Conventions states:

> **Pydantic v2 strict** — All data schemas: `frozen=True`, `extra="forbid"`, strict mode — non-negotiable

In practice, the IKIGAI entities violate this invariant:

```python
# src/ikigai/entities/base.py:30 — PlanEntity (base, polymorphic)
class PlanEntity(BaseModel):
    # NO frozen=True
    # NO extra="forbid" (default is "ignore")
    # NO strict mode (default is lax)
```

A scan of `life-ops/ikigai/src/ikigai/entities/` (12+ entity files) shows:
- 0 of 12 use `frozen=True`
- 0 of 12 use `extra="forbid"`
- All 12 use default lax mode (coerces int → str, etc.)

The exception: `RegimeOverrideAudit` and `VectorScorePoint` do use `frozen=True` (correctly).

The vibe-ops entities (17 modules) follow the invariant more closely but still have drift.

This violation produces concrete defects:

1. **Silent data loss.** A typo in a field name passes validation; the value is dropped silently.
2. **Type coercion bugs.** `"5"` (string) coerces to `5` (int) in lax mode; downstream arithmetic fails.
3. **Mutation bugs.** Non-frozen entities can be modified after construction; idempotency guarantees break.
4. **Inconsistency with vibe-ops.** The cybernetic engine uses strict entities; IKIGAI uses lax. Two semantics for the same data.

---

## Decision

**Awaiting user decision between two options:**

### Option A — Enforce strict mode across all entities (per CLAUDE.md)

**Implication:** All 12+ IKIGAI entities and 17+ vibe-ops entities are converted to `frozen=True, extra="forbid"`, `model_config = ConfigDict(strict=True)`. Migration:
- Audit each entity for `frozen=False` dependencies (e.g., `score_history` lists, mutable defaults)
- Add `frozen=True` + `extra="forbid"` + `strict=True`
- Fix any test that relies on lax behavior (int coercion, extra field acceptance)
- Add a CI check that fails if a new entity lacks strict mode

**Cost:** ~30 entity files, ~50 tests potentially affected. Migration script MIG-S-M3-OPTION-A.

### Option B — Relax the invariant (downgrade CLAUDE.md)

**Implication:** Update CLAUDE.md §Global Conventions to permit lax mode for entities that have a documented reason (e.g., `score_history` requires mutability). Each lax entity gets a `# INVARIANT-RELAXED: <reason>` comment.

**Cost:** CLAUDE.md edit + 12+ entity annotations. No code changes. Migration script MIG-S-M3-OPTION-B.

---

## Consequences

### If Option A (strict, per current invariant)

**Positive:**
- Catches typos and type errors at validation time (defense in depth)
- Aligns all subsystems on same semantics
- Future agents inherit the discipline (CI enforces it)
- Idempotency guarantees hold (no in-place mutation)
- Better self-documentation (every field is required or has explicit default)

**Negative:**
- Migration touches 30+ files
- Some tests rely on lax behavior (int coercion, etc.) and need updates
- `score_history` lists need redesign (probably becomes a separate frozen model)
- Mutable defaults must be replaced with `Field(default_factory=...)`

**Neutral:**
- Performance impact minimal (Pydantic strict is fast)
- Documentation effort: 30+ entity docstrings to add

### If Option B (relaxed, update CLAUDE.md)

**Positive:**
- Less migration work
- Existing tests pass unchanged
- Preserves entities that legitimately need mutability

**Negative:**
- Loosens the safety net CLAUDE.md provides
- Future agents may default to lax mode (drift accumulates)
- Inconsistency between IKIGAI (lax) and vibe-ops (strict) persists
- Silent data loss continues

**Neutral:**
- CLAUDE.md becomes more nuanced (less "non-negotiable")
- Need to add a `# INVARIANT-RELAXED:` comment standard

---

## Alternatives Considered

### A1 — Strict mode only for new entities (grandfather existing)

**Rejected because.** Half-measures are worse than either option. New entities strict, old entities lax → no consistency, harder to reason about. Pick a lane.

### A2 — Strict mode only for entities crossing boundaries (vault ↔ SQLite ↔ API)

**Rejected because.** Boundary detection is fuzzy. Most entities cross at least one boundary eventually. Simpler to enforce uniformly.

### A3 — Strict mode + automatic migration via codegen

**Rejected because.** Codegen adds tool complexity. Hand-conversion is feasible (12 files) and surfaces implicit dependencies.

---

## Implementation Rules (Option A path)

1. **Audit phase:** list every entity that violates invariant; document each violation's reason
2. **Conversion phase:** add `model_config = ConfigDict(frozen=True, extra="forbid", strict=True)` to each
3. **Default factory phase:** replace all mutable defaults with `Field(default_factory=...)`
4. **Test phase:** fix any test that breaks; add new tests for the rejected cases
5. **CI phase:** add a `scripts/check-pydantic-strict.py` that fails if any entity lacks strict mode
6. **Verification:**
   ```bash
   python scripts/check-pydantic-strict.py  # should exit 0
   uv run pytest tests/ -v                   # all pass
   ```

### Implementation Rules (Option B path)

1. **CLAUDE.md edit:** §Global Conventions → Pydantic v2 (relaxed) — permitted lax mode for documented reasons
2. **Entity annotations:** each lax entity gets `# INVARIANT-RELAXED: <reason>` comment
3. **Documentation:** add a section to `vibe-ops/specs/` explaining when to relax
4. **Verification:**
   ```bash
   grep -r "INVARIANT-RELAXED" src/ikigai/entities/ | wc -l  # matches entity count
   ```

---

## Roll-back Criteria

Reversible until the migration script runs against the entity library. After:

- Option A → Option B: requires revert + annotation
- Option B → Option A: requires conversion + test fixes

If 6 months after migration the user reports "strict mode is too rigid" (Option A) or "we hit too many silent data loss bugs" (Option B), schedule a re-evaluation.

---

## Related Decisions

- **CLAUDE.md §Global Conventions:** the invariant currently in force
- **Master diagnostic S-M3:** the source of this ADR
- **ADR-007 (Data-First Methodology):** encourages minimal schema; lax mode encourages "just add a field" which conflicts
- **Master diagnostic S-C1 (schema split-brain):** the table-level analog of this entity-level problem

---

## Notes

- The CLAUDE.md invariant was likely added aspirationally without enforcement. This ADR either enforces it (Option A) or revises it (Option B).
- Per CLAUDE.md §Pitfalls: "**Two CLAUDE.md files** (root + `life-ops/operational/CLAUDE.md`) describe overlapping scopes" — the invariant appears in both with same wording, so the decision applies to both surfaces.
- The vibe-ops team has been more disciplined about strict mode; the IKIGAI team has been lax. The decision should align both.

---

*ADR-009 — Proposta — 2026-08-27 — human decision required — Pydantic strict mode enforcement*
