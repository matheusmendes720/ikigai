---
name: M81-drift-orphan-fix
description: Fix drift test regex to handle nested parens in titles + add missing M73 STATUS marker
owner: matheus-mendes
status: DONE
milestone: M81
estimated_cost_usd: 0.05
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
  - tests_are_the_contract
---

# M81 - Drift test regex + roadmap orphan fix

## Context

After M74-M80 commits, the drift test `test_no_orphan_milestone_specs`
started failing because it was using a regex that couldn't handle
nested parens in milestone titles (e.g. M75 has "Notify router
(multi-channel outbound)").

## What changed

### src/ikigai/tests/test_drift_extended_invariants.py

Old regex (broken for nested parens):
```python
r"^#{3,4}\s+(M\d+)[^(]*\(STATUS:\s*([\w-]+)\)"
```

New regex (handles nested parens via `.*?` lazy match):
```python
r"^#{3,4}\s+(M\d+(?:\.\d+)?).*?\(STATUS:\s*([\w-]+)\)$"
```

Also added support for `M{NN.NN}` style (M70.1, M73.7, etc.) via
`(?:\.\d+)?` group.

### .claude/loop/roadmap.md

- Added `(STATUS: DONE)` to `### M73 - UEID regex widens` (was the only
  shipped milestone without an explicit status marker).
- Converted em-dash to hyphen in milestone headers (`M74 --` to
  `M74 -`) to match the regex pattern.

## Acceptance

- [x] tests/test_drift_extended_invariants.py : 18/18 PASS
       (was 17/18 with `test_no_orphan_milestone_specs` failing)
- [x] tests/ root : 318 PASS + 27 SKIP (no regression)
- [x] ikigai : 752 PASS + 13 SKIP (no regression)

## Lessons

- **Regex + nested parens**: `[^(]*` is greedy until first `(`. If your
  text has parens in the title, the regex never reaches `(STATUS:`.
  Use `.*?` (lazy match) + line-end anchor `$` instead.
- **Milestone titles must avoid `(STATUS:` markers**: a future regex
  improvement could explicitly forbid this in lint, but for now
  the test author assumed no internal parens.
- **DRIFT test pattern**: `### M\d+ .*\(STATUS: \w+)\$` is more
  robust than `### M\d+ [^(]*\(STATUS: ...)`.

## Out of scope

- The pre-existing flake in `test_resources.py::test_health_resource_matches_tool`
  (passes alone, fails in suite - shared state issue with the auto-use
  notify fixture). Tracked separately.
