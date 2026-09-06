# ADR-023 — UEID Canonical Format Adjudication (4-part WINS)

> **Status:** Accepted
> **Deciders:** matheus (project owner)
> **Wave:** dcode-harness roadmap Wave 5, Task 3d (W5.3d)
> **Supersedes:** `ueid-5part-canonical-decision-2026-08-31` memory (5-part promotion reversed within 24h)
> **Load-bearing:** YES — all cross-fork join keys and drift detector invariants depend on this decision

---

## Context

Two parallel sources of truth existed for the UEID canonical format on 2026-08-31:

1. **Memory (`ueid-5part-canonical-decision-2026-08-31`):** 5-part format
   `<namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>` promoted to
   canonical; 4-part demoted to deprecated alias.
2. **Code (`src/contracts/common.py` UEID class):** 4-part regex
   `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` enforced by drift detector
   invariants.

The 5-part promotion was reversed within 24 hours. ADR-014 (Accepted 2026-09-04)
formally established 4-part as canonical and documented the supersession trail. The
`memory/ueid-5part-canonical-decision-2026-08-31.md` file retains the original
decision for audit trail purposes but is explicitly superseded.

CLAUDE.md still claimed 5-part as canonical until the 2026-09-04 Q3 audit
correction, which updated the 4-part regex throughout.

This ADR formalizes the adjudication: 4-part is canonical; 5-part is rejected;
the `ueid-5part-canonical-decision-2026-08-31` memory entry is superseded.

---

## Decision

**UEID canonical format = 4-part. 5-part is REJECTED.**

**Canonical regex:** `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`

The 5-part format `<CLUSTER>:<SUBCLUSTER>:<ENTITY>:<HASH>:<SEQ>` was promoted to
canonical on 2026-08-31 per the now-superseded `ueid-5part-canonical-decision-2026-08-31`
memory entry. This promotion was reversed within 24 hours. The 5-part format MUST NOT
be used as a canonical join key across forks.

**Enforcement:**
- Drift detector invariant `test_ueid_canonical_regex_enforced` enforces the 4-part
  regex against all UEID constructors in `src/contracts/common.py`.
- Sub-agent IDs (ADR-026 R4) MUST be 4-part UEIDs. The dispatcher copies UEIDs
  as-is from parent to child state; it MUST NOT rewrite or migrate UEIDs.
- `taskdog` and `solverforge-calendar` adapters validate 4-part on UPSERT.
- CLI commands reject 5-part IDs at parse time.

---

## Consequences

### Positive

- **Canonical regex enforced.** `src/contracts/common.py` UEID class and drift
  invariant `test_ueid_canonical_regex_enforced` are in sync.
- **Drift invariant catches regressions.** `test_ueid_canonical_regex_enforced`
  and `test_subagent_spec_ueid_validation` detect any drift back toward 5-part.
- **Sub-agent dispatch safe.** ADR-026 R4 guarantees all inter-parent-child UEIDs
  are 4-part, preventing a 5-part UEID from propagating through the dispatch
  protocol.
- **Single join key.** All three fork adapters (CLI, taskdog, UPI) share the same
  4-part UEID as canonical join key.

### Negative

- **Migration required for any 5-part code path.** Any legacy code path still
  emitting 5-part UEIDs must migrate to 4-part. The CLAUDE.md 5-part claims were
  corrected in the 2026-09-04 Q3 audit.
- **Supersession noise.** The audit trail contains both the original 5-part decision
  (retained as supersedable) and the ADR-014/ADR-023 adjudication. Acceptable per
  append-only convention.

---

## Format Specification

| Segment | Regex | Example | Meaning |
|---------|-------|---------|---------|
| `CLUSTER` | `^[a-z]{2,5}$` | `ikig` | cluster identifier |
| `ENTITY` | `^[a-z0-9-]+$` | `meta-planner` | entity name |
| `HASH` | `^[a-f0-9-]+$` | `a3f2c8e1` | 8-char content hash |
| `SEQ` | `^[a-f0-9-]+$` | `7b4f2a91` | sequence number |

Full canonical regex: `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`

---

## Cross-references

- **ADR-014** — UEID Canonical Format (4-part) — establishes 4-part as canonical, supersedes 5-part claims in ADR-012 §31 and ADR-013 §7
- **ADR-026 R4** — Sub-Agent Dispatch Protocol: UEIDs flowing between parent and child graphs MUST match the 4-part canonical regex; 5-part UEIDs are REJECTED
- **Drift invariant** `test_ueid_canonical_regex_enforced` (`src/ikigai/tests/test_canonical_scope.py`) — enforces canonical regex against `src/contracts/common.py`
- **Drift invariant** `test_subagent_spec_ueid_validation` (`src/ikigai/tests/test_canonical_scope.py`) — enforces ADR-026 R4: sub-agent IDs are 4-part UEIDs
- **Source memory** `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/ueid-5part-canonical-decision-2026-08-31.md` — original 5-part promotion (superseded within 24h)

---

*ADR-023 — accepted 2026-09-06 — formal adjudication of 4-part canonical UEID format superseding the 2026-08-31 5-part promotion*
