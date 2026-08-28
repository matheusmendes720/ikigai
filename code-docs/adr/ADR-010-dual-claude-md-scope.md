> **[STATUS-CHANGED 2026-08-28 — see claude-md-reconciliation-2026-08-28]**
> This ADR proposed two strategies (Option A boundary headers / Option B
> merge + delete root). The 2026-08-28 reconciliation pass effectively
> implemented Option B outcomes — root \`CLAUDE.md\` was restructured to
> redirect into life/CLAUDE.md as authoritative, and life/CLAUDE.md
> absorbed monorepo-level orientation. **This ADR is effectively
> superseded by the applied reconciliation**; retained for audit trail.
> Per CLAUDE.md reconciliation memory: fixed poetry→uv, src/operational/
> paths, added Current Mode + Root Layout + LangGraph Graphs sections.
> **Do not re-litigate the option choice.**

# ADR-010 — Dual CLAUDE.md Scope Strategy

**Status:** Proposta
**Date:** 2026-08-27
**Deciders:** human (Matheus) — **decision required**
**Consulted:** `life/CLAUDE.md §Pitfalls`, `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` §3 P8, `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md` MIG-8
**Informed:** all agents, contributors
**Scope:** which CLAUDE.md file owns which concerns (or whether to merge)

---

## Status

**Proposta** — pending user decision. Two CLAUDE.md files describe overlapping scopes. This ADR proposes two strategies and asks the user to choose.

---

## Context

The repository has two CLAUDE.md files at different levels:

1. **`C:\Users\mathe\code_space\life-oss\CLAUDE.md`** (root, monorepo level)
   - Sections: Repository Structure, Submodule: life/, Build/Run/Test, Architecture, CI/Quality Gates
   - Treats `life/`, `fin_ops/`, `strategics/` as 3 submodules
   - Last updated: pre-2026-08

2. **`C:\Users\mathe\code_space\life-oss\life\CLAUDE.md`** (life submodule level)
   - Sections: What This Repo Is, Recent Major Changes, Global Conventions, Build/Run/Test, Architecture, Subsystem Map, Where to Start, Pitfalls
   - Treats `life-ops/operational/`, `vibe-ops/`, etc. as sub-subsystems
   - Last updated: 2026-08-27 (most recent observability sprint update)

Concrete defects from the overlap:

1. **Stale content in root file.** Root `CLAUDE.md` says "Active development is in `life/`" but doesn't mention IKIGAI subsystem, observability sprint, or 3-repo coordination.
2. **Conflicting test counts.** Root file says "2839 tests"; life submodule says "74 pytest files" (different metrics).
3. **Inconsistent conventions.** Root file says "Pydantic v2 strict" in §Global Conventions; life submodule says the same; the invariant is violated across the codebase (see ADR-009).
4. **Pitfalls listed in one but not the other.** "PAV CLI broken post-`604d6af`" only in life submodule; "uv vs poetry workspace" only in root.
5. **New contributors confused about which to read first.**

There is also a third CLAUDE.md: `life-ops/operational/CLAUDE.md` (PAV kernel). It overlaps with both. The pitfall note explicitly says "verify against git log + filesystem" — i.e., the team acknowledges the confusion.

---

## Decision

**Awaiting user decision between two options:**

### Option A — Keep both, add explicit scope boundaries

**Implication:** Both files stay. Each gets a `## Scope` section at the top clarifying what it owns. Cross-references added between the two.

- **Root `CLAUDE.md`** owns: monorepo-level concerns (3 submodules, monorepo CI, cross-submodule contracts)
- **`life/CLAUDE.md`** owns: life submodule internals (PAV, IKIGAI, vibe-ops, conventions, pitfalls)

Cost: 2 file edits + boundary headers. No content loss.

### Option B — Merge root into life submodule, delete root

**Implication:** The unique content from root `CLAUDE.md` is moved into `life/CLAUDE.md`. Root file is deleted. The repo becomes effectively single-CLAUDE.md.

- All monorepo-level concerns become life-submodule-level (which is the only active submodule anyway per `life-ops/ikigai/`)
- `fin_ops/` and `strategics/` submodules (if they exist) lose their CLAUDE.md inheritance — but they don't have their own CLAUDE.md anyway

Cost: 1 file edit (merge) + 1 file delete. Some content reorganization needed.

---

## Consequences

### If Option A (keep both with boundaries)

**Positive:**
- Preserves monorepo-level abstraction (in case `fin_ops/` or other submodules come back online)
- Clear scope for new contributors: read root first for orientation, life submodule for deep work
- Low risk — no content loss, no breakage
- Easy to revert if Option B becomes attractive later

