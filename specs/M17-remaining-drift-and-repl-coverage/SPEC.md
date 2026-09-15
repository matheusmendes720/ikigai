---
name: M17-remaining-drift-and-repl-coverage
description: Close M11 Priority 2 drift gaps and add REPL smoke tests to drift net
constitution_refs:
  - composition_over_inheritance
  - spec_driven_not_vibe_driven
  - tests_are_the_contract
status: DONE
owner: loop-orchestrator
created: 2026-09-14
---

# M17 — Remaining Drift Tests + M16 REPL Coverage

> **Spec authored retroactively on 2026-09-14 from M17 description in `roadmap.md`.**
> Work shipped on master in 3 atomic commits prior to SPEC authoring.
> This SPEC captures acceptance criteria as the single source of truth.

## Goal

Close the 2 remaining M11 Priority 2 drift gaps + close the M16 REPL test-coverage gap.

## Why

Drift net is a load-bearing invariant per drift net extended invariants. M11 surfaced 6 Priority 2 gaps; M15 closed 4 (T-15.1 to T-15.4); M17 closes the remaining 2. The REPL is the user-facing surface for the agent layer; 0 dedicated tests = silent regression risk.

## Acceptance Criteria

### T-17.1 — Taskdog Path 3 read-only contract drift test
- [ ] `test_taskdog_tools_read_only_contract` added to `src/ikigai/tests/test_drift_extended_invariants.py`
- [ ] Test asserts `src/ikigai/src/mcp_server/taskdog_tools.py` exports ONLY the 3 read tools (`taskdog_read`, `taskdog_list`, `taskdog_supports_field`)
- [ ] Test explicitly fails if a write tool like `taskdog_apply_change` is added without updating the drift test
- [ ] Locks in Path 3 read-only architecture per ADR-024

### T-17.2 — Investigation queue tools present drift test
- [ ] `test_investigation_queue_tools_present` added to `src/ikigai/tests/test_drift_extended_invariants.py`
- [ ] Test asserts the 3 Plan C investigation tools (`investigation_enqueue`, `investigation_status`, `investigation_complete`) are wired in `server.py` `@MCP.tool` registrations
- [ ] Prevents silent removal during future server.py refactors

### T-17.3 — M16 REPL test coverage
- [ ] `src/ikigai/tests/test_chat_repl.py` (NEW file) created
- [ ] Smoke tests cover:
  - `test_chat_repl_imports` — script imports without error; `--help` exits 0; arg parser validates `--vault` is required
  - `test_chat_repl_handles_eof` — piping empty stdin exits gracefully (no traceback, no crash)
  - `test_chat_repl_profile_command_parses` — `/profile X` is parsed by `parse_profile_command`; mid-REPL switch logs to `profile-switches.log`
- [ ] 8 tests total (also covers file existence + syntax + banner + single-input EOF)

### Drift net + regression
- [ ] Drift net preserved (existing tests still pass + new tests pass)
- [ ] No regression in canonical_scope / drift_invariants / drift_extended_invariants suites
- [ ] All 16 prior milestones stable

## Dependencies

M16 (REPL shipped without test coverage)

## Estimated Ticks

3 (1 per task)

## Constitution Gate

- Append-only preserved on vault/, vibe-ops/, strategics/, review_queue/
- Drift-net invariants preserved
- Pydantic v2 strict preserved
- ADR-013 planner-only scope preserved
- ADR-024 taskdog Path 3 read-only invariants preserved

## Atomic Commits (Actual)

- `626bafe9` — T-17.1 + T-17.2 (both landed in same commit batch due to parallel-agent race; net +2 tests)
- `15b5b2e0` — T-17.3 chat_repl.py smoke tests (8 tests)
- `46e4e3da` — M17 closeout (status flip)

## Out of Scope

- Modifying AGENTS.md / CLAUDE.md (agent-readable, human-editable only)
- Restoring missing tests for removed M12/Phase 8.2 behavior (already done in commit `6564efba`)