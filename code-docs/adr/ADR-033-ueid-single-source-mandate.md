# ADR-033 — UEID Single-Source Mandate

> **Status:** Accepted (initial)
> **Deciders:** matheus (project owner)
> **Date:** 2026-09-21
> **Wave:** R4 (Master-04 attribution gap closure)
> **Supersedes:** none (new decision — codifies an existing implicit invariant)
> **Related code:**
> - `src/contracts/common.py:40-48` — `_UEID_PATTERN` (CANONICAL definition)
> - `sys_ikigai/entities/ueid.py:22-30` — duplicate `_UEID_PATTERN` (MUST import, NOT redeclare)
> - `vault/run-continuation/2026-09-21-master-review-revisited.json` — tiebreaker verdict (conflict #3)
> - `src/ikigai/tests/test_drift_extended_invariants.py` — R1.5 enforcement target (forthcoming)

---

## Context

The UEID canonical regex (per ADR-014, 4-part format) is currently declared in **two parallel locations**:

1. **`src/contracts/common.py:40-48`** — the canonical contracts layer:
   ```python
   _UEID_PATTERN = re.compile(
       r"^(?:"
       r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
       r"|"
       r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{4,64}"
       r"|"
       r"[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
       r")$"
   )
   ```

2. **`sys_ikigai/entities/ueid.py:22-30`** — the bare-namespace consumer:
   ```python
   _UEID_PATTERN = (
       r"^(?:"
       r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
       r"|"
       r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{4,64}"
       r"|"
       r"[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
       r")$"
   )
   ```

The two patterns are **byte-identical today** (post-M73 triple-pattern reconciliation), but they are independent string literals with independent evolution. **If they drift, every cross-fork join key silently degrades.**

### Master-04 attribution gap (2026-09-21)

`vault/run-continuation/2026-09-21-master-review-revisited.json` `conflicts_resolved.conflicts[2]` records the tiebreaker verdict on Master-04's P0 attribution claim:

- **Master-04 said:** "sys_ikigai/entities/ueid.py:16 5-part regex — P0 violation competing with ADR-014 4-part"
- **Master-01 said:** "Resolved with triple-pattern identical in both files"
- **Verdict:** Master-01 wins (partially) — the 5-part branch is BY DESIGN (legacy compatibility per docstring) and NOT a violation of ADR-014.
- **However:** "Master-04 errou na severity mas acertou na fragilidade (duas fontes de verdade paralelas). ADR-033 ainda útil."

This ADR formalizes the structural fix: even though the current regexes are aligned, the **structural fragility** (two parallel definitions) remains. If a future edit adds a 4th branch to one file but not the other, every cross-fork validation will fail or accept UEIDs inconsistently.

### M73 reconciliation history

The two files drifted independently before M73:

- **M73 (early September):** widened the regex to a triple-pattern (4-part short OR 4-part long-UUID OR 5-part legacy) to accept legacy fixture variants. Both files were updated to the same triple-pattern.
- **M73.1:** widened lower bound from `{6,8}` to `{4,8}` hex chars so test fixtures with `cccc3` (5 chars) and `dddd4` (5 chars) pass alongside canonical `{6,8}` short form. Both files were updated.
- **M73.2:** narrowed namespace range from `{2,8}` with explicit allowlist (note: `src/contracts/common.py` retains `{2,8}` literal range; the docstring on `sys_ikigai/entities/ueid.py` notes the allowlist intent but the code is currently still `{2,8}`).

The fact that every M73 reconciliation needed to touch **both** files (and that M73.1 had to be applied to **both** files in separate commits) is the smoking gun for the structural fragility.

---

## Decision

**`src/contracts/common.py` is the canonical source of the UEID regex pattern.** `sys_ikigai/entities/ueid.py` MUST import `_UEID_PATTERN` from `src.contracts.common`, NOT redeclare it locally.

The contract has **3 rules (R1–R3)** and **1 enforcement invariant** (forthcoming R1.5).

### R1 — `src/contracts/common.py` is canonical

`_UEID_PATTERN` (and its compiled form, if any) MUST be defined in `src/contracts/common.py` and only there. Any edit to the regex body — branch additions, char-class widening, anchor changes — MUST land in this file as the single source of truth.

### R2 — `sys_ikigai/entities/ueid.py` MUST import, not redeclare

`sys_ikigai/entities/ueid.py` MUST consume `_UEID_PATTERN` via direct import from `src.contracts.common`:

```python
from src.contracts.common import _UEID_PATTERN  # CANONICAL
```

(Or, if the namespace alias is preferred, the equivalent:

```python
from contracts.common import _UEID_PATTERN  # bare-namespace mirror, if conftest resolves both
```

— see R3 for the dual-identity patch requirement.) Redeclaring the regex body in `sys_ikigai/entities/ueid.py` is **FORBIDDEN**.

### R3 — Future edits go to `src/contracts/common.py` ONLY

If the regex needs a new branch (e.g., a 4-part UUIDv7 variant), the edit MUST land in `src/contracts/common.py:_UEID_PATTERN`. `sys_ikigai/entities/ueid.py` requires no edit because it imports.

---

## Rationale

1. **`src/contracts/` is the canonical contracts layer per the global conventions.** CLAUDE.md (repo root) §"Global Conventions" states: "Contracts in `src/contracts/` — Pydantic models imported from `src/contracts/` everywhere." `sys_ikigai/` is a downstream consumer that should import, not duplicate.

2. **The drift already happened.** M73 vs M73.1 vs M73.2 are three consecutive reconciliation passes where the same regex change had to be applied to two files in separate commits. Each pass is a window where the two files diverge silently — the next contributor who edits one but not the other triggers the bug.

3. **Test-typed alignment beats documentation.** A drift detector that pins "the regex string in `sys_ikigai/entities/ueid.py:22-30` MUST equal the regex string in `src/contracts/common.py:40-48`" cannot go stale without CI catching it. The forthcoming R1.5 invariant (next bullet) is exactly that.

4. **`sys_ikigai/` was renamed later, not earlier.** The `sys_ikigai/` namespace was renamed on 2026-09-05 (`src/ikigai/src/ikigai/` → `sys_ikigai/`, commit `685dec5`) — AFTER `src/contracts/common.py` already established the canonical UEID class. The rename did not flip the canonical direction; it just moved the downstream consumer.

5. **Reversibility favors the simpler invariant.** If we ever need a regex split (e.g., canonical vs legacy as separate constants), the split MUST originate in `src/contracts/common.py`; `sys_ikigai/entities/ueid.py` simply re-exports. There is no scenario where the reverse direction is preferable.

6. **Prevents the M11 silent-failure pattern.** The same class of bug — wrapper/registry drift surfaced by M11 (ADR-032 context) — applies to regex/canonical drift. ADR-032 establishes "bridge ⊆ server" with a drift detector; this ADR establishes the parallel "imported regex ≡ canonical regex" with a parallel drift detector (R1.5).

---

## Implementation Rules

**R1 — `src/contracts/common.py:_UEID_PATTERN` is canonical.** Edits MUST land in `src/contracts/common.py:40-48` (or its replacement location if the class refactors). `sys_ikigai/entities/ueid.py` requires no edit.

**R2 — `sys_ikigai/entities/ueid.py` MUST import.** The file MUST contain:

```python
from src.contracts.common import _UEID_PATTERN
```

(Or via the bare-namespace mirror `from contracts.common import _UEID_PATTERN`, depending on which sys.path prefix the conftest has set. See R3.) The local redefinition of `_UEID_PATTERN` MUST be deleted.

**R3 — Dual-identity patch for tests.** When monkeypatching `_UEID_PATTERN` in tests, patch BOTH identities (per the dual-module identity bug class — `memory/test-review-queue-worker-dual-module-fix-2026-09-05.md`). The dotted-prefix identity is `sys.modules["src.contracts.common"]._UEID_PATTERN`; the bare-namespace mirror is `sys.modules["contracts.common"]._UEID_PATTERN` if it exists. The drift detector (R1.5) handles this automatically because it inspects the actual source files.

**R4 — Single source enforcement.** A new drift test `test_ueid_regex_single_source` (R1.5) MUST be added to `src/ikigai/tests/test_drift_extended_invariants.py` (or a new file under `src/ikigai/tests/`). The test MUST:

1. Parse `src/contracts/common.py` and extract `_UEID_PATTERN.pattern` (or the raw string literal if uncompiled).
2. Parse `sys_ikigai/entities/ueid.py` and assert the file does NOT contain a `_UEID_PATTERN` re-declaration (e.g., assert the regex string literal `^[a-z]{2,8}:` does not appear in `sys_ikigai/entities/ueid.py`).
3. Assert that `sys_ikigai/entities/ueid.py` imports `_UEID_PATTERN` from `src.contracts.common` (or its bare-namespace mirror).
4. Optionally, assert `sys.modules["sys_ikigai.entities.ueid"]._UEID_PATTERN is sys.modules["src.contracts.common"]._UEID_PATTERN` at runtime.

If the test fails, CI fails. There is no override flag.

**R5 — ADR is the canonical amendment process.** Any proposal to change the UEID regex body, to introduce a 4th branch, or to flip the canonical direction MUST create a new ADR (or amend this one). Per append-only invariant (CLAUDE.md), the original `_UEID_PATTERN` definition MUST be annotated as "superseded by ADR-XXX" rather than silently rewritten.

---

## Consequences

### Positive

- **Eliminates the M73 reconciliation cycle.** Future regex changes apply to one file. M73.1-style "we forgot to update `sys_ikigai/`" bugs cannot recur.
- **Single source of truth.** `src/contracts/common.py` is the only file a contributor edits when changing the UEID canonical format. `sys_ikigai/entities/ueid.py` is a pure consumer.
- **Drift detector load-bearing.** R1.5 (`test_ueid_regex_single_source`) prevents re-introduction of the structural fragility. Per ADR-013 §"Persistent enforcement": drift detectors are the canonical mechanism for invariant protection.
- **No functional behavior change.** The current regex body is identical in both files. After this ADR ships, the regex body lives in one file and is imported by the other — byte-identical behavior, half the maintenance surface.

### Negative

- **1 drift test to maintain.** `test_ueid_regex_single_source` is load-bearing; if it breaks (false positive) every CI run fails. Per Phase 8.2 SPEC §3 — "drift tests grow with the system; weakening them is forbidden."
- **Cross-module import brittleness.** `sys_ikigai/entities/ueid.py` now imports from `src.contracts.common`, which crosses the dotted-prefix / bare-namespace boundary. Per the dual-module identity bug class, this is resolvable but requires the test to handle both identities.
- **One-time refactor required.** The redeclaration in `sys_ikigai/entities/ueid.py:22-30` MUST be deleted and replaced with `from src.contracts.common import _UEID_PATTERN`. Estimated effort: ~10 minutes.

### Neutral

- **Master-04's P0 attribution claim is REFUTED.** The 5-part branch in `sys_ikigai/entities/ueid.py:22-30` is intentional legacy compat per the docstring (ADR-014 R5: 5-part is accepted for vault reads only, never written). The Master-04 verdict was downgraded by the Master-01 tiebreaker to "structural fragility, not violation." This ADR resolves the structural fragility without changing the regex body or the 5-part acceptance policy.
- **`UEID = Annotated[str, StringConstraints(pattern=_UEID_PATTERN, ...)]` in `sys_ikigai/entities/ueid.py:32-38` is preserved.** The Pydantic `StringConstraints` wrapper around the imported regex remains; only the regex source changes.

---

## Alternatives Considered

### Alt A — Reverse direction: `sys_ikigai/entities/ueid.py` is canonical

Make `sys_ikigai/` the source of truth and have `src/contracts/common.py` import from it.

- **Rejected:** `sys_ikigai/` was renamed later (2026-09-05) than `src/contracts/common.py` was established. The canonical contracts layer is the global convention; reversing it would require updating CLAUDE.md global conventions and would conflict with the established import direction in 30+ test files.

### Alt B — Extract to a third module (`src/contracts/_ueid_pattern.py`)

Create a tiny dedicated module that exports only `_UEID_PATTERN`. Both `src/contracts/common.py` and `sys_ikigai/entities/ueid.py` import from it.

- **Rejected:** over-engineering for one regex. The `_UEID_PATTERN` is one of several primitives in `src/contracts/common.py` (alongside `UEID` class, `Period`, `Priority`, `EntityType`, `RegimeState`). Extracting only the regex would split the canonical contracts layer across two files for no functional benefit. YAGNI.

### Alt C — Compile-time codegen: generate `sys_ikigai/entities/ueid.py` from `src/contracts/common.py`

Build-time codegen produces the bare-namespace file from the dotted-prefix source.

- **Rejected:** codegen adds a build step and a codegen tool for one regex. Drift detector (R1.5) achieves the same enforcement with zero build complexity. ADR-012 §"Tool versioning: YAGNI" precedent.

### Alt D — Keep both, rely on visual review

Continue documenting "both files must be updated together" without drift enforcement.

- **Rejected:** this is the pre-M73 state. M73.1 was the proof that visual review fails: the regex change was applied to one file, then a separate commit applied it to the other, with a window where the two diverged. Drift detector is the only mechanism that prevents the class of bug.

### Alt E — Drop the sys_ikigai regex entirely; make `sys_ikigai/entities/ueid.py` re-export the `src/contracts.common.UEID` class

Eliminate the `Annotated[str, StringConstraints(...)]` wrapper in `sys_ikigai/entities/ueid.py:32-38` entirely; have `sys_ikigai/entities/ueid.py` re-export `from src.contracts.common import UEID`.

- **Deferred (not rejected).** This is the next-step simplification once R1–R4 stabilize. The Pydantic `Annotated` wrapper has different validation semantics than the `UEID(str)` subclass (different type identity, different `__get_pydantic_core_schema__` implementation). Merging them is an API-level decision that should ship as a separate ADR after the single-source invariant is enforced. Out of scope for ADR-033.

---

## Format Specification (unchanged from ADR-014)

| Segment | Regex | Example | Meaning |
|---------|-------|---------|---------|
| `CLUSTER` / `namespace` | `^[a-z]{2,8}$` | `ikig` | cluster / namespace identifier |
| `ENTITY` / `slug` | `^[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]$` | `meta-planner` | entity name |
| `HASH` / `uuid` | `^[a-f0-9]{4,8}$` or `^[a-f0-9-]{8,36}$` | `a3f2c8e1` | short hash OR long UUID |
| `SEQ` / `hash` | `^[a-f0-9]{4,8}$` or `^[a-f0-9]{4,64}$` | `7b4f2a91` | sequence / content hash |

Full canonical regex (post-M73.2 triple-pattern):

```
^[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}
|[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{4,64}
|[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}
```

---

## Cross-references

### Load-bearing prior ADRs

- **ADR-014 — UEID Canonical Format (4-part)** (Accepted 2026-09-04) — establishes 4-part as canonical and supersedes the 5-part claim. ADR-033 enforces the structural invariant (single source) that ADR-014 implicitly assumed.
- **ADR-023 — UEID Canonical Format Adjudication** (Accepted 2026-09-06) — formal adjudication that 4-part wins, 5-part rejected. ADR-033 does not change the format decision; it locks the structural enforcement.
- **ADR-013 — Canonical scope discipline** (Accepted 2026-08-31) — establishes the pattern of drift-detector load-bearing invariants. R1.5 (`test_ueid_regex_single_source`) follows the ADR-013 §"Persistent enforcement" template.
- **ADR-032 — Bridge-Wrapper Drift Contract** (Accepted 2026-09-21) — sister ADR addressing the same class of bug (wrapper/registry drift) for `mcp_bridge.py ⊆ server.py`. ADR-033 applies the same pattern to regex/canonical drift for `sys_ikigai/entities/ueid.py ⊆ src/contracts/common.py`.

### Related decisions

- **ADR-009 — Pydantic v2 strict** (Accepted 2026-08-31) — `UEID = Annotated[str, StringConstraints(...)]` is a Pydantic-level validation wrapper. ADR-033 preserves the wrapper semantics; only the regex source changes.
- **ADR-026 R4 — Sub-Agent Dispatch Protocol** (Accepted 2026-09-05) — sub-agent IDs MUST be 4-part UEIDs. ADR-033's drift detector guarantees that the validation rule the dispatcher relies on cannot silently drift.

### Code references

- `src/contracts/common.py:40-48` — CANONICAL `_UEID_PATTERN = re.compile(...)`
- `src/contracts/common.py:60-152` — `class UEID(str)` validator using `_UEID_PATTERN`
- `sys_ikigai/entities/ueid.py:22-30` — REDECLARATION (MUST be deleted post-ADR-033 acceptance)
- `sys_ikigai/entities/ueid.py:32-38` — `UEID = Annotated[str, StringConstraints(pattern=_UEID_PATTERN, ...)]` (preserved)
- `src/ikigai/tests/test_drift_extended_invariants.py` — R1.5 enforcement target (`test_ueid_regex_single_source`, forthcoming)

### Memory / review references

- `vault/run-continuation/2026-09-21-master-review-revisited.json` `conflicts_resolved.conflicts[2]` — Master-01 vs Master-04 tiebreaker verdict: Master-01 wins (5-part is BY DESIGN), but Master-04 was correct on structural fragility
- `memory/ueid-5part-canonical-decision-2026-08-31.md` — original 5-part promotion (superseded by ADR-014)
- `memory/m12-bottom-up-infra-shipped-2026-09-14.md` — M12 P0 attribution fixes; T-12.2 added the sys_ikigai 4-part correction (now stable, but parallel to src/contracts/common.py — ADR-033 closes the parallel)
- `memory/test-review-queue-worker-dual-module-fix-2026-09-05.md` — dual-module identity bug class; R3 of this ADR inherits the dual-patch pattern

### Implementation steps (post-acceptance)

1. Delete the redeclaration at `sys_ikigai/entities/ueid.py:22-30`.
2. Add `from src.contracts.common import _UEID_PATTERN` to `sys_ikigai/entities/ueid.py:1-13` (replacing or supplementing the module docstring).
3. Verify `UEID = Annotated[str, StringConstraints(pattern=_UEID_PATTERN, ...)]` at `sys_ikigai/entities/ueid.py:32-38` continues to resolve.
4. Add `test_ueid_regex_single_source` to `src/ikigai/tests/test_drift_extended_invariants.py` (R1.5).
5. Run drift net + targeted pytest; expect 53 → 54 invariants PASS.

---

*ADR-033 — accepted 2026-09-21 — locks the single-source invariant that ADR-014 implicitly assumed; drift detector forthcoming as R1.5 in `test_drift_extended_invariants.py`*
