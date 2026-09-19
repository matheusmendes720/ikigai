---
name: M85-v2-subcommand-wiring
description: Wire interfaces.cli.v2 Typer sub-app into main life CLI under `life v2`
owner: matheus-mendes
status: DONE
milestone: M85
estimated_cost_usd: 0.05
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
---

# M85 - life v2 subcommand wiring (M78 wiring fix)

## Context

M78 added `invoke-skill` + `skill-list` to `interfaces.cli.v2.app`
(separate Typer app), but `life.cli.cli` never registered it.
M84 added `skill-show` to the same v2 app, also unwired.

This meant users had to use `python -m interfaces.cli.v2` separately
instead of `python -m life.cli.cli`. M85 closes this gap.

## What changed

### life/cli/cli.py

Added one line block:
```python
from interfaces.cli.v2 import app as v2_app
app.add_typer(v2_app, name="v2")
```

Now `python -m life.cli.cli v2` exposes:
- `life v2 plan` - Plan D meta-planner
- `life v2 invoke-skill <name>` - W3.5/W3.6 skill runner
- `life v2 skill-list` - introspection: list all skills
- `life v2 skill-show <name>` - introspection: skill details

### tests/test_life_task_cli.py

Added 3 tests:
- `test_v2_subcommand_registered` - all 3 commands in `v2 --help`
- `test_v2_skill_list_via_life_cli` - JSON output
- `test_v2_skill_show_via_life_cli` - human-readable output

## Acceptance

- [x] `python -m life.cli.cli v2 --help` shows all 4 v2 commands
- [x] `python -m life.cli.cli v2 skill-show ikigai-quarterly` works
- [x] `python -m life.cli.cli v2 skill-list` works
- [x] 3/3 new tests PASS
- [x] Drift 18/18 PASS
- [x] Root 334 PASS + 27 SKIP (was 331, +3 new)

## Lessons

- **Typer `add_typer(other_app, name="x")` is the standard pattern
  for sub-commands.** Saves the user from needing to remember which
  module to invoke.
- **`from interfaces.cli.v2 import app as v2_app` works because v2.py
  registers all commands at module load time** (the `register_*()`
  calls run at module bottom). No lazy wiring needed.
