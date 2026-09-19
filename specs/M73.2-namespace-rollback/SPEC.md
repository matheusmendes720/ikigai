---
name: M73.2-namespace-rollback
description: Drop M73.2 strict namespace allowlist (broke SONHO sn: and other production namespaces); revert to {2,8} permissive range
owner: matheus-mendes
status: DONE
milestone: M73.2
estimated_cost_usd: 0.10
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
---

# M73.2 — Rollback of strict namespace allowlist

## Context

M73 added a strict explicit namespace allowlist
(`ikigai|tw|obsidian|external|sf|sc|tb|tsk|life|cli|vibe|ext`) to
`_UEID_PATTERN` in `src/contracts/common.py:34` and
`sys_ikigai/entities/ueid.py`. The intent was to reject
foreign namespaces (`other`, `abcdef`).

But production code uses many namespaces NOT in the allowlist:
- `sn` (SONHO system)
- `hab` (habits)
- `mem` (memory)
- `proj` (projects)
- `sa` (system administration)
- and several others (`ik`, `chk`, `sub`, `task`, `prop`, `study`)

After M73.2, 27 tests failed (all SONHO `sn:` UEIDs rejected).

## Fix (rolled back to M73.1)

Reverted `_UEID_PATTERN` to M73.1 shape:
- Namespace range back to `{2,8}` (no explicit allowlist)
- Hex range stays at `{4,8}` (solverforge `cccc3`/`dddd4` compat)
- 3-branch alternation preserved (4-part short / 4-part long-UUID / 5-part legacy)

Tests updated:
- `test_wrong_namespace_rejected` — `@pytest.mark.skip` (regex no
  longer enforces allowlist)
- `test_short_uuid_rejected` — fixture changed from `4f6a202` (6-char
  which is now valid) to `abc` (3-char which still fails)
- `test_ueid_canonical_regex_enforced` — assertion changed from
  exact-string match to allow either the decision-id comment OR the
  old pattern as substring

## Acceptance (verified 2026-09-19)

- [x] tests/test_ueid_validator.py : 4 PASS + 1 SKIP (was 3 PASS + 2 FAIL)
- [x] tests/test_canonical_scope.py : 35 PASS (was 34 PASS + 1 FAIL)
- [x] tests/test_drift_extended_invariants.py : 18 PASS (was 17 PASS + 1 FAIL)
- [x] tests/ root : 329 PASS + 1 SKIP (no regression)
- [x] SONHO sn: fixtures work
- [x] solverforge sf:/sc:/tb: fixtures work

## Out of scope (M74+)

- 79 remaining ikigai test failures in src/ikigai/tests/ (test_v2_*
  features not yet built, _VAULT_DIR rename in legacy code)
- tests/mcp_server/test_investigation_lifecycle and
  tests/mcp_server/test_vault_read_actor pre-existing collector errors

## Lesson

Don't tighten a regex with an explicit allowlist without first
auditing ALL production namespaces. SONHO uses `sn:` for sleep
dreams, IKIGAi uses `hab:` for habits, etc. The permissive `{2,8}`
range is correct because:
1. UEID consumers validate the namespace downstream (via entity_type
   discriminators in pydantic models).
2. A typo in a single namespace produces a low-impact false-positive
   that surfaces immediately in tests.
3. Tightening requires a registry of namespaces, which itself drifts.
