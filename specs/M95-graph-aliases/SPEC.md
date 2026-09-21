---
name: M95-graph-aliases
description: v2 score/regime/suggest/cycle as thin aliases for invoke-skill with entry_point override
owner: matheus-mendes
status: DONE
milestone: M95
estimated_cost_usd: 0.05
constitution_refs:
  - tests_are_the_contract
  - composition_over_inheritance
---

# M95 - v2 score/regime/suggest/cycle graph aliases

## Context

After M94 unblocked `v2 daily`, the remaining skip-tagged tests were
the V5-D-removed commands (`score/regime/suggest/cycle`). Rather than
re-implementing each command's full logic, M95 adds them as thin
aliases that invoke `invoke_skill("ikigai-daily", entry_point_override=...)`.

## What changed

### interfaces/cli/v2.py

- New `register_graph_aliases(app)` registers 4 commands:
  - `v2 score` → `invoke_skill("ikigai-daily", entry_point_override="score_vectors")`
  - `v2 regime` → `invoke_skill("ikigai-daily", entry_point_override="heuristics")`
  - `v2 suggest` → `invoke_skill("ikigai-daily", entry_point_override="surface_intentions")`
  - `v2 cycle` → `invoke_skill("ikigai-daily", entry_point_override="observe")`
- All commands support `--date`, `--json`, `--dry-run` flags
- All commands catch ValueError and return structured JSON error

### src/ikigai/tests/test_v2_interface_dispatch.py

- Removed all 4 M92 skip-tags for V5-D-removed commands
- All 14 tests now PASS

## Acceptance

- [x] test_v2_score_command_help PASS (exit 0, --help works)
- [x] test_v2_score_routes_to_prompt_chain PASS (output has passion_score)
- [x] test_v2_score_does_not_write_vault PASS (read-only invariant)
- [x] test_v2_regime_command_help + routes + no_vault_write: all PASS
- [x] test_v2_suggest_command_help + routes: all PASS
- [x] test_v2_cycle_command_help + dry_run: all PASS
- [x] ikigai 814 PASS + 13 SKIP, 0 FAIL (was 804 + 23, +10 tests PASS)
- [x] root 368 PASS + 27 SKIP, 0 FAIL (unchanged)
- [x] drift 18/18 PASS

## Lessons

- **Loop variable capture in decorators**: Typer `app.command()` runs at
  decoration time. When you build commands in a `for` loop, all
  commands see the LAST iteration's loop variable unless you bind via
  default argument: `_entry_pt: str = entry_pt`. WITHOUT this fix, all
  4 commands called `invoke_skill("ikigai-daily", entry_point_override="observe")`
  (the last iteration's value).
- **Aliases > re-implementations**: M95 added 4 thin commands (≈80 LOC)
  vs M94's ~250 LOC of invoke_skill rework. Aliases preserve the
  v2 architecture's intent (invoke_skill is the canonical entry).
- **Typer requires Typer-style signatures**: `@click.pass_context` with
  manual `click.option(...)` decorators breaks Typer's parameter parsing
  (`--json` was being treated as the `ctx` first positional arg). Use
  `@app.command()` with `typer.Option(...)` directly.
- **Default arg trick is idiomatic Python**: see
  https://docs.python-guide.org/writing/gotchas/#late-binding-closures

## Out of scope

- 1 remaining skip in test_v2_daily_skill.py: `test_daily_command_surface_suggestions_via_skill`
  Skip was already removed; test PASSES.
- Total v2 graph recovery: 100% of v2 tests unskipped (only stale
  test_v2_e2e_smoke.py placeholder remains at 0 tests).
