# ADR-014 — UEID Canonical Format (4-part)

> **Status:** ACCEPTED (2026-09-04)
> **Deciders:** matheus (project owner)
> **Supersedes:** ADR-013 §7 in-scope #1 (2026-08-31 decision to make 5-part canonical) — REVERSED
> **Supersedes also:** ADR-012 §31 (which cited 5-part regex)
> **Supersedes also:** CLAUDE.md §243 + §255 (5-part claims)
> **Load-bearing:** YES — every cross-fork join key + drift detector invariant depends on this decision

---

## Context

Two parallel sources of truth for the UEID canonical format existed at 2026-09-04:

1. **Code (drift detector, `src/contracts/common.py` UEID class, Phase 9 invariant B-D08):**
   `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` — 4-part. Verified 8/8 PASS, SHIPPED.
2. **Docs (CLAUDE.md §243 + §255, ADR-012 §31, ADR-013 §7 in-scope #1):**
   `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` — 5-part. Claims 4-part is "deprecated alias."

The drift was first documented at `memory/memory-drift-reconciliation-2026-09-04.md` (Diag 02) as item #6: "5-part canonical claim vs 4-part regex enforcement."

Multiple downstream artifacts were affected:
- `docs/superpowers/specs/2026-09-03-planning-contract-plan-a.md` references 5-part UEIDs in vault templates
- `docs/superpowers/specs/2026-09-03-sonho-tree-hybrid-design.md` uses 5-part format
- `.git/sdd/task-*-brief.md` briefs use 5-part (implementers had to correct to 4-part per `.git/sdd/progress.md` lines 141, 146, 170)

This ADR adjudicates the conflict.

---

## Decision

**UEID canonical format = 4-part. Drift detector regex wins.**

**Format:** `<CLUSTER>:<ENTITY>:<HASH>:<SEQ>`

- `CLUSTER`: 2-5 lowercase letters (e.g., `prj`, `ikigai`, `sn`)
- `ENTITY`: lowercase alphanumeric + dash (variable length)
- `HASH`: 8+ hex chars (UUID-like)
- `SEQ`: 4+ hex chars (sequence/instance discriminator)

**Canonical regex:** `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`

**Examples:**
```
prj:task:a3f1:9c2d          # canonical
sn:life-os-v1:abc12345-1234-5678-9abc-def012345678:0123456789abcdef
ikigai:task:11111111-2222-3333-4444-555555555555:aaaaaaaaaaaaaaaa
```

**NOT canonical (rejected by regex):**
```
prj:task:byd-research:abc123:def456     # 5-part — REJECTED
ikigai:task:t:1                          # 5-part — REJECTED
```

---

## Rationale

1. **Drift detector is the enforcement mechanism.** ADR-013 §8 made drift detectors load-bearing. Reversing the regex would require updating 9 invariants + CliAdapter + UPI column + all test fixtures. Cost: 2-3h of code work + risk of regression.

2. **Code is already shipped and tested.** Phase 9 verified 8/8 PASS at commit `fe61dcc`. Multiple downstream implementers (`.git/sdd/task-*`) found the 4-part regex and silently adapted. The 5-part claims were never enforced.

3. **The 5-part format conflates two concerns.** `<HASH>:<SEQ>` works as 4-part; adding a 5th `<SUBSEQ>` field offers no discriminative power for the canonical join key. Adding it just to satisfy an old decision is busy-work.

4. **Reversibility favors the simpler format.** If we ever need a 5-part format, we can add a discriminator (e.g., `<HASH>:<SEQ>:<SUBSEQ>`) without breaking the 4-part regex. The 5-part → 4-part migration is harder (would invalidate all existing test fixtures).

---

## Implementation Rules

### R1 — Drift detector regex is canonical

`src/ikigai/src/security/drift_invariants.py` (or equivalent location per Plan A architecture) MUST keep the regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`. Any proposal to change this regex MUST create a new ADR (not amend this one).

### R2 — All UEID generators emit 4-part

Helpers like `make_ueid(cluster, entity, hash, seq)` MUST emit 4-part. 5-part generators are FORBIDDEN.

### R3 — Tests use 4-part UEIDs

All test fixtures (and any new tests) MUST use 4-part UEIDs. If a brief or plan uses 5-part, the implementer MUST correct to 4-part (per `.git/sdd/progress.md` line 170 convention).

### R4 — Documentation cites 4-part

CLAUDE.md, specs/, plans/, and ADRs MUST reference 4-part. 5-part references MUST be flagged as superseded (per ADR-013 persistent enforcement).

### R5 — 5-part claims in existing docs are SUPERSEDED (not deleted)

Per append-only convention, 5-part claims in ADR-013 §7, ADR-012 §31, and CLAUDE.md MUST be annotated as "superseded by ADR-014" rather than deleted. Future readers follow the supersession chain.

---

## Supersession Trail

| Doc | Location | What changes | When |
|-----|----------|--------------|------|
| ADR-013 | §7 in-scope #1 | Was "5-part canonical; 4-part deprecated; 2-part isolated" | 2026-08-31 |
| | | **Now: superseded by ADR-014 (4-part canonical)** | 2026-09-04 |
| ADR-012 | §31 (line 31) | Was "5-part regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`" | 2026-08-30 |
| | | **Now: superseded — see ADR-014** | 2026-09-04 |
| CLAUDE.md | §243 | Was "UEID is the canonical join key across all forks (5-part regex ...)" | 2026-08-31 |
| | | **Now: 4-part regex per ADR-014** | 2026-09-04 |
| CLAUDE.md | §255 | Was "UEID format: `<CLUSTER>:<ENTITY>:<ID>` (5-part canonical; 4-part is deprecated alias)" | 2026-08-31 |
| | | **Now: 4-part canonical per ADR-014** | 2026-09-04 |
| Plan A spec | 2026-09-03-planning-contract-plan-a.md | 5-part UEIDs in vault templates | 2026-09-03 |
| | | **Now: 4-part UEIDs (drift detector enforced)** | 2026-09-04 |
| Plan A design | 2026-09-03-sonho-tree-hybrid-design.md | 5-part format | 2026-09-03 |
| | | **Now: 4-part format** | 2026-09-04 |

---

## Consequences

### Positive

- **Single source of truth.** Code = docs = tests = briefs. No more "implementers silently correct" pattern (per `.git/sdd/progress.md`).
- **Zero code changes.** Regex stays as-is; CliAdapter + UPI column + 9 drift invariants unchanged.
- **Unblocks downstream work.** Wave 1 (test hardening) and Wave 3 (Scenario A critical path) can proceed without UEID-format decisions in their critical path.

### Negative

- **Reversal precedent.** This is the 2nd reversal on UEID canonical format (2026-08-31 was #1). Future scope decisions should be more conservative on format changes.
- **Supersession annotations add noise.** Future readers see "5-part canonical" + "superseded by ADR-014" — slightly noisier than a clean rewrite. Acceptable per append-only invariant.

### Neutral

- The 5-part format is not FORBIDDEN — it just isn't CANONICAL. New code may use 5-part for internal discriminator fields, but the canonical join key is always 4-part.

---

## Alternatives Considered

### Alt A — 5-part canonical (CLAUDE.md wins)

Update drift regex + CliAdapter + UPI column + 9 invariants + all test fixtures to 5-part.
- **Rejected**: 2-3h code work + regression risk for a format with no discriminative benefit.

### Alt B — Hybrid: 4-part default, 5-part optional discriminator

Add 5-part as an optional 5th group with no enforcement.
- **Rejected**: violates "single source of truth" principle; complicates drift invariants.

### Alt C — Defer decision (status quo)

Continue claiming 5-part in docs while code enforces 4-part.
- **Rejected**: ongoing drift + implementer confusion + memory/code divergence.

---

## References

- **Superseded:** ADR-013 §7 in-scope #1 (2026-08-31)
- **Superseded:** ADR-012 §31 (2026-08-30)
- **Superseded:** CLAUDE.md §243, §255 (2026-08-31)
- **Related:** `memory/memory-drift-reconciliation-2026-09-04.md` (Diag 02 item #6)
- **Related:** `memory/ueid-5part-canonical-decision-2026-08-31.md` (the 2026-08-31 decision being reversed)
- **Related:** `.git/sdd/progress.md` lines 141, 146, 170 (implementer-side adaptations)
- **Related:** `Plan A spec` (`docs/superpowers/specs/2026-09-03-planning-contract-plan-a.md`) — needs 5-part → 4-part in vault templates
- **Related:** `Plan A design` (`docs/superpowers/specs/2026-09-03-sonho-tree-hybrid-design.md`) — needs 5-part → 4-part update

---

*ADR-014 — accepted 2026-09-04 — closes the longest-running drift in the repo (5-part claim vs 4-part code, ~6 days)*
