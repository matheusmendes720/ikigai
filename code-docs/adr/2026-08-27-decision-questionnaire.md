> **[SUPERSEDED 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> Decision questionnaire for pre-pivot Proposta ADRs (ADR-008..011).
> PAV is desativado; decision flow is paused per data-first methodology
> (ADR-007) until 5+ manual SONHO logs exist. Answers to this
> questionnaire are deferred with the underlying ADR scope.

# Decision Questionnaire — 2026-08-27 — Proposta ADRs

> **Companion to:** `code-docs/adr/ADR-008..011` (4 Proposta ADRs awaiting human decision)
> **Format:** one-page decision aids per ADR. Each ADR section can be answered in isolation.
> **Reading order:** §0 → §5 (decision order) → the ADR section most relevant to you → §6 (log your choice).

---

## §0 Purpose

This document operationalizes the four **Proposta** ADRs drafted on 2026-08-27 so the decider
(Matheus) can choose with full context. Each ADR is presented as:

- **Question** (one sentence, the actual decision)
- **Stakes** (what we lose by deferring or picking wrong)
- **Option A / Option B** (verbatim from source ADR + first 3 concrete actions + weighted criteria table)
- **Pre-mortem** (most likely failure mode if we pick Option A)
- **Reversibility** (rollback cost)
- **Recommendation** (the author's tentative call; user can override)

These are not new ADRs. They are decision aids over the existing Propostas. Total target: 400–500
lines so each ADR gets ~80 lines of focused comparison.

**ADR inventory:**

| ADR   | Title                                       | Status     | Blocks            |
|-------|---------------------------------------------|------------|-------------------|
| 008   | IKIGAI Vector Count (5 vs 4)                | Proposta   | MIG-5, scoring    |
| 009   | Pydantic Strict Mode Invariance             | Proposta   | 30+ entity files  |
| 010   | Dual `CLAUDE.md` Scope Strategy             | Proposta   | new contributor UX |
| 011   | HTTP+SSE Transport for IKIGAI MCP           | Proposta*  | S-C2 (dcode)      |

(*ADR-011 is "recommended acceptance"; the others are neutral.)

---

## §1 ADR-008 — IKIGAI Vector Count (5 vs 4)

### Question

**Should the canonical IKIGAI vector set be `{passion, skill, market, revenue, course}` (5 vectors)
or `{passion, skill, market, revenue}` (4 vectors)?**

### Stakes

- The codebase is split: `IKIGAiProfile` instantiates 5 `VectorScorePoint` fields; `PRD-07` and
  `ikigai_scorer` operate on 4. Every agent that reads one source and writes to the other
  introduces a bug.
- ~25 files affected (root docs, PRD, entity files, vault frontmatter, tests).
- Vector weight mechanism (memory `algorithm-issues-registry.md` N01) is already deferred until
  5+ SONHO logs; picking 5 vectors without data first may violate ADR-007 (data-first methodology).

### Option A — Promote to 5 vectors (Course becomes canonical)

**Verbatim decision text (ADR-008 §Decision):**

> "Promote to 5 vectors (add Course as canonical). PRD-07 is updated to document 5 vectors.
> Course becomes a first-class vector with: Scoring rubric (0.0-1.0 range, like the others),
> Propagation rules in `life-ops/ikigai/src/ikigai/entities/profile.py`, Heuristic support in
> `vibe-ops/pipeline/ikigai_scorer.py` (4 → 5 weight normalization), Test coverage: all 5
> vectors exercised in unit + integration tests, Vault frontmatter: backfill missing Course
> entries with default 0.0 + flag for review."

**First 3 concrete actions:**

1. Run `python life-ops/ikigai/scripts/migrate_mig5.py --option=A --dry-run` to enumerate
   affected files and frontmatter entries needing Course backfill.
2. Edit `life-ops/ikigai/src/ikigai/entities/profile.py` to formalize `course: VectorScorePoint`
   with a `0.0` default + `course_weight = 0.1` (lowest among the 5).
3. Update `PRD-07.md` to list Course as vector #5 with a one-paragraph rubric.

**Weighted decision criteria:**

| Criterion                                | Weight | Score (1-5) | Weighted |
|------------------------------------------|--------|-------------|----------|
| Alignment with user's mental model       | 0.30   | 5           | 1.50     |
| Adherence to ADR-007 (data-first)        | 0.25   | 2           | 0.50     |
| Migration cost (lower = better)          | 0.15   | 3           | 0.45     |
| Future-proofing for academic workflows   | 0.20   | 5           | 1.00     |
| Test suite coherence                     | 0.10   | 3           | 0.30     |
| **Total**                                | 1.00   | —           | **3.75** |

### Option B — Revert to 4 vectors (drop Course)

**Verbatim decision text (ADR-008 §Decision):**

> "Revert to 4 vectors (remove Course). Course vector is removed from all surfaces. Affected:
> `IKIGAiProfile` drops the 5th `VectorScorePoint` field. `IKIGAiVectorEntity` enum drops
> `COURSE`. `data/matheus/dreams/*.md` frontmatter strips Course entries. Tests: remove
> 5-vector assertions, add 4-vector assertions. PRD-07 remains canonical (no change needed).
> `ikigai.vector list` returns 4 (down from 5)."

**First 3 concrete actions:**

1. Run `python life-ops/ikigai/scripts/migrate_mig5.py --option=B --dry-run` to enumerate
   files where Course entries must be stripped.
2. Edit `life-ops/ikigai/src/ikigai/entities/profile.py` to remove the `course` field and
   `COURSE` from `IKIGAiVectorEntity` enum.
3. Update `vibe-ops/pipeline/ikigai_scorer.py` (if needed) to confirm 4-vector geo + harmonic
   mean math is unchanged (per ADR-008, this path is already aligned).

**Weighted decision criteria:**

| Criterion                                | Weight | Score (1-5) | Weighted |
|------------------------------------------|--------|-------------|----------|
| Alignment with user's mental model       | 0.30   | 3           | 0.90     |
| Adherence to ADR-007 (data-first)        | 0.25   | 5           | 1.25     |
| Migration cost (lower = better)          | 0.15   | 3           | 0.45     |
| Future-proofing for academic workflows   | 0.20   | 2           | 0.40     |
| Test suite coherence                     | 0.10   | 5           | 0.50     |
| **Total**                                | 1.00   | —           | **3.50** |

### Pre-mortem — Option A

**If we pick A and it fails 6 months from now, the most likely cause is** we promoted Course to
canonical without 5+ SONHO manual logs proving the workflow (violating ADR-007), so Course ends
up holding placeholder `0.0` values in most dream entries, the geo-mean drags the meta_vector_score
lower than expected, and the heuristic-tuning complexity (5 weights) cascades into test-suite
drift. Mitigation: gate Option A on N01 resolution (vector weight mechanism) per Algorithm Issues
Registry.

### Pre-mortem — Option B

**If we pick B and it fails 6 months from now, the most likely cause is** we silently discard
semantically meaningful Course scores already captured in `data/matheus/dreams/*.md` frontmatter
(those rows are *evidence* the user took Course seriously), and the data loss surfaces as
"I dropped a vector I was actually using" six months later when reviewing archived logs.

### Reversibility

Reversible until MIG-5 runs against production vault data. After MIG-5:

- A → B: re-migration + manual Course cleanup (estimated 4 hours)
- B → A: re-migration + frontmatter backfill from git history (estimated 2 hours)

### Recommendation

**Option B (4 vectors), gated on a 30-day audit:** before deleting Course entries, count Course
occurrences in `data/matheus/dreams/*.md`, `data/matheus/objectives/*.md`, and SONHO logs. If
count ≥ 5 across 30 days, escalate to Option A. ADR-007 explicitly forbids promoting vectors
without observed usage; defaulting to Option B respects data-first methodology.

---

## §2 ADR-009 — Pydantic Strict Mode Invariance

### Question

**Should all Pydantic v2 entities use `frozen=True, extra="forbid", strict=True`, or should the
invariant be relaxed for entities that legitimately need lax behavior?**

### Stakes

- CLAUDE.md §Global Conventions already says "Pydantic v2 strict ... non-negotiable" but the
  invariant is violated across 0 of 12 IKIGAI entities.
- Silent data loss bugs (typos dropped, `int → str` coercion) will continue accumulating.
- Two-semantics drift between vibe-ops (mostly strict) and IKIGAI (mostly lax).

### Option A — Enforce strict mode across all entities (per current CLAUDE.md)

**Verbatim decision text (ADR-009 §Decision):**

> "Enforce strict mode across all entities (per CLAUDE.md). All 12+ IKIGAI entities and 17+
> vibe-ops entities are converted to `frozen=True, extra="forbid"`, `model_config =
> ConfigDict(strict=True)`. Migration: Audit each entity for `frozen=False` dependencies (e.g.,
> `score_history` lists, mutable defaults). Add `frozen=True` + `extra="forbid"` + `strict=True`.
> Fix any test that relies on lax behavior (int coercion, extra field acceptance). Add a CI
> check that fails if a new entity lacks strict mode."

**First 3 concrete actions:**

1. Run `python scripts/audit_pydantic_strict.py --report=missing.json` to enumerate every entity
   file missing `frozen=True`, `extra="forbid"`, or `strict=True`.
2. Convert `src/ikigai/entities/base.py` (`PlanEntity`) first as the base class; ripple impact
   to 11 derived classes. Replace mutable defaults (`score_history: list = []`) with
   `Field(default_factory=list)`.
3. Add `scripts/check-pydantic-strict.py` to CI; the script fails if any entity lacks strict mode.

**Weighted decision criteria:**

| Criterion                                | Weight | Score (1-5) | Weighted |
|------------------------------------------|--------|-------------|----------|
| Defense in depth (catches bugs early)    | 0.30   | 5           | 1.50     |
| Migration cost (lower = better)          | 0.20   | 2           | 0.40     |
| Test breakage exposure                   | 0.15   | 2           | 0.30     |
| Idempotency guarantees                   | 0.20   | 5           | 1.00     |
| Future-agent discipline (CI-enforced)    | 0.15   | 5           | 0.75     |
| **Total**                                | 1.00   | —           | **3.95** |

### Option B — Relax the invariant (downgrade CLAUDE.md)

**Verbatim decision text (ADR-009 §Decision):**

> "Relax the invariant (downgrade CLAUDE.md). Update CLAUDE.md §Global Conventions to permit lax
> mode for entities that have a documented reason (e.g., `score_history` requires mutability).
> Each lax entity gets a `# INVARIANT-RELAXED: <reason>` comment."

**First 3 concrete actions:**

1. Edit `life/CLAUDE.md` §Global Conventions to add a "Pydantic v2 (relaxed)" variant that
   permits documented lax mode.
2. Annotate each of the 12 IKIGAI entity files with `# INVARIANT-RELAXED: <one-line reason>`.
3. Add a `vibe-ops/specs/pydantic-relaxation.md` document listing the rules for invoking
   `# INVARIANT-RELAXED` (when to relax, when not to).

**Weighted decision criteria:**

| Criterion                                | Weight | Score (1-5) | Weighted |
|------------------------------------------|--------|-------------|----------|
| Defense in depth (catches bugs early)    | 0.30   | 2           | 0.60     |
| Migration cost (lower = better)          | 0.20   | 5           | 1.00     |
| Test breakage exposure                   | 0.15   | 5           | 0.75     |
| Idempotency guarantees                   | 0.20   | 2           | 0.40     |
| Future-agent discipline (CI-enforced)    | 0.15   | 2           | 0.30     |
| **Total**                                | 1.00   | —           | **3.05** |

### Pre-mortem — Option A

**If we pick A and it fails 6 months from now, the most likely cause is** we tightened too many
entities at once, breaking production code paths that relied on lax coercion (e.g., a CLI flag that
accepts `"5"` as a string and coerces to int for arithmetic), and the resulting fix-fest
consumes enough review bandwidth that two subsequent sprints stall. Migration should be staged
entity-by-entity, not all-at-once.

### Pre-mortem — Option B

**If we pick B and it fails 6 months from now, the most likely cause is** the `# INVARIANT-RELAXED`
annotation standard becomes a rubber stamp (every new lax entity gets the comment without a
genuine reason), the safety net CLAUDE.md was supposed to provide dissolves, and silent data loss
incidents resume — the exact failure ADR-009 was supposed to prevent.

### Reversibility

Reversible until the migration script runs against the entity library. After:

- A → B: revert + annotation (1 hour)
- B → A: conversion + test fixes (~3-5 days, the original migration cost)

### Recommendation

**Option A, staged per namespace.** Convert `src/ikigai/entities/base.py` first; let it stabilize
for one sprint before converting the derived classes. Add the CI check (`scripts/check-pydantic-strict.py`)
on day 1 so new entities cannot regress. CLAUDE.md is currently the law of the codebase; relaxing
it without exhausting the enforcement option first is premature.

---

## §3 ADR-010 — Dual `CLAUDE.md` Scope Strategy

### Question

**Should we keep both root and `life/CLAUDE.md` with explicit scope boundaries (and accept ongoing
maintenance burden), or merge root into `life/CLAUDE.md` and delete the root?**

### Stakes

- Two competing CLAUDE.md files describe overlapping scopes with conflicting test counts and
  stale content (root says "2839 tests"; life submodule says "74 pytest files").
- New contributors don't know which to read first; pitfall notes are scattered.
- Low-stakes *as documentation* but high-stakes *as onboarding friction* — and every agent
  reads these files at session start.

### Option A — Keep both, add explicit scope boundaries

**Verbatim decision text (ADR-010 §Decision):**

> "Keep both, add explicit scope boundaries. Both files stay. Each gets a `## Scope` section at
> the top clarifying what it owns. Cross-references added between the two. Root `CLAUDE.md`
> owns: monorepo-level concerns (3 submodules, monorepo CI, cross-submodule contracts).
> `life/CLAUDE.md` owns: life submodule internals (PAV, IKIGAI, vibe-ops, conventions,
> pitfalls). Cost: 2 file edits + boundary headers. No content loss."

**First 3 concrete actions:**

1. Edit `life-oss/CLAUDE.md`: prepend a `## Scope` section declaring "monorepo-level only; see
   life/CLAUDE.md for life work."
2. Edit `life/CLAUDE.md`: prepend a `## Scope` section declaring "life submodule only; see root
   CLAUDE.md for monorepo orientation."
3. Add `See also` cross-references between the two files; verify with `grep -A2 "## Scope"`.

**Weighted decision criteria:**

| Criterion                                | Weight | Score (1-5) | Weighted |
|------------------------------------------|--------|-------------|----------|
| Onboarding clarity for new contributors  | 0.25   | 5           | 1.25     |
| Maintenance burden (lower = better)      | 0.20   | 3           | 0.60     |
| Monorepo abstraction preserved           | 0.20   | 5           | 1.00     |
| Risk of boundary drift over time         | 0.20   | 2           | 0.40     |
| Reversibility if Option B becomes better | 0.15   | 5           | 0.75     |
| **Total**                                | 1.00   | —           | **4.00** |

### Option B — Merge root into life submodule, delete root

**Verbatim decision text (ADR-010 §Decision):**

> "Merge root into life submodule, delete root. The unique content from root `CLAUDE.md` is
> moved into `life/CLAUDE.md`. Root file is deleted. The repo becomes effectively
> single-CLAUDE.md. All monorepo-level concerns become life-submodule-level (which is the only
> active submodule anyway per `life-ops/ikigai/`). `fin_ops/` and `strategics/` submodules (if
> they exist) lose their CLAUDE.md inheritance — but they don't have their own CLAUDE.md anyway.
> Cost: 1 file edit (merge) + 1 file delete. Some content reorganization needed."

**First 3 concrete actions:**

1. Diff root `CLAUDE.md` against `life/CLAUDE.md`; identify the unique monorepo-level sections
   (Repository Structure, Submodule: fin_ops/, Submodule: strategics/) that need to migrate.
2. Append those sections to `life/CLAUDE.md` under a `## Monorepo Overview (moved from root)` header.
3. Delete `life-oss/CLAUDE.md` and update any `README.md` or `docs/` cross-references that pointed
   to it.

**Weighted decision criteria:**

| Criterion                                | Weight | Score (1-5) | Weighted |
|------------------------------------------|--------|-------------|----------|
| Onboarding clarity for new contributors  | 0.25   | 4           | 1.00     |
| Maintenance burden (lower = better)      | 0.20   | 5           | 1.00     |
| Monorepo abstraction preserved           | 0.20   | 1           | 0.20     |
| Risk of boundary drift over time         | 0.20   | 5           | 1.00     |
| Reversibility if Option B becomes better | 0.15   | 2           | 0.30     |
| **Total**                                | 1.00   | —           | **3.50** |

### Pre-mortem — Option A

**If we pick A and it fails 6 months from now, the most likely cause is** the boundary headers
stay clean for ~3 months but then one file's section gradually expands into the other's territory
(e.g., someone adds "fin_ops revival notes" to root CLAUDE.md that drift into life submodule
internals); the two files re-converge on the same overlapping mess we tried to fix.

### Pre-mortem — Option B

**If we pick B and it fails 6 months from now, the most likely cause is** `fin_ops/` or another
sibling submodule comes back online (e.g., via a project revival) and discoverers have no
top-level CLAUDE.md to read for orientation, costing 1-2 days of confusion per new contributor.

### Reversibility

Reversible until file deletion (Option B) or header additions (Option A) are committed. After:

- A → B: re-run merge (1-2 hours)
- B → A: git revert + boundary header addition (30 min)

### Recommendation

**Option A (keep both with boundaries).** This is the lowest-risk path; monorepo abstraction is
preserved in case `fin_ops/` or `strategics/` are revived, and the boundary headers are a 5-minute
edit. Option B's merge cost is small but its irreversibility (file deletion + broken cross-links)
is not worth it for a documentation decision.

---

## §4 ADR-011 — HTTP+SSE Transport for IKIGAI MCP Server

### Question

**Should we add HTTP+SSE transport alongside stdio for the IKIGAI MCP server (recommended), or
stay stdio-only and accept current client limitations?**

### Stakes

- Stdio blocks LangChain deep agents, web UIs, multi-client setups, and observability tools.
- dcode MCP registration (S-C2) and observability sprint Spec 03 work converge on needing HTTP+SSE
  for span flow.
- 3-5 days dev cost + 2 days test cost, against enabling an entire downstream product surface
  (HTTP clients, web UIs, continuous observability).

### Option A — Add HTTP+SSE transport alongside stdio (recommended in source ADR)

**Verbatim decision text (ADR-011 §Decision):**

> "Add HTTP+SSE transport alongside stdio. Use FastAPI or `starlette` for the HTTP layer; SSE for
> streaming responses. Keep stdio as the default for backward compatibility.
>
> ```python
> TRANSPORT = os.getenv("IKIGAI_MCP_TRANSPORT", "stdio")  # stdio | http
> async def main():
>     if TRANSPORT == "http":
>         from mcp.server.sse import SseServerTransport
>         ...
> ```
>
> Default port: `127.0.0.1:3737` (matches solverforge's HTTP feature port). Toggle:
> `IKIGAI_MCP_TRANSPORT=stdio|http`, `IKIGAI_MCP_PORT=3737`. Auth: no auth for local dev
> (127.0.0.1 bind); bearer token via `IKIGAI_MCP_AUTH_TOKEN` for prod."

**First 3 concrete actions:**

1. Add `TRANSPORT = os.getenv("IKIGAI_MCP_TRANSPORT", "stdio")` at the top of
   `src/mcp_server/server.py`; import `SseServerTransport` lazily inside the http branch.
2. Branch `main()`: `if TRANSPORT == "http":` → build a `Starlette` app with `Mount("/sse", ...)`
   and bind to `127.0.0.1:3737`; `else:` → keep the existing stdio_server block unchanged.
3. Add `IKIGAI_MCP_AUTH_TOKEN` middleware (no-op when unset); parametrize the existing test
   suite over both transports with `pytest.mark.parametrize("transport", ["stdio", "http"])`.

**Weighted decision criteria:**

| Criterion                                | Weight | Score (1-5) | Weighted |
|------------------------------------------|--------|-------------|----------|
| Unblocks downstream (LangChain, web UI)  | 0.30   | 5           | 1.50     |
| Backward compatibility (stdio default)   | 0.20   | 5           | 1.00     |
| Attack surface increase (lower = better) | 0.15   | 3           | 0.45     |
| Test coverage burden                     | 0.10   | 3           | 0.30     |
| Alignment with MCP ecosystem standard    | 0.25   | 5           | 1.25     |
| **Total**                                | 1.00   | —           | **4.50** |

### Option B — Stay stdio-only (status quo)

**Verbatim decision text (ADR-011 §Alternatives):**

> "stdio only (status quo). Rejected because. Blocks deep agent integration, web UI,
> multi-client. Decision deferred since observability sprint."

**First 3 concrete actions:**

1. Document current stdio limitations in `life-ops/ikigai/README.md` §Transports so future
   requesters know what's blocked.
2. Decline all requests for HTTP-based integrations until a follow-up ADR is filed.
3. Maintain dcode workaround (S-C2) via stdio-bridge if needed; accept ongoing observability
   limitations.

**Weighted decision criteria:**

| Criterion                                | Weight | Score (1-5) | Weighted |
|------------------------------------------|--------|-------------|----------|
| Unblocks downstream (LangChain, web UI)  | 0.30   | 1           | 0.30     |
| Backward compatibility (stdio default)   | 0.20   | 5           | 1.00     |
| Attack surface increase (lower = better) | 0.15   | 5           | 0.75     |
| Test coverage burden                     | 0.10   | 5           | 0.50     |
| Alignment with MCP ecosystem standard    | 0.25   | 2           | 0.50     |
| **Total**                                | 1.00   | —           | **3.05** |

### Pre-mortem — Option A

**If we pick A and it fails 6 months from now, the most likely cause is** the HTTP path silently
grows edge cases (auth bypass attempts, in-flight request leaks on SIGTERM, connection storms
from a buggy client) that the test suite didn't catch because HTTP branch coverage was added in
a single sprint with no production soak time. Mitigation: deploy HTTP behind a feature flag
(`IKIGAI_MCP_TRANSPORT=http`), keep stdio default for 30 days, then promote.

### Pre-mortem — Option B

**If we pick B and it fails 6 months from now, the most likely cause is** the LangChain deep
agents + observability tools fail to converge on a transport we can support, every workaround
costs a sprint of hackery, and we end up doing Option A anyway with a year of accumulated friction.

### Reversibility

Reversible until prod deployment. The HTTP path is opt-in via env var; reverting to stdio
default is a one-line change (`IKIGAI_MCP_TRANSPORT=stdio`).

### Recommendation

**Option A (HTTP+SSE alongside stdio).** This is also the source ADR's recommendation. The
downstream blockers (S-C2, Spec 03, LangChain deep agents) make the cost-benefit clearly
favorable. Bind to 127.0.0.1 by default; gate bearer-token auth behind
`IKIGAI_MCP_AUTH_TOKEN` so dev stays frictionless.

---

## §5 Cross-ADR Decision Order

These ADRs have soft dependencies. Recommended decision order:

| Order | ADR   | Why first/later                                                    |
|-------|-------|--------------------------------------------------------------------|
| 1     | 010   | Documentation-only decision; lowest stakes; can decide in 5 min    |
| 2     | 011   | Recommended acceptance in source ADR; unblocks S-C2 + Spec 03      |
| 3     | 008   | Data-first gating (ADR-007) requires the 30-day SONHO audit         |
| 4     | 009   | Largest blast radius (30+ entities); tackle when sprint bandwidth |

**Decision order rationale:**

- **010 first.** Pure docs, fully reversible, no downstream blockers. Get the win, build momentum.
- **011 second.** The source ADR already recommends acceptance, and downstream work is queued.
  If deferred, S-C2 (dcode MCP) and Spec 03 (observability) stall.
- **008 third.** The decision is data-gated (ADR-007); a 30-day audit of Course mentions in
  SONHO logs is the prerequisite for Option A. Without the audit, deciding on gut feel violates
  ADR-007.
- **009 fourth.** Largest migration, biggest test breakage risk. Save it for a sprint with
  review bandwidth; convert one namespace at a time, not all at once.

Some unblockings:
- ADR-010 → no code blockers, only contributor UX
- ADR-011 → unblocks S-C2 (dcode MCP) and Spec 03 (observability)
- ADR-008 → unblocks MIG-5; if deferred, the 5-vs-4 drift continues
- ADR-009 → unblocks 30+ entity files; if deferred, silent data loss continues

Some that *don't* unblock each other but are coupled:
- ADR-008 + ADR-009: both touch entity files (`IKIGAiProfile`'s 5 fields, `PlanEntity` base).
  Decide 008 before 009 to avoid double-migration churn.

---

## §6 Decision Log Template

Once a decision is made, append an entry to `code-docs/adr/DECISIONS-LOG.md` (create file if absent)
using the template below. This is the auditable record; the ADR's `## Status` block should also
be updated to `Accepted` or `Rejected`.

```markdown
## YYYY-MM-DD — ADR-NNN — Decision: <Option X>

**Decider:** Matheus
**Context link:** code-docs/adr/ADR-NNN-<slug>.md
**Questionnaire link:** code-docs/adr/2026-08-27-decision-questionnaire.md §N

**Choice:** Option A | Option B
**Rationale (one paragraph, free-form):**
> <Why this option. Reference pre-mortem risks if you rejected them; cite ADR-007 /
> data-first methodology if relevant; note any conditions (e.g., "gated on 30-day audit").>

**Consequences accepted:**
- <List 2-3 known positive/negative consequences from §Consequences of the chosen option.>

**Gating conditions (if any):**
- <e.g., "Option B pending 30-day SONHO audit before committing to revert.">

**Migration kickoff:**
- Owner: <name>
- Target migration script: MIG-<id>
- Earliest implementation date: <YYYY-MM-DD>

**ADR update plan:**
- [ ] Flip ADR-008 status from Proposta → Accepted (or Rejected)
- [ ] Add "Decision Log" section at the bottom of the ADR with the rationale paragraph
- [ ] If Option B of ADR-008/009, schedule a re-evaluation at +6 months
```

The same template applies for all four ADRs. If a decision is *deferred* (not chosen), log it
as `Decision: Defer` with a `Next review date`.

---

## §7 Cross-references

- **Source ADRs:**
  - `code-docs/adr/ADR-008-ikigai-vector-count.md`
  - `code-docs/adr/ADR-009-pydantic-strict-mode-invariance.md`
  - `code-docs/adr/ADR-010-dual-claude-md-scope.md`
  - `code-docs/adr/ADR-011-ikigai-mcp-http-sse-transport.md`

- **Diagnostics referenced by these ADRs:**
  - `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` (G2, G3, S-M3, S-H1, S-C1, S-C2, P8)
  - `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md` (MIG-5, MIG-8)

- **Methodology ADR:**
  - `code-docs/adr/ADR-007-data-first-methodology.md` — gates ADR-008 Option A behind 5+ SONHO logs

- **Memory files cited:**
  - `algorithm-issues-registry.md` — N01 (vector weight mechanism deferral)
  - `ikigai-weight-mechanism-defer.md` — Option C chosen 2026-07-03

- **Implementation points:**
  - `life-ops/ikigai/src/ikigai/entities/profile.py` — `IKIGAiProfile` (5 vectors currently)
  - `vibe-ops/planning/PRD-07.md` — IKIGAI PRD (4 vectors currently)
  - `life-ops/ikigai/src/ikigai/entities/base.py:30` — `PlanEntity` (lax mode currently)
  - `life-ops/ikigai/src/mcp_server/server.py:534` — stdio-only MCP server entrypoint
  - `life-oss/CLAUDE.md` + `life/CLAUDE.md` — the two CLAUDE.md files in scope for ADR-010

---

*Decision Questionnaire — 2026-08-27 — companion to ADR-008..011 (Proposta)*
