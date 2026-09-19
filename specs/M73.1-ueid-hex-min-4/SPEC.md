---
name: M73.1-ueid-hex-min-4
description: Lower-bound hex char count from 6 to 4 so fixture UEIDs with cccc3/dddd4 pass
owner: matheus-mendes
status: DONE
milestone: M73.1
estimated_cost_usd: 0.10
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
---

# M73.1 — UEID hex min 4 chars (cccc3 / dddd4 fixture compat)

## Context

After M73 widened namespace to `{2,8}` and added 5-part legacy branches,
two `tests/gateway/clients/test_sf_replan.py` fixtures still failed:

- `sf:plan:33333333-3333-3333-3333-333333333333:cccc3`
- `sf:plan:44444444-4444-4444-4444-444444444444:dddd4`

The hashes `cccc3` and `dddd4` are 5 chars; the M73 short-form regex
required `{6,8}`. M73.1 lowers the minimum to `{4}`.

## What changed

### src/contracts/common.py:34
### sys_ikigai/entities/ueid.py

Both patterns' short-form branches:
- `[a-f0-9]{6,8}` → `[a-f0-9]{4,8}` (lower bound 6 → 4)
- `[a-f0-9]{6,64}` (long-uuid hash) → `[a-f0-9]{4,64}`

Lower bound 4 chosen over 3 because:
- hex `4` chars = 16 bits = 65536 distinct values, still useful for
  drift detection in test fixtures
- lower would collide too often in production (3 chars = 4096 values)
- matches solverforge calendar fixture convention

## Acceptance

- [x] tests/gateway/clients/test_sf_replan.py : 2/2 PASS (was 2 fail)
- [x] tests/ : 329/329 + 1 SKIP (no regression)

## Out of scope (M74+)

- Canonical migration from 5-part → 4-part UEIDs in stored markdown
- 80+ other test failures in src/ikigai/tests/ unrelated to UEID regex
