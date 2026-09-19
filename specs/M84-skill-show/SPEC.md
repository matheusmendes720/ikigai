---
name: M84-skill-show
description: life skill-show <name> introspection - shows full manifest details for a single skill
owner: matheus-mendes
status: DONE
milestone: M84
estimated_cost_usd: 0.05
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
---

# M84 - life skill-show <name> CLI command

## Context

After M78 (`life skill-list`) users could see all skills but not the
details of a single one without opening the manifest file directly.
Added `skill-show` as the introspection complement.

## What changed

### interfaces/cli/v2.py

- Added `register_skill_show(app)` that registers `skill-show` command.
- Loads manifest via `load_skill_manifest(name)`, returns JSON or
  pretty-printed human-readable view.
- Empty manifest = "not found" error with non-zero exit.
- `_print_skill_human()` helper for the human view.

### tests/test_skill_show_cli.py (NEW)

5 tests:
- Human-readable output (header, entry_point, actor, fires_taskdog)
- JSON output structure
- Not-found error path
- Inputs section rendering
- Metadata section rendering

## Acceptance

- [x] `python -m interfaces.cli.v2 skill-show ikigai-quarterly` works
- [x] `python -m interfaces.cli.v2 skill-show <name> --json` emits JSON
- [x] Missing skill returns non-zero exit + error JSON
- [x] 5/5 unit tests PASS
- [x] Drift 18/18 PASS
- [x] Root 331 PASS + 27 SKIP (was 326, +5 new tests)

## Lessons

- **Lazy imports defeat monkeypatch**: `load_skill_manifest` is
  imported inside the function body, so patching
  `interfaces.cli.v2.load_skill_manifest` fails with AttributeError.
  Patch the SOURCE module (`interfaces.cli.invoke_skill`) instead.
- **Empty dict vs None return**: `load_skill_manifest` returns `{}`
  for missing files (not None). Check `if not manifest` not
  `if manifest is None`.
- **v2 Typer app is separate**: `interfaces.cli.v2.app` is not added
  to the main `life` CLI's `app`. To run `skill-show`, use
  `python -m interfaces.cli.v2` (not `python -m life.cli.cli`).
  M78 register_invoke_skill wiring gap tracked separately.
