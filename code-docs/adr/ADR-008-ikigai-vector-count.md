# ADR-008 — IKIGAI Vector Count (5 vs 4)

**Status:** Proposta
**Date:** 2026-08-27
**Deciders:** human (Matheus) — **decision required**
**Consulted:** `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` §5 G2; `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md` MIG-5
**Informed:** IKIGAI team, all agents touching entity definitions
**Scope:** canonical number of IKIGAI vectors (Passion, Skill, Market, Revenue, ?)

---

## Status

**Proposta** — pending user decision. The vector count is currently inconsistent across the codebase. This ADR proposes two options and asks the user to choose. Once accepted, migration script MIG-5 executes.

---

## Context

The IKIGAI meta-brain has historically had two competing vector counts:

- **5 vectors** — Passion, Skill, Market, Revenue, **Course** (the 5th is "external/obligation")
  - Source: `life/CLAUDE.md`, `life/README.md`, `life/ARCHITECTURE_INDEX.md`, `life-ops/ikigai/src/ikigai/entities/profile.py` (`IKIGAiProfile`)
  - The Course vector was added in late 2025 to represent academic / obligatory learning arcs
- **4 vectors** — Passion, Skill, Market, Revenue
  - Source: `vibe-ops/planning/PRD-07.md` (IKIGAI PRD)
  - The cybernetic engine's scoring layer operates on 4 vectors

The split produces concrete defects:

1. **Drift between code and docs.** `IKIGAiProfile` instantiates 5 `VectorScorePoint` fields; `PRD-07` enumerates 4. When agents read one source and write to the other, they introduce bugs.
2. **Heuristic ambiguity.** `ikigai_scorer` in `vibe-ops/pipeline/ikigai_scorer.py` reads 4 vectors; `ikigai.vector list` in `life-ops/ikigai/cli/app.py` returns 5. Same data, two different views.
3. **Test contradictions.** Tests in `tests/` assume 4; tests in `life-ops/ikigai/tests/` assume 5.
4. **Vault frontmatter inconsistencies.** Some `data/matheus/dreams/*.md` files have `ikigai_vectors: [passion, skill, market, revenue, course]`; others have 4.

Per data-first methodology (ADR-007), the count should reflect observed manual log behavior, not theoretical completeness.

---

## Decision

**Awaiting user decision between two options:**

### Option A — Promote to 5 vectors (add Course as canonical)

**Implication:** PRD-07 is updated to document 5 vectors. Course becomes a first-class vector with:
- Scoring rubric (0.0-1.0 range, like the others)
- Propagation rules in `life-ops/ikigai/src/ikigai/entities/profile.py`
- Heuristic support in `vibe-ops/pipeline/ikigai_scorer.py` (4 → 5 weight normalization)
- Test coverage: all 5 vectors exercised in unit + integration tests
- Vault frontmatter: backfill missing Course entries with default 0.0 + flag for review

**Cost:** ~25 files affected (3 root docs + 1 PRD + 2 entity files + ~6 vault files + ~10 tests). Migration script MIG-5-OPTION-A.

### Option B — Revert to 4 vectors (remove Course)

**Implication:** Course vector is removed from all surfaces. Affected:
- `IKIGAiProfile` drops the 5th `VectorScorePoint` field
- `IKIGAiVectorEntity` enum drops `COURSE`
- `data/matheus/dreams/*.md` frontmatter strips Course entries
- Tests: remove 5-vector assertions, add 4-vector assertions
- PRD-07 remains canonical (no change needed)
- `ikigai.vector list` returns 4 (down from 5)

**Cost:** ~25 files affected (same surface area). Migration script MIG-5-OPTION-B.

---

## Consequences

### If Option A (5 vectors, add Course)

**Positive:**
- Course as a vector surfaces academic / obligatory learning arcs as first-class concerns
- Aligns with how the user already thinks about IKIGAI (per root docs + memory)
- 5-vector `meta_vector_score` (geo + harmonic mean) has more degrees of freedom for regime tuning