**Negative:**
- Maintenance burden: two files to keep in sync
- Boundary drift over time (one file's section gradually expands into the other's)
- Future agents may still be confused about which to read first

**Neutral:**
- Slightly more documentation surface to maintain

### If Option B (merge, delete root)

**Positive:**
- Single source of truth — no confusion
- Smaller doc surface to maintain
- Aligns with reality (life submodule IS the active work)

**Negative:**
- Loses monorepo-level abstraction
- If `fin_ops/` or other submodules come back online, they have no CLAUDE.md to inherit
- Content merge requires care (no information loss)
- Existing links from other docs to root CLAUDE.md break

**Neutral:**
- Cleaner git history (one file vs two)

---

## Alternatives Considered

### A1 — Create a third CLAUDE.md at the package level for IKIGAI

**Rejected because.** More files = more drift. The problem is fragmentation, not granularity.

### A2 — Keep both, add a CLAUDE-INDEX.md that points to each

**Rejected because.** Index adds another file. Option A's boundary headers accomplish the same thing inline.

### A3 — Use symlinks (root CLAUDE.md → life/CLAUDE.md)

**Rejected because.** Symlinks break in Windows + git checkout. Not portable.

---

## Implementation Rules (Option A path)

1. **Edit root `CLAUDE.md`:** add `## Scope` section at top
   ```markdown
   ## Scope

   This CLAUDE.md describes **monorepo-level concerns only**:
   - The 3 submodules (`life/`, `fin_ops/`, `strategics/`)
   - Cross-submodule contracts and CI

   For life-submodule internals (PAV, IKIGAI, vibe-ops, conventions, pitfalls),
   see `life/CLAUDE.md`. **That file is authoritative for life work.**
   ```
2. **Edit `life/CLAUDE.md`:** add `## Scope` section at top
   ```markdown
   ## Scope

   This CLAUDE.md describes **life submodule internals**:
   - PAV kernel (`life-ops/operational/`)
   - IKIGAI meta-brain (`life-ops/ikigai/`)
   - Cybernetic engine (`vibe-ops/`)
   - Global conventions + pitfalls specific to life work

   For monorepo-level orientation (3 submodules, cross-submodule CI),
   see the root `CLAUDE.md`. **That file is the entry point for newcomers.**
   ```
3. **Cross-reference:** add `See also: life/CLAUDE.md` to root §1 and vice versa
4. **Verification:**
   ```bash
   head -20 "C:\Users\mathe\code_space\life-oss\CLAUDE.md" | grep -A 5 "## Scope"
   head -20 "C:\Users\mathe\code_space\life-oss\life\CLAUDE.md" | grep -A 5 "## Scope"
   ```

### Implementation Rules (Option B path)

1. **Identify unique content in root file** (sections not duplicated in life submodule)
2. **Append to `life/CLAUDE.md`** with a "## Monorepo Overview (moved from root)" header
3. **Verify no information loss:** diff each section before deletion
4. **Delete root `CLAUDE.md`**
5. **Update all links** in other docs that reference root CLAUDE.md
6. **Verification:**
   ```bash
   ls "C:\Users\mathe\code_space\life-oss\CLAUDE.md" 2>&1  # should fail (file deleted)
   grep -c "Monorepo Overview" "C:\Users\mathe\code_space\life-oss\life\CLAUDE.md"  # should be ≥1
   ```

---

## Roll-back Criteria

Reversible until file deletion (Option B) or header additions (Option A) are committed. After:

- Option A → Option B: requires re-running merge
- Option B → Option A: requires git revert + boundary header addition

If 6 months after migration the user reports "I keep reading the wrong file" (Option A) or "the merged file is too long" (Option B), schedule a re-evaluation.

---

## Related Decisions

- **Master diagnostic P8:** the source of this ADR
- **Master diagnostic G3 (ADRs in 3 separate places):** related — both ADR surfaces and CLAUDE.md surfaces have fragmentation
- **CLAUDE.md §Global Conventions:** referenced from both files; should not be duplicated
- **Migration MIG-8:** the implementation script

---

## Notes

- The third CLAUDE.md (`life-ops/operational/CLAUDE.md`) is also part of the fragmentation problem. This ADR focuses on the two main ones; the third is implicitly handled by Option B (merged into life) or Option A (boundary headers clarify it as PAV-kernel-specific).
- Per CLAUDE.md rule "Keep files under 500 lines; split when they grow" — the life submodule CLAUDE.md is already at ~300+ lines. Option B risks pushing it over 500, requiring further split.
- This is a documentation decision, not a code decision. Either option is low-risk and reversible.

---

*ADR-010 — Proposta — 2026-08-27 — human decision required — dual CLAUDE.md scope strategy*
