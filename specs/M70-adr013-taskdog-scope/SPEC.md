---
name: M70-adr013-taskdog-scope
description: ADR-013 enforcement — found taskdog_start/pause/cancel are out-of-scope and reverted the M70 attempt
owner: matheus-mendes
status: DONE
# M70's "work" was discovering that 3 more taskdog tools would
# cross ADR-013 (which forbids them) and reverting them. The revert
# is complete; downstream state is unchanged from M69. Use DONE
# (work-done-on-this-milestone) rather than REVERTED (out of enum).
milestone: M70
estimated_cost_usd: 0.10
constitution_refs:
  - correctness_over_speed
  - state_on_disk_not_conversation
---

# M70 — ADR-013 discovered and respected (reverted after ~10 min)

## Context

After M69 (`taskdog_complete_task` auto-starts PENDING tasks) the deep
agent could call `complete` ergonomically without manually calling
`start` first. I attempted to extend the surface with `taskdog_start`,
`taskdog_pause`, `taskdog_cancel` standalone tools (M70), updated
`tools.py` to register them in `IKIGAI_TOOLS` (15 entries total).

## What happened

The tests `test_canonical_scope::test_ikigai_tools_count_is_12` and
`test_taskdog_harness_e2e::test_ikigai_tools_total_count_is_twelve`
**failed**, surfacing the invariant:

    IKIGAI_TOOLS must contain exactly 12 entries per ADR-013; found 15.

Reading `code-docs/adr/ADR-013-canonical-scope-discipline.md` confirmed
the rule was already documented (and prohibited by intent):

> | `taskdog_start` @tool | Out of scope until workflow needs it (Phase 7 deferred) |
> | Path 3 taskdog MCP gateway | Out of scope; module missing; resurrect only on explicit demand |
> | New `taskdog_*` MCP tools | **Forbidden** by drift detector; Path 1 (harness subprocess) is canonical |

So the drift detector was working as designed — it caught my scope
violation immediately. The implementation worked end-to-end (7-step
smoke was green) but it crossed an explicitly-declared boundary.

## What changed (final state)

This commit **REVERTS** my M70 implementation:

### src/ikigai/src/agents/tools_taskdog.py
- Removed 3 functions: `taskdog_start_task`, `taskdog_pause_task`,
  `taskdog_cancel_task`
- Removed helper `_run_subcommand` (no longer needed)
- `__all__` back to 4 entries

### src/ikigai/src/agents/tools.py
- Reverted import block to 4 tools
- Reverted IKIGAI_TOOLS list to 4 tools (back to 12 total with
  vault/solverforge/tuiboard entries)

### Net behavior
- M67 + M68 + M69 remain: deep agent can `list/get/create/complete`
  with structured JSON, against a daemon-managed server, with
  auto-start inside `complete`. End-to-end workflow is operational.
- 3 new tools (start/pause/cancel) are deliberately NOT exposed.

## Acceptance

- [x] IKIGAI_TOOLS count returns to 12 (drift invariant satisfied)
- [x] 91/91 + 1 SKIP across 8 test files re-passed (drift,
  chat_repl, chat_system, canonical_scope, taskdog tests)
- [x] Deep agent still operational: list/create/get/complete work
  (subset verified in M69 smoke)
- [x] ADR-013 contract intact (out-of-scope tools stay out-of-scope)

## Future work (proper path)

If `taskdog_start/pause/cancel` are needed, the correct path is:

1. **User explicit demand** (per ADR-013) to lift the prohibition
2. Create a new ADR / supersede ADR-013 to add the new scope items
3. Update tests that gate IKIGAI_TOOLS count
4. THEN add the tools (and the M70 patch becomes the reference impl)

The M69 internal "auto-start" workaround is the strategic-acceptable
middle ground: deep-agent expresses "complete this task" intent and
the tool figures out that the underlying state machine requires
auto-start. That respected the ADR constraint and gave ergonomic UX.

## Lessons logged

- **Always read ADR files in the target area BEFORE adding new surface**
- Drift detectors that gate "count = N" are not pedantic — they encode
  ADRs as test-enforced invariants
- The auto-start workaround (M69) was already the user-shaped gesture
  ("complete this task"), so no extra surface was needed at all