**Negative:**
- Migration touches 25+ files; non-trivial frontmatter backfill
- Heuristic tuning becomes more complex (5 weights instead of 4)
- If Course is rarely logged, per ADR-007 it may be premature (data-first says no new vectors until 5+ manual logs prove the workflow)

**Neutral:**
- IKIGAI vector count formally diverges from the original Japanese IKIGAI concept (which is 4 elements: passion, mission, vocation, profession) — but our mapping is interpretive anyway

### If Option B (4 vectors, remove Course)

**Positive:**
- Aligns with PRD-07 (canonical)
- Aligns with original IKIGAI concept
- Heuristic tuning simpler
- All existing tests pass without modification of 4-vector assumptions

**Negative:**
- Loses ability to track academic / obligatory learning as a first-class vector
- If user has been treating Course as important, the migration is destructive (data loss for those entries)
- Root docs (CLAUDE.md, README.md, ARCHITECTURE_INDEX.md) need to be re-edited to remove Course references

**Neutral:**
- `ikigai_scorer` is unchanged (already operates on 4)
- `IKIGAiProfile` becomes a frozen 4-vector snapshot (no dynamic Course add/remove)

---

## Alternatives Considered

### A1 — Keep 5 in some places, 4 in others (status quo)

**Rejected because.** Drift is the root problem. Status quo perpetuates the split-brain, which is the same anti-pattern as the schema split-brain (S-C1). Two schema split-brains is worse than one.

### A2 — Add a 6th vector (Compounding / Habit)

**Rejected because.** Out of scope. ADR-007 says no new vectors until 5+ manual logs prove the workflow. Course has not yet met that bar; Habit definitely has not.

### A3 — Make vector count dynamic (configurable per profile)

**Rejected because.** Adds complexity (every scoring function must check profile's vector set). Most users have a fixed set. YAGNI.

---

## Implementation Rules (whichever option is chosen)

1. **MIG-5 migration script** executes per the chosen option (see `2026-08-27-migration-scripts-catalog.md` §6)
2. **Update PRD-07** to match the canonical count
3. **Update root docs** (CLAUDE.md, README.md, ARCHITECTURE_INDEX.md) for consistency
4. **Update all entity definitions** to use the canonical count
5. **Update all tests** to use the canonical count
6. **Update vault frontmatter** for all entities in `data/matheus/`
7. **Verification command** post-migration:
   ```bash
   ikigai vector list --json | jq 'length'  # should return 4 or 5
   grep -r "ikigai_vectors" data/matheus/ | awk -F'[][]' '{print $2}' | tr ',' '\n' | sort -u
   # should show 4 or 5 unique vector names per entity
   ```

---

## Roll-back Criteria

Reversible until the migration script runs against production data. After MIG-5 executes:

- Option A → Option B: requires re-migration + manual Course entry cleanup
- Option B → Option A: requires re-migration + frontmatter backfill from git history

If 6 months after migration the user reports "I miss the Course vector" (Option B) or "Course is rarely used" (Option A), schedule a re-evaluation.

---

## Related Decisions

- **ADR-007 (Data-First Methodology):** vector count should follow observed behavior
- **Algorithm Issues Registry (memory `algorithm-issues-registry.md`):** N01 — vector weight mechanism, deferred until 5+ SONHO logs
- **`code-docs/00-INDEX.md §12` Known Gaps #2:** the 5-vs-4 issue, tracked here
- **Master diagnostic G2:** the source of this ADR
- **Migration MIG-5:** the implementation script

---

## Notes

- The Course vector was added informally; no ADR documented the addition. This is the canonical decision record.
- Per data-first methodology, **the right answer depends on which vector count appears in 5+ manual logs of the same workflow.** The user should review their `data/matheus/dreams/`, `data/matheus/objectives/`, and `data/matheus/ikigai_state/` notes and count which vector count is more common in real use.
- If the count is mixed (some 4, some 5), the dominant count wins and migration backfills the rest.

---

*ADR-008 — Proposta — 2026-08-27 — human decision required — vector count reconciliation*
